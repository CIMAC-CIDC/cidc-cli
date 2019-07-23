"""Methods for working with id tokens"""
import click
from jose import jwt

from . import api
from . import cache


TOKEN = "id_token"


class AuthError(click.ClickException):
    pass


def unauthenticated() -> AuthError:
    return AuthError(
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
    # Validate the id token
    validate_token(id_token)

    # Save the provided token
    cache.store(TOKEN, id_token)


def get_id_token() -> str:
    """
    Look for a cached id_token for this user. If one exists and is valid, return it.
    Otherwise, exit and prompt the user to log in.
    """
    # Try to find a cached token
    id_token = cache.get(TOKEN)

    # If there's no cached token, the user needs to log in
    if not id_token:
        raise unauthenticated()

    # Return the cached token if it is still valid
    try:
        validate_token(id_token)
    except AuthError:
        raise unauthenticated()

    return id_token


def get_user_email() -> str:
    """Extract a user's email from their id token."""
    token = get_id_token()

    # We don't need to check verifications here,
    # because get_id_token validates the token it returns
    # with the API (this includes signature verification).
    claims = jwt.get_unverified_claims(token)

    return claims['email']
