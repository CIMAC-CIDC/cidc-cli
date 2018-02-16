#!/usr/bin/env python3
"""
Tests for the upload script
"""

from upload import validate_and_extract


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
