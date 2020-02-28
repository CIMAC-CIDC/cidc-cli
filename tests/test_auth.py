import pytest

from cli import auth


def test_get_user_email(monkeypatch):
    """Check that get_user_email extracts an email from a JWT"""
    # This is a JWT with payload {"email": "test@email.com"}
    TOKEN = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6InRlc3RAZW1haWwuY29tIn0.jTck01ns477JzZY-KLMM82OOZcc6ctJA11HKE8sXiq4"

    monkeypatch.setattr(auth, "get_id_token", lambda: TOKEN)

    email = auth.get_user_email()

    assert email == "test@email.com"

    # Test that it handles invalid JWTs
    monkeypatch.setattr(auth, "get_id_token", lambda: "uh oh")
    with pytest.raises(auth.AuthError, match="not authenticated"):
        auth.get_user_email()


def test_valid_token_flow(monkeypatch, runner):
    """Check that caching works as expected for a valid token"""
    monkeypatch.setattr(auth, "validate_token", lambda token: None)

    TOKEN = "test-token"

    with runner.isolated_filesystem():
        # Login
        auth.validate_and_cache_token(TOKEN)

        # Use the token
        assert auth.get_id_token() == TOKEN


def test_invalid_token_flow(monkeypatch, runner):
    """Check that errors are thrown as expected for an invalid token"""

    def auth_error(*args):
        raise auth.AuthError("uh oh")

    monkeypatch.setattr(auth, "validate_token", auth_error)

    with runner.isolated_filesystem():
        # Invalid tokens shouldn't be cached
        with pytest.raises(auth.AuthError):
            auth.validate_and_cache_token("blah")

        # Invalid tokens *can* be read.
        monkeypatch.setattr("cli.cache.get", lambda key: "blah")
        assert auth.get_id_token() == "blah"
