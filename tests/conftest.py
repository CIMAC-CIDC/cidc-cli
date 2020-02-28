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

from cli.config import CIDC_WORKING_DIR

PACKAGE_PATH = abspath(dirname(dirname(__file__)))
sys.path.insert(0, PACKAGE_PATH)

os.environ["TESTING"] = "True"
if not os.path.isdir(CIDC_WORKING_DIR):
    os.mkdir(CIDC_WORKING_DIR)


@pytest.fixture
def runner():
    return CliRunner()
