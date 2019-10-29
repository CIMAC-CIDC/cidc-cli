"""Implements a client for the CIDC API running on Google App Engine"""
from typing import Optional, List, BinaryIO, NamedTuple, Dict

import click
import requests

from . import auth, __version__
from .config import API_V2_URL


class ApiError(click.ClickException):
    pass


def _url(endpoint: str) -> str:
    """Append `endpoint` to the API's base URL"""
    endpoint = endpoint.lstrip("/")
    return f"{API_V2_URL}/{endpoint}"


def _error_message(response: requests.Response):
    try:
        message = response.json()['_error']['message']
        if response.status_code >= 500:
            message = f"API server error: {message}"
        if type(message) == dict and "errors" in message:
            return 'Multiple errors:\n  ' + '\n  '.join(map(str, message["errors"]))
        else:
            return str(message)
    except:
        return f"API server encountered an error processing your request {response.status_code}"


_USER_AGENT = f"cidc-cli/{__version__}"


def _with_auth(headers: dict = None, id_token: str = None) -> dict:
    """Add an id token to the given headers"""
    if not id_token:
        id_token = auth.get_id_token()
    return {
        **(headers or {}),
        'Authorization': f'Bearer {id_token}',
        # Also, include user agent with info about the CLI version
        'User-Agent': _USER_AGENT
    }


def check_auth(id_token: str) -> Optional[str]:
    """Check if an id_token is valid by making a request to the base API URL."""
    response = requests.get(_url('/'), headers=_with_auth(id_token=id_token))

    if response.status_code != 200:
        raise ApiError(_error_message(response))

    # No errors, so the token is valid
    return None


def list_assays() -> List[str]:
    """Get a list of all supported assays."""
    response = requests.get(_url('/info/assays'))
    assays = response.json()
    return assays


class UploadInfo(NamedTuple):
    """Container for data we expect to get back from an initiate upload request"""
    job_id: int
    job_etag: str
    gcs_bucket: str
    url_mapping: dict
    extra_metadata: list


def initiate_assay_upload(assay_name: str, xlsx_file: BinaryIO) -> UploadInfo:
    """
    Initiate an assay upload.

    Args:
        assay_name: the name of the API-supported assay
        xlsx_file: an open .xlsx file

    Returns:
        UploadInfo: a mapping from local filepaths to GCS upload URIs,
        along with an upload job ID.
    """
    data = {'schema': assay_name}

    files = {'template': xlsx_file}

    response = requests.post(_url('/ingestion/upload_assay'),
                             headers=_with_auth(), data=data, files=files)

    if response.status_code != 200:
        raise ApiError(_error_message(response))

    try:
        upload_info = response.json()
        return UploadInfo(
            upload_info['job_id'],
            upload_info['job_etag'],
            upload_info['gcs_bucket'],
            upload_info['url_mapping'],
            upload_info['extra_metadata']
        )
    except:
        raise ApiError(
            "Cannot decode API response. You may need to update the CIDC CLI.")


def _update_assay_upload_status(job_id: int, etag: str, status: str):
    """Update the status for an existing assay upload job"""
    url = _url(f'/assay_uploads/{job_id}')
    data = {'status': status}
    if_match = {'If-Match': etag}
    response = requests.patch(url, json=data, headers=_with_auth(if_match))

    if response.status_code != 200:
        raise ApiError(_error_message(response))


def assay_upload_succeeded(job_id: int, etag: str):
    """Tell the API that an assay upload job succeeded"""
    _update_assay_upload_status(job_id, etag, 'upload-completed')


def insert_extra_metadata(job_id: int, extra_metadata: Dict[str, BinaryIO]):
    """Insert extra metadata into the patch for the given job"""
    data = {'job_id': job_id}

    response = requests.post(_url('/ingestion/extra-assay-metadata'),
                             headers=_with_auth(), data=data, files=extra_metadata)

    if response.status_code != 200:
        raise ApiError(_error_message(response))


def assay_upload_failed(job_id: int, etag: str):
    """Tell the API that an assay upload job failed"""
    _update_assay_upload_status(job_id, etag, 'upload-failed')


class MergeStatus(NamedTuple):
    status: Optional[str]
    status_details: Optional[str]
    retry_in: Optional[int]


def poll_upload_merge_status(job_id: int) -> MergeStatus:
    """Check the merge status of an upload job"""
    url = _url(f'/ingestion/poll_upload_merge_status')
    params = dict(id=job_id)
    response = requests.get(url, params=params, headers=_with_auth())

    if response.status_code != 200:
        raise ApiError(_error_message(response))

    merge_status = response.json()
    status = merge_status.get("status")
    status_details = merge_status.get("status_details")
    retry_in = merge_status.get("retry_in")

    if not (status or retry_in):
        raise ApiError(
            "The server responded with an unexpected upload status message.")

    return MergeStatus(status, status_details, retry_in)
