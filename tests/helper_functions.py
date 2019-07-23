#!/usr/bin/env python
"""
Some functions for running unit tests more easily.
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

from typing import Callable, List
from unittest.mock import patch


def mock_with_inputs(inputs: List[object], function: Callable, arguments: List[object]):
    """
    Function that passes strings to input calls in the function.

    Arguments:
        inputs {List[object]} -- Responses to the prompts, in order.
        function {Callable} -- The function being mocked.
        arguments {List[object]} -- Arguments to be called on the actual function.

    Returns:
        object -- Return type is dependent on the function passed in.
    """

    def mock_input(prompt: object) -> str:
        """
        Simple function that pops the input array.

        Arguments:
            s {object} -- [description]

        Returns:
            str -- The next prompt response.
        """
        return inputs.pop(0)

    with patch("builtins.input", mock_input):
        return function(*arguments)


class FakeFetcher(object):
    """
    Class to provide the .json() method for mocking http response calls.

    Arguments:
        object {[type]} -- [description]

    Returns:
        [type] -- [description]
    """

    def __init__(self, response):
        """[summary]

        Arguments:
            response {[type]} -- [description]
        """
        self.response = response

    def json(self):
        """
        Returns the json object passed to it on init.

        Returns:
            [type] -- [description]
        """
        return self.response
