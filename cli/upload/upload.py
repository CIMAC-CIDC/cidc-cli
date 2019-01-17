"""
This is a simple command-line tool that allows users to upload data to our google storage
"""
# pylint: disable=R0903
import collections
import datetime
from os.path import isfile, dirname, getsize
import subprocess
from typing import List, NamedTuple, Tuple

from cidc_utils.requests import SmartFetch

from constants import EVE_URL, FILE_EXTENSION_DICT
from utilities.cli_utilities import (
    get_valid_dir,
    select_assay_trial,
    option_select_framework,
    get_files,
    create_payload_objects,
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
    was succesful, or with the error message if it failed.

    Arguments:
        status {bool} -- True if upload succeeds, false otherwise.
        request_info {RequestInfo} -- Dict containing information about the request.
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
            json=payload
        )
    except RuntimeError as error:
        print("Status update failed: %s" % str(error))


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
    non_static_inputs: List[str], selections: Selections
) -> Tuple[str, dict, List[str]]:
    """
    Upload for files going to a WDL pipeline

    Arguments:
        non_static_inputs {List[str]} -- List of non static inputs to pipeline
        selections {Selections} -- User selections for assay/trial.

    Returns:
        Tuple[str, dict, List[str]] -- Directory path, upload payload, file names.
    """
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
    non_static_inputs: List[str], selections: Selections
) -> Tuple[str, dict, List[str]]:
    """
    Upload for non-pipeline files.

    Arguments:
        non_static_inputs {List[str]} -- List of required files.
        selections {Selections} -- User selections.

    Returns:
        Tuple[str, dict, List[str]] -- Directory path, upload payload, file names.
    """

    upload_dir, files_to_upload = get_valid_dir(is_download=False)
    file_copy = files_to_upload[:]
    upload_list = []
    append_to_upload_list = upload_list.append

    while file_copy:
        for inp in non_static_inputs:
            selection = option_select_framework(
                file_copy, "Please choose the file which corresponds to: %s" % inp
            )
            # save selection, then delete from list.
            append_to_upload_list(
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


def parse_upload_manifest(file_path: str) -> List[dict]:
    """
    Breaks a TSV or CSV manifest file into paired records.

    Arguments:
        file_path {str} -- Path to upload manifest.

    Returns:
        List[dict] -- List of dictionaries of patientIDs + Timepoints.
    """
    tumor_normal_pairs = []

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

        # Get the column headers.
        headers = first_line.split(separator)

        while as_deque:
            # split line into chunks.
            columns = as_deque.popleft().strip().split(separator)
            tumor_normal_pairs.append(
                dict(
                    (header_value, column_value)
                    for column_value, header_value in zip(columns, headers)
                )
            )

            if not len(tumor_normal_pairs[-1]) == len(headers):
                raise IndexError(
                    "Line %s has the wrong number of columns" % len(tumor_normal_pairs)
                    + 1
                )

    return tumor_normal_pairs


def confirm_manifest_files(directory: str, file_names: List[str]) -> bool:
    """
    Loops over file paths to confirm that all files exist.

    Arguments:
        file_names {List[str]} -- List of file paths.

    Returns:
        bool -- True if all found, else false.
    """
    all_found = True
    for name in file_names:
        if not isfile(directory + "/" + name):
            print("Error: File %s not found" % name)
            all_found = False

    return all_found


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

    if not file_path:
        raise ValueError("Path undefined")

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
    if not sample_id in list_of_ids:
        print("Error: SampleID %s is not a valid sample ID for this trial" % sample_id)
        return False
    return True


def guess_file_ext(file_name) -> str:
    """
    Guesses a file extension from the file name.

    Arguments:
        file_name {[type]} -- [description

    Returns:
        str -- [description]
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


def create_manifest_payload(
    entry: dict, non_static_inputs: List[str], selections: Selections, directory: str
) -> Tuple[List[dict], List[str]]:
    """[summary]

    Arguments:
        entry {dict} -- [description]
        non_static_inputs {List[str]} -- [description]
        selections {Selections} -- [description]
        directory {str} -- Root directory holding files.

    Returns:
        List[dict] -- [description]
    """
    payload = []
    file_names = []
    append_to_payload = payload.append
    append_to_file_names = file_names.append
    selected_assay = selections.selected_assay
    selected_assay_name = selected_assay["assay_name"]
    trial_id = selections.selected_trial["_id"]
    trial_name = selections.selected_trial["trial_name"]

    for key in entry:
        if key in non_static_inputs:
            file_name = entry[key]
            append_to_payload(
                {
                    "assay": selected_assay["assay_id"],
                    "experimental_strategy": selected_assay_name,
                    "data_format": guess_file_ext(file_name),
                    "file_name": file_name,
                    "file_size": getsize(directory + "/" + file_name),
                    "mapping": key,
                    "number_of_samples": 1,
                    "sample_ids": [entry["#SAMPLE_ID"]],
                    "trial": trial_id,
                    "trial_name": trial_name,
                }
            )
            append_to_file_names(entry[key])

    return payload, file_names


def upload_manifest(
    non_static_inputs: List[str], selections: Selections
) -> Tuple[str, dict, List[str]]:
    """
    Upload method using a manifest file.

    Arguments:
        non_static_inputs {List[str]} -- List of required files for the pipeline.
        selections {Selections} -- User selections.

    Returns:
        Tuple[str, dict, List[str]] -- Tuple, file directory, payload object, file names.
    """
    sample_ids = selections.selected_trial["samples"]
    file_path = find_manifest_path()

    tumor_normal_pairs = parse_upload_manifest(file_path)
    print("Metadata analyzed. Found %s entries." % len(tumor_normal_pairs))

    file_names = []
    payload = []
    bad_sample_id = False
    file_dir = dirname(file_path)

    for entry in tumor_normal_pairs:
        if not check_id_present(entry["#SAMPLE_ID"], sample_ids):
            bad_sample_id = True

        # Map to inputs. If this works correctly it should add all the file names to the list.
        # will depend on the non static inputs exactly matching the keys that contain the filenames.
        if not bad_sample_id:
            next_payload, next_file_names = create_manifest_payload(
                entry, non_static_inputs, selections, file_dir
            )
            file_names = file_names + next_file_names
            payload = payload + next_payload

    if not len(file_names) == (len(non_static_inputs) * len(tumor_normal_pairs)):
        raise RuntimeError(
            "Number of files does not correspond to the number of inputs."
        )

    if bad_sample_id:
        raise RuntimeError(
            "One or more SampleIDs were not recognized as valid IDs for this trial"
        )

    if not confirm_manifest_files(file_dir, file_names):
        raise FileNotFoundError("Some files were not able to be found.")

    ingestion_payload = {
        "number_of_files": len(payload),
        "status": {"progress": "In Progress"},
        "files": payload,
    }

    return file_dir, ingestion_payload, file_names


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
        [
            "Upload using a metadata file.",
            "Upload inputs for a WDL pipeline",
            "Upload data.",
        ],
        "Pick an upload method:",
    )

    try:
        upload_dir, payload, file_list = [upload_manifest, upload_pipeline, upload_np][
            method - 1
        ](assay_r["non_static_inputs"], selections)

        print(payload)

        response_upload = EVE_FETCHER.post(
            token=eve_token, endpoint="ingestion", json=payload, code=201
        )

        req_info = RequestInfo(
            response_upload.json(), eve_token, response_upload.headers, file_list
        )

        job_id = upload_files(upload_dir, req_info)
        print("Uploaded, your ID is: " + job_id)
    except FileNotFoundError:
        print("There was a problem locating the files for upload.")
    except RuntimeError:
        print("There was an error processing your file for upload.")
