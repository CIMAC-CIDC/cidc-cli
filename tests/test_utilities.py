#!/usr/bin/env python
"""
Tests for the command line interface
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

import os
import unittest
from unittest.mock import patch

import pytest
from tests.helper_functions import FakeFetcher, mock_with_inputs

from cli.constants import USER_CACHE
from cli.utilities.cli_utilities import (
    Selections,
    cache_token,
    ensure_logged_in,
    force_valid_menu_selection,
    generate_options_list,
    get_valid_dir,
    lock_trial,
    option_select_framework,
    pick_sample_id,
    run_jwt_login,
    run_lock_trial,
    select_assay_trial,
    select_trial,
    show_countdown,
    simple_query,
    user_prompt_yn,
    run_sample_delete,
    delete_related_records,
    set_unprocessed_maf,
)

TRIAL_RESPONSE = {
    "_items": [
        {
            "trial_name": "trial1",
            "_id": "123",
            "assays": [{"assay_name": "assay1", "assay_id": "245"}],
            "collaborators": ["test@test.com"],
            "email": "test@test.com",
            "locked": False,
            "_etag": "ackjsdckj23123213",
        }
    ],
    "status_code": 200,
}
TRIAL_RESPONSE_NO_LOCK_FIELD = {
    "_items": [
        {"trial_name": "nofield", "_id": "567", "assays": [], "_etag": "bcbdcbdcb"}
    ]
}
TRIAL_RESPONSE_LOCKED = {
    "_items": [
        {
            "trial_name": "trial1",
            "_id": "123",
            "assays": [{"assay_name": "assay1", "assay_id": "245"}],
            "collaborators": ["test@test.com"],
            "email": "test@test.com",
            "locked": True,
            "_etag": "ackjsdckj23123213",
        }
    ],
    "status_code": 200,
}
TRIAL_RESPONSE_UNLOCKED = {
    "_items": [
        {
            "trial_name": "trial_unlocked",
            "_id": "123",
            "assays": [{"assay_name": "assay1", "assay_id": "245"}],
            "collaborators": ["test@test.com"],
            "email": "test@test.com",
            "locked": False,
            "_etag": "ackjsdckj23123213",
        }
    ],
    "status_code": 200,
}
SMART_FETCH = "cli.utilities.cli_utilities.EVE_FETCHER."
SMART_GET = SMART_FETCH + "get"
SMART_PATCH = SMART_FETCH + "patch"
SELECTIONS = Selections("something", TRIAL_RESPONSE["_items"][0], {})


@pytest.mark.skip("this will fail until our SSL cert is renewed...:/")
def test_set_unprocessed_maf():
    """
    Test set_unprocessed_maf
    """
    records = {"_items": [{"_id": "9494", "file_name": "yyy", "_etag": "e"}]}
    with patch(SMART_GET, side_effect=[RuntimeError("T")]):
        set_unprocessed_maf(SELECTIONS)
    with patch(SMART_GET, return_value=FakeFetcher(records)):
        with patch(SMART_PATCH, return_value=True):
            set_unprocessed_maf(SELECTIONS)
        with patch(SMART_PATCH, side_effect=[RuntimeError("I")]):
            set_unprocessed_maf(SELECTIONS)
    with patch(SMART_GET, side_effect=[FakeFetcher(records), RuntimeError("Y")]):
        set_unprocessed_maf(SELECTIONS)


def test_delete_related_records():
    """
    Test delete_related_records
    """
    records = [
        {"sample_ids": ["1"], "file_name": "abc1"},
        {"sample_ids": ["1"], "file_name": "abc2"},
        {"sample_ids": ["2"], "file_name": "abc3"},
    ]
    sample_id = "1"
    selections = Selections("something", TRIAL_RESPONSE["_items"][0], {})
    with patch(SMART_GET, side_effect=[RuntimeError("Planned Error")]):
        delete_related_records(records, sample_id, selections)
    analysis = {"_items": [{"_id": "abcd"}]}
    with patch(SMART_GET, return_value=FakeFetcher(analysis)):
        with patch("cli.utilities.cli_utilities.delete_record", return_value=True):
            delete_related_records(records, sample_id, selections)
        with patch(
            "cli.utilities.cli_utilities.delete_record", side_effect=[RuntimeError("B")]
        ):
            delete_related_records(records, sample_id, selections)


@pytest.mark.skip("this will fail until our SSL cert is renewed...:/")
def test_run_sample_delete():
    """
    Test run_sample_delete
    """
    with patch("cli.utilities.cli_utilities.select_trial", return_value=None):
        run_sample_delete()
    with patch(
        "utilities.cli_utilities.select_trial",
        return_value=Selections(
            "something", TRIAL_RESPONSE_UNLOCKED["_items"][0], {}),
    ):
        mock_with_inputs(["n"], run_sample_delete, [])
        with patch("cli.utilities.cli_utilities.pick_sample_id", return_value=None):
            with patch("cli.utilities.cli_utilities.lock_trial", return_value=True):
                mock_with_inputs(["y"], run_sample_delete, [])

    with patch(
        "utilities.cli_utilities.select_trial",
        return_value=Selections(
            "something", TRIAL_RESPONSE_UNLOCKED["_items"][0], {}),
    ), patch(
        "utilities.cli_utilities.simple_query",
        side_effect=[
            [{"sample_ids": ["S1", "S2"]}],
            [{"sample_ids": ["S1", "S2"]}],
            [{"sample_ids": ["S1", "S2"]}],
            [{"sample_ids": ["S1", "S2"]}],
        ],
    ), patch(
        "utilities.cli_utilities.delete_related_records", return_value=True
    ), patch(
        SMART_GET,
        side_effect=[
            FakeFetcher({"_id": "123"}),
            FakeFetcher({"_items": []}),
            FakeFetcher({"_id": "123"}),
            FakeFetcher({"_items": []}),
        ],
    ), patch(
        "utilities.cli_utilities.lock_trial", return_value=True
    ), patch(
        SMART_PATCH, return_value=True
    ):
        mock_with_inputs(["Y", "1", "n", "n", "Y"], run_sample_delete, [])
        mock_with_inputs(["Y", "1", "y", "1", "n", "n", "Y"],
                         run_sample_delete, [])


def test_simple_query():
    """
    test simple_query
    """
    with patch(SMART_GET, return_value=FakeFetcher({"_items": ["moo"]})):
        if not simple_query("foo", "bar"):
            raise AssertionError("Simple query failed to return")
    with patch(SMART_GET, return_value=FakeFetcher({"status_code": 200})):
        if simple_query("foo", "bar"):
            raise AssertionError("Simple_query failed to catch no items.")
    with patch(SMART_GET, return_value={}, side_effect=RuntimeError("MOO")):
        if simple_query("foo", "bar"):
            raise AssertionError("simple_query failed to catch error.")


def test_show_countdown():
    """
    Test show_countdown
    """
    try:
        show_countdown(0, "", 1)
        raise AssertionError("Failed to throw error for bad step value.")
    except ValueError:
        pass
    show_countdown(1, "", -1)


def test_pick_sample_id():
    """
    Test pick_sample_id
    """
    records = [{"sample_ids": ["S1", "S2"]}]
    with patch("builtins.input", return_value=1):
        pick = pick_sample_id(records)
        if not pick == "S1":
            print(pick, "bad pick")
            raise AssertionError("Pick sample id failed.")
        if pick_sample_id([]):
            raise AssertionError(
                "pick_sample_id returned even with empty input.")


def test_run_lock_trial():
    """
    Test run_lock_trial
    """
    select = Selections("something", TRIAL_RESPONSE_LOCKED["_items"][0], {})
    un_select = Selections(
        "something", TRIAL_RESPONSE_UNLOCKED["_items"][0], {})
    no_field = Selections(
        "something", TRIAL_RESPONSE_NO_LOCK_FIELD["_items"][0], {})
    with patch("cli.utilities.cli_utilities.select_trial", return_value=None):
        run_lock_trial()
    with patch("cli.utilities.cli_utilities.select_trial", return_value=no_field):
        run_lock_trial()
    with patch("cli.utilities.cli_utilities.select_trial", return_value=select):
        with patch(SMART_PATCH, return_value={"status_code": 200}):
            mock_with_inputs(["y"], run_lock_trial, [])
            mock_with_inputs(["n"], run_lock_trial, [])
    with patch("cli.utilities.cli_utilities.select_trial", return_value=un_select):
        with patch(SMART_PATCH, return_value={"status_code": 200}):
            mock_with_inputs([], run_lock_trial, [])


def test_lock_trial():
    """
    Test lock_trial
    """
    with patch(SMART_PATCH, return_value={"status_code": 200}):
        if not lock_trial(True, SELECTIONS):
            raise AssertionError("Failed to lock trial test")
    with patch(SMART_PATCH, side_effect=RuntimeError("401")):
        if lock_trial(True, SELECTIONS):
            raise AssertionError("Failed to catch 401")
    with patch(SMART_PATCH, side_effect=RuntimeError("412")):
        if lock_trial(True, SELECTIONS):
            raise AssertionError("Failed to catch 412")


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
        mock_with_inputs(inputs, force_valid_menu_selection,
                         [number_options, prompt])
        != 2
    ):
        raise AssertionError(
            "test_force_valid_menu_selection: Assertion Failed")


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
            os.mkdir("tests/empty_dir")
        except FileExistsError:
            pass
        with self.subTest():
            inputs = ["tests/test_directory", "y"]
            self.assertEqual(
                len(mock_with_inputs(inputs, get_valid_dir, [False])[1]), 3
            )
        with self.subTest():
            inputs = [1, mock_with_inputs, "tests/test_directory", "y"]
            self.assertEqual(
                len(mock_with_inputs(inputs, get_valid_dir, [False])[1]), 3
            )
        with self.subTest():
            inputs = ["tests/empty_dir", "tests/test_directory", "y"]
            self.assertEqual(
                len(mock_with_inputs(inputs, get_valid_dir, [False])[1]), 0
            )
        with self.subTest():
            inputs = ["tests/empty_dir", "tests/test_directory", "y"]


def test_option_select_framework():
    """
    Test function for option_select_framework
    """
    options = ["one", "two", "three"]
    prompt = "foo"
    with patch("builtins.input", return_value="1"):
        if not option_select_framework(options, prompt):
            raise AssertionError(
                "test_option_select_framework: Assertion Failed")


def test_ensure_logged_in():
    """
    Test function for ensure_logged_in
    """
    if ensure_logged_in():
        raise AssertionError("test_ensure_logged_in: Assertion Failed")
    USER_CACHE.cache_key("foo")
    if not ensure_logged_in():
        AssertionError("test_ensure_logged_in: Assertion Failed")


@pytest.mark.skip("this will fail until our SSL cert is renewed...:/")
def test_run_jwt_login():
    """
    Test run_jwt_login.
    """
    fake = "foo"
    if run_jwt_login(None):
        raise AssertionError("test_run_jwt_login: Assertion Failed")

    with patch(SMART_GET, return_value={"status_code": 200}):
        if not run_jwt_login(fake):
            raise AssertionError("test_run_jwt_login: Assertion Failed")
    # todo: disabled this test because we want to propogate errors
    #if run_jwt_login(fake):
    #    raise AssertionError("test_run_jwt_login: Assertion Failed")


def test_store_token():
    """
    Test for storing/retrieving a token in Cache.
    """
    cache_token("test")
    if USER_CACHE.get_key() != "test":
        raise AssertionError("test_store_token: Assertion Failed")


def test_select_trial():
    """
    Test select_trial
    """
    with patch("cli.constants.USER_CACHE.get_key", return_value="foo"):
        with patch(
            SMART_GET,
            side_effect=[FakeFetcher(TRIAL_RESPONSE),
                         FakeFetcher({"_items": []})],
        ):
            if select_trial(""):
                raise AssertionError("Returned after user not found")
        with patch(SMART_GET, side_effect=RuntimeError("401")):
            if select_trial(""):
                raise AssertionError("Returned after 401")
        with patch(
            SMART_GET,
            side_effect=[
                FakeFetcher({"_items": []}),
                FakeFetcher({"_items": [{"email": "abcd"}]}),
            ],
        ):
            if select_trial(""):
                raise AssertionError("Returned with no trials")
        with patch(
            SMART_GET,
            side_effect=[
                FakeFetcher(TRIAL_RESPONSE),
                FakeFetcher({"_items": [{"email": "abcd"}]}),
            ],
        ):
            if select_trial(""):
                raise AssertionError("Returned with no user trials")


@pytest.mark.skip("this will fail until our SSL cert is renewed...:/")
def test_select_assay_trial():
    """
    Test select_assay_trial
    """
    with patch("cli.constants.USER_CACHE.get_key", return_value=None):
        value = select_assay_trial("prompt")
        if value:
            raise AssertionError(
                "test_select_assay_trial: Assertion  1 Failed")
    inputs = [1, 1]
    USER_CACHE.cache_key("foo")
    no_assays = {
        "_items": [
            {
                "trial_name": "1",
                "_id": "2",
                "collaborators": ["a"],
                "email": "b",
                "locked": False,
            }
        ]
    }
    with patch(SMART_GET, return_value=FakeFetcher(TRIAL_RESPONSE)):
        with patch("cli.constants.USER_CACHE.get_key", return_value="foo"):
            selections = mock_with_inputs(
                inputs, select_assay_trial, ["Prompt"])
            if (
                selections.eve_token != "foo"
                or selections.selected_trial != TRIAL_RESPONSE["_items"][0]
                or selections.selected_assay
                != {"assay_name": "assay1", "assay_id": "245"}
            ):
                raise AssertionError(
                    "test_select_assay_trial: Assertion 2 Failed")

    if select_assay_trial(""):
        raise AssertionError("test_select_assay_trial: Assertion 3 Failed")
    with patch(
        "utilities.cli_utilities.select_trial", return_value=Selections("a", {}, {})
    ):
        with patch("cli.utilities.cli_utilities.ensure_logged_in", return_value="token"):
            if select_assay_trial(""):
                raise AssertionError(
                    "test_select_assay_trial: Assertion 4 Failed")
    with patch(
        "utilities.cli_utilities.select_trial",
        return_value=Selections("something", no_assays, {}),
    ):
        if select_assay_trial(""):
            raise AssertionError("test_select_assay_trial: Assertion 5 Failed")
