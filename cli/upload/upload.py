"""
This is a simple command-line tool that allows users to upload data to our google storage
"""
# pylint: disable=R0903
import datetime
import subprocess
from typing import List, NamedTuple, Tuple

from cidc_utils.requests import SmartFetch

from constants import EVE_URL
from utilities.cli_utilities import (
    get_valid_dir,
    select_assay_trial,
    option_select_framework,
    get_files,
    create_payload_objects,
    user_prompt_yn,
    Selections,
)

EVE_FETCHER = SmartFetch(EVE_URL)


class RequestInfo(NamedTuple):
    """
    Data class to hold information for upload operation.

    Arguments:
        NamedTuple {NamedTuple} -- NamedTuple class.
    """

    mongo_data: dict
    eve_token: str
    headers: dict
    files_uploaded: List[dict]


def update_job_status(
    status: bool, request_info: RequestInfo, message: str = None
) -> None:
    """
    Updates the status of the job in MongoDB, either with the URIs if the upload
    was succesfull, or with the error message if it failed.

    Arguments:
        status {bool} -- True if upload succeeds, false otherwise.
        request_info {RequestInfo} -- Dict containing information about the request
        message {str} -- If upload failed, contains error.
    """
    payload = None
    if status:
        payload = {
            "status": {"progress": "Completed", "message": ""},
            "end_time": datetime.datetime.now().isoformat(),
        }
    else:
        payload = {"status": {"progress": "Aborted", "message": message}}

    try:
        EVE_FETCHER.patch(
            endpoint="ingestion",
            item_id=request_info.mongo_data["_id"],
            _etag=request_info.mongo_data["_etag"],
            token=request_info.eve_token,
            json=payload,
        )
    except RuntimeError as error:
        print("Status update failed: %s" % error)


def upload_files(directory: str, request_info: RequestInfo) -> str:
    """
    Launches the gsutil command using subprocess and uploads files to the
    google bucket.

    Arguments:
        directory {str} -- Directory of the files you want to upload.
        request_info {RequestInfo} -- Object containing the details for the upload operation.
    Returns:
        str -- Returns the google URIs of the newly uploaded files.
    """
    try:
        gsutil_args = ["gsutil"]
        google_path = request_info.headers["google_folder_path"]
        if len(request_info.files_uploaded) > 3:
            gsutil_args.append("-m")

        # Insert records into a staging area for later processing
        gsutil_args.extend(
            [
                "cp",
                "-r",
                directory,
                "gs://" + google_path + "/" + request_info.mongo_data["_id"],
            ]
        )
        subprocess.check_output(gsutil_args)
        update_job_status(True, request_info)
        return request_info.mongo_data["_id"]
    except subprocess.CalledProcessError as error:
        print("Error: Upload to Google failed: " + str(error))
        update_job_status(False, request_info, error)
        return None


def upload_pipeline(
    assay_response: dict, selections: Selections
) -> Tuple[str, dict, List[str]]:
    """
    Upload for files going to a WDL pipeline

    Arguments:
        assay_response {dict} -- Response to the chosen assay being queried
        selections {Selections} -- User selections for assay/trial.

    Returns:
        Tuple[str, dict, List[str]] -- Directory path, upload payload, file names.
    """
    non_static_inputs = assay_response["non_static_inputs"]
    sample_ids = selections.selected_trial["samples"]
    file_upload_dict, upload_dir = get_files(sample_ids, non_static_inputs)

    payload = {
        "number_of_files": len(file_upload_dict),
        "status": {"progress": "In Progress"},
        "files": create_payload_objects(
            file_upload_dict, selections.selected_trial, selections.selected_assay
        ),
    }

    return upload_dir, payload, [file_upload_dict[key] for key in file_upload_dict]


def upload_np(
    assay_response: dict, selections: Selections
) -> Tuple[str, dict, List[str]]:
    """
    Upload for non-pipeline files.

    Arguments:
        assay_response {dict} -- API response to assay endpoint query.
        selections {Selections} -- User selections.

    Returns:
        Tuple[str, dict, List[str]] -- Directory path, upload payload, file names.
    """

    non_static_inputs = assay_response["non_static_inputs"]
    upload_dir, files_to_upload = get_valid_dir(is_download=False)
    file_copy = files_to_upload[:]
    upload_list = []

    while file_copy:
        for inp in non_static_inputs:
            selection = option_select_framework(
                file_copy, "Please choose the file which corresponds to: %s" % inp
            )
            # save selection, then delete from list.
            upload_list.append(
                {
                    "assay": selections.selected_assay["assay_id"],
                    "trial": selections.selected_trial["_id"],
                    "file_name": file_copy[selection - 1],
                    "mapping": inp,
                }
            )
            del file_copy[selection - 1]

    payload = {
        "number_of_files": len(upload_list),
        "status": {"progress": "In Progress"},
        "files": upload_list,
    }

    return upload_dir, payload, files_to_upload


def run_upload_process() -> None:
    """
    Function responsible for guiding the user through the upload process
    """

    selections = select_assay_trial("This is the upload function\n")

    if not selections:
        return

    # Have user make their selections
    eve_token = selections.eve_token
    selected_assay = selections.selected_assay

    # Query the selected assay ID to get the inputs.
    assay_r = EVE_FETCHER.get(
        token=eve_token, endpoint="assays/" + selected_assay["assay_id"]
    ).json()

    upload_dir = None
    payload = None
    file_list = None

    if user_prompt_yn("Is this data the input to a WDL pipeline? [Y/N] "):
        upload_dir, payload, file_list = upload_pipeline(assay_r, selections)
    else:
        upload_dir, payload, file_list = upload_np(assay_r, selections)

    response_upload = EVE_FETCHER.post(
        token=selections.eve_token, endpoint="ingestion", json=payload, code=201
    )

    req_info = RequestInfo(
        response_upload.json(), selections.eve_token, response_upload.headers, file_list
    )

    job_id = upload_files(upload_dir, req_info)
    print("Uploaded, your ID is: " + job_id)
