#!/usr/bin/env python3
"""
Utility methods for the CIDC-CLI Interface
"""

import json
import os
from upload.cache_user import CredentialCache
from upload.upload import request_eve_endpoint, validate_and_extract, find_eve_token

USER_CACHE = CredentialCache(100, 600)


def fetch_eve_or_fail(token, endpoint, data, code, method='POST'):
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


def generate_options_list(options, header):
    """
    Generates a list of user options

    Arguments:
        trial_list {str} -- List of options

    Returns:
        str -- Completed list in string form
    """
    opts = ''.join(
        [('[' + str(idx + 1) + '] - ' + option + '\n') for idx, option in enumerate(options)]
    )
    return header + '\n' + opts


def force_valid_menu_selection(number_options, prompt, err_msg='Invalid selection'):
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
        if int(selection) not in range(1, number_options + 1):
            print(err_msg)
    return int(selection)


def option_select_framework(options, prompt_header):
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


def user_prompt_yn(prompt):
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


def get_files(sample_ids, non_static_inputs):
    """
    Asks the user for input, then returns list of files in that directory

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

   
def create_payload_objects(file_dict, trial, assay):
    """
    Returns objects formatted for inserting into the API

    Arguments:
        file_dict {[dict]} -- [description]
        trial {str} -- Trial ID
        assay {str} -- Assay ID

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


def select_assay_trial(username_prompt):
    """
    Returns the user's selection of adday and trial

    Arguments:
        username_prompt {String} -- Text promp describing the function and asking for username.

    Returns:
        tuple -- username, selected trial and selected assay
    """

    username = None
    eve_token = None

    creds = check_for_credentials()
    if not creds:
        username = input(username_prompt)
        token_path = input(
            "Welcome, " + username + " please enter the path to your authorization token:\n"
            )
        eve_token = find_eve_token(token_path)
    else:
        username = creds['username']
        eve_token = creds['token']

    # Fetch list of trials
    response = request_eve_endpoint(eve_token, {'username': username}, 'trials', 'GET')
    if not response.status_code == 200:
        print('There was a problem fetching the data: ')
        if response.json:
            print(response.json())
        return None

    # Select Trial
    response_data = response.json()
    trials = response_data['_items']

    if not trials:
        print("No trials were found for your username, your credentials will not be saved")
        return None

    USER_CACHE.add_login_to_cache(username, eve_token)
    trial_names = [x['trial_name'] for x in trials]
    trial_selection = option_select_framework(trial_names, '=====| Available Trials |=====')
    selected_trial = trials[trial_selection - 1]

    # Select Assay
    assays = selected_trial['assays']
    assay_names = [x['assay_name'] for x in assays]
    assay_selection = option_select_framework(assay_names, '=====| Available Assays |=====')
    selected_assay = assays[assay_selection - 1]

    return username, eve_token, selected_trial, selected_assay


def check_for_credentials():
    """
    Function that checks if the user has credentials in the cache,
    if credentials are found, retreives them
    Returns:
        dict -- Dictionary container user's login info.
    """
    if bool(USER_CACHE.get_login()):
        return USER_CACHE.get_login()
    return None
