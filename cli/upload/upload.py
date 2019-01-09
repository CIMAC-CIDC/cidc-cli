"""
This is a simple command-line tool that allows users to upload data to our google storage
"""
# pylint: disable=R0903
import collections
import datetime
from os.path import isfile, dirname
import subprocess
from abc import ABC, abstractmethod
from typing import List, NamedTuple, Tuple

from cidc_utils.requests import SmartFetch

from constants import EVE_URL
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


class UploadMethod(ABC):
    """
    Abstract class that defines the interface for an upload method.

    Arguments:
        ABC {[type]} -- [description]
    """

    @abstractmethod
    def do_upload_method(
        self, assay_response: dict, selections: Selections
    ) -> Tuple[str, dict, List[str]]:
        """
        Function signature for a method of uploading data to our buckets.

        Arguments:
            assay_response {dict} -- Information from queried assay.
            selections {Selections} -- User selections

        Returns:
            Tuple[str, dict, List[str]] -- File path, payload, file names.
        """
        pass


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
            raise TypeError("Unable to recognize manifest format")

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
        if not isfile(directory + name):
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
        path = input("Please enter the file path to your download manifest: ")
        if not isfile(path):
            print("The given path is not valid, please enter a new one.")
            path = None

    if not path:
        raise ValueError("Path undefined")

    return file_path


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
    print("Manifest analyzed. Found %s entries." % len(tumor_normal_pairs))

    file_names = []
    payload = []
    bad_sample_id = False

    # Loop over the list and do all processing operations needed.
    for entry in tumor_normal_pairs:
        if not entry["SAMPLE_ID"] in sample_ids:
            print(
                "Error: SampleID %s is not a valid sample ID for this trial"
                % entry["SAMPLE_ID"]
            )
            bad_sample_id = True

        # Map to inputs. If this works correctly it should add all the file names to the list.
        # will depend on the non static inputs exactly matching the keys that contain the filenames.
        if not bad_sample_id:
            for key in entry:
                if key in non_static_inputs:
                    payload.append(
                        {
                            "assay": selections.selected_assay["assay_id"],
                            "trial": selections.selected_trial["trial_id"],
                            "file_name": entry[key],
                            "mapping": key,
                        }
                    )
                    file_names.append(entry[key])

    if not len(file_names) == (len(non_static_inputs) * len(tumor_normal_pairs)):
        raise RuntimeError(
            "Number of files does not correspond to the number of inputs."
        )

    if bad_sample_id:
        raise RuntimeError(
            "One or more SampleIDs were not recognized as valid IDs for this trial"
        )

    file_dir = dirname(file_path)
    if not confirm_manifest_files(file_dir, file_names):
        raise FileNotFoundError("Some files were not able to be found.")

    return file_dir, payload, file_names


def run_upload_process() -> None:
    """
    Function responsible for guiding the user through the upload process
    """

    selections = select_assay_trial("This is the upload function\n")

    if not selections:
        return

    eve_token = selections.eve_token
    selected_assay = selections.selected_assay

    # Query the selected assay ID to get the inputs.
    assay_r = EVE_FETCHER.get(
        token=eve_token, endpoint="assays/" + selected_assay["assay_id"]
    ).json()

    method = option_select_framework(
        [
            "Upload using a manifest file.",
            "Upload inputs for a WDL pipeline",
            "Upload data.",
        ],
        "Pick an upload method:",
    )

    try:
        upload_dir, payload, file_list = [upload_manifest, upload_pipeline, upload_np][
            method
        ](assay_r["non_static_inputs"], selections)

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
