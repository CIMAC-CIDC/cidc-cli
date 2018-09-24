#!/usr/bin/env python3.6
"""
Hashfunctions
"""
import hashlib

BLOCKSIZE = 65536


def compute_hash(file_path: str) -> str:
    """
    Computes the SHAKE128 sum of a file.

    Arguments:
        file_path {str} -- File to be processed

    Returns:
        str -- Hash of the file.
    """
    hasher = hashlib.shake_128()
    with open(file_path, 'rb') as source:
        buffer = source.read(BLOCKSIZE)
        while buffer:
            hasher.update(buffer)
            buffer = source.read(BLOCKSIZE)
    return hasher.digest(128)
