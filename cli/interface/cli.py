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
from upload.upload import upload_files, RequestInfo
from interface.download import run_selective_download
from utilities.cli_utilities import (
    option_select_framework,
    get_files,
    get_valid_dir,
    create_payload_objects,
    select_assay_trial,
    ensure_logged_in,
    user_prompt_yn,
    cache_token,
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
        return

    print("Files to be downloaded: ")
    for ret in records["_items"]:
        print(ret["file_name"])

    download_directory = get_valid_dir()

    for record in records["_items"]:
        gs_uri = record["gs_uri"]
        gs_args = ["gsutil", "cp", gs_uri, download_directory]
        try:
            subprocess.run(gs_args)
        except subprocess.CalledProcessError as error:
            error_string = "Shell command generated error" + str(error.output)
            print(error_string)

    print("Download of files complete")


def run_upload_process() -> None:
    """
    Function responsible for guiding the user through the upload process
    """

    selections = select_assay_trial("This is the upload function\n")

    if not selections:
        return

    # Have user make their selections
    eve_token = selections.eve_token
    selected_trial = selections.selected_trial
    selected_assay = selections.selected_assay

    # Query the selected assay ID to get the inputs.
    assay_r = EVE_FETCHER.get(
        token=eve_token, endpoint="assays/" + selected_assay["assay_id"]
    ).json()

    non_static_inputs = assay_r["non_static_inputs"]
    sample_ids = selected_trial["samples"]
    file_upload_dict, upload_dir = get_files(sample_ids, non_static_inputs)

    payload = {
        "number_of_files": len(file_upload_dict),
        "status": {"progress": "In Progress"},
        "files": create_payload_objects(
            file_upload_dict, selected_trial, selected_assay
        ),
    }

    response_upload = EVE_FETCHER.post(
        token=eve_token, endpoint="ingestion", json=payload, code=201
    )

    req_info = RequestInfo(
        [file_upload_dict[key] for key in file_upload_dict],
        response_upload.json(),
        eve_token,
        response_upload.header,
    )

    # Execute uploads
    job_id = upload_files(upload_dir, req_info)

    print("Uploaded, your ID is: " + job_id)


def run_job_query() -> None:
    """
    Allows user to check on the status of running jobs.
    """

    eve_token = ensure_logged_in()
    res = EVE_FETCHER.get(token=eve_token, endpoint="status").json()
    jobs = res["_items"]

    if not jobs:
        print("No jobs found for this user.")
        return

    job_ids = [x["_id"] for x in jobs]

    for job in job_ids:
        print(job)

    selection = option_select_framework(job_ids, "===Jobs===")
    status = jobs[selection - 1]
    progress = status["status"]["progress"]

    if progress == "In Progress":
        print("Job is still in progress, check back later")
    elif progress == "Completed":
        print("Job is completed.")
    elif progress == "Aborted":
        print("Job was aborted: " + status["status"]["message"])


def run_upload_np() -> None:
    """
    Allows a user to upload data that is not marked for pipeline use.
    """
    selections = select_assay_trial("This is the non-pipeline upload function\n")
    if not selections:
        return

    # Have user make their selections
    eve_token = selections.eve_token
    selected_trial = selections.selected_trial
    selected_assay = selections.selected_assay
    upload_dir, files_to_upload = get_valid_dir(is_download=False)

    if not len(files_to_upload) == len(set(files_to_upload)):
        print("Error, duplicate names in file list, aborting")
        return None

    # Sanity check number of files per ID
    if not len(files_to_upload) % 2 == 0:
        print(
            "Odd number of files being uploaded. \
            Each file must have an associated metadata file."
        )
        return None

    print(
        "You are uploading a data format which requires a \
        metadata file. For each file being uploaded, first select the data file, then its \
        associated metadata"
    )
    # Copy list by value for manipualtion.
    file_list = files_to_upload[:]
    payload_list = []

    while file_list:
        # Select the data file.
        selection = option_select_framework(file_list, "Please select a data file")
        # Save a reference.
        selected_file = file_list[selection - 1]
        # Add it to the ingestion manifest.
        payload_list.append(
            {
                "assay": selected_assay["assay_id"],
                "trial": selected_trial["_id"],
                "file_name": selected_file,
                "mapping": "olink-data",
            }
        )

        # Delete from the list.
        del file_list[selection - 1]

        # Select the metadata.
        meta_selection = option_select_framework(
            file_list, "Select the corresponding metadata"
        )

        # Add to ingestion manifest, with the mapping being a reference to the associated file.
        payload_list.append(
            {
                "assay": selected_assay["assay_id"],
                "trial": selected_trial["_id"],
                "file_name": file_list[meta_selection - 1],
                "mapping": selected_file,
            }
        )
        del file_list[meta_selection - 1]

        payload = {
            "number_of_files": len(files_to_upload),
            "status": {"progress": "In Progress"},
            "files": payload_list,
        }

        response_upload = EVE_FETCHER.post(
            token=eve_token, endpoint="ingestion", json=payload, code=201
        )

        req_info = RequestInfo(
            files_to_upload, response_upload.json(), eve_token, response_upload.headers
        )

        # Execute uploads
        job_id = upload_files(upload_dir, req_info)

        print("Uploaded, your ID is: " + job_id)


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
        if not user_prompt_yn("Do you agree to the above terms and conditions? "):
            return True
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
        """
        Graceful exit behavior

        Arguments:
            line {[type]} -- [description]

        Returns:
            bool -- Returns whether or not user wants to exit.
        """
        response = super(ExitCmd, self).onecmd(line)
        if response and (self.can_exit() or input("exit anyway ? (yes/no):") == "yes"):
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
        print("Now exiting")
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

    intro = (
        "Welcome to the CIDC CLI Tool, you are about to access a system which contains "
        "private medical data protected by federal law. Unauthorized use of this system is "
        "strictly prohibited and subject to criminal and civil penalties "
        "\n"
        "All information "
        "stored on this system is owned by the NCI. By using this tool you consent to the "
        "monitoring and recording of your actions on this system. You also agree to "
        "refrain from engaging in any illegal or improper behavior while using this system. "
        "\n"
        "By downloading any data from the CIDC information system, you are agreeing to take "
        "responsibility for the security of said data. You may not copy, transmit, print out"
        ", or in any way cause the information to leave a secured computing environment "
        "where it may be seen or accessed by unauthorized individuals. Sharing your account "
        "with anyone else is strictly prohibited."
        "\n"
        "If you become aware of any threat to the system or possible breach of data, you "
        "are required to immediately notify the CIDC"
    )

    def do_upload_data(self, rest=None) -> None:
        """
        Starts the upload process
        """
        run_upload_process()

    def do_upload_no_pipeline(self, rest=None) -> None:
        """[summary]

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})

        Returns:
            None -- [description]
        """
        run_upload_np()

    def do_download_data(self, rest=None) -> None:
        """
        Starts the download process
        """
        run_download_process()

    def do_selective_download(self, rest=None) -> None:
        """
        Download individual data items.

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})

        Returns:
            None -- [description]
        """
        run_selective_download()

    def do_query_job(self, rest=None) -> None:
        """
        Allows user to check if their job is done
        """
        run_job_query()

    def get_user_consent(self, rest=None) -> None:
        """
        Ensures the user reads and agrees to TOS.

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})

        Returns:
            None -- [description]
        """
        if not user_prompt_yn("Do you agree to the above terms and conditions?"):
            return True

    def do_jwt_login(self, token=None) -> None:
        """
        Stores the users Auth Token to be used for calls to the Eve server.
        :param rest:
        :return:
        """
        if not token:
            print(
                "Please paste your JWT token obtained from the CIDC Portal to log in."
            )
        else:
            cache_token(token)


def main():
    """
    Main, starts the loop
    """
    CIDCCLI().cmdloop()


if __name__ == "__main__":
    CIDCCLI().cmdloop()
