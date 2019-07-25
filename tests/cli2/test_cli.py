from click.testing import CliRunner

from cli2 import cli, consent


def skip_consent(monkeypatch):
    monkeypatch.setattr('cli2.consent.check_consent', lambda: True)


def test_cidc_structure(runner: CliRunner, monkeypatch):
    """
    Check that the interface is wired up correctly, and that
    usage is printed when commands are supplied without arguments.
    """
    skip_consent(monkeypatch)

    res = runner.invoke(cli.cidc)
    assert "Usage: cidc" in res.output

    res = runner.invoke(cli.cidc, ['manifests'])
    assert "Usage: cidc manifests" in res.output

    res = runner.invoke(cli.cidc, ['assays'])
    assert "Usage: cidc assays" in res.output

    res = runner.invoke(cli.cidc, ['config'])
    assert "Usage: cidc config" in res.output

    res = runner.invoke(cli.cidc, ['login', '-h'])
    assert "Usage: cidc login" in res.output


def test_no_gcloud_installation(runner: CliRunner, monkeypatch):
    """
    Check that running `cidc [subcommand]` without a gcloud installation prompts
    the user to install gcloud.
    """
    skip_consent(monkeypatch)

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
    monkeypatch.setattr("cli2.api.list_assays", lambda: ['wes', 'pbmc'])
    res = runner.invoke(cli.assays, ['list'])
    assert '* wes' in res.output
    assert '* pbmc' in res.output


def test_env_config(runner: CliRunner, monkeypatch):
    """
    Test setting and getting the current environment.
    """
    monkeypatch.setattr('cli2.cache._cache_dir', lambda: 'workdir')
    with runner.isolated_filesystem():
        # Get default value
        res = runner.invoke(cli.get_env)
        assert 'prod' in res.output

        # Set to valid value
        res = runner.invoke(cli.set_env, ['dev'])
        assert 'dev' in res.output
        res = runner.invoke(cli.get_env)
        assert 'dev'in res.output

        # Try to set to invalid value
        res = runner.invoke(cli.set_env, ['blah'])
        assert 'Invalid value' in res.output


def test_consent(runner: CliRunner, monkeypatch):
    """Check the consent flow."""
    monkeypatch.setattr('cli2.cache._cache_dir', lambda: 'workdir')
    with runner.isolated_filesystem():
        # User has not yet consented, so prompt for consent.
        res = runner.invoke(cli.cidc, ['assays'], input='y')
        assert consent.TERMS in res.output
        assert consent.AGREEMENT in res.output

        # User has now consented, so don't prompt.
        res = runner.invoke(cli.cidc, ['assays'])
        assert consent.TERMS not in res.output


def test_assays_upload(runner: CliRunner, monkeypatch):
    pass
