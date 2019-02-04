#!/usr/bin/env python3
"""
Tests for the command line interface
"""
from typing import Callable, List
from unittest.mock import patch

from utilities.cli_utilities import (
    generate_options_list,
    ensure_logged_in,
    option_select_framework,
    cache_token,
    force_valid_menu_selection,
    user_prompt_yn,
    get_valid_dir,
)
from tests.helper_functions import mock_with_inputs
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

    USER_CACHE.cache_key("foo")
    assert ensure_logged_in()


def test_store_token():
    """
    Test for storing/retrieving a token in Cache.
    """
    cache_token("test")
    assert USER_CACHE.get_key() is "test"
