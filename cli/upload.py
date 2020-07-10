"""Upload local files to CIDC's upload bucket"""
import os
import time
import shutil
import subprocess
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, BinaryIO

import click

from . import api
from . import gcloud


def run_upload(upload_type: str, xlsx_path: str, is_analysis: bool = False):
    """
    Upload data.

    Orchestrator execution flow:
    1. Log in to gcloud. The CLI user must be authenticated with
       gcloud to be able to upload to GCS.
    2. Make an initiate_upload request to the API. The API adds a
       record to the database tracking that the CLI user started an
       upload job, grants the CLI user write permissions to the CIDC
       upload bucket in GCS, and returns information needed to
       carry out the gsutil upload (like a mapping from local file paths
       to GCS URIs).
    3. Carry out the gsutil upload using the returned upload info.
    4. If the gsutil upload fails, alert the api that the job failed.
       Else, if the upload succeeds, alert the api that the job was
       successful.
    """
    # Log in to gcloud (required for gsutil to work)
    gcloud.login()

    try:
        # Read the .xlsx file and make the API call
        # that initiates the upload job and grants object-level GCS access.
        with open(xlsx_path, "rb") as xlsx_file:
            upload_info = api.initiate_upload(upload_type, xlsx_file, is_analysis)

    except (Exception, KeyboardInterrupt) as e:
        _handle_upload_exc(e)

    try:
        # Insert extra metadata for the upload, if any
        if upload_info.extra_metadata:
            with _open_file_mapping(
                upload_info.extra_metadata, xlsx_path
            ) as open_files:
                api.insert_extra_metadata(upload_info.job_id, open_files)

        # Actually upload the assay data
        _gsutil_assay_upload(upload_info, xlsx_path)
    except (Exception, KeyboardInterrupt) as e:
        # we need to notify api of a failed upload
        api.upload_failed(upload_info.job_id, upload_info.token, upload_info.job_etag)
        _handle_upload_exc(e)
        # _handle_upload_exc should raise, but raise for good measure
        raise
    else:
        api.upload_succeeded(
            upload_info.job_id, upload_info.token, upload_info.job_etag
        )

    _poll_for_upload_completion(upload_info.job_id, upload_info.token)


@contextmanager
def _open_file_mapping(extra_metadata: dict, base_path: str) -> Dict[str, BinaryIO]:
    """
    Given a dictionary mapping local paths to artifact uuids, return
    a dictionary mapping artifact uuids to open files.
    """
    base_dir = os.path.abspath(os.path.dirname(base_path))

    open_files = {}
    for source_path, uuid in extra_metadata.items():

        # if user wants us to get file from GCS
        # and we want it to be analysed for extra_md
        # we say we don't support it
        if source_path.startswith("gs://"):
            raise Exception(
                "File transfers from Google Cloud Storage are not supported for this assay type."
                f" Please download locally the files that you wish to upload ({source_path}),"
                " update the file paths in your metadata Excel file, and try again"
            )

        source_path = os.path.join(base_dir, source_path)
        open_files[uuid] = open(source_path, "rb")
    try:
        yield open_files
    except:
        raise
    finally:
        for f in open_files.values():
            f.close()


# This is how `gsutil` warns user when s/he sends large files.
# We don't want them to see that or enable `parallel_composite_upload_threshold`
# because composite files are problematic to download - see:
# https://cloud.google.com/storage/docs/gsutil/commands/cp#parallel-composite-uploads
_IGNORED_WARN_LINES = set(
    map(
        str.strip,
        """==> NOTE: You are uploading one or more large file(s), which would run
significantly faster if you enable parallel composite uploads. This
feature can be enabled by editing the
"parallel_composite_upload_threshold" value in your .boto
configuration file. However, note that if you do this large files will
be uploaded as `composite objects
<https://cloud.google.com/storage/docs/composite-objects>`_,which
means that any user who downloads such objects will need to have a
compiled crcmod installed (see "gsutil help crcmod"). This is because
without a compiled crcmod, computing checksums on composite objects is
so slow that gsutil disables downloads of composite objects.""".split(
            "\n"
        ),
    )
)


def _start_procs(upload_info: api.UploadInfo, xlsx: str) -> list:
    """
    Starts multiple "gsutil cp" subprocesses.
    Returns a list of subprocess.Popen objects
    """
    procs = []

    for src, dst in _compose_file_mapping(upload_info, xlsx):

        # Construct the upload command
        gsutil_args = ["gsutil", "-m", "cp", src, dst]

        try:
            # Run the upload command
            procs.append(
                subprocess.Popen(
                    gsutil_args,
                    universal_newlines=True,
                    bufsize=1,  # line buffered so we can read output line by line
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                )
            )

        except OSError as e:

            # stopping already created processes
            for p in procs:
                p.kill()

            _handle_upload_exc(e)
    return procs


def _wait_for_upload(procs: list) -> bool:
    """
    Waits for all subprocesses and prints their stderr streams.
    Returns bool - if an error has occurred during any if uploads
    """

    finished = set()
    errored = False
    while len(finished) != len(procs) and not errored:
        for i, p in enumerate(procs):

            if i in finished:
                continue

            if p.poll() != None:
                finished.add(i)

                if p.returncode != 0:
                    errored = True

            errline = p.stderr.readline()

            # skipping "large file" warnings
            if errline.strip() in _IGNORED_WARN_LINES:
                continue

            if errline and len(errline) > 2:  # skipping '* ' spinner lines

                # changing output from always "[0/1 files]" - due to manual
                # parallelization of gsutil to "[x/y files]"
                if errline.split("]", 1)[0].endswith("/1 files"):
                    errline = errline.split("]", 1)[1]
                print(
                    f"[{len(finished)}/{len(procs)} done] {i+1}: {p.args[-2]}: "
                    + errline,
                    end="",
                )

    print(f"[{len(finished)}/{len(procs)} done]")
    return errored


def _gsutil_assay_upload(upload_info: api.UploadInfo, xlsx: str):
    """
    Upload local assay data to GCS using gsutil.
    """

    procs = _start_procs(upload_info, xlsx)

    err = _wait_for_upload(procs)

    if err:
        for p in procs:

            if p.poll() != 0:

                print(f"\nFailed uploading {p.args[3]}.")

                print(f"Stopping other uploads...")
                # stopping all other processes
                for other_p in procs:
                    if p != other_p:
                        other_p.kill()

                e = Exception(f"Couldn't upload all files.")
                _handle_upload_exc(e)
                # _handle_upload_exc should raise, but raise for good measure
                # to guarantee execution stops here
                raise e


def _compose_file_mapping(upload_info: api.UploadInfo, xlsx: str):
    """
    Returns a list of (source_path, target uri) pairs for all 
    the files from the upload info relative to the `work dir` 
    that is xlsx file locaction. If s source_path is a GCS uri,
    it will return it w/o change.
    """
    res = []
    missing_files = []
    xlsx_dir = os.path.abspath(os.path.dirname(xlsx))
    for source_path, gcs_uri in upload_info.url_mapping.items():

        # if we're not copying from GCS to GCS, then
        # resolve local path against .xslx file dir
        if not source_path.startswith("gs://"):
            source_path = os.path.join(xlsx_dir, source_path)

            if not os.path.isfile(source_path):
                missing_files.append(source_path)

        res.append([source_path, f"gs://{upload_info.gcs_bucket}/{gcs_uri}"])

    if missing_files:
        raise Exception(f'Could not locate files: {", ".join(missing_files)}')

    return res


def _poll_for_upload_completion(
    job_id: int, job_token: str, timeout: int = 600, _did_timeout_test_impl=None
):
    """Repeatedly check if upload finalization either failed or succeed"""
    click.echo("Finalizing upload", nl=False)

    cutoff = datetime.now().timestamp() + timeout

    did_timeout = _did_timeout_test_impl or (
        lambda: datetime.now().timestamp() >= cutoff
    )

    debug_info_message = f"Please include this info in your inquiry: (job_id={job_id})"

    while not did_timeout():
        status = api.poll_upload_merge_status(job_id, job_token)
        if status.retry_in:
            # Loop in one second increments, checking
            # for a timeout on each iteration.
            for _ in range(status.retry_in - 1):
                if did_timeout():
                    break
                click.echo(".", nl=False)
                time.sleep(1)
        elif status.status:
            if "merge-completed" == status.status:
                click.echo(click.style("✓", fg="green", bold=True))
                click.echo(
                    "Upload succeeded. Visit the CIDC Portal "
                    "file browser to view your upload."
                )
            else:
                click.echo(click.style("✗", fg="red", bold=True))
                if status.status_details:
                    click.echo("Upload failed with the following message:")
                    click.echo()
                    click.echo(click.style(status.status_details, fg="red", bold=True))
                    click.echo()
                else:
                    click.echo("Upload failed. ", nl=False)
                click.echo(
                    "Please contact a CIDC administrator "
                    "(cidc@jimmy.harvard.edu) if you need assistance."
                )
                click.echo(debug_info_message)
            return
        else:
            # we should never reach this code block
            raise

    click.echo(click.style("!!!", fg="yellow", bold=True))
    click.echo(
        "Upload timed out. Please contact a CIDC administrator "
        "(cidc@jimmy.harvard.edu) for assistance."
    )
    click.echo(debug_info_message)


def _handle_upload_exc(e: Exception):
    """Handle an exception thrown during an upload attempt."""
    if isinstance(e, KeyboardInterrupt):
        raise KeyboardInterrupt(f"Upload canceled.")
    raise type(e)(f"Upload failed: {e}") from e
