"""
Tests for the download module.
"""
from unittest.mock import patch
from download.download import paginate_selections, elegant_options

LIST_ITEMS = [{ "file_name": str(x) } for x in range(0, 100)]
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
