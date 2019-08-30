from click.testing import CliRunner

from cli import cache


def test_cache_hit(runner: CliRunner):
    """Test storing and getting an object from the cache"""
    key = "foo"
    value1 = "bar"
    value2 = "baz"

    with runner.isolated_filesystem():
        cache.store(key, value1)
        assert cache.get(key) == value1

        cache.store(key, value2)
        assert cache.get(key) == value2


def test_cache_miss(runner: CliRunner):
    """Test that we can't get an object that doesn't exist in the cache."""
    assert cache.get("missing key") is None
