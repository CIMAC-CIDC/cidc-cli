"""
Tests for the download module.
"""
from unittest.mock import patch
from download.download import (
    paginate_selections,
    elegant_options,
    run_download_process,
    get_files_for_dl,
)
from utilities.cli_utilities import Selections
from tests.helper_functions import FakeFetcher


LIST_ITEMS = [{"file_name": str(x)} for x in range(0, 100)]
COMMANDS = ["[N]ext", "[P]revious", "[E]xit", "Download [A]ll: "]


def test_paginate_selections():
    """
    Test paginate_selections.
    """
    paginated_list = paginate_selections(LIST_ITEMS)
    assert len(paginated_list) == 7


def test_elegant_options():
    """
    Test elegant_options
    """
    paginated_list = paginate_selections(LIST_ITEMS)
    pages = elegant_options(paginated_list, COMMANDS, "=====| Files to Download |=====")
    assert len(pages) == 7


def test_get_files_for_dl():
    """
    Test run_download_process.
    """
    sel = Selections(
        "token",
        {
            "trial_name": "trial1",
            "_id": "123",
            "assays": [{"assay_name": "assay1", "assay_id": "245"}],
        },
        {"assay_name": "assay1", "assay_id": "245"},
    )
    response = FakeFetcher({"_items": [{"file_name": "a", "gs_uri": "gs://000"}]})

    with patch("download.download.select_assay_trial", return_value=sel):
        with patch("download.download.EVE_FETCHER.get", return_value=response):
            assert get_files_for_dl() == {
                "_items": [{"file_name": "a", "gs_uri": "gs://000"}]
            }
        with patch(
            "download.download.EVE_FETCHER.get",
            return_value=FakeFetcher({"_items": []}),
        ):
            assert not get_files_for_dl()
