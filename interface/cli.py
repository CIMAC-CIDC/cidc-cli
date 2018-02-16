#!/usr/bin/env python3
"""
Class defining the behavior of the interactive command line interface
"""


import cmd
import os
from upload import find_eve_token


def run_upload_process():
    """
    Function responsible for guiding the user through the upload process
    """
    username = input("This is the upload functionality, to begin please enter a username:\n")
    token_path = print(
        "Welcome, " + username + "please enter the path to your authorization token:\n"
        )
    eve_token = find_eve_token(token_path)


class CIDCCLI(cmd.Cmd):
    """
    Defines the CLI interface
    """

    intro = "Welcome to the CIDC CLI Tool"

    def do_upload_data(self):
        run_upload_process()

    def do_EOF(self):
        """
        Provides a way to exit tool

        Arguments:
            line {[type]} -- [description]

        Returns:
            [type] -- [description]
        """

        return True


if __name__ == '__main__':
    CIDCCLI().cmdloop()
