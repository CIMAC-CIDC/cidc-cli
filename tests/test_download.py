#!/usr/bin/env python
"""
Tests for the download module.
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

from unittest.mock import patch
from cli.download.download import (
    paginate_selections,
    elegant_options,
    get_files_for_dl,
    run_selective_download,
)
from cli.utilities.cli_utilities import Selections

from .helper_functions import FakeFetcher, mock_with_inputs


LIST_ITEMS = [{"file_name": str(x)} for x in range(0, 100)]
COMMANDS = ["[N]ext", "[P]revious", "[E]xit", "Download [A]ll: "]
SEL = Selections(
    "token",
    {
        "trial_name": "trial1",
        "_id": "123",
        "assays": [{"assay_name": "assay1", "assay_id": "245"}],
    },
    {"assay_name": "assay1", "assay_id": "245"},
)


def test_run_selective_download():
    """
    Test run_selective_download
    """
    response = FakeFetcher(
        {"_items": [{"file_name": "a", "gs_uri": "gs://000"}]})
    with patch("cli.download.download.select_assay_trial", return_value=SEL), patch(
        "cli.download.download.EVE_FETCHER.get", return_value=response
    ), patch("cli.download.download.gsutil_copy_data", return_value=True), patch(
        "cli.download.download.get_valid_dir", return_value=[True]
    ):
        mock_with_inputs(["1", "e"], run_selective_download, [])
        mock_with_inputs(["2", "e"], run_selective_download, [])
        mock_with_inputs(["a"], run_selective_download, [])
    with patch("cli.download.download.select_assay_trial", return_value=None):
        run_selective_download()
    with patch("cli.download.download.select_assay_trial", return_value=SEL):
        with patch(
            "cli.download.download.EVE_FETCHER.get",
            return_value=FakeFetcher({"_items": []}),
        ):
            run_selective_download()


def test_paginate_selections():
    """
    Test paginate_selections.
    """
    paginated_list = paginate_selections(LIST_ITEMS)
    if len(paginated_list) != 7:
        raise AssertionError("test_paginate_selections: Assertion Failed")


def test_elegant_options():
    """
    Test elegant_options
    """
    paginated_list = paginate_selections(LIST_ITEMS)
    pages = elegant_options(paginated_list, COMMANDS,
                            "=====| Files to Download |=====")
    if len(pages) != 7:
        raise AssertionError("test_elegant_options: Assertion Failed")


def test_get_files_for_dl():
    """
    Test run_download_process.
    """
    response = FakeFetcher(
        {"_items": [{"file_name": "a", "gs_uri": "gs://000"}]})

    with patch("cli.download.download.select_assay_trial", return_value=SEL):
        with patch("cli.download.download.EVE_FETCHER.get", return_value=response):
            if get_files_for_dl() != {
                "_items": [{"file_name": "a", "gs_uri": "gs://000"}]
            }:
                raise AssertionError("test_get_files_for_dl: Assertion Failed")
        with patch(
            "cli.download.download.EVE_FETCHER.get",
            return_value=FakeFetcher({"_items": []}),
        ):
            if get_files_for_dl():
                raise AssertionError("test_get_files_for_dl: Assertion Failed")
    with patch("cli.download.download.select_assay_trial", return_value=None):
        if get_files_for_dl():
            raise AssertionError("Function failed to exit")
