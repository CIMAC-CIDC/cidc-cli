#!/usr/bin/env python
"""
Configuration file for pytest.
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

import sys
from os.path import abspath, dirname
PACKAGE_PATH = abspath(dirname(dirname(__file__)))
sys.path.insert(0, PACKAGE_PATH)
