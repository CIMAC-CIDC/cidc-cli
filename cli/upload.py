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
from .config import UPLOAD_WORKSPACE


def upload_assay(assay_type: str, xlsx_path: str):
    """
    Upload data for an assay.

    Orchestrator execution flow:
    1. Log in to gcloud. The CLI user must be authenticated with
       gcloud to be able to upload to GCS.
    2. Make an initiate_assay_upload request to the API. The API adds a
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
        with open(xlsx_path, 'rb') as xlsx_file:
            upload_info = api.initiate_assay_upload(assay_type, xlsx_file)

    except (Exception, KeyboardInterrupt) as e:
        _handle_upload_exc(e)

    try:
        # Actually upload the assay
        _gsutil_assay_upload(upload_info, xlsx_path)

        # Insert extra metadata for the upload, if any
        if upload_info.extra_metadata:
            with _open_file_mapping(upload_info.extra_metadata) as open_files:
                api.insert_extra_metadata(upload_info.job_id, open_files)

    except (Exception, KeyboardInterrupt) as e:
        # we need to notify api of a failed upload
        api.assay_upload_failed(upload_info.job_id, upload_info.job_etag)
        _handle_upload_exc(e)
        # _handle_upload_exc should raise, but raise for good measure
        # to guarantee execution stops here
        raise
    else:
        api.assay_upload_succeeded(upload_info.job_id, upload_info.job_etag)

    _poll_for_upload_completion(upload_info.job_id)

@contextmanager
def _open_file_mapping(extra_metadata: dict) -> Dict[str, BinaryIO]:
    """
    Given a dictionary mapping local paths to artifact uuids, return
    a dictionary mapping artifact uuids to open files.
    """
    open_files = {}
    for local_path, uuid in extra_metadata.items():
        open_files[uuid] = open(local_path, 'rb')
    try:
        yield open_files
    except:
        raise
    finally:
        for f in open_files.values():
            f.close()


def _gsutil_assay_upload(upload_info: api.UploadInfo, xlsx: str):
    """
    Upload local assay data to GCS using gsutil.
    """
    workspace = _get_workspace_path()

    try:
        # Create the required local directory structure
        # to support parallel uploads with gsutil
        _populate_workspace(upload_info, xlsx, workspace)

        # Construct the upload command
        gcs_bucket_uri = 'gs://%s' % upload_info.gcs_bucket
        gsutil_args = ["gsutil", "-m", "cp", "-r",
                       f'{workspace}/*', gcs_bucket_uri]

        # Run the upload command
        subprocess.check_output(gsutil_args)
    except (Exception, KeyboardInterrupt) as e:
        _cleanup_workspace(workspace)
        _handle_upload_exc(e)
    else:
        _cleanup_workspace(workspace)


def _get_workspace_path():
    """Generate a unique upload workspace path"""
    return '%s.%s' % (UPLOAD_WORKSPACE, datetime.now().isoformat())


def _populate_workspace(upload_info: api.UploadInfo, xlsx: str, workspace_dir: str):
    """
    Copy the local files into a nested file structure equivalent
    to the structure we want to create in GCS, rooted in the `workspace_dir`
    directory. Having the files organized in this manner allows
    us to upload all files in parallel using the "gsutil -m ...".
    """
    xlsx_dir = os.path.abspath(os.path.dirname(xlsx))
    for local_path, gcs_uri in upload_info.url_mapping.items():
        source_path = os.path.join(xlsx_dir, local_path)
        target_path = os.path.join(workspace_dir, gcs_uri)
        os.makedirs(os.path.dirname(target_path))
        shutil.copy(source_path, target_path)


def _cleanup_workspace(workspace_dir: str):
    """Delete the upload workspace directory if it exists."""
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir)


def _poll_for_upload_completion(job_id: int, timeout: int = 120, _did_timeout_test_impl=None):
    """Repeatedly check if upload finalization either failed or succeed"""
    click.echo("Finalizing upload", nl=False)

    cutoff = datetime.now().timestamp() + timeout

    did_timeout = _did_timeout_test_impl or (
        lambda: datetime.now().timestamp() >= cutoff)

    debug_info_message = f"Please include this info in your inquiry: (job_id={job_id})"

    while not did_timeout():
        status = api.poll_upload_merge_status(job_id)
        if status.retry_in:
            # Loop in one second increments, checking
            # for a timeout on each iteration.
            for _ in range(status.retry_in - 1):
                if did_timeout():
                    break
                click.echo(".", nl=False)
                time.sleep(1)
        elif status.status:
            if 'merge-completed' == status.status:
                click.echo(click.style("✓", fg="green", bold=True))
                click.echo(
                    "Upload succeeded. Visit the CIDC Portal "
                    "file browser to view your upload.")
            else:
                click.echo(click.style("✗", fg="red", bold=True))
                if status.status_details:
                    click.echo(
                        "Upload failed with the following message:")
                    click.echo()
                    click.echo(click.style(
                        status.status_details, fg="red", bold=True))
                    click.echo()
                else:
                    click.echo("Upload failed. ", nl=False)
                click.echo("Please contact a CIDC administrator "
                           "(cidc@jimmy.harvard.edu) if you need assistance.")
                click.echo(debug_info_message)
            return
        else:
            # we should never reach this code block
            raise

    click.echo(click.style('!!!', fg="yellow", bold=True))
    click.echo(
        "Upload timed out. Please contact a CIDC administrator "
        "(cidc@jimmy.harvard.edu) for assistance.")
    click.echo(debug_info_message)


def _handle_upload_exc(e: Exception):
    """Handle an exception thrown during an upload attempt."""
    if isinstance(e, KeyboardInterrupt):
        raise KeyboardInterrupt(f"Upload canceled.")
    raise type(e)(f"Upload failed: {e}") from e
