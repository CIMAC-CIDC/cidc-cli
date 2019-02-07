#!/usr/bin/env python3
"""
Tests for the command line interface
"""
import unittest
from unittest.mock import patch
from cidc_utils.caching import CredentialCache

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
    select_assay_trial,
    Selections,
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
    assert len(menu.split("\n")) == 5


def test_force_valid_menu_selection():
    """
    Test for the function force_valid_menu_selection
    """
    number_options = 3
    prompt = "a"
    with patch("builtins.input", return_value="2"):
        assert force_valid_menu_selection(number_options, prompt) == 2
    inputs = [4, unittest, 2]
    assert (
        mock_with_inputs(inputs, force_valid_menu_selection, [number_options, prompt])
        == 2
    )


def test_user_prompt_yn():
    """
    Test for the function user_prompt_yn
    """
    with patch("builtins.input", return_value="y"):
        assert user_prompt_yn("")
    with patch("builtins.input", return_value="n"):
        assert not user_prompt_yn("")
    inputs = ["z", "n"]
    assert not mock_with_inputs(inputs, user_prompt_yn, [""])


class TestUploadFunctions(unittest.TestCase):
    """Test class for the update job status function

    Arguments:
        unittest {[type]} -- [description]
    """

    def test_get_valid_dir(self):
        """
        Test function for get_valid_dir
        """
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
        assert option_select_framework(options, prompt)


def test_ensure_logged_in():
    """
    Test function for ensure_logged_in
    """
    assert not ensure_logged_in()
    USER_CACHE.cache_key("foo")
    assert ensure_logged_in()


def test_run_jwt_login():
    """
    Test run_jwt_login.
    """
    token = "token"
    assert not run_jwt_login(None)
    with patch(
        "utilities.cli_utilities.EVE_FETCHER.get", return_value={"status_code": 200}
    ):
        assert run_jwt_login(token)
    assert not run_jwt_login(token)


def test_store_token():
    """
    Test for storing/retrieving a token in Cache.
    """
    cache_token("test")
    assert USER_CACHE.get_key() == "test"


def test_terminal_sensitive_print():
    """
    Test terminal_sensitive_print.
    """
    terminal_sensitive_print("hello hello", width=7)
    assert True


def test_select_assay_trial():
    """
    Test select_assay_trial
    """
    with patch("constants.USER_CACHE.get_key", return_value=None):
        assert not select_assay_trial("prompt")
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
        assert (
            selections.eve_token == "foo"
            and selections.selected_trial
            == {
                "trial_name": "trial1",
                "_id": "123",
                "assays": [{"assay_name": "assay1", "assay_id": "245"}],
            }
            and selections.selected_assay == {"assay_name": "assay1", "assay_id": "245"}
        )
    assert not select_assay_trial("")
    with patch("utilities.cli_utilities.EVE_FETCHER.get", return_value=bad_response):
        assert not select_assay_trial("")
