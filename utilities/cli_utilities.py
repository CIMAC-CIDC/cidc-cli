#!/usr/bin/env python3
"""
Utility methods for the CIDC-CLI Interface
"""

import json
import os
import re
from typing import List, Tuple

import requests
from auth0.auth0 import run_auth_proc
from upload.cache_user import CredentialCache

USER_CACHE = CredentialCache(100, 600)
EVE_URL = "http://0.0.0.0:5000"
SELECTIONS = Tuple[str, dict, dict]


def fetch_eve_or_fail(
    token: str, endpoint: str, data: dict, code: int, method: str='POST'
) -> dict:
    """
    Method for fetching results from eve with a fail safe

    Arguments:
        token {string} -- access token
        endpoint {string} -- endpoint data is being inserted into
        data {dict} -- payload data to be uploaded
        code {int} -- expected status code of the response

    Keyword Arguments:
        method {str} -- HTTP method (default: {'POST'})

    Returns:
        dict -- json formatted response from eve
    """
    response = request_eve_endpoint(token, data, endpoint, method)
    if not response.status_code == code:
        error_string = "There was a problem with your request: "
        if response.json:
            error_string += json.dumps(response.json())
        else:
            error_string += response.reason
        raise RuntimeError(error_string)
    return response.json()


def generate_options_list(options: List[str], header: str) -> str:
    """
    Generates a list of user options

    Arguments:
        options {[str]} -- List of options
        header {str} -- Text you want displayed above the list.

    Returns:
        str -- Completed list in string form
    """
    opts = ''.join(
        [('[' + str(idx + 1) + '] - ' + option + '\n') for idx, option in enumerate(options)]
    )
    return header + '\n' + opts


def force_valid_menu_selection(
        number_options: int, prompt: str, err_msg: str='Invalid selection'
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
    selection = "-1"
    # Force user to make valid selection
    while int(selection) not in range(1, number_options + 1):
        selection = input(prompt)
        try:
            int(selection)
        except ValueError:
            print('Please enter an integer')
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
    number_of_options = len(options)
    prompt = generate_options_list(options, prompt_header)
    return force_valid_menu_selection(
        number_of_options,
        prompt
    )


def ensure_logged_in() -> str:
    """
    Checks if the user is logged in, and if they are not, promps them to log in.

    Returns:
        str -- API access token
    """
    eve_token = None
    creds = USER_CACHE.get_key()

    if not creds:
        print('You are not currently authenticated. Launching a page to sign in with google')
        eve_token = run_auth_proc()
        USER_CACHE.cache_key(eve_token)
    else:
        eve_token = creds

    return eve_token


def user_prompt_yn(prompt: str) -> bool:
    """
    Prompts the user to pick in a yes or no scenario

    Arguments:
        prompt {str} -- User input prompt

    Returns:
        bool -- True if yes, false if no
    """
    selection = -1
    while selection not in ['y', 'yes', 'n', 'no', 'Y', 'Yes', 'YES', 'N', 'NO']:
        selection = input(prompt)
        if selection not in ['y', 'yes', 'n', 'no', 'Y', 'Yes', 'YES', 'N', 'NO']:
            print("Please select either yes or no")
    if selection in ['y', 'yes', 'Y', 'Yes', 'YES']:
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
    confirm_upload = False
    valid_sample_ids = False
    files_to_upload = None
    upload_dir = None

    while not confirm_upload or not valid_sample_ids:
        if confirm_upload:
            upload_dictionary = validate_and_extract(
                files_to_upload, sample_ids, non_static_inputs
                )
            if upload_dictionary:
                return upload_dictionary, upload_dir
            else:
                confirm_upload = False
                print('Files contained invalid IDs!')

        upload_dir = input("Enter the path to the files you wish to upload:\n")

        try:
            files_to_upload = [
                name for name in os.listdir(upload_dir) if
                os.path.isfile(os.path.join(upload_dir, name))
            ]

            if not len(files_to_upload) == len(set(files_to_upload)):
                print("Error, duplicate names in file list, aborting")
                return

        except FileNotFoundError as error:
            print("Error: " + error)

        for file_name in files_to_upload:
            print(file_name)

        if files_to_upload:
            confirm_upload = user_prompt_yn(
                "These are the files found in provided directory, proceed? [Y/N]"
            )
        else:
            print("Directory contained no files")


def create_payload_objects(file_dict: List[dict], trial: dict, assay: dict) -> List[dict]:
    """
    Returns objects formatted for inserting into the API

    Arguments:
        file_dict {[dict]} -- List of file objects.
        trial {dict} -- Trial ID dictionary
        assay {dict} -- Assay ID dictionary

    Returns:
        [type] -- [description]
    """
    return [
        {
            "assay": assay['assay_id'],
            "trial": trial['_id'],
            "file_name": key,
            "sample_id": file_dict[key]['sample_id'],
            "mapping": file_dict[key]['mapping']
        } for key in file_dict
    ]


def select_assay_trial(prompt: str) -> SELECTIONS:
    """
    Returns the user's selection of assay and trial

    Arguments:
        prompt {String} -- Text promp describing the function.

    Returns:
        tuple -- selected trial and selected assay
    """
    print(prompt)
    eve_token = ensure_logged_in()

    # Fetch list of trials
    response = request_eve_endpoint(eve_token, None, 'trials', 'GET')
    if not response.status_code == 200:
        print('There was a problem fetching the data: ')
        if response.json:
            print(response.json())
        return None

    # Select Trial
    response_data = response.json()
    trials = response_data['_items']

    if not trials:
        print("No trials were found for your id, your credentials will not be saved")
        return None

    USER_CACHE.cache_key(eve_token)
    trial_names = [x['trial_name'] for x in trials]
    trial_selection = option_select_framework(trial_names, '=====| Available Trials |=====')
    selected_trial = trials[trial_selection - 1]

    # Select Assay
    assays = selected_trial['assays']

    if not assays:
        print("No assays are registered for the selected trial.")
        return

    assay_names = [x['assay_name'] for x in assays]
    assay_selection = option_select_framework(assay_names, '=====| Available Ass ays |=====')
    selected_assay = assays[assay_selection - 1]

    return eve_token, selected_trial, selected_assay


def request_eve_endpoint(
        eve_token: str, payload_data: dict, endpoint: str, method: str='POST'
) -> requests.Response:
    """
    Generic method for running a request against the API with authorization

    Arguments:
        eve_token {str} -- API token
        payload_data {dict} -- The payload to be sent
        endpoint {str} -- Name of the endpoint the request should be sent to

    Returns:
        requests.Response -- Returns request object
    """
    method_dictionary = {
        'GET': requests.get,
        'POST': requests.post,
        'PUT': requests.put,
        'HEAD': requests.head,
        'OPTIONS': requests.options,
        'DELETE': requests.delete
    }

    if method not in method_dictionary:
        error_string = 'Method argument ' + method + ' not a valid operation'
        raise KeyError(error_string)

    request_func = method_dictionary[method]
    if request_func == requests.get:
        return request_func(
            EVE_URL + "/" + endpoint,
            headers={"Authorization": 'Bearer {}'.format(eve_token)},
            params=payload_data
        )
    return request_func(
        EVE_URL + "/" + endpoint,
        json=payload_data,
        headers={"Authorization": 'Bearer {}'.format(eve_token)}
    )


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
                mapped_input: "mapping"
            }
        }
    """
    # Create RE object based on valid samples
    search_string = re.compile(str.join('|', sample_ids))
    # create a dictionary of type filename: regex search result
    name_dictionary = dict((item, re.search(search_string, item)) for item in file_names)
    # Check for any "None" types and return empty list if any found.
    if not all(name_dictionary.values()):
        return []
    # If all valid, return map of filename: sample_id
    mapped_names = dict((name, name_dictionary[name].group()) for name in name_dictionary)

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
    upload_guide = dict((item, {"sample_id": mapped_names[item]}) for item in mapped_names)

    for sample_id in sample_id_dict:

        # Copy list by value for manipulation
        nsi = non_static_inputs[:]

        print(
            "These files are associated with SampleID: " + sample_id + ", please map them to the \
            assay inputs"
        )
        files_to_map = sample_id_dict[sample_id]

        # Sanity check number of files per ID
        if len(files_to_map) > len(nsi):
            print("Error! Too many files for this sampleID")
            return []

        # Loop over files and make the user map them.
        for filename in files_to_map:
            selection = option_select_framework(
                nsi,
                "Please choose which input " + filename + " maps to."
            )
            # save selection, then delete from list.
            upload_guide[filename]['mapping'] = nsi[selection - 1]
            del nsi[selection - 1]

    return upload_guide


def find_eve_token(token_dir: str) -> str:
    """Searches for a file containing a token for the API

    Arguments:
        token_dir {str} -- directory where token is stored

    Raises:
        FileNotFoundError -- Raise error if no token file found

    Returns:
        str -- Authorization token
    """
    for file_name in os.listdir(token_dir):
        if file_name.endswith('.token'):
            with open(token_dir + '/' + file_name) as token_file:
                eve_token = token_file.read().strip()
                return eve_token
    raise FileNotFoundError('No valid token file was found')
