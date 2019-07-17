import os
import functools
from typing import Optional

import click

from . import api
from ..constants import CIDC_WORKING_DIR, TOKEN_CACHE_PATH


class AuthError(click.ClickException):
    pass


def raise_unauthenticated():
    raise AuthError(
        'You are not authenticated. Please login with:\n'
        '   $ cidc login [YOUR PORTAL TOKEN]')


def validate_token(id_token: str):
    """
    Raises AuthError if id_token is not valid
    """
    error = api.check_auth(id_token)

    if error:
        raise AuthError(error)


def cache_token(id_token: str):
    """
    If a token is valid, cache it for use in future commands.
    """
    # Create the cache directory if it doesn't exist
    if not os.path.exists(CIDC_WORKING_DIR):
        os.mkdir(CIDC_WORKING_DIR)

    # Validate the id token
    validate_token(id_token)

    # Save the provided token
    with open(TOKEN_CACHE_PATH, 'w') as cache:
        cache.write(id_token)


def get_id_token() -> str:
    """
    Look for a cached id_token for this user. If one exists and is valid, return it.
    Otherwise, exit and prompt the user to log in.
    """
    # If the cache doesn't exist, there is no cached token
    if not os.path.exists(TOKEN_CACHE_PATH):
        raise_unauthenticated()

    # Get the cached token
    with open(TOKEN_CACHE_PATH, 'r') as cache:
        id_token = cache.read()

    # Return the cached token if it is still valid
    try:
        validate_token(id_token)
        return id_token
    except AuthError as e:
        raise_unauthenticated()
