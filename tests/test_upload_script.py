#!/usr/bin/env python3
"""
Tests for the upload script
"""

from upload.upload import validate_and_extract


def test_validate_and_extract():
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
