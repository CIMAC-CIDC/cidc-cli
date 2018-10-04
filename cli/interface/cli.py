"""
Class defining the behavior of the interactive command line interface
"""
import cmd
import os

from cidc_utils.caching import CredentialCache
from cidc_utils.requests import SmartFetch

from constants import EVE_URL
from download import run_selective_download, run_download_process
from upload import run_upload_np, run_upload_process
from utilities.cli_utilities import (
    cache_token,
    ensure_logged_in,
    option_select_framework,
    user_prompt_yn,
)

USER_CACHE = CredentialCache(100, 600)
EVE_FETCHER = SmartFetch(EVE_URL)


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


class ShellCmd(cmd.Cmd):
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


class ExitCmd(cmd.Cmd):
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

    def do_exit(self, ess) -> bool:  # pylint: disable=W0613
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

    def do_upload_data(self, rest=None) -> None:  # pylint: disable=W0613
        """
        Starts the upload process
        """
        run_upload_process()

    def do_upload_no_pipeline(self, rest=None) -> None:  # pylint: disable=W0613
        """[summary]

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})

        Returns:
            None -- [description]
        """
        run_upload_np()

    def do_download_data(self, rest=None) -> None:  # pylint: disable=W0613
        """
        Starts the download process
        """
        run_download_process()

    def do_selective_download(self, rest=None) -> None:  # pylint: disable=W0613
        """
        Download individual data items.

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})

        Returns:
            None -- [description]
        """
        run_selective_download()

    def do_query_job(self, rest=None) -> None:  # pylint: disable=W0613
        """
        Allows user to check if their job is done
        """
        run_job_query()

    def get_user_consent(self, rest=None) -> None:  # pylint: disable=W0613
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