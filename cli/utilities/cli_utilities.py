#!/usr/bin/env python
"""
Utility methods for the CIDC-CLI Interface
"""

__author__ = "Lloyd McCarthy"
__license__ = "MIT"
# pylint: disable=R0903
import json
import os
from typing import List, Tuple, NamedTuple, Optional
from cidc_utils.requests import SmartFetch
from constants import EVE_URL, USER_CACHE

EVE_FETCHER = SmartFetch(EVE_URL)


class Selections(NamedTuple):
    """
    Simple class for storing user selections
    """

    eve_token: str
    selected_trial: dict
    selected_assay: dict


def terminal_sensitive_print(message: str, width: int = 80) -> None:
    """
    Prints a given string with a number of characters as a max width. Attempts to respect
    whitespaces.

    Arguments:
        message {str} -- Message to be printed
        width {int} -- Terminal width

    Returns:
        None -- No return.
    """
    for _ in range(0, len(message), width):
        blank: bool = False
        chars: int = width + 1
        while not blank:
            chars -= 1
            if message[_: _ + chars][-1] == " ":
                blank = True
            if chars <= 60:
                blank = True
                chars = width

        print(message[_: _ + chars].strip())


def generate_options_list(options: List[str], header: str) -> str:
    """
    Generates a list of user options

    Arguments:
        options {List[str]} -- List of options
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
    return "%s\n%s" % (header, opts)


def get_valid_dir(is_download: bool = True) -> Tuple[str, List[str]]:
    """
    Have the user select a valid directory for either down or upload.

    Arguments:
        is_download {bool} -- True if used in a download function, else false.
    Returns:
        Tuple[str, List[str]] -- Download directory and list of files in it.
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
                    for item in files_to_upload:
                        print(item)
                    confirm_upload = user_prompt_yn(
                        "These are the files found in the provided directory, proceed? [Y/N] "
                    )
                    directory = directory if confirm_upload else None
                else:
                    print("Directory contained no files")
        except (ValueError, TypeError):
            directory = None
            print("Please only enter valid filepaths")
        except FileNotFoundError as error:
            directory = None
            print("Error loading file: " + str(error))

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
    selection = "-1"
    user_input = None

    # Force user to make valid selection
    while int(selection) not in range(1, number_options + 1):
        user_input = input(prompt)
        try:
            int(user_input)
            selection = user_input
        except TypeError:
            print("Please enter an integer")
        if int(selection) not in range(1, number_options + 1):
            print(err_msg)
    return int(selection)


def option_select_framework(options: List[str], prompt_header: str) -> int:
    """
    Framework for generating a list of options, having the user select one,
    and returning the selection

    Arguments:
        options {List[str]} -- List of options for user to choose from
        prompt_header {str} -- Banner message to display above options

    Returns:
        int - index of user selection
    """
    prompt: str = generate_options_list(options, prompt_header)
    return force_valid_menu_selection(len(options), prompt)


def ensure_logged_in() -> Optional[str]:
    """
    Checks if the user is logged in, and if they are not, prompts them to log in.

    Returns:
        str -- API access token
    """

    if not USER_CACHE.get_key():
        print(
            "You are not currently authenticated. Run 'jwt_login' to log in\b"
            + " with a token. If you do not have a token, you can get one from the website."
        )
        return None

    return USER_CACHE.get_key()


def cache_token(token: str) -> None:
    """
    Stashes a token in the cli_utilities instantiated USER_CACHE

    Arguments:
        token {str} -- JWT Token

    Returns:
        None -- [description]
    """
    USER_CACHE.cache_key(token)


def run_jwt_login(token: str) -> bool:
    """
    Takes a user's JWT and confirms its validity.
    If it is valid

    Arguments:
        token {str} -- JWT

    Returns:
        bool -- True if login succeeds, else false.
    """
    if not token:
        print("Please enter a token when running this command")
        return False
    try:
        EVE_FETCHER.get(token=token, endpoint="trials")
        cache_token(token)
        print("Token is valid, you are now logged in!")
        return True
    except RuntimeError:
        print(
            "Your token is invalid. Please make sure your token was entered correctly"
        )
        return False


def user_prompt_yn(prompt: str) -> bool:
    """
    Prompts the user to pick in a yes or no scenario

    Arguments:
        prompt {str} -- User input prompt

    Returns:
        bool -- True if yes, false if no
    """
    selection = "-1"
    while selection.lower() not in {"y", "yes", "n", "no"}:
        selection = input(prompt)
        if selection.lower() not in {"y", "yes", "n", "no"}:
            print("Please select either yes or no")
    if selection.lower() in {"y", "yes"}:
        return True
    return False


def select_trial(prompt: str) -> Optional[Selections]:
    """
    Returns the user's selection of trial

    Arguments:
        prompt {String} -- Text promp describing the function.

    Returns:
        dict -- selected trial
    """
    print(prompt)
    eve_token = ensure_logged_in()

    if not eve_token:
        return None

    try:
        response = EVE_FETCHER.get(token=eve_token, endpoint="trials")
        email = EVE_FETCHER.get(endpoint="accounts_info", token=eve_token).json()
    except RuntimeError as rte:
        if "401" in str(rte):
            print(
                "Error: Your credentials could not be validated. Please check that you have "
                + "registered on our website, and that you correctly copied the token."
            )
        else:
            print("ERROR: %s" % rte)
        return None

    # Select Trial
    trials = response.json()["_items"]

    if not trials:
        print("No trials were found for this user")
        return None

    user_email = email["_items"][0]["email"]

    user_trials = list(filter(lambda x: user_email in x["collaborators"], trials))

    if not user_trials:
        print("No trials were found for this user.")
        return None

    selected_trial = user_trials[
        option_select_framework(
            [trial["trial_name"] for trial in user_trials],
            "=====| Available Trials |=====",
        )
        - 1
    ]
    return Selections(eve_token, selected_trial, {})


def select_assay(selected_trial: dict) -> Optional[dict]:
    """
    Choose an assay from the list of assays registered to the trial.

    Arguments:
        selected_trial {dict} -- Trial mongo record.

    Returns:
        dict -- Assay dictionary object.
    """
    if not selected_trial["assays"]:
        print("No assays are registered for the selected trial.")
        return None

    assay_selection = option_select_framework(
        [x["assay_name"] for x in selected_trial["assays"]],
        "=====| Available Assays |=====",
    )

    return selected_trial["assays"][assay_selection - 1]


def select_assay_trial(prompt: str) -> Optional[Selections]:
    """
    Returns the user's selection of assay and trial

    Arguments:
        prompt {String} -- Text promp describing the function.

    Returns:
        Selections -- token, selected trial, and selected assay.
    """
    trial_selection = select_trial(prompt)

    if not trial_selection:
        return None

    selected_trial = trial_selection.selected_trial
    selected_assay = select_assay(selected_trial)

    if not selected_assay:
        return None

    return Selections(trial_selection.eve_token, selected_trial, selected_assay)


def run_sample_delete() -> None:
    """
    Allows user to delete a sample on a trial.

    Returns:
        None -- No return.
    """
    # Get trial.
    selections = select_trial("Please select a trial to delete samples from: ")

    if not selections:
        return

    # Create query.

    query = {"trial": selections.selected_trial["_id"]}
    endpoint = "data/?where=%s" % json.dumps(query)
    data = EVE_FETCHER.get(endpoint=endpoint, token=selections.eve_token).json()["_items"]

    # List sample ids.
    sample_ids: List[str] = []
    for rec in data:
        sample_ids = sample_ids + rec["sample_ids"]

    sample_set = list(set(sample_ids))

    # Select one to delete.
    sample_selection = option_select_framework(
        sample_set, "These are the available samples, choose one to delete."
    )
    sample_id = sample_set[sample_selection - 1]

    to_delete = list(filter(lambda x: sample_id in x["sample_ids"], data))

    try:
        for item in to_delete:
            EVE_FETCHER.delete(
                endpoint="data_edit",
                item_id=item["_id"],
                _etag=item["_etag"],
                token=selections.eve_token,
                code=204
            )
            print("File %s deleted." % item["file_name"])
        print("All files related to sample %s deleted." % sample_id)
    except RuntimeError as rte:
        print("There was an error deleting the files: %s" % str(rte))


def run_lock_trial() -> None:
    """
    Allows an administrator to lock or unlock a = trial.

    Returns:
        None -- Returns None.
    """
    selections = select_trial("This is the trial locking function:")

    if not selections:
        return

    selected_trial = selections.selected_trial
    trial_id = selected_trial["_id"]
    if "locked" in selected_trial and selected_trial["locked"]:
        if user_prompt_yn("Trial is locked. Do you want to unlock it? [Y/n]: "):
            payload = {
                "locked": False
            }
        else:
            return
    else:
        payload = {"locked": True}

    verb = "locked" if payload["locked"] else "unlocked"

    try:
        EVE_FETCHER.patch(
            endpoint="trials",
            item_id=trial_id,
            _etag=selected_trial["_etag"],
            json=payload,
            token=selections.eve_token
        )
        print("Trial %s %s successfully" % (trial_id, verb))
    except RuntimeError as rte:
        if "401" in str(rte):
            print(
                "You are not allowed to lock trials."
                + "Trials may only be locked by an administrator"
            )
        else:
            print("Failed to %s trial %s: %s" % (verb[:-2], trial_id, str(rte)))
