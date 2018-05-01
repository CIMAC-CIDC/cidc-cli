#!/usr/bin/env python3
"""
Class defining the behavior of the interactive command line interface
"""

import cmd
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
    ensure_logged_in
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
        'trial': selections.selected_assay['_id'],
        'assay': selections.selected_trial['assay_id']
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


def run_upload_process() -> None:
    """
    Function responsible for guiding the user through the upload process
    """

    selections = select_assay_trial(
        "This is the upload function\n"
    )

    if not selections:
        return

    # Have user make their selections
    eve_token = selections.eve_token
    selected_trial = selections.selected_trial
    selected_assay = selections.selected_assay

    # Query the selected assay ID to get the inputs.
    assay_r = EVE_FETCHER.get(
        token=eve_token, endpoint="assays/" + selected_assay['assay_id']
    ).json()

    non_static_inputs = assay_r['non_static_inputs']
    sample_ids = selected_trial['samples']
    file_upload_dict, upload_dir = get_files(sample_ids, non_static_inputs)

    payload = {
        'number_of_files': len(file_upload_dict),
        'status': {
            'progress': 'In Progress',
        },
        'files': create_payload_objects(file_upload_dict, selected_trial, selected_assay)
    }

    response_upload = EVE_FETCHER.post(
        token=eve_token, endpoint='ingestion', json=payload, code=201
    )

    # Execute uploads
    job_id = upload_files(
        upload_dir,
        [file_upload_dict[key] for key in file_upload_dict],
        response_upload.json(),
        eve_token,
        response_upload.headers,
    )

    print("Uploaded, your ID is: " + job_id)


def run_job_query() -> None:
    """
    Allows user to check on the status of running jobs.
    """

    eve_token = None
    progress = None
    status = None

    eve_token = ensure_logged_in()
    res = EVE_FETCHER.get(token=eve_token, endpoint='status').json()
    jobs = res['_items']

    if not jobs:
        print("No jobs found for this user.")
        return

    job_ids = [x['_id'] for x in jobs]

    for job in job_ids:
        print(job)

    selection = option_select_framework(job_ids, "===Jobs===")
    status = jobs[selection - 1]
    progress = status['status']['progress']

    if progress == 'In Progress':
        print('Job is still in progress, check back later')
    elif progress == 'Completed':
        print('Job is completed.')
    elif progress == 'Aborted':
        print('Job was aborted: ' + status['status']['message'])


class ShellCmd(cmd.Cmd, object):
    """
    Class to impart shell functionality to CMD
    """

    def do_shell(self, s):
        """
        Instantiates shell environment

        Arguments:
            s {[type]} -- [description]
        """
        os.system(s)

    def help_shell(self):
        """
        Help message.
        """
        print("Execute shell commands")


class ExitCmd(cmd.Cmd, object):
    """
    Class put together to generate more graceful exit functionality for CMD.
    """

    def cmdloop(self, intro=None):
        """
        Overrides default method to catch ctrl-c and exit gracefully.
        """
        print(self.intro)
        while True:
            try:
                super(ExitCmd, self).cmdloop(intro="")
                self.postloop()
                return False
            except KeyboardInterrupt:
                return True

    def can_exit(self) -> bool:
        """
        Confirms that the CLI can exit.

        Returns:
            boolean -- Simply returns true.
        """
        return True

    def onecmd(self, line) -> bool:
        """Graceful exit behavior

        Arguments:
            line {[type]} -- [description]

        Returns:
            bool -- Returns whether or not user wants to exit.
        """
        response = super(ExitCmd, self).onecmd(line)
        if response and (self.can_exit() or input('exit anyway ? (yes/no):') == 'yes'):
            return True
        return False

    def do_exit(self, s) -> bool:
        """
        Exit the command line tool.

        Arguments:
            s {[type]} -- [description]

        Returns:
            bool -- [description]
        """
        print('Now exiting')
        return True

    def help_exit(self):
        """
        Help function for exit function.
        """
        print("Exit the interpreter.")
        print("You can also use the Ctrl-D shortcut.")

    do_EOF = do_exit
    help_EOF = help_exit


class CIDCCLI(ExitCmd, ShellCmd):
    """
    Defines the CLI interface
    """
    intro = "Welcome to the CIDC CLI Tool"

    def do_upload_data(self, rest=None) -> None:
        """
        Starts the upload process
        """
        run_upload_process()

    def do_download_data(self, rest=None) -> None:
        """
        Starts the download process
        """
        run_download_process()

    def do_query_job(self, rest=None) -> None:
        """
        Allows user to check if their job is done
        """
        run_job_query()


def main():
    """
    Main, starts the loop
    """
    CIDCCLI().cmdloop()


if __name__ == '__main__':
    CIDCCLI().cmdloop()
