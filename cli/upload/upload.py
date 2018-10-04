"""
This is a simple command-line tool that allows users to upload data to our google storage
"""
import datetime
import subprocess
from os import environ as env
from typing import List, NamedTuple

import requests
from cidc_utils.requests import SmartFetch
from simplejson.errors import JSONDecodeError

from constants import EVE_URL
from utilities.cli_utilities import (
    get_valid_dir,
    select_assay_trial,
    option_select_framework,
    get_files,
    create_payload_objects
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
    status: bool, mongo_data: dict, eve_token: str, message: str = None
) -> None:
    """
    Updates the status of the job in MongoDB, either with the URIs if the upload
    was succesfull, or with the error message if it failed.

    Arguments:
        status {bool} -- True if upload succeeds, false otherwise.
        mongo_data {dict} -- The response object from the mongo insert.
        eve_token {str} -- Token for accessing EVE API.
        google_data {[dict]} -- If successfull, list of dicts of the file
        names and their associated uris.
        message {str} -- If upload failed, contains error.
    """
    if status:
        url = None
        if env.get("JENKINS"):
            url = (
                "http://"
                + env.get("INGESTION_API_SERVICE_HOST")
                + ":"
                + env.get("INGESTION_API_SERVICE_PORT")
            )
        else:
            url = EVE_URL

        print(url)
        res = requests.post(
            url + "/ingestion/" + mongo_data["_id"],
            json={
                "status": {"progress": "Completed", "message": ""},
                "end_time": datetime.datetime.now().isoformat(),
            },
            headers={
                "If-Match": mongo_data["_etag"],
                "Authorization": "Bearer {}".format(eve_token),
                "X-HTTP-Method-Override": "PATCH",
            },
        )

        if not res.status_code == 200:
            print("Error! Patching unsuccesful")
            print(res.reason)
            try:
                print(res.json())
            except JSONDecodeError:
                print("No valid JSON response")

    else:
        requests.post(
            EVE_URL + "/ingestion/" + mongo_data["_id"],
            json={"status": {"progress": "Aborted", "message": message}},
            headers={
                "If-Match": mongo_data["_etag"],
                "Authorization": "Bearer {}".format(eve_token),
                "X-HTTP-Method-Override": "PATCH",
            },
        )


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
        google_url = request_info.headers["google_url"]
        google_path = request_info.headers["google_folder_path"]
        if len(request_info.files_uploaded) > 3:
            gsutil_args.append("-m")

        # Insert records into a staging area for later processing
        gsutil_args.extend(
            [
                "cp",
                "-r",
                directory,
                google_url + google_path + "staging/" + request_info.mongo_data["_id"],
            ]
        )
        subprocess.check_output(gsutil_args)
        update_job_status(True, request_info.mongo_data, request_info.eve_token)
        return request_info.mongo_data["_id"]
    except subprocess.CalledProcessError as error:
        print("Error: Upload to Google failed: " + str(error))
        update_job_status(False, request_info.mongo_data, request_info.eve_token, error)
        return None


def run_upload_process() -> None:
    """
    Function responsible for guiding the user through the upload process
    """

    selections = select_assay_trial("This is the upload function\n")

    if not selections:
        return

    # Have user make their selections
    eve_token = selections.eve_token
    selected_trial = selections.selected_trial
    selected_assay = selections.selected_assay

    # Query the selected assay ID to get the inputs.
    assay_r = EVE_FETCHER.get(
        token=eve_token, endpoint="assays/" + selected_assay["assay_id"]
    ).json()

    non_static_inputs = assay_r["non_static_inputs"]
    sample_ids = selected_trial["samples"]
    file_upload_dict, upload_dir = get_files(sample_ids, non_static_inputs)

    payload = {
        "number_of_files": len(file_upload_dict),
        "status": {"progress": "In Progress"},
        "files": create_payload_objects(
            file_upload_dict, selected_trial, selected_assay
        ),
    }

    response_upload = EVE_FETCHER.post(
        token=eve_token, endpoint="ingestion", json=payload, code=201
    )

    req_info = RequestInfo(
        [file_upload_dict[key] for key in file_upload_dict],
        response_upload.json(),
        eve_token,
        response_upload.header,
    )

    # Execute uploads
    job_id = upload_files(upload_dir, req_info)

    print("Uploaded, your ID is: " + job_id)


def run_upload_np() -> None:
    """
    Function responsible for guiding the user through the upload process
    """

    selections = select_assay_trial("This is the upload function\n")

    if not selections:
        return

    # Have user make their selections
    selected_trial = selections.selected_trial
    selected_assay = selections.selected_assay

    # Query the selected assay ID to get the inputs.
    assay_r = EVE_FETCHER.get(
        token=selections.eve_token, endpoint="assays/" + selected_assay["assay_id"]
    ).json()

    non_static_inputs = assay_r["non_static_inputs"]
    upload_dir, files_to_upload = get_valid_dir(is_download=False)

    if not len(files_to_upload) % len(non_static_inputs) == 0:
        print(
            "Not enough files detected for this upload operation. This upload requires %s files "
            "per upload"
            % len(non_static_inputs)
        )
        return

    print(
        "You are uploading a data format which required %s files per upload. Follow the prompts "
        "and select the corresponding files."
        % len(non_static_inputs)
    )

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
                    "assay": selected_assay["assay_id"],
                    "trial": selected_trial["_id"],
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

    response_upload = EVE_FETCHER.post(
        token=selections.eve_token, endpoint="ingestion", json=payload, code=201
    )

    req_info = RequestInfo(
        response_upload.json(),
        selections.eve_token,
        response_upload.headers,
        files_to_upload,
    )

    # Execute uploads
    job_id = upload_files(upload_dir, req_info)
    print("Uploaded, your ID is: " + job_id)