#!/usr/bin/env python
"""
Tests for the command line interface
"""
import os
import unittest
from unittest.mock import patch

from utilities.cli_utilities import (
    generate_options_list,
    ensure_logged_in,
    option_select_framework,
    cache_token,
    force_valid_menu_selection,
    user_prompt_yn,
    get_valid_dir,
    terminal_sensitive_print,
    run_jwt_login,
    select_assay_trial
)
from tests.helper_functions import mock_with_inputs, FakeFetcher
from constants import USER_CACHE


def test_generate_options_list():
    """
    Test for the function generate_options_list
    """
    menu_items = ["A", "B", "C"]
    header = "test"
    menu = generate_options_list(menu_items, header)
    if not len(menu.split("\n")) == 5:
        raise AssertionError("test_generate_options_list: Assertion Failed")


def test_force_valid_menu_selection():
    """
    Test for the function force_valid_menu_selection
    """
    number_options = 3
    prompt = "a"
    with patch("builtins.input", return_value="2"):
        if force_valid_menu_selection(number_options, prompt) != 2:
            raise AssertionError
    inputs = [4, unittest, 2]
    if (
        mock_with_inputs(inputs, force_valid_menu_selection, [number_options, prompt])
        != 2
    ):
        raise AssertionError("test_force_valid_menu_selection: Assertion Failed")


def test_user_prompt_yn():
    """
    Test for the function user_prompt_yn
    """
    with patch("builtins.input", return_value="y"):
        if not user_prompt_yn(""):
            raise AssertionError("test_user_prompt_yn: Assertion Failed")
    with patch("builtins.input", return_value="n"):
        if user_prompt_yn(""):
            raise AssertionError("test_user_prompt_yn: Assertion Failed")
    inputs = ["z", "n"]
    if mock_with_inputs(inputs, user_prompt_yn, [""]):
        raise AssertionError("test_user_prompt_yn: Assertion Failed")


class TestUploadFunctions(unittest.TestCase):
    """Test class for the update job status function

    Arguments:
        unittest {[type]} -- [description]
    """

    def test_get_valid_dir(self):
        """
        Test function for get_valid_dir
        """
        try:
            os.mkdir("cli/tests/empty_dir")
        except FileExistsError:
            pass
        with self.subTest():
            inputs = ["cli/tests/test_directory", "y"]
            self.assertEqual(
                len(mock_with_inputs(inputs, get_valid_dir, [False])[1]), 3
            )
        with self.subTest():
            inputs = [1, mock_with_inputs, "cli/tests/test_directory", "y"]
            self.assertEqual(
                len(mock_with_inputs(inputs, get_valid_dir, [False])[1]), 3
            )
        with self.subTest():
            inputs = ["cli/tests/empty_dir", "cli/tests/test_directory", "y"]
            self.assertEqual(
                len(mock_with_inputs(inputs, get_valid_dir, [False])[1]), 0
            )


def test_option_select_framework():
    """
    Test function for option_select_framework
    """
    options = ["one", "two", "three"]
    prompt = "foo"
    with patch("builtins.input", return_value="1"):
        if not option_select_framework(options, prompt):
            raise AssertionError("test_option_select_framework: Assertion Failed")


def test_ensure_logged_in():
    """
    Test function for ensure_logged_in
    """
    if ensure_logged_in():
        raise AssertionError("test_ensure_logged_in: Assertion Failed")
    USER_CACHE.cache_key("foo")
    if not ensure_logged_in():
        AssertionError("test_ensure_logged_in: Assertion Failed")


def test_run_jwt_login():
    """
    Test run_jwt_login.
    """
    token = "token"
    if run_jwt_login(None):
        raise AssertionError("test_run_jwt_login: Assertion Failed")
    with patch(
        "utilities.cli_utilities.EVE_FETCHER.get", return_value={"status_code": 200}
    ):
        if not run_jwt_login(token):
            raise AssertionError("test_run_jwt_login: Assertion Failed")
    if run_jwt_login(token):
        raise AssertionError("test_run_jwt_login: Assertion Failed")


def test_store_token():
    """
    Test for storing/retrieving a token in Cache.
    """
    cache_token("test")
    if USER_CACHE.get_key() != "test":
        raise AssertionError("test_store_token: Assertion Failed")


def test_terminal_sensitive_print():
    """
    Test terminal_sensitive_print.
    """
    terminal_sensitive_print("hello hello", width=7)


def test_select_assay_trial():
    """
    Test select_assay_trial
    """
    with patch("constants.USER_CACHE.get_key", return_value=None):
        if select_assay_trial("prompt"):
            raise AssertionError("test_select_assay_trial: Assertion Failed")
    inputs = [1, 1]
    USER_CACHE.cache_key("foo")
    response = {
        "_items": [
            {
                "trial_name": "trial1",
                "_id": "123",
                "assays": [{"assay_name": "assay1", "assay_id": "245"}],
            }
        ],
        "status_code": 200,
    }
    no_trials = {
        "_items": [],
        "status_code": 200,
    }
    bad_response = FakeFetcher(no_trials)
    response_with_method = FakeFetcher(response)
    with patch("utilities.cli_utilities.EVE_FETCHER.get", return_value=response_with_method):
        selections = mock_with_inputs(inputs, select_assay_trial, ["Prompt"])
        if (
            selections.eve_token != "foo"
            or selections.selected_trial
            != {
                "trial_name": "trial1",
                "_id": "123",
                "assays": [{"assay_name": "assay1", "assay_id": "245"}],
            }
            or selections.selected_assay != {"assay_name": "assay1", "assay_id": "245"}
        ):
            raise AssertionError("test_select_assay_trial: Assertion Failed")
    if select_assay_trial(""):
        raise AssertionError("test_select_assay_trial: Assertion Failed")
    with patch("utilities.cli_utilities.EVE_FETCHER.get", return_value=bad_response):
        if select_assay_trial(""):
            raise AssertionError("test_select_assay_trial: Assertion Failed")
