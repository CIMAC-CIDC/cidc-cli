#!/usr/bin/env python3
"""
Class defining the behavior of the interactive command line interface
"""


import cmd
import os
import datetime
import json
import requests
from upload import find_eve_token, request_eve_endpoint, validate_and_extract, upload_files


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
    print(opts)
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


def get_files(sample_ids):
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
            upload_dictionary = validate_and_extract(files_to_upload, sample_ids)
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
            'assay': assay,
            'trial': trial['_id'],
            'file_name': key,
            'sample_id': file_dict[key]
        } for key in file_dict
    ]


def run_upload_process():
    """
    Function responsible for guiding the user through the upload process
    """

    # Get username
    username = input("This is the upload functionality, to begin please enter a username:\n")
    # Get auth token
    token_path = input(
        "Welcome, " + username + " please enter the path to your authorization token:\n"
        )
    eve_token = find_eve_token(token_path)
    # Fetch list of trials
    response = request_eve_endpoint(eve_token, None, 'trials', 'GET')
    if not response.status_code == 200:
        print('There was a problem fetching the data')
        return

    # Select Trial
    response_data = response.json()
    trials = response_data['_items']
    trial_names = [x['trial_name'] for x in trials]
    trial_selection = option_select_framework(trial_names, '=====| Available Trials |=====')
    selected_trial = trials[trial_selection - 1]

    # Select Assay
    assays = selected_trial['assays']
    assay_selection = option_select_framework(assays, '=====| Available Assays |=====')
    selected_assay = assays[assay_selection - 1]

    # Get list of files in directory
    sample_ids = selected_trial['samples']
    file_upload_dict, upload_dir = get_files(sample_ids)

    payload = {
        'number_of_files': len(file_upload_dict),
        'started_by': username,
        'status': {
            'progress': 'In Progress',
        },
        'files': create_payload_objects(file_upload_dict, selected_trial, selected_assay)
    }

    response_upload = request_eve_endpoint(eve_token, payload, 'ingestion')
    print(response_upload.json())
    if not response_upload.status_code == 201:
        print('Communication with Eve Failed, exiting')
        print(response_upload.reason)
        return

    # Execute uploads
    job_id = upload_files(
        upload_dir,
        [file_upload_dict[key] for key in file_upload_dict],
        response_upload.json(),
        eve_token,
        response_upload.headers,
        selected_assay,
        selected_trial
    )
    # If this line is reached, upload has been completed
    # Poll for completed job:


class CIDCCLI(cmd.Cmd):
    """
    Defines the CLI interface
    """

    intro = "Welcome to the CIDC CLI Tool"

    def do_upload_data(self, rest=None):
        """
        Starts the upload process
        """
        run_upload_process()

    def do_EOF(self, rest=None):
        """
        Provides a way to exit tool

        Arguments:
            line {[type]} -- [description]

        Returns:
            [type] -- [description]
        """
        return True


if __name__ == '__main__':
    CIDCCLI().cmdloop()
