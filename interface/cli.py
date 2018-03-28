#!/usr/bin/env python3
"""
Class defining the behavior of the interactive command line interface
"""

import cmd
import os
import subprocess
import json
from upload.upload import upload_files
from upload.cache_user import CredentialCache
from utilities.cli_utilities import fetch_eve_or_fail, option_select_framework, user_prompt_yn, \
    get_files, create_payload_objects, select_assay_trial, request_eve_endpoint, ensure_logged_in
from auth0.auth0 import run_auth_proc

USER_CACHE = CredentialCache(100, 600)


def run_download_process() -> None:
    """
    Function for users to download data.
    """

    selections = select_assay_trial("This is the download function\n")

    if not selections:
        return

    eve_token, selected_trial, selected_assay = selections
    trial_query = {'trial': selected_trial['_id']}
    assay_query = {'assay': selected_assay['assay_id']}
    query_string = "data?where=%s&where=%s" % (json.dumps(trial_query), json.dumps(assay_query))
    records = fetch_eve_or_fail(eve_token, query_string, None, 200, 'GET')
    download_directory = None
    retreived = records['_items']

    if not retreived:
        print('No data records found matching that criteria')
        return

    print('Files to be downloaded: ')
    for ret in retreived:
        print(ret['file_name'])

    while not download_directory:
        download_directory = input(
            "Please enter the path where you would like the files to be downloaded:\n"
        )
        if not os.path.isdir(download_directory):
            print("The given path is not valid, please enter a new one.")
            download_directory = None

    for record in records['_items']:
        gs_uri = record['gs_uri']
        gs_args = [
            "gsutil",
            "cp",
            gs_uri,
            download_directory
        ]
        try:
            subprocess.run(gs_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
    eve_token, selected_trial, selected_assay = selections

    # Query the selected assay ID to get the inputs.
    assay_r = fetch_eve_or_fail(
        eve_token, "assays/" + selected_assay['assay_id'], None, 200, 'GET'
    )
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

    response_upload = request_eve_endpoint(eve_token, payload, 'ingestion')

    if not response_upload.status_code == 201:
        print('Upload Failed:')
        if response_upload.json:
            print(response_upload.json())
        return

    # Execute uploads
    job_id = upload_files(
        upload_dir,
        [file_upload_dict[key] for key in file_upload_dict],
        response_upload.json(),
        eve_token,
        response_upload.headers,
    )

    print("Uploaded, your ID is: " + job_id)


def run_analysis() -> None:
    """
    Developer function for letting user select analysis to run
    """

    # Obtain user information
    selections = select_assay_trial(
        "This is the analysis function\n"
    )

    if not selections:
        return

    eve_token, selected_trial, selected_assay = selections

    # Get list of sample IDs
    sample_ids = selected_trial['samples']

    # Construct payload, for now just run on all samples
    payload = {
        'trial': selected_trial['_id'],
        'assay': selected_assay['assay_id'],
        'samples': sample_ids,
    }

    res_json = fetch_eve_or_fail(eve_token, "analysis", payload, 201)
    print("Your run has started, to check on its status, query this id: " + res_json['_id'])
    USER_CACHE.add_job_to_cache(res_json['_id'])


def run_job_query() -> None:
    """
    Allows user to check on the status of running jobs.
    """

    eve_token = None
    progress = None
    status = None
    jobs = USER_CACHE.get_jobs()

    if not jobs:
        answer = user_prompt_yn(
            'No records found locally for jobs, would you like to query the database?'
            )
        if not answer:
            return
        eve_token = ensure_logged_in()
        res = fetch_eve_or_fail(eve_token, 'status', None, 200, 'GET')
        jobs = res['_items']
        job_ids = [x['_id'] for x in jobs]
        for job in job_ids:
            print(job)
        selection = option_select_framework(job_ids, "===Jobs===")
        status = jobs[selection - 1]
        progress = status['status']['progress']
    else:
        eve_token = ensure_logged_in()
        selection = option_select_framework(jobs, '====Jobs====')
        res = fetch_eve_or_fail(eve_token, 'analysis', {'_id': jobs[selection - 1]}, 200, 'GET')
        progress = res['_items'][0]['status']['progress']

    if progress == 'In Progress':
        print('Job is still in progress, check back later')
    elif progress == 'Completed':
        print('Job is completed.')
    elif progress == 'Aborted':
        print('Job was aborted: ' + status['status']['message'])

    if not jobs:
        print("There appears to be no running jobs")
        return


def run_oauth() -> None:
    """
    Runs the oauth pipeline.
    """
    key = run_auth_proc()
    USER_CACHE.cache_key(key)


class ShellCmd(cmd.Cmd, object):
    """
    Class to impart shell functionality to CMD
    """

    def do_shell(self, s):
        """Instantiates shell environment

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
                break
            except KeyboardInterrupt:
                return True

    def can_exit(self) -> bool:
        """Confirms that the CLI can exit.

        Returns:
            boolean -- Simply returns true.
        """
        return True

    def onecmd(self, line) -> bool:
        """Graceful exit behavior

        Arguments:
            line {[type]} -- [description]

        Returns:
            [type] -- [description]
        """
        response = super(ExitCmd, self).onecmd(line)
        if response and (self.can_exit() or input('exit anyway ? (yes/no):') == 'yes'):
            return True
        return False

    def do_exit(self, s) -> bool:
        """[summary]

        Arguments:
            s {[type]} -- [description]

        Returns:
            bool -- [description]
        """
        return True

    def help_exit(self):
        """[summary]
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

    def do_oauth(self, rest=None) -> None:
        """[summary]

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})
        """
        run_oauth()

    def do_download_data(self, rest=None) -> None:
        """
        Starts the download process
        """
        run_download_process()

    def do_run_analysis(self, rest=None) -> None:
        """
        Lets user run analysis
        """
        run_analysis()

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
