#!/usr/bin/env python
"""
Class defining the behavior of the interactive command line interface
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

# pylint: disable=R0201
import cmd
import os
import platform

from cidc_utils.requests import SmartFetch

from ..constants import EVE_URL, BANNER, USER_CACHE
from ..download import run_selective_download, run_download_process
from ..upload import run_upload_process
from ..utilities.cli_utilities import (
    user_prompt_yn,
    run_jwt_login,
    run_sample_delete,
    run_lock_trial,
)

EVE_FETCHER = SmartFetch(EVE_URL)

if platform.system() == "Darwin":
    import readline  # noqa: F401


class ShellCmd(cmd.Cmd):
    """
    Class to impart shell functionality to CMD
    """

    def shell(self, command):
        """
        Instantiates shell environment

        Arguments:
            command {[type]} -- [description]
        """
        os.system(command)

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
        if not user_prompt_yn("Do you agree to the above terms and conditions?"):
            return True

        print(BANNER)
        login_message = (
            "Welcome to the CIDC CLI! Before doing anything else, log in to our "
            + "system using the JWT you received from the web portal."
        )
        print(login_message)

        while not USER_CACHE.get_key():
            token = input("Please enter your token here: ")
            run_jwt_login(token)

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


class CIDCCLI(ExitCmd, ShellCmd):
    """
    Defines the CLI
    """

    intro = (
        "Welcome to the CIDC Command Line Interface (CLI) Tool."
        "\n"
        "\n"
        "You are about to access a system which contains data protected by federal law."
        "\n"
        "\n"
        "Unauthorized use of this system is strictly prohibited and subject to criminal "
        "\n"
        "and civil penalties. All information stored on this system is owned by the "
        "\n"
        "National Cancer Institute (NCI)."
        "\n"
        "\n"
        "By using this tool, you consent to the monitoring and recording of your "
        "\n"
        "actions on this system. You also agree to refrain from engaging in any illegal "
        "\n"
        "or improper behavior while using this system."
        "\n"
        "\n"
        "By downloading any data from the CIDC information system, you are agreeing to "
        "\n"
        "take responsibility for the security of said data. You may not copy, transmit, "
        "\n"
        "print out, or in any way cause the information to leave a secured computing "
        "\n"
        "environment where it may be seen or accessed by unauthorized individuals."
        "\n"
        "\n"
        "Sharing your account with anyone else is strictly prohibited."
        "\n"
        "\n"
        "If you become aware of any threat to the system or possible breach of data, "
        "\n"
        "you are required to immediately notify the CIDC."
        "\n"
    )

    def do_upload_data(self, rest=None) -> None:  # pylint: disable=W0613
        """
        Starts the upload process
        """
        run_upload_process()

    def do_download_trial_data(self, rest=None) -> None:  # pylint: disable=W0613
        """
        Starts the download process
        """
        run_download_process()

    def do_download_individual_files(self, rest=None) -> None:  # pylint: disable=W0613
        """
        Download individual data items.

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})

        Returns:
            None -- [description]
        """
        run_selective_download()

    def do_delete_wes_sample(self, rest=None) -> None:  # pylint: disable=W0613:
        """
        Delete all files associated with a sample (for WES).
        """
        run_sample_delete()

    def do_toggle_trial_lock(self, rest=None) -> None:  # pylint: disable=W0613:
        """
        Lock or unlock a trial.
        """
        run_lock_trial()

    def get_user_consent(self, rest=None) -> bool:  # pylint: disable=W0613
        """
        Ensures the user reads and agrees to TOS.

        Keyword Arguments:
            rest {[type]} -- [description] (default: {None})

        Returns:
            None -- [description]
        """
        if not user_prompt_yn("Do you agree to the above terms and conditions?"):
            return True
        return False

    def do_login(self, token: str = None) -> None:
        """
        Function for handling a user's login.

        Keyword Arguments:
            token {str} -- User's JWT (default: {None})

        Returns:
            None -- [description]
        """
        if not token:
            print(
                "Please paste your JWT token obtained from the CIDC Portal to log in."
            )
        else:
            run_jwt_login(token)


def main():
    """
    Main, starts the loop
    """
    CIDCCLI().cmdloop()


if __name__ == "__main__":
    CIDCCLI().cmdloop()
