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
        "You are not authenticated. Please login with:\n"
        "   $ cidc login [YOUR PORTAL TOKEN]"
    )


def validate_token(id_token: str):
    """
    Raises AuthError if id_token is not valid
    """
    try:
        error = api.check_auth(id_token)
    except api.ApiError as e:
        raise AuthError(str(e))


def cache_token(id_token: str, validate: bool = True):
    """
    Cache a token for use in future commands. If `validate` is True,
    only cache the token if it is valid.
    """
    # Validate the id token
    if validate:
        validate_token(id_token)

    # Save the provided token
    cache.store(TOKEN, id_token)


def get_id_token(validate: bool = True) -> str:
    """
    Look for a cached id_token for this user. If `validate` is True and the token is invalid, or
    if no token is cached, exit and prompt the user to log in. Otherwise, return the cached token.
    """
    # Try to find a cached token
    id_token = cache.get(TOKEN)

    # If there's no cached token, the user needs to log in
    if not id_token:
        raise unauthenticated()

    # Check if cached token is still valid
    if validate:
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

    return claims["email"]
