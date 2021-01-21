"""Upload local files to CIDC's upload bucket"""
import os
import time
import subprocess
from contextlib import contextmanager
from datetime import datetime
from typing import BinaryIO, Dict, Generator, List, Optional, Tuple

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
        click.secho("> preparing upload job via the CIDC API", dim=True)
        # Read the .xlsx file and make the API call
        # that initiates the upload job and grants object-level GCS access.
        with open(xlsx_path, "rb") as xlsx_file:
            upload_info = api.initiate_upload(upload_type, xlsx_file, is_analysis)

    except (Exception, KeyboardInterrupt) as e:
        _handle_upload_exc(e)

    try:
        # Insert extra metadata for the upload, if any
        if upload_info.extra_metadata:
            click.secho(
                f"> pulling additional metadata from files staged for upload", dim=True
            )
            with _open_file_mapping(
                upload_info.extra_metadata, xlsx_path
            ) as open_files:
                api.insert_extra_metadata(upload_info.job_id, open_files)

        # Actually upload the assay data
        click.secho(f"> initiating GCS upload", dim=True)
        gcs_file_map = _gsutil_assay_upload(upload_info, xlsx_path)
    except (Exception, KeyboardInterrupt) as e:
        # we need to notify api of a failed upload
        api.upload_failed(
            upload_info.job_id,
            upload_info.token,
            upload_info.job_etag,
            upload_info.gcs_file_map,
        )
        _handle_upload_exc(e)
        # _handle_upload_exc should raise, but raise for good measure
        raise
    else:
        api.upload_succeeded(
            upload_info.job_id, upload_info.token, upload_info.job_etag, gcs_file_map
        )

    click.secho("> finalizing upload via the CIDC API", dim=True)
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


def _start_procs(src_dst_pairs: list) -> Generator[subprocess.Popen, None, None]:
    """
    Starts multiple "gsutil cp" subprocesses.
    
    src_dst_pairs: a list of tuples (local file path, target GCS path)

    Yields subprocess.Popen objects
    """
    procs = []

    src_dst_stack = list(src_dst_pairs)

    while True:
        try:
            src, dst = src_dst_stack.pop()
        except IndexError:
            return

        # Construct the upload command
        gsutil_args = ["gsutil", "cp", src, dst]

        try:
            # Run the upload command
            p = subprocess.Popen(
                gsutil_args,
                universal_newlines=True,
                bufsize=1,  # line buffered so we can read output line by line
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            procs.append(p)
            yield p

        except OSError as e:
            # stopping already created processes
            for p in procs:
                p.kill()
            _handle_upload_exc(e)

        except Exception as e:
            # stopping already created processes
            for p in procs:
                p.kill()
            _handle_upload_exc(e)


def _wait_for_upload(
    procs: list, total: int, optional_files: List[str]
) -> Optional[str]:
    """
    Waits for all subprocesses and click.echos their stderr streams.
    Returns Optional[str] - an error message if an error has occurred during any if uploads
    """

    # First we account all already successfully finished procs
    finished = set([i for i, p in enumerate(procs) if p.poll() == 0])

    error = None

    # GCS upload errors are generally spread across two lines.
    # Since we consume stderr one line at a time will polling upload processes,
    # we need to save the previous stderr line for each process in order
    # to reconstruct a full GCS upload error.
    prev_errlines = {}
    while len(finished) != len(procs) and not error:
        for i, p in enumerate(procs):
            if i in finished:
                continue

            # start building user feedback for this process
            message = f"[{len(finished)}/{total} done] "
            message += click.style(f"(file {i + 1}) ", fg="bright_blue")

            # read stderr for this process
            errline = p.stderr.readline()

            if p.poll() is not None:
                p.stderr.close()
                finished.add(i)

                if p.returncode != 0:
                    message += click.style("!!! upload error !!! ", fg="red", bold=True)
                    message += p.args[-2]
                    click.echo(message)
                    # Reconstruct multiline GCS error message
                    error = f"{prev_errlines.get(i, '')}{errline}"
                    break

            # skipping "large file" warnings
            if errline.strip() in _IGNORED_WARN_LINES:
                continue

            if (
                errline
                and len(errline) > 2  # skip '* ' spinner lines
                and errline.split("]", 1)[0].endswith(
                    "1 files"
                )  # include gsutil output with upload progress
            ):
                message += errline.split("]", 1)[1].rstrip()
                message += f" {p.args[-2]}"
                click.echo(message)
            else:
                # This might be the first line of a multiline error message,
                # so save it.
                prev_errlines[i] = errline

    return error


# default from `gsutil -m` but maybe better to load from env
MAX_GSUTIL_PARALLEL_PROCESS = 12


def _gsutil_assay_upload(upload_info: api.UploadInfo, xlsx: str) -> Dict[str, str]:
    """
    Upload local assay data to GCS using gsutil.
    Return modified GCS file map with missing files removed
    """

    upload_pairs, skipping = _compose_file_mapping(upload_info, xlsx)
    file_count = len(upload_pairs)
    for s in skipping:
        upload_info.gcs_file_map.pop(s, "")

    proc_iter = _start_procs(upload_pairs)
    procs = []
    all_uploads_have_run = False
    while not all_uploads_have_run:

        # Here we start with just 1 parallel process and gradually
        # increase that to MAX_GSUTIL_PARALLEL_PROCESS doubling the number every time.
        try:
            current_count = len(procs) or 1  # 1 is for starters
            how_many_to_add = min(current_count, MAX_GSUTIL_PARALLEL_PROCESS)
            for _ in range(how_many_to_add):
                procs.append(next(proc_iter))
        except StopIteration:
            all_uploads_have_run = True

        err = _wait_for_upload(procs, file_count, upload_info.optional_files)

        if err:
            for p in procs:

                if p.poll() != 0:

                    # stopping all other processes
                    for other_p in procs:
                        if p != other_p:
                            other_p.kill()

                    click.echo(
                        f"\nGCS upload failed on {p.args[-2]} with the following message:\n"
                    )
                    prev_err = prev_errlines.get(i, "")
                    click.secho(f"{prev_err}{errline}", fg="red")

                    raise click.Abort()

    click.echo(
        f"[{file_count}/{file_count} done] All files uploaded to GCS and staged for ingestion."
    )

    return upload_info.gcs_file_map


def _compose_file_mapping(
    upload_info: api.UploadInfo, xlsx: str
) -> Tuple[Dict[str, str], List[str]]:
    """
    Returns a list of (source_path, target uri) pairs for all 
    the files from the upload info relative to the `work dir` 
    that is xlsx file locaction. If s source_path is a GCS uri,
    it will return it w/o change.
    """
    res = []
    missing_optional_files = []
    missing_required_files = []
    xlsx_dir = os.path.abspath(os.path.dirname(xlsx))
    for source_path, gcs_uri in upload_info.url_mapping.items():

        # if we're not copying from GCS to GCS, then
        # resolve local path against .xslx file dir
        if not source_path.startswith("gs://"):
            source_path = os.path.join(xlsx_dir, source_path)

            if not os.path.isfile(source_path):
                if source_path in upload_info.optional_files:
                    missing_optional_files.append(gcs_uri)
                    continue
                else:
                    missing_required_files.append(source_path)

        # gsutil treats brackets in a gs-uri as a character set
        # see https://cloud.google.com/storage/docs/gsutil/addlhelp/WildcardNames#other-wildcard-characters
        # this replaces opening with a generic wildcard, which should map to only a single file
        else:
            if "[" in source_path and "]" in source_path:
                source_path = source_path.replace("[", "?")

            sub = subprocess.run(["gsutil", "ls", source_path], capture_output=True)
            if sub.returncode != 0:
                if source_path.replace("?", "[") in upload_info.optional_files:
                    missing_optional_files.append(gcs_uri)
                    continue
                else:
                    missing_required_files.append(source_path)

        res.append([source_path, f"gs://{upload_info.gcs_bucket}/{gcs_uri}"])

    if missing_required_files:
        raise Exception(
            f'Could not locate the following required files:\n{", ".join(missing_required_files)}'
        )

    return res, missing_optional_files


def _poll_for_upload_completion(
    job_id: int, job_token: str, timeout: int = 600, _did_timeout_test_impl=None
):
    """Repeatedly check if upload finalization either failed or succeed"""
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
                if status.status_details:
                    click.echo("Upload failed with the following message:")
                    click.echo()
                    click.secho(status.status_details, fg="red", bold=True)
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

    click.secho("!!!", fg="yellow", bold=True)
    click.echo(
        "Upload timed out. Please contact a CIDC administrator "
        "(cidc@jimmy.harvard.edu) for assistance."
    )
    click.echo(debug_info_message)


def _handle_upload_exc(e: Exception):
    """Handle an exception thrown during an upload attempt."""
    if isinstance(e, KeyboardInterrupt):
        raise KeyboardInterrupt(f"Upload canceled.")
    raise type(e)(f"Upload failed.\n{e}") from e
