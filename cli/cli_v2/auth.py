import os
import functools
from typing import Optional

import click

from . import api
from ..constants import TOKEN_CACHE_DIR, TOKEN_CACHE_PATH


class AuthError(click.ClickException):
    pass


def request_login():
    """Prompt the user to login."""
    raise click.ClickException(
        'Please login with:\n'
        '   $ cidc login [YOUR PORTAL TOKEN]')


def requires_id_token(f):
    """
    Provide an ID token to `f` as its first positional argument.
    """

    @functools.wraps(f)
    def wrapped(*args, **kwargs):
        """
        Cache the id_token passed as the first argument to `f`,
        then forward it to `f`. 
        """
        id_token = get_cached_token()
        if not id_token:
            request_login()
        return f(id_token, *args, **kwargs)

    return wrapped


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
    if not os.path.exists(TOKEN_CACHE_DIR):
        os.mkdir(TOKEN_CACHE_DIR)

    # Validate the id token
    validate_token(id_token)

    # Save the provided token
    with open(TOKEN_CACHE_PATH, 'w') as cache:
        cache.write(id_token)


def get_cached_token() -> Optional[str]:
    """
    Look for a cached id_token for this user. If found, validate it.
    If not, return None.
    """
    # If the cache doesn't exist, there is no cached token
    if not os.path.exists(TOKEN_CACHE_PATH):
        return None

    # Get the cached token
    with open(TOKEN_CACHE_PATH, 'r') as cache:
        id_token = cache.read()

    # Return the cached token if it is still valid
    try:
        validate_token(id_token)
        return id_token
    except AuthError as e:
        request_login()
