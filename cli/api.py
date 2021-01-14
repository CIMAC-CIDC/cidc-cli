"""Implements a client for the CIDC API running on Google App Engine"""
from functools import wraps
from collections import namedtuple
from typing import Optional, List, BinaryIO, NamedTuple, Dict, Callable

import click
import requests
import pyperclip

from . import auth, __version__
from .config import API_V2_URL, get_env


class ApiError(click.ClickException):
    pass


def _read_clipboard() -> str:
    """Read the current contents of the user's clipboard."""
    txt = pyperclip.paste()
    return txt


def _url(endpoint: str) -> str:
    """Append `endpoint` to the API's base URL"""
    endpoint = endpoint.lstrip("/")
    return f"{API_V2_URL}/{endpoint}"


def _error_message(response: requests.Response):
    try:
        message = response.json()["_error"]["message"]
        if response.status_code >= 500:
            message = f"API server error: {message}"
        if type(message) == dict and "errors" in message:
            message_lines = ["Multiple errors:"]
            message_lines.extend(
                [
                    click.style("* ", fg="red", bold=True) + message
                    for message in message["errors"]
                ]
            )
            return "\n".join(message_lines)
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
        "Authorization": f"Bearer {id_token}",
        # Also, include user agent with info about the CLI version
        "User-Agent": _USER_AGENT,
        **(headers or {}),
    }


def check_auth(id_token: str) -> Optional[str]:
    """Check if an id_token is valid by making a request to the base API URL."""
    response = requests.get(_url("/users/self"), headers=_with_auth(id_token=id_token))

    if response.status_code != 200:
        raise ApiError(_error_message(response))


def retry_with_reauth(api_request):
    """
    For a function `api_request` that returns a `Response` object, if that response
    has status code 403, prompt the user to enter a fresh ID token from the portal,
    and retry the request.
    """

    TOKEN_URL = f'https://{"staging" if get_env() != "prod" else ""}portal.cimac-network.org/assays/cli-instructions'

    @wraps(api_request)
    def wrapped(*args, **kwargs):
        retry = True
        while retry:
            res = api_request(*args, **kwargs)
            # If the error isn't auth-related, break out of the retry loop.
            if res.status_code != 401:
                break

            # Check if the user got an error because they lack sufficient permissions.
            # If so, don't prompt them for another token, since they'll just get the same error again.
            error_message = _error_message(res)
            if "is not authorized to upload" in error_message:
                raise ApiError(error_message)

            # Prompt the user for a new ID token.
            while True:
                click.prompt(
                    (
                        "\nCIDC reauthentication required. Please copy a fresh identity token from the Portal "
                        f"to your clipboard at this URL:\n\n\t{TOKEN_URL}\n\n"
                        "Then, press 'enter' to paste your copied token below"
                    ),
                    default="enter",
                    show_default=False,
                )
                try:
                    id_token = _read_clipboard()
                except:
                    click.echo(
                        f"\n\nError: could not read token from clipboard.\n",
                        color="red",
                    )
                    retry = False
                    break
                click.echo(f"\n{id_token}\n")

                # Validate and cache the user's ID token. If the token is invalid,
                # inform the user, and re-prompt them for an identity token.
                try:
                    auth.validate_and_cache_token(id_token)
                    kwargs["headers"] = _with_auth(kwargs.get("headers"), id_token)
                    break
                except auth.AuthError:
                    click.echo("The token you entered is invalid.")

            if not retry:
                break

            # Rewind any file pointers to avoid sending empty files on retry
            if "files" in kwargs:
                for file in kwargs["files"].values():
                    file.seek(0)

        # Handle error responses
        if res.status_code != 200:
            raise ApiError(_error_message(res))

        return res

    return wrapped


class _RequestsWithReauth:
    def __init__(self):
        """Build a `request` instance with all methods wrapped in the `retry_with_reauth` decorator."""
        pass

    def __getattribute__(self, name):
        return retry_with_reauth(getattr(requests, name))


_requests_with_reauth = _RequestsWithReauth()


def list_assays() -> List[str]:
    """Get a list of all supported assays."""
    response = requests.get(_url("/info/assays"))
    assays = response.json()
    return assays


def list_analyses() -> List[str]:
    """Get a list of all supported analyses."""
    response = requests.get(_url("/info/analyses"))
    assays = response.json()
    return assays


class UploadInfo(NamedTuple):
    """Container for data we expect to get back from an initiate upload request"""

    job_id: int
    job_etag: str
    gcs_bucket: str
    url_mapping: dict
    extra_metadata: list
    gcs_file_map: dict
    optional_files: list
    token: str


def initiate_upload(
    upload_type: str, xlsx_file: BinaryIO, is_analysis: bool = False
) -> UploadInfo:
    """
    Initiate an upload.

    Args:
        upload_type: the name of the API-supported assay
        xlsx_file: an open .xlsx file
        is_analysis: whether this is an analysis upload. If `False`,
                     then it's assumed to be an assay upload.

    Returns:
        UploadInfo: a mapping from local filepaths to GCS upload URIs,
        along with an upload job ID.
    """
    data = {"schema": upload_type}

    files = {"template": xlsx_file}

    endpoint = "upload_analysis" if is_analysis else "upload_assay"

    response = _requests_with_reauth.post(
        _url(f"/ingestion/{endpoint}"), headers=_with_auth(), data=data, files=files
    )

    try:
        upload_info = response.json()
        return UploadInfo(**upload_info)
    except:
        raise ApiError(
            "Cannot decode API response. You may need to update the CIDC CLI."
        )


def _update_upload_status(
    job_id: int, job_token: str, etag: str, status: str, gcs_file_map: Dict[str, str]
):
    """Update the status for an existing upload job"""
    url = _url(f"/upload_jobs/{job_id}")
    data = {"status": status, "gcs_file_map": gcs_file_map}

    if_match = {"If-Match": etag}
    response = _requests_with_reauth.patch(
        url, params={"token": job_token}, json=data, headers=_with_auth(if_match)
    )
    return response


def upload_succeeded(
    job_id: int, job_token: str, etag: str, gcs_file_map: Dict[str, str]
):
    """Tell the API that an upload job succeeded"""
    _update_upload_status(job_id, job_token, etag, "upload-completed", gcs_file_map)


def insert_extra_metadata(job_id: int, extra_metadata: Dict[str, BinaryIO]):
    """Insert extra metadata into the patch for the given job"""
    data = {"job_id": job_id}

    response = _requests_with_reauth.post(
        _url("/ingestion/extra-assay-metadata"),
        headers=_with_auth(),
        data=data,
        files=extra_metadata,
    )

    if response.ok:
        return response
    else:
        raise ApiError(_error_message(response))


def upload_failed(job_id: int, job_token: str, etag: str, gcs_file_map: Dict[str, str]):
    """Tell the API that an upload job failed"""
    _update_upload_status(job_id, job_token, etag, "upload-failed", gcs_file_map)


class MergeStatus(NamedTuple):
    status: Optional[str]
    status_details: Optional[str]
    retry_in: Optional[int]


def poll_upload_merge_status(job_id: int, job_token: str) -> MergeStatus:
    """Check the merge status of an upload job"""
    url = _url(f"/ingestion/poll_upload_merge_status/{job_id}")
    params = {"token": job_token}

    response = _requests_with_reauth.get(url, params=params, headers=_with_auth())

    merge_status = response.json()
    status = merge_status.get("status")
    status_details = merge_status.get("status_details")
    retry_in = merge_status.get("retry_in")

    if not (status or retry_in):
        raise ApiError("The server responded with an unexpected upload status message.")

    return MergeStatus(status, status_details, retry_in)
