"""Implements a simple persistent file-store cache.

Values set using this cache will persist across CLI command invocations.
"""

import os
from typing import Optional

from ..constants import CIDC_WORKING_DIR


def _key_path(key: str) -> str:
    return os.path.join(CIDC_WORKING_DIR, key)


def store(key: str, value: str):
    """Persist a value across CLI commands."""
    # Create the cache directory if it doesn't exist
    if not os.path.exists(CIDC_WORKING_DIR):
        os.mkdir(CIDC_WORKING_DIR)

    # Save the provided value in a file named key
    with open(_key_path(key), 'w') as cache:
        cache.write(value)


def get(key: str) -> Optional[str]:
    """Try to get a value for the given key"""
    key_path = _key_path(key)

    # Check if the key exists
    if not os.path.exists(key_path):
        return None

    # Get the value
    with open(key_path, 'r') as value:
        return value.read()
