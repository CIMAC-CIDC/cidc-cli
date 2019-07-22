#!/usr/bin/env python
"""
Configuration file for pytest.
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

import sys
from os.path import abspath, dirname, join
PACKAGE_PATH = join(abspath(dirname(dirname(__file__))), 'cli')
sys.path.insert(0, PACKAGE_PATH)
