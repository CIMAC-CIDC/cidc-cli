#!/usr/bin/env python3
"""
Tests for the command line interface
"""
from typing import Callable, List
from unittest.mock import patch
from unittest import TestCase

from cidc_utils.caching import CredentialCache

import utilities.cli_utilities
from utilities.cli_utilities import *


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


def test_generate_options_list():
    """
    Test for the function generate_options_list
    """
    menu_items = ["A", "B", "C"]
    header = "test"
    menu = generate_options_list(menu_items, header)
    assert len(menu.split("\n")) == 5


def test_force_valid_menu_selection():
    """
    Test for the function force_valid_menu_selection
    """
    number_options = 3
    prompt = "a"
    with patch("builtins.input", return_value="2"):
        assert force_valid_menu_selection(number_options, prompt) == 2


def test_user_prompt_yn():
    """
    Test for the function user_prompt_yn
    """
    with patch("builtins.input", return_value="y"):
        assert user_prompt_yn("")
    with patch("builtins.input", return_value="n"):
        assert not user_prompt_yn("")


def test_get_valid_dir():
    """
    Test function for get_valid_dir
    """
    inputs = ["cli/tests/test_directory", "y"]
    assert len(mock_with_inputs(inputs, get_valid_dir, [False])[1]) == 3


def test_option_select_framework():
    """
    Test function for option_select_framework
    """
    options = ["one", "two", "three"]
    prompt = "foo"
    with patch("builtins.input", return_value="1"):
        assert option_select_framework(options, prompt)


def test_ensure_logged_in():
    """
    Test function for ensure_logged_in
    """
    cache = CredentialCache(100, 300)
    cache.cache_key("foo")
    utilities.cli_utilities.USER_CACHE = cache
    assert ensure_logged_in()


def test_get_files():
    """
    Test for get_files,
    """
    with patch(
        "utilities.cli_utilities.get_valid_dir",
        return_value=("./some/path", ["file_3D", "file2_3D"]),
    ):
        with patch(
            "utilities.cli_utilities.validate_and_extract",
            return_value={"foo": {"sample_id": "3D", "mapping": "file2"}},
        ):
            assert get_files(["3D"], ["file", "file2"]) == (
                {"foo": {"sample_id": "3D", "mapping": "file2"}},
                "./some/path",
            )


def test_create_payload_objects():
    """
    Test for create_payload_objects
    """

    file_dict = {"file_name_1": {"mapping": "map", "sample_id": "1234"}}
    assay = {"assay_id": "321"}
    trial = {"_id": "456"}
    payload = create_payload_objects(file_dict, trial, assay)
    assert payload == [
        {
            "assay": "321",
            "trial": "456",
            "file_name": "file_name_1",
            "sample_id": "1234",
            "mapping": "map",
        }
    ]


def test_validate_and_extract():
    """
    Test function for validate_and_extract
    """
    # Test good input.
    inputs = ["file1", "file2"]
    arguments_good = [
        ["file1_3D", "file2_3D", "file1_4C", "file2_4C"],
        ["3D", "4C"],
        inputs,
    ]
    result = mock_with_inputs(
        ["1", "1", "1", "1"], validate_and_extract, arguments_good
    )
    assert result == {
        "file1_3D": {"sample_id": "3D", "mapping": "file1"},
        "file2_3D": {"sample_id": "3D", "mapping": "file2"},
        "file1_4C": {"sample_id": "4C", "mapping": "file1"},
        "file2_4C": {"sample_id": "4C", "mapping": "file2"},
    }
    # Test unmatched sample ID.
    arguments_bad = [["file1_4B", "file2_3D"], ["3D"], inputs]
    result_bad = mock_with_inputs(["1", "1"], validate_and_extract, arguments_bad)
    assert not result_bad


class TestValidateThrow(TestCase):
    """
    Simple test to confirm correct error is raised.

    Arguments:
        TestCase {unittest.TestCase} -- unittest testcase class.
    """
    def test_validate_and_extract_error(self):
        """
        Assert calling too many files raises error.
        """
        inputs = ["file1", "file2"]
        arguments_many = [["file1_3D_B", "file1_3D", "file2_3D"], ["3D"], inputs]
        self.assertRaises(
            RuntimeError,
            mock_with_inputs,
            ["1", "1"],
            validate_and_extract,
            arguments_many,
        )


def test_store_token():
    """
    Test for storing/retrieving a token in Cache.
    """
    from utilities.cli_utilities import USER_CACHE

    cache_token("test")
    assert USER_CACHE.get_key() == "test"
