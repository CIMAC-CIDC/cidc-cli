from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from cli.cli_v2 import cli


@pytest.fixture
def runner():
    return CliRunner()


def test_cidc_structure(runner: CliRunner):
    """
    Check that the interface is wired up correctly, and that
    usage is printed when commands are supplied without arguments.
    """
    res = runner.invoke(cli.cidc)
    assert "Usage: cidc" in res.output

    res = runner.invoke(cli.cidc, ['manifests'])
    assert "Usage: cidc manifests" in res.output

    res = runner.invoke(cli.cidc, ['assays'])
    assert "Usage: cidc assays" in res.output

    res = runner.invoke(cli.cidc, ['login', '-h'])
    assert "Usage: cidc login" in res.output
