#!/usr/bin/env python
"""
This is a simple command-line tool that allows users to upload data to our google storage
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

import collections
import datetime
from os.path import isfile, dirname, getsize, join

from typing import List, NamedTuple, Tuple, Optional
from uuid import uuid4

from cidc_utils.requests import SmartFetch
from google.cloud import storage
from google.api_core.exceptions import NotFound


from constants import EVE_URL, FILE_EXTENSION_DICT
from utilities.cli_utilities import (
    select_assay_trial,
    option_select_framework,
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
) -> bool:
    """
    Updates the status of the job in MongoDB, either with the URIs if the upload
    was succesful, or with the error message if it failed.

    Arguments:
        status {bool} -- True if upload succeeds, false otherwise.
        request_info {RequestInfo} -- Dict containing information about the request.
        message {str} -- If upload failed, contains error.

    Returns:
        bool -- True if succesful, else false.
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
        return True
    except RuntimeError as error:
        print("Status update failed: %s" % str(error))
        return False


def upload_files(directory: str, request_info: RequestInfo) -> Optional[str]:
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
        insert_id: str = request_info.mongo_data["_id"]
        bucket = storage.Client().bucket(request_info.headers["google_folder_path"])
        files_to_upload: List[dict] = request_info.files_uploaded
        for item in files_to_upload:
            upload_name = "%s/%s" % (insert_id, item["uuid_alias"])
            blob = bucket.blob(upload_name)
            blob.upload_from_filename(join(directory, item["file_name"]))
            print(blob.name)
        update_job_status(True, request_info)
        return insert_id
    except (NotFound, FileNotFoundError) as error:
        print("Error: Upload to Google failed: %s" % str(error))
        update_job_status(False, request_info, str(error))
        return None


def parse_upload_manifest(file_path: str) -> List[dict]:
    """
    Breaks a TSV or CSV manifest file into paired records.

    Arguments:
        file_path {str} -- Path to upload manifest.

    Returns:
        List[dict] -- List of dictionaries of patientIDs + Timepoints.
    """
    tumor_normal_pairs: list = []

    with open(file_path, "r") as manifest:
        separator = None
        as_deque = collections.deque(manifest, maxlen=500)
        first_line = as_deque.popleft()
        if len(first_line.split(",")) == 13:
            separator = ","
        elif len(first_line.split("\t")) == 13:
            separator = "\t"
        else:
            raise TypeError("Unable to recognize metadata format")

        headers = first_line.split(separator)

        while as_deque:
            columns = as_deque.popleft().strip().split(separator)
            if not len(columns) == len(headers):
                raise IndexError(
                    "Line %s has the wrong number of columns"
                    % str(len(tumor_normal_pairs) + 1)
                )
            tumor_normal_pairs.append(
                dict(
                    (header_value.strip(), column_value)
                    for column_value, header_value in zip(columns, headers)
                )
            )
    return tumor_normal_pairs


def find_manifest_path() -> str:
    """
    Prompts the user to enter a valid path.

    Raises:
        ValueError -- Triggers if path is undefined.

    Returns:
        string -- Path to manifest file.
    """
    file_path = None
    while not file_path:
        file_path = input("Please enter the file path to your metadata file: ")
        if not isfile(file_path):
            print("The given path is not valid, please enter a new one.")
            file_path = None

    return file_path


def check_id_present(sample_id: str, list_of_ids: List[str]) -> bool:
    """
    Checks if sampleID is in the list of sample IDs, if not, error.

    Arguments:
        sample_id {str} -- [description]
        list_of_ids {List[str]} -- [description]

    Returns:
        bool -- [description]
    """
    if sample_id not in list_of_ids:
        print("Error: SampleID %s is not a valid sample ID for this trial" % sample_id)
        return False
    return True


def guess_file_ext(file_name) -> Optional[str]:
    """
    Guesses a file extension from the file name.

    Arguments:
        file_name {str} -- Name of the file.

    Returns:
        Optional[str] -- Data type corresponding to file extension.
    """
    split_name = file_name.split(".")
    try:
        file_type = FILE_EXTENSION_DICT[split_name[-1]]
        return file_type
    except KeyError:
        try:
            ext = "%s.%s" % (split_name[-2], split_name[-1])
            return FILE_EXTENSION_DICT[ext]
        except KeyError:
            print("Error processing file %s. Extension not recognized" % (file_name))
            return None


def create_manifest_payload(
    entry: dict, non_static_inputs: List[str], selections: Selections, directory: str
) -> Tuple[List[dict], List[dict]]:
    """
    Turns the files

    Arguments:
        entry {dict} -- Row from the manifest file.
        non_static_inputs {List[str]} -- Names of inputs from the trial.
        selections {Selections} -- User selection of trial/assay.
        directory {str} -- Root directory holding files.

    Returns:
        Tuple[List[dict], List[dict]] -- List of dictionaries formatted to be sent to the API.
    """
    payload = []
    file_name_and_alias: List[dict] = []
    selected_assay = selections.selected_assay
    trial_id = selections.selected_trial["_id"]
    trial_name = selections.selected_trial["trial_name"]

    for key in entry:
        if key in non_static_inputs:
            file_name = entry[key]
            file_size = None

            try:
                file_size = getsize(directory + "/" + file_name)
            except FileNotFoundError:
                print("File: %s was not found" % (directory + "/" + file_name))

            tumor_normal = "TUMOR"
            pair_label = "PAIR 1"
            if key in {"FASTQ_NORMAL_1", "FASTQ_NORMAL_2"}:
                tumor_normal = "NORMAL"
            if key in {"FASTQ_NORMAL_2", "FASTQ_TUMOR_2"}:
                pair_label = "PAIR 2"
            alias = str(uuid4())
            payload.append(
                {
                    "assay": selected_assay["assay_id"],
                    "experimental_strategy": selected_assay["assay_name"],
                    "data_format": guess_file_ext(file_name),
                    "file_name": file_name,
                    "file_size": file_size,
                    "mapping": key,
                    "number_of_samples": 1,
                    "sample_ids": [entry["#CIMAC_SAMPLE_ID"]],
                    "trial": trial_id,
                    "trial_name": trial_name,
                    "uuid_alias": alias,
                    "fastq_properties": {
                        "patient_id": entry["CIMAC_PATIENT_ID"],
                        "timepoint": entry["TIMEPOINT"],
                        "timepoint_unit": entry["TIMEPOINT_UNIT"],
                        "batch_id": entry["BATCH_ID"],
                        "instrument_model": entry["INSTRUMENT_MODEL"],
                        "read_length": entry["READ_LENGTH"],
                        "avg_insert_size": entry["AVG_INSERT_SIZE"],
                        "sample_id": entry["#CIMAC_SAMPLE_ID"],
                        "sample_type": tumor_normal,
                        "pair_label": pair_label,
                    },
                }
            )
            file_name_and_alias.append({"file_name": entry[key], "uuid_alias": alias})

    return payload, file_name_and_alias


def upload_manifest(
    non_static_inputs: List[str], selections: Selections
) -> Tuple[str, dict, List[dict]]:
    """
    Upload method using a manifest file.

    Arguments:
        non_static_inputs {List[str]} -- List of required files for the pipeline.
        selections {Selections} -- User selections.

    Returns:
        Tuple[str, dict, List[dict]] -- Tuple, file directory, payload object, file names.
    """
    sample_ids = selections.selected_trial["samples"]
    file_path = find_manifest_path()

    tumor_normal_pairs = parse_upload_manifest(file_path)
    print("Metadata analyzed. Found %s entries." % len(tumor_normal_pairs))

    file_details: List[dict] = []
    payload: List[dict] = []
    bad_sample_id = False
    file_dir: str = dirname(file_path)

    for entry in tumor_normal_pairs:
        if not check_id_present(entry["#CIMAC_SAMPLE_ID"], sample_ids):
            bad_sample_id = True

        # Map to inputs. If this works correctly it should add all the file names to the list.
        # will depend on the non static inputs exactly matching the keys that contain the filenames.
        if not bad_sample_id:
            next_payload, next_file_details = create_manifest_payload(
                entry, non_static_inputs, selections, file_dir
            )
            file_details = file_details + next_file_details
            payload = payload + next_payload

    if bad_sample_id:
        raise RuntimeError(
            "One or more SampleIDs were not recognized as valid IDs for this trial"
        )

    for elem in payload:
        if elem["file_size"] is None:
            raise FileNotFoundError("One or more files could not be found")

    ingestion_payload = {
        "number_of_files": len(payload),
        "status": {"progress": "In Progress"},
        "files": payload,
    }

    return file_dir, ingestion_payload, file_details


def run_upload_process() -> None:
    """
    Function responsible for guiding the user through the upload process
    """

    selections = select_assay_trial("This is the upload function\n")

    if not selections:
        return

    eve_token = selections.eve_token
    selected_assay = selections.selected_assay
    assay_r = EVE_FETCHER.get(
        token=eve_token, endpoint="assays/" + selected_assay["assay_id"]
    ).json()

    method = option_select_framework(
        ["Upload using a metadata file."], "Pick an upload method:"
    )

    try:
        upload_dir, payload, file_details = [upload_manifest][method - 1](
            assay_r["non_static_inputs"], selections
        )

        response_upload = EVE_FETCHER.post(
            token=eve_token, endpoint="ingestion", json=payload, code=201
        )

        req_info = RequestInfo(
            response_upload.json(), eve_token, response_upload.headers, file_details
        )

        job_id = upload_files(upload_dir, req_info)

        if not job_id:
            raise RuntimeError("File upload failed.")
        upload_complete: str = str.join(
            " ",
            (
                "Upload completed. There will be a short delay while the files are processed.",
                "After processing is complete, you will be able to see the files within the",
                "CIMAC-CIDC Data Portal.",
            ),
        )
        print(upload_complete)
    except FileNotFoundError:
        print("There was a problem locating the files for upload.")
    except RuntimeError:
        print("There was an error processing your file for upload.")
