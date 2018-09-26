"""
Class defining the behavior of the interactive command line interface
"""
import cmd
import os
import json
from cidc_utils.requests import SmartFetch
from cidc_utils.caching import CredentialCache
from upload.upload import upload_files, RequestInfo, run_upload_np
from interface.download import run_selective_download, gsutil_copy_data
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

    gsutil_copy_data(records["_items"], get_valid_dir())


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

    def do_exit(self, ess) -> bool: #pylint: disable=W0613
        """
        Exit the command line tool.

        Arguments:
            ess {[type]} -- [description]

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
    Defines the CLI
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

    def do_upload_data(self, rest=None) -> None: #pylint: disable=W0613
        """
        Starts the upload process
        """
        run_upload_process()

    def do_upload_no_pipeline(self, rest=None) -> None: #pylint: disable=W0613
        """[summary]

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})

        Returns:
            None -- [description]
        """
        run_upload_np()

    def do_download_data(self, rest=None) -> None: #pylint: disable=W0613
        """
        Starts the download process
        """
        run_download_process()

    def do_selective_download(self, rest=None) -> None: #pylint: disable=W0613
        """
        Download individual data items.

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})

        Returns:
            None -- [description]
        """
        run_selective_download()

    def do_query_job(self, rest=None) -> None: #pylint: disable=W0613
        """
        Allows user to check if their job is done
        """
        run_job_query()

    def get_user_consent(self, rest=None) -> None: #pylint: disable=W0613
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
