from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from cli.cli_v2 import cli
from cli import constants


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
    """
    Check that the upload function follows the expected execution flow.
    """
    JOB_ID = 1
    JOB_ETAG = 'abcd'
    GCS_BUCKET = 'upload-bucket'
    URL_MAPPING = {
        'local_path1.fastq.gz': 'gcs/path/1234/local_path1.fastq.gz',
        'local_path2.fastq.gz': 'gcs/path/4321/local_path2.fastq.gz'
    }

    def run_upload():
        with runner.isolated_filesystem():
            files = ['wes.xlsx'] + list(URL_MAPPING.keys())
            for fname in files:
                with open(fname, 'wb') as f:
                    f.write(b'blah blah metadata')
            args = ['--assay', 'wes', '--xlsx', 'wes.xlsx']
            runner.invoke(cli.upload_assay, args)

    # Set up mocks
    gcloud_login = MagicMock()
    monkeypatch.setattr("cli.cli_v2.gcloud.login", gcloud_login)

    api_initiate_upload = MagicMock()
    api_initiate_upload.return_value = {
        'job_id': JOB_ID,
        'job_etag': JOB_ETAG,
        'url_mapping': URL_MAPPING,
        'gcs_bucket': GCS_BUCKET
    }
    monkeypatch.setattr('cli.cli_v2.api.initiate_upload', api_initiate_upload)

    api_job_succeeded = MagicMock()
    monkeypatch.setattr('cli.cli_v2.api.job_succeeded', api_job_succeeded)

    api_job_failed = MagicMock()
    monkeypatch.setattr('cli.cli_v2.api.job_failed', api_job_failed)

    upload_success = MagicMock()
    monkeypatch.setattr("subprocess.check_output", upload_success)

    monkeypatch.setattr(cli, 'UPLOAD_WORKSPACE', 'workspace')

    # Run a successful upload.
    run_upload()

    gcloud_login.assert_called_once()
    api_initiate_upload.assert_called_once()
    upload_success.assert_called_once()
    api_job_succeeded.assert_called_once_with(JOB_ID, JOB_ETAG)

    # Make an unsuccessful upload
    upload_failure = MagicMock()
    upload_failure.side_effect = Exception
    monkeypatch.setattr("subprocess.check_output", upload_failure)

    run_upload()

    api_job_failed.assert_called_once_with(JOB_ID, JOB_ETAG)
