#!/usr/bin/env python
"""
Module for doing downloads and related functions.
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

import json
import math
import os
import sys
import subprocess
from typing import List, Optional

from cidc_utils.requests import SmartFetch

from ..constants import EVE_URL
from ..utilities.cli_utilities import (
    generate_options_list,
    get_valid_dir,
    select_assay_trial,
)

EVE_FETCHER = SmartFetch(EVE_URL)
VALID_COMMANDS = ["n", "p", "e", "a"]


def gsutil_copy_data(records: List[dict], download_directory: str) -> None:
    """
    Copies files from a google bucket to the user's local filesystem.

    Arguments:
        records {List[str]} -- List of google bucket URIs.
        download_directory {str} -- Path where the user wants the files to go.
    """
    for record in records:
        gs_uri = record["gs_uri"]
        gs_args = ["gsutil", "cp", gs_uri, download_directory]
        try:
            subprocess.check_output(gs_args, shell=False)
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
    rows = 0
    try:
        if sys.stdout.isatty():
            rows = os.get_terminal_size(0)[0]
    except OSError:
        rows = 20
    except IndexError:
        rows = 20

    if not rows or rows < 2:
        rows = 20

    # If someone has a super tall terminal, don't give them a giant list.
    if rows > 50:
        rows = 50

    # Assume that some of the rows will be taken up with console print statements.
    available_rows = int(rows * 0.8)
    return [
        list_items[available_rows * i: available_rows * i + available_rows]
        for i in range(0, math.ceil(len(list_items) / available_rows))
    ]


def elegant_options(
    paginated_list: List[List[dict]], commands: List[str], prompt: str
) -> List[str]:
    """
    Function that persents users with a list of choices, along with management functions
    letting them browse pages.

    Arguments:
        items {List[List[dict]]} -- Options to be displayed.
        commands {List[str]} -- Commands for navigating the menu.
        prompt {str} -- Message to be displayed.

    Returns:
        List[str] -- Formatted options list.
    """
    str_pag_list = [[x['file_name'] for x in page] for page in paginated_list]
    formatted_list = [generate_options_list(
        page, prompt) for page in str_pag_list]
    with_commands = [sublist + "\n" +
                     ", ".join(commands) for sublist in formatted_list]
    return with_commands


def get_files_for_dl() -> Optional[List[dict]]:
    """
    Workflow for guiding users to download their files.

    Returns:
        List[dict] -- List of files.
    """
    selections = select_assay_trial("This is the download function\n")

    if not selections:
        return None

    trial_query = {
        "trial": selections.selected_trial["_id"],
        "assay": selections.selected_assay["assay_id"],
    }
    query_string = "data?where=%s" % (json.dumps(trial_query))
    records = EVE_FETCHER.get(
        token=selections.eve_token, endpoint=query_string, code=200
    ).json()
    retreived = records["_items"]

    if not retreived:
        print("No data records found matching that criteria")
        return None

    print("Files to be downloaded: ")
    for ret in records["_items"]:
        print(ret["file_name"])
    return records


def run_download_process() -> None:
    """
    Function for users to download data.
    """
    records = get_files_for_dl()
    if not records:
        return
    gsutil_copy_data(records, get_valid_dir()[0])


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

    commands = ["[N]ext", "[P]revious", "[E]xit", "Download [A]ll: "]
    paginated_list = paginate_selections(retrieved)
    pages = elegant_options(paginated_list, commands,
                            "=====| Files to Download |=====")
    print(paginated_list)
    page_index = 0
    end_dl = False

    mercy = 0
    while not end_dl and mercy < 10:
        mercy += 1
        try:
            selection = input(pages[page_index])
            sel_str = selection.lower()

            if sel_str not in VALID_COMMANDS:
                selected_item = paginated_list[page_index][int(selection) - 1]
                print(selected_item, "SELECTED_ITEM")
                download_dir = get_valid_dir()[0]
                gsutil_copy_data([selected_item], download_dir)
                print("Data download successful")

            # Next page.
            if sel_str == "n" and page_index + 1 < len(pages):
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
            selection = None
            print("Please enter either an integer or a command")
        except IndexError:
            print("Selection out of range. Choose only from the files shown.")
