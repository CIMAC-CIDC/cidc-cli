#!/usr/bin/env python
"""
Configuration file for pytest.
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

import sys
import os
from os.path import abspath, dirname

import pytest
from click.testing import CliRunner

PACKAGE_PATH = abspath(dirname(dirname(__file__)))
sys.path.insert(0, PACKAGE_PATH)

os.environ["TESTING"] = "True"


@pytest.fixture
def runner():
    return CliRunner()
