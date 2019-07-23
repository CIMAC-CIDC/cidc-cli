import pytest

from cli2 import auth


def test_get_user_email(monkeypatch):
    """Check that get_user_email extracts an email from a JWT"""
    # This is a JWT with payload {"email": "test@email.com"}
    TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6InRlc3RAZW1haWwuY29tIn0.jTck01ns477JzZY-KLMM82OOZcc6ctJA11HKE8sXiq4"

    monkeypatch.setattr(auth, 'get_id_token', lambda: TOKEN)

    email = auth.get_user_email()

    assert email == 'test@email.com'


def test_valid_token_flow(monkeypatch):
    """Check that caching works as expected for a valid token"""
    monkeypatch.setattr('cli2.config.CIDC_WORKING_DIR', 'foo')
    monkeypatch.setattr(auth, 'validate_token', lambda token: None)

    TOKEN = "test-token"

    # Login
    auth.cache_token(TOKEN)

    # Use the token
    assert auth.get_id_token() == TOKEN


def test_invalid_token_flow(monkeypatch):
    """Check that errors are thrown as expected for an invalid token"""
    monkeypatch.setattr('cli2.config.CIDC_WORKING_DIR', 'foo')

    def auth_error(*args):
        raise auth.AuthError('uh oh')

    monkeypatch.setattr(auth, 'validate_token', auth_error)

    # Invalid tokens shouldn't be cached
    with pytest.raises(auth.AuthError):
        auth.cache_token('blah')

    # If a cached token is now invalid, the user should
    # be prompted to log in.
    monkeypatch.setattr('cli2.cache.get', lambda key: 'blah')
    with pytest.raises(auth.AuthError, match='Please login'):
        auth.get_id_token()
