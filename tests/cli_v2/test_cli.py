from click.testing import CliRunner

from cli.cli_v2 import cli


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


def test_no_gcloud_installation(runner: CliRunner, monkeypatch):
    """
    Check that running `cidc [subcommand]` without a gcloud installation prompts
    the user to install gcloud.
    """
    def assert_gcloud_message(res):
        assert 'requires an installation of the gcloud SDK' in res.output

    monkeypatch.setattr('shutil.which', lambda *args: False)
    assert_gcloud_message(runner.invoke(cli.cidc, ['manifests']))
    assert_gcloud_message(runner.invoke(cli.cidc, ['assays']))
    assert_gcloud_message(runner.invoke(cli.cidc, ['login']))


def test_assays_list(runner: CliRunner, monkeypatch):
    """
    Check that assay_list displays supported assays as expected.
    """
    monkeypatch.setattr("cli.cli_v2.api.list_assays", lambda: ['wes', 'pbmc'])
    res = runner.invoke(cli.assays, ['list'])
    assert '* wes' in res.output
    assert '* pbmc' in res.output


def test_assays_upload(runner: CliRunner, monkeypatch):
    pass
