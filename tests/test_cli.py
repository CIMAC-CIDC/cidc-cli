#!/usr/bin/env python
"""
Tests for functions in the interface.cli module
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

from unittest.mock import patch
from cli.interface.cli import CIDCCLI

from .helper_functions import mock_with_inputs


def raise_interrupt():
    raise KeyboardInterrupt


def test_cli_class():
    """
    Test creation of a CLI object.
    """
    with patch("builtins.input", return_value="N"):
        cli = CIDCCLI()
        cli.cmdloop()
    with patch("cli.interface.cli.USER_CACHE.get_key", return_value="foo"):
        mock_with_inputs(["Y", "exit"], cli.cmdloop, [])
