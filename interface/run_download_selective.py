import os
import subprocess
import json
from cidc_utils.requests import SmartFetch
from cidc_utils.caching import CredentialCache
from upload.upload import upload_files
from utilities.cli_utilities import (
    option_select_framework,
    get_files,
    create_payload_objects,
    select_assay_trial,
    ensure_logged_in,
    user_prompt_yn,
    cache_token
)
from auth0.constants import EVE_URL

USER_CACHE = CredentialCache(100, 600)

EVE_FETCHER = SmartFetch(EVE_URL)


def run_download_process() -> None:
    """
    Function for users to download data.
    """
    selections = select_assay_trial("This is the download function\n")

    if not selections:
        return

    trial_query = {
        'trial': selections.selected_trial['_id'],
        'assay': selections.selected_assay['assay_id']
    }

    query_string = "data?where=%s" % (json.dumps(trial_query))
    records = EVE_FETCHER.get(
        token=selections.eve_token, endpoint=query_string, code=200).json()
    download_directory = None
    retreived = records['_items']

    if not retreived:
        print('No data records found matching that criteria')
        return

    print('Files to be downloaded: ')
    for ret in records['_items']:
        print(ret['file_name'])

    while not download_directory:
        download_directory = input(
            "Please enter the path where you would like the files to be downloaded:\n"
        )
        try:
            if not os.path.isdir(download_directory):
                print("The given path is not valid, please enter a new one.")
                download_directory = None
        except ValueError:
            download_directory = None
            print("Please only enter valid filepaths")

    for record in records['_items']:
        gs_uri = record['gs_uri']
        gs_args = [
            "gsutil",
            "cp",
            gs_uri,
            download_directory
        ]
        try:
            subprocess.run(gs_args)
        except subprocess.CalledProcessError as error:
            error_string = 'Shell command generated error' + str(error.output)
            print(error_string)

    print("Download of files complete")