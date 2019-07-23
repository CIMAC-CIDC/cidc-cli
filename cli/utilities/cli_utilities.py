#!/usr/bin/env python
"""
Utility methods for the CIDC-CLI Interface
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

import json
import os
import time
from typing import List, Tuple, NamedTuple, Optional
from cidc_utils.requests import SmartFetch

from ..constants import EVE_URL, USER_CACHE

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
        options {List[str]} -- List of options
        header {str} -- Text you want displayed above the list.

    Returns:
        str -- Completed list in string form
    """
    opts = "".join(
        ["[%s] - %s\n" % (str(idx + 1), option)
         for idx, option in enumerate(options)]
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
            "Please enter the path where %s :\n" % (
                dl_msg if is_download else ul_msg)
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
                        "These are the files found in the provided directory, proceed?"
                    )
                    directory = directory if confirm_upload else None
                else:
                    print("Directory contained no files")
        except (ValueError, TypeError):
            directory = None
            print("Please only enter valid filepaths")
    return directory, files_to_upload


def force_valid_menu_selection(
    number_options: int, prompt: str, err_msg: str = "Invalid selection"
) -> int:
    """
    Script that forces a user to choose a valid option based on the number of options.

    Arguments:
        number_options {int} -- Number of valid options.
        prompt {str} -- Message you want displayed to user.
        err_msg {str} -- Message to be printed when a bad selection is made.

    Returns:
        int -- Index of the user's selection.
    """
    selection = "-1"
    user_input = None

    # Force user to make valid selection
    while int(selection) not in range(1, number_options + 1):
        user_input = input(prompt)
        try:
            int(user_input)
            selection = user_input
        except (TypeError, ValueError):
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


def show_countdown(num_seconds: int, notification: str, step: int = -1) -> None:
    """
    Shows a countdown that counts down from the total number of seconds.

    Arguments:
        num_seconds {int} -- Number of seconds to count down from.
        notification {str} -- Message to print with remaining time.

    Keyword Arguments:
        step {int} -- increment to update count (default: {-1})

    Returns:
        None -- No return.
    """
    if step > 0:
        raise ValueError(
            "Cannot call with positive step. Negative numbers only.")

    for i in range(num_seconds, 0, step):
        print(notification + str(i), end="\r", flush=True)
        time.sleep(step * -1)


def ensure_logged_in() -> Optional[str]:
    """
    Checks if the user is logged in, and if they are not, prompts them to log in.

    Returns:
        str -- API access token
    """
    if not USER_CACHE.get_key():
        print(
            "You are not currently authenticated. Run 'login' to log in"
            + " with a token. If you do not have a token, you can get one from the website."
        )
        return None
    return USER_CACHE.get_key()


def cache_token(token: Optional[str]) -> None:
    """
    Stashes a token in the cli_utilities instantiated USER_CACHE

    Arguments:
        token {str} -- JWT Token

    Returns:
        None -- No return.
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
        cache_token(token)
        print("HEY")
        EVE_FETCHER.get(token=token, endpoint="trials")
        print("Token is valid, you are now logged in!")
        return True
    except RuntimeError as e:
        cache_token(None)
        print(
            "Your token is invalid. Please make sure your token was entered correctly"
        )
        print(e)
        raise e
        return False


def user_prompt_yn(prompt: str) -> bool:
    """
    Prompts the user to pick in a yes or no scenario

    Arguments:
        prompt {str} -- User input prompt

    Returns:
        bool -- True if yes, false if no
    """
    choices = {"y", "yes", "n", "no", "Y", "YES", "N", "NO"}
    selection = "-1"
    while selection not in choices:
        selection = input(prompt + " [Y/n]:")
        if selection not in choices:
            print("Please select either yes or no")
    return bool(selection in {"y", "yes", "Y", "YES"})


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
        user_response = EVE_FETCHER.get(
            endpoint="accounts_info", token=eve_token
        ).json()["_items"]
        if not user_response:
            print("No account found for user.")
            return None
        email = user_response[0]["email"]
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

    user_trials = [x for x in trials if email in x["collaborators"]]

    if not user_trials:
        print("No trials were found for this user.")
        return None

    trial_name_display = []
    for trial in user_trials:
        if "locked" in trial and not trial["locked"]:
          status = u"\U0001f535"
        else:
          status = u"\U0001f512" 
        trial_name_display.append(trial["trial_name"] + "    " + status)

    selected_trial = user_trials[
        option_select_framework(
            trial_name_display, "=====| Available Trials |=====")
        - 1
    ]
    return Selections(eve_token, selected_trial, {})


def select_assay(selected_trial: dict) -> Optional[dict]:
    """
    Choose an assay from the list of assays registered to the trial.

    Arguments:
        selected_trial {dict} -- Trial mongo record.

    Returns:
        Optional[dict] -- Assay dictionary object, or None.
    """
    if "assays" not in selected_trial or not selected_trial["assays"]:
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


def delete_record(record: dict, endpoint: str, token: str) -> None:
    """
    Delete a record from the specified endpoint.

    Arguments:
        record {dict} -- Record to be included. Must include _id and _etag.
        endpoint {str} -- Endpoint to send the request to.
        token {str} -- JWT.

    Returns:
        None -- No return.
    """
    EVE_FETCHER.delete(
        endpoint=endpoint,
        item_id=record["_id"],
        _etag=record["_etag"],
        token=token,
        code=204,
    )


def pick_sample_id(records: List[dict]) -> Optional[str]:
    """
    Function to let a user pick a sample ID from all unique sample IDs in a list of records.

    Arguments:
        records {List[dict]} -- List of /data records.

    Returns:
        Optional[str] -- Chosen sample ID.
    """
    sample_ids: List[str] = []
    for rec in records:
        sample_ids = sample_ids + rec["sample_ids"]

    sample_set = list(set(sample_ids))
    if not sample_set:
        return None
    sample_set.sort()
    sample_selection = option_select_framework(
        sample_set, "These are the available samples, choose one to delete."
    )

    return sample_set[sample_selection - 1]


def delete_related_records(
    records: List[dict], sample_id: str, selections: Selections
) -> None:
    """
    Deletes all records related to a particular sample ID.

    Arguments:
        records {List[dict]} -- List of records returned from /data
        sample_id {str} -- Chosen Sample ID.
        selections {Selections} -- User's trial selection.

    Returns:
        None -- No return.
    """
    query: dict = {
        "trial": selections.selected_trial["_id"], "sample_ids": sample_id}
    token = selections.eve_token
    to_delete = [x for x in records if sample_id in x["sample_ids"]]

    # Also get related analysis records
    an_endpoint = "analysis?where=%s" % json.dumps(query)

    try:
        analysis = EVE_FETCHER.get(
            endpoint=an_endpoint, token=token).json()["_items"]
    except RuntimeError as rte:
        print("Failed to fetch records from /analysis: %s" % str(rte))
        return

    try:
        for item in to_delete:
            delete_record(item, "data_edit", token)
            print("Record %s deleted." % item["file_name"])
        for run in analysis:
            delete_record(run, "analysis", token)
            print("Analysis run record %s deleted." % run["_id"])
        print("All records related to sample %s deleted." % sample_id)
    except RuntimeError as rte:
        print("There was an error deleting the records: %s" % str(rte))


def set_unprocessed_maf(selections: Selections):
    try:
        query = "data?where=%s" % json.dumps(
            {"trial": selections.selected_trial["_id"], "data_format": "MAF"}
        )
        records = EVE_FETCHER.get(
            endpoint=query, token=selections.eve_token).json()
    except RuntimeError as rte:
        print(str(rte))
        return

    for rec in records["_items"]:
        try:
            EVE_FETCHER.patch(
                endpoint="data_edit",
                item_id=rec["_id"],
                _etag=rec["_etag"],
                json={"processed": False},
                code=200,
                token=selections.eve_token,
            )
            print("Set record %s to unprocessed" % rec["file_name"])
        except RuntimeError as rte:
            print(
                "Failed to set sample maf %s as unprocessed: %s"
                % (rec["file_name"], str(rte))
            )


def simple_query(endpoint: str, token: str) -> List[dict]:
    """
    Fetches from an endpoint using values from selections.

    Arguments:
        endpoint {str} -- API Endpoint to query.
        token {str} -- JWT

    Returns:
        List[dict] -- List of records returned.
    """
    try:
        return EVE_FETCHER.get(endpoint=endpoint, token=token).json()["_items"]
    except RuntimeError as rte:
        print("Failed to fetch records from endpoint: %s : %s" %
              (endpoint, str(rte)))
    except KeyError:
        print("No _items field returned.")
    return []


def run_sample_delete() -> None:
    """
    Allows user to delete a sample on a trial.

    Returns:
        None -- No return.
    """
    selections = select_trial("Please select a trial to delete samples from: ")

    if not selections:
        return

    if not selections.selected_trial["locked"]:
        if not user_prompt_yn(
            "The selected trial is not locked. Would you like to lock it?"
        ) or not lock_trial(True, selections):
            print("The delete option requires the trial to be locked to proceed.")
            return

    query: dict = {"trial": selections.selected_trial["_id"]}
    endpoint: str = "data?where=%s" % json.dumps(query)
    data = simple_query(endpoint, selections.eve_token)
    sample_id = pick_sample_id(data)

    if not sample_id:
        print("No samples found for this trial!")
        return

    query["sample_ids"] = sample_id
    delete_related_records(data, sample_id, selections)

    yes = True
    while yes:
        yes = user_prompt_yn(
            "Do you want to delete another sample from this trial?")
        if yes:
            # Fetch from /data again to get rid of the deleted sample.
            data = simple_query(endpoint, selections.eve_token)
            sample_id = pick_sample_id(data)
            if not sample_id:
                print("There are no more samples associated with this trial.")
                yes = False
            else:
                delete_related_records(data, sample_id, selections)

    try:
        trial_refresh = EVE_FETCHER.get(
            endpoint="trials",
            item_id=selections.selected_trial["_id"],
            token=selections.eve_token,
        ).json()
        selections = Selections(selections.eve_token, trial_refresh, {})
    except RuntimeError as rte:
        print("Failed to get an updated _etag for trial: %s" % str(rte))

    if user_prompt_yn("Do you want to delete samples from another trial?"):
        if user_prompt_yn(
            "Before switching to the new trial, is this trial ready to be unlocked?"
        ):
            lock_trial(False, selections)
        run_sample_delete()
    elif user_prompt_yn("Is the trial ready to be unlocked?"):
        lock_trial(False, selections)
        set_unprocessed_maf(selections)


def run_lock_trial() -> None:
    """
    Allows an administrator to lock or unlock a trial.

    Returns:
        None -- No return.
    """
    selections = select_trial("This is the trial locking function:")

    if not selections:
        return

    selected_trial = selections.selected_trial
    if "locked" in selected_trial and selected_trial["locked"]:
        if user_prompt_yn("Trial is locked. Do you want to unlock it?"):
            is_locking = False
        else:
            return
    elif "locked" in selected_trial:
        is_locking = True
    else:
        print(
            "Error: Trial record has no lock status field. Please report this to the developers."
        )
        return

    lock_trial(is_locking, selections)


def lock_trial(is_locking: bool, selections: Selections) -> bool:
    """
    Function to lock or unlock a trial.

    Arguments:
        is_locking {dict} -- Boolean to indicate whether it is a lock or unlock.
        selections {Selections} -- User selection object.

    Returns:
        bool -- True if success, else false.
    """
    adjective = "locked" if is_locking else "unlocked"
    selected_trial = selections.selected_trial
    trial_id = selected_trial["_id"]
    try:
        EVE_FETCHER.patch(
            endpoint="trials",
            item_id=trial_id,
            _etag=selected_trial["_etag"],
            json={"locked": is_locking},
            token=selections.eve_token,
        )
        print("Trial %s %s successfully" %
              (selected_trial["trial_name"], adjective))
        return True
    except RuntimeError as rte:
        if "401" in str(rte):
            print(
                "You are not allowed to lock trials."
                + " Trials may only be locked by an administrator"
            )
        else:
            print(
                "Failed to %s trial %s: %s"
                % (adjective[:-2], selected_trial["trial_name"], str(rte))
            )
        return False
