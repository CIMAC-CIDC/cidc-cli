"""Upload local files to CIDC's upload bucket"""
import os
import shutil
import subprocess
from datetime import datetime

from . import api
from . import gcloud
from .config import UPLOAD_WORKSPACE


def upload_assay(assay_type: str, xlsx_path: str):
    """
    Upload data for an assay.

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
    # Read the .xlsx file and make the API call
    # that initiates the upload job and grants object-level GCS access.
    with open(xlsx_path, 'rb') as xlsx_file:
        upload_info = api.initiate_upload(assay_type, xlsx_file)

    try:
        # Log in to gcloud (required for gsutil to work)
        gcloud.login()

        # Actually upload the assay
        _gsutil_assay_upload(upload_info, xlsx_path)
    except (Exception, KeyboardInterrupt) as e:
        api.job_failed(upload_info.job_id, upload_info.job_etag)
        raise e
    else:
        api.job_succeeded(upload_info.job_id, upload_info.job_etag)


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
        raise e
    else:
        _cleanup_workspace(workspace)


def _get_workspace_path():
    """Generate a unique upload workspace path"""
    return '%s.%s' % (UPLOAD_WORKSPACE, datetime.now())


def _populate_workspace(upload_info: api.UploadInfo, xlsx: str, workspace_dir: str):
    """
    Copy the local files into a nested file structure equivalent
    to the structure we want to create in GCS, rooted in the `workspace_dir`
    directory. Having the files organized in this manner allows
    us to upload all files in parallel using the "gsutil -m ...".
    """
    xlsx_dir = os.path.abspath(os.path.dirname(xlsx))
    for local_path, gcs_object in upload_info.url_mapping.items():
        source_path = os.path.join(xlsx_dir, local_path)
        gcs_prefix = gcs_object.rstrip(local_path)
        target_path = os.path.join(workspace_dir, gcs_prefix)
        os.makedirs(target_path)
        shutil.copy(source_path, target_path)


def _cleanup_workspace(workspace_dir: str):
    """Delete the upload workspace directory if it exists."""
    if os.path.exists(workspace_dir):
        shutil.rmtree(workspace_dir)
