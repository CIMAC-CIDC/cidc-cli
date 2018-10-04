#!/usr/bin/env python3.6
"""
Utility methods for the CIDC-CLI Interface
"""
import os
import re
from typing import List, Tuple, NamedTuple
from cidc_utils.requests import SmartFetch
from cidc_utils.caching import CredentialCache
from auth0.auth0 import run_auth_proc
from constants import EVE_URL

USER_CACHE = CredentialCache(100, 600)
EVE_FETCHER = SmartFetch(EVE_URL)


class Selections(NamedTuple):
    """
    Simple class for storing user selections
    """
    eve_token: str
    selected_trial: dict
    selected_assay: dict


def generate_options_list(options: List[str], header: str) -> str:
    """
    Generates a list of user options

    Arguments:
        options {[str]} -- List of options
        header {str} -- Text you want displayed above the list.

    Returns:
        str -- Completed list in string form
    """
    opts = "".join(
        [
            ("[" + str(idx + 1) + "] - " + option + "\n")
            for idx, option in enumerate(options)
        ]
    )
    return header + "\n" + opts


def get_valid_dir(is_download: bool = True) -> Tuple[str, List[str]]:
    """
    Have the user select a valid directory for either down or upload.

    Arguments:
        is_download {bool} -- True if used in a download function, else false.
    Returns:
        str -- Download directory.
    """

    directory = None
    dl_msg = "you would like the files to be downloaded to."
    ul_msg = "your sample data resides."
    files_to_upload = None

    while not directory:
        # Change prompt based on action.
        directory = input(
            "Please enter the path where %s :\n" % (dl_msg if is_download else ul_msg)
        )
        print(directory)
        try:
            # Check that the directory path exists.
            if not os.path.isdir(directory):
                print("The given path is not valid, please enter a new one.")
                directory = None

            # If upload operation, check that there are files at the path.
            if not is_download and directory:
                files_to_upload = [
                    name
                    for name in os.listdir(directory)
                    if os.path.isfile(os.path.join(directory, name))
                ]

                # Get confirmation of upload.
                if files_to_upload:
                    for x in files_to_upload:
                        print(x)
                    confirm_upload = user_prompt_yn(
                        "These are the files found in the provided directory, proceed? [Y/N]"
                    )
                    directory = directory if confirm_upload else None
                else:
                    print("Directory contained no files")
        except (ValueError, TypeError):
            directory = None
            print("Please only enter valid filepaths")
        except FileNotFoundError as error:
            directory = None
            print("Error loading file: " + error)

    return directory, files_to_upload


def force_valid_menu_selection(
    number_options: int, prompt: str, err_msg: str = "Invalid selection"
) -> int:
    """
    Script that forces a user to choose a valid option based on the number of options.

    Arguments:
        number_options {int} -- number of valid options
        prompt {str} -- Message you want displayed to user
        err_msg {str} -- Message to be printed when a bad selection is made

    Returns:
        int -- The user's selection
    """
    selection = -1
    user_input = None

    # Force user to make valid selection
    while int(selection) not in range(1, number_options + 1):
        user_input = input(prompt)
        try:
            int(user_input)
            selection = user_input
        except ValueError:
            print("Please enter an integer")
        if int(selection) not in range(1, number_options + 1):
            print(err_msg)
    return int(selection)


def option_select_framework(options: List[str], prompt_header: str) -> int:
    """
    Framework for generating a list of options, having the user select one,
    and returning the selection

    Arguments:
        options {[str]} -- List of options for user to choose from
        prompt_header {str} -- Banner message to display above options

    Returns:
        int - index of user selection
    """
    prompt = generate_options_list(options, prompt_header)
    return force_valid_menu_selection(len(options), prompt)


def ensure_logged_in() -> str:
    """
    Checks if the user is logged in, and if they are not, promps them to log in.

    Returns:
        str -- API access token
    """
    eve_token = None
    creds = USER_CACHE.get_key()

    if not creds:
        print(
            "You are not currently authenticated. Launching a page to sign in with google"
        )
        eve_token = run_auth_proc()
        if not eve_token:
            print("Authentication failed!")
            return None
        USER_CACHE.cache_key(eve_token)
    else:
        eve_token = creds

    return eve_token


def cache_token(token: str) -> None:
    """
    Stashes a token in the cli_utilities instantiated USER_CACHE
    :param token: Identity Token (usually a JWT)
    :return: None
    """
    USER_CACHE.cache_key(token)


def user_prompt_yn(prompt: str) -> bool:
    """
    Prompts the user to pick in a yes or no scenario

    Arguments:
        prompt {str} -- User input prompt

    Returns:
        bool -- True if yes, false if no
    """
    selection = -1
    while selection not in ["y", "yes", "n", "no", "Y", "Yes", "YES", "N", "NO"]:
        selection = input(prompt)
        if selection not in ["y", "yes", "n", "no", "Y", "Yes", "YES", "N", "NO"]:
            print("Please select either yes or no")
    if selection in ["y", "yes", "Y", "Yes", "YES"]:
        return True

    return False


def get_files(sample_ids: List[str], non_static_inputs: List[str]) -> List[str]:
    """
    Asks for user to input a directory, then fetches all files from it.

    Arguments:
        sample_ids {[str]} -- List of sample IDs from selected trial.
        non_static_inputs {[str]} -- Variable inputs from selected assay.

    Returns:
        [str] -- List of filenames
    """
    valid_sample_ids = False
    files_to_upload = None

    while not valid_sample_ids:
        upload_dir, files_to_upload = get_valid_dir(is_download=False)
        upload_dictionary = validate_and_extract(
            files_to_upload, sample_ids, non_static_inputs
        )
        if upload_dictionary:
            return upload_dictionary, upload_dir

        print("Files contained invalid IDs!")


def create_payload_objects(
    file_dict: List[dict], trial: dict, assay: dict
) -> List[dict]:
    """
    Returns objects formatted for inserting into the API

    Arguments:
        file_dict {[dict]} -- List of file objects.
        trial {dict} -- Trial ID dictionary
        assay {dict} -- Assay ID dictionary

    Returns:
        [dict] -- List of records in payload format.
    """
    return [
        {
            "assay": assay["assay_id"],
            "trial": trial["_id"],
            "file_name": key,
            "sample_id": file_dict[key]["sample_id"],
            "mapping": file_dict[key]["mapping"],
        }
        for key in file_dict
    ]


def select_assay_trial(prompt: str) -> Selections:
    """
    Returns the user's selection of assay and trial

    Arguments:
        prompt {String} -- Text promp describing the function.

    Returns:
        Selections -- token, selected trial, and selected assay.
    """
    print(prompt)
    eve_token = ensure_logged_in()

    if not eve_token:
        return None

    # Fetch list of trials
    response = EVE_FETCHER.get(token=eve_token, endpoint="trials")

    # Select Trial
    response_data = response.json()
    trials = response_data["_items"]

    if not trials:
        print("No trials were found for your id, your credentials will not be saved")
        return None

    USER_CACHE.cache_key(eve_token)
    trial_names = [trial["trial_name"] for trial in trials]
    trial_selection = option_select_framework(
        trial_names, "=====| Available Trials |====="
    )
    selected_trial = trials[trial_selection - 1]

    # Select Assay
    assays = selected_trial["assays"]

    if not assays:
        print("No assays are registered for the selected trial.")
        return None

    assay_names = [x["assay_name"] for x in assays]
    assay_selection = option_select_framework(
        assay_names, "=====| Available Assays |====="
    )
    selected_assay = assays[assay_selection - 1]

    return Selections(eve_token, selected_trial, selected_assay)


def validate_and_extract(
    file_names: List[str], sample_ids: List[str], non_static_inputs: List[str]
) -> dict:
    """
    Compares each file name in upload to list of valid sample IDs in trial.
    If all names are valid, returns a mapping of filename to sample id.

    Arguments:
        file_names {[str]} -- list of file names
        sample_ids {[str]} -- list of valid ids
        non_static_inputs {[str]} -- list of non static inputs for selected assay.
    Returns:
        dict -- Dictionary mapping file name to sample id. Format:
        {
            file_name: {
                sample_id: "sample_id",
                mapping: "mapping"
            }
        }
    """
    # Create RE object based on valid samples
    search_string = re.compile(str.join("|", sample_ids))
    # create a dictionary of type filename: regex search result
    name_dictionary = dict(
        (item, re.search(search_string, item)) for item in file_names
    )
    # Check for any "None" types and return empty list if any found.
    if not all(name_dictionary.values()):
        return []
    # If all valid, return map of filename: sample_id
    mapped_names = dict(
        (name, name_dictionary[name].group()) for name in name_dictionary
    )

    # Create dictionary of involved sampleIDS
    sample_id_dict = {}

    # Group filenames under associated sampleIDs.
    # Format: sample_id: [list, of, files, with, that, id]
    for key, value in mapped_names.items():
        if value in sample_id_dict:
            sample_id_dict[value].append(key)
        else:
            sample_id_dict[value] = [key]

    # Guide for associating file names with sample ids, and later, inputs
    upload_guide = dict(
        (item, {"sample_id": mapped_names[item]}) for item in mapped_names
    )

    for sample_id in sample_id_dict:

        # Copy list by value for manipulation
        nsi = non_static_inputs[:]

        print(
            "These files are associated with SampleID: "
            + sample_id
            + ", please map them to the "
            + "assay inputs"
        )
        files_to_map = sample_id_dict[sample_id]

        # Sanity check number of files per ID
        if len(files_to_map) > len(nsi):
            print("Error! Too many files for this sampleID")
            raise RuntimeError

        # Loop over files and make the user map them.
        for filename in files_to_map:
            selection = option_select_framework(
                nsi, "Please choose which input " + filename + " maps to."
            )
            # save selection, then delete from list.
            upload_guide[filename]["mapping"] = nsi[selection - 1]
            del nsi[selection - 1]

    return upload_guide