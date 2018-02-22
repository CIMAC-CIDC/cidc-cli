#!/usr/bin/env python3
"""
Tests for the upload script
"""

import unittest
from upload import validate_and_extract, request_eve_endpoint, find_eve_token


class TestUpload(unittest.TestCase):
    """
    Small test class to use some basic assertions
    """
    def test_find_eve_token_bad(self):
        """
        Assert that error is thrown when key not found
        """
        with self.assertRaises(FileNotFoundError):
            find_eve_token('./tests')

    def test_request_bad_method(self):
        """
        Assert that unknown methods are rejected
        """
        with self.assertRaises(KeyError):
            request_eve_endpoint('', '', '', 'FOO')


def test_find_eve_token():
    """
    Test that a sample token is found and appropriately reported
    """
    token = find_eve_token('./tests/fake_token')
    assert token == 'ABCD1234'


def test_validate_and_extract():
    """
    Test for the validate and extact function
    """
    file_names = ['aaa123', 'bbb234', 'cc456ccc']
    sample_ids = ['123', '234', '456']
    expected_results = {
        'aaa123': '123',
        'bbb234': '234',
        'cc456ccc': '456',
    }
    results = validate_and_extract(file_names, sample_ids)
    shared_items = set(expected_results.items()) & set(results.items())
    assert len(shared_items) == 3


def test_bad_validate_and_extract():
    """
    Tests that the validate and extract function properly handles bad input
    """
    file_names = ['aaa123', 'bbb234', 'ccccc']
    sample_ids = ['123', '234', '456']
    assert not validate_and_extract(file_names, sample_ids)
