#!/usr/bin/env python3
"""
Tests for the command line interface
"""

import requests
from unittest.mock import patch, MagicMock
from utilities.cli_utilities import generate_options_list, force_valid_menu_selection, \
    user_prompt_yn, get_files, create_payload_objects

from utilities.cli_utilities import cache_token
from utilities.cli_utilities import USER_CACHE


def test_generate_options_list():
    """
    Test for the function generate_options_list
    """
    menu_items = ['A', 'B', 'C']
    header = 'test'
    menu = generate_options_list(menu_items, header)
    assert len(menu.split('\n')) == 5


def test_force_valid_menu_selection():
    """
    Test for the function force_valid_menu_selection
    """
    number_options = 3
    prompt = "a"
    with patch('builtins.input', return_value='2'):
        assert force_valid_menu_selection(number_options, prompt) == 2


def test_user_prompt_yn():
    """
    Test for the function user_prompt_yn
    """
    with patch('builtins.input', return_value='y'):
        assert user_prompt_yn("")
    with patch('builtins.input', return_value='n'):
        assert not user_prompt_yn("")


def test_create_payload_objects():
    """
    Test for create_payload_objects
    """

    file_dict = {
        'file_name_1': {
            'mapping': 'map',
            'sample_id': '1234'
        }

    }
    assay = {'assay_id': '321'}
    trial = {'_id': '456'}
    payload = create_payload_objects(file_dict, trial, assay)
    assert payload == [{
        'assay': '321',
        'trial': '456',
        'file_name': 'file_name_1',
        'sample_id': '1234',
        'mapping': 'map'
    }]


def test_store_token():
    """
    Test for storing/retrieving a token in Cache.
    """
    cache_token("test")

    assert USER_CACHE.get_key() == "test"
