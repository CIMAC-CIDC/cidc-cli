"""
Function for doing downloads.
"""
import os
import math
import subprocess
import json
from typing import List
from cidc_utils.requests import SmartFetch
from utilities.cli_utilities import (
    select_assay_trial,
    generate_options_list,
    get_valid_dir,
)
from auth0.constants import EVE_URL

EVE_FETCHER = SmartFetch(EVE_URL)


def gsutil_copy_data(records: List[str], download_directory: str) -> None:
    """
    Copies files from a google bucket to the user's local filesystem.

    Arguments:
        records {List[str]} -- List of google bucket URIs.
        download_directory {str} -- Path where the user wants the files to go.
    """
    for record in records["_items"]:
        gs_uri = record["gs_uri"]
        gs_args = ["gsutil", "cp", gs_uri, download_directory]
        try:
            subprocess.run(gs_args)
        except subprocess.CalledProcessError as error:
            error_string = "Shell command generated error" + str(error.output)
            print(error_string)


def paginate_selections(list_items: List[dict]) -> List[List[dict]]:
    """
    Takes a list of items, and attempts to paginate them to fit the user's terminal.

    Arguments:
        list_items {List[dict]} -- List of objects to be paginated.

    Returns:
       List[List[dict]] -- A list of list of dicts, with each sublist
       being made to fit in the user's terminal.
    """
    rows, columns = os.popen("stty size", "r").read().split()

    # If someone has a super tall terminal, don't give them a giant list.
    if rows > 50:
        rows = 50

    # Assume that some of the rows will be taken up with console print statements.
    available_rows = int(rows * 0.8)
    return [
        list_items[available_rows * i : available_rows * i + available_rows]
        for i in range(0, math.ceil(len(list_items) / available_rows))
    ]


def elegant_options(
    paginated_list: List[List[dict]], commands: List[str], prompt: str
) -> List[str]:
    """[summary]

    Arguments:
        items {List[List[dict]]} -- [description]
        commands {List[str]} -- [description]
        prompt {str} -- [description]

    Returns:
        List[str] -- [description]
    """
    # Split the items into pages.
    # Create the text for each page
    formatted_list = [generate_options_list(page, prompt) for page in paginated_list]
    # List available commands
    with_commands = [sublist + "\n" + ", ".join(commands) for sublist in formatted_list]
    return with_commands


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


VALID_COMMANDS = ["n", "p", "e", "a"]


def run_selective_download() -> None:
    """
    Work in progress function for providing a cleaner interface for
    selective user downloads.
    """
    selections = select_assay_trial("This is the download function \n")

    if not selections:
        return

    trial_query = {
        "trial": selections.selected_trial["_id"],
        "assay": selections.selected_assay["assay_id"],
    }

    query_string = "data?where=%s" % (json.dumps(trial_query))
    records = EVE_FETCHER.get(
        token=selections.eve_token, endpoint=query_string, code=200
    ).json()
    retrieved = records["_items"]

    if not retrieved:
        print("No data records found matching that criteria")
        return

    commands = ["[N]ext", "[P]revious", "[E]xit", "Download [A]ll"]
    paginated_list = paginate_selections(retrieved)
    pages = elegant_options(paginated_list, commands, "====== Files to Download =====.")
    page_index = 0
    end_dl = False

    while not end_dl:
        try:
            selection = input(pages[page_index])
            sel_str = selection.lower()

            if not sel_str in VALID_COMMANDS:
                int_selection = int(selection)
                selected_item = paginated_list[page_index][int_selection]
                download_dir = get_valid_dir()[0]
                gsutil_copy_data([selected_item], download_dir)
                print("Data download successful")

            # Next page.
            if sel_str == "n" and page_index + 1 <= len(pages):
                page_index += 1
            elif sel_str == "n":
                print("You are on the last page already.")

            # Previous page.
            if sel_str == "p" and page_index - 1 >= 0:
                page_index -= 1
            elif sel_str == "p":
                print("You are on the first page already.")

            # Download all.
            if sel_str == "a":
                download_dir = get_valid_dir()[0]
                gsutil_copy_data(retrieved, download_dir)
                print("Data download successful, exiting download function.")
                end_dl = True

            # Exit.
            if sel_str == "e":
                end_dl = True

        except ValueError:
            print("Please enter either an integer or a command")
        except IndexError:
            print("Selection out of range. Choose only from the files shown.")