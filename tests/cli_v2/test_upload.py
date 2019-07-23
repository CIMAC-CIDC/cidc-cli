from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from cli.cli_v2 import api
from cli.cli_v2 import upload

JOB_ID = 1
JOB_ETAG = 'abcd'
GCS_BUCKET = 'upload-bucket'
URL_MAPPING = {
    'local_path1.fastq.gz': 'gcs/path/1234/local_path1.fastq.gz',
    'local_path2.fastq.gz': 'gcs/path/4321/local_path2.fastq.gz'
}


class UploadMocks:
    def __init__(self, monkeypatch):
        self.gcloud_login = MagicMock()
        monkeypatch.setattr("cli.cli_v2.gcloud.login", self.gcloud_login)

        self.api_initiate_upload = MagicMock()
        self.api_initiate_upload.return_value = api.UploadInfo(
            JOB_ID, JOB_ETAG, GCS_BUCKET, URL_MAPPING)
        monkeypatch.setattr(api, "initiate_upload", self.api_initiate_upload)

        self.api_job_succeeded = MagicMock()
        monkeypatch.setattr(api, "job_succeeded", self.api_job_succeeded)

        self.api_job_failed = MagicMock()
        monkeypatch.setattr(api, "job_failed", self.api_job_failed)

        monkeypatch.setattr(upload, 'UPLOAD_WORKSPACE', 'workspace')

    def assert_expected_calls(self, failure=False):
        self.gcloud_login.assert_called_once()
        self.api_initiate_upload.assert_called_once()
        if failure:
            self.api_job_failed.assert_called_once_with(JOB_ID, JOB_ETAG)
        else:
            self.api_job_succeeded.assert_called_once_with(JOB_ID, JOB_ETAG)


def run_upload(runner: CliRunner):
    with runner.isolated_filesystem():
        files = ['wes.xlsx'] + list(URL_MAPPING.keys())
        for fname in files:
            with open(fname, 'wb') as f:
                f.write(b'blah blah metadata')
        upload.upload_assay('wes', 'wes.xlsx')


def test_upload_assay_success(runner: CliRunner, monkeypatch):
    """
    Check that a successful upload call follows the expected execution flow.
    """
    mocks = UploadMocks(monkeypatch)

    upload_success = MagicMock()
    monkeypatch.setattr(upload, "_gsutil_assay_upload", upload_success)

    # Run a successful upload.
    run_upload(runner)

    upload_success.assert_called_once()
    mocks.assert_expected_calls()


def test_upload_assay_interrupt(runner: CliRunner, monkeypatch):
    """
    Check that a KeyboardInterrupt-ed upload call alerts the API that the job errored.
    """
    mocks = UploadMocks(monkeypatch)

    # Simulate a keyboard interrupt
    upload_failure = MagicMock()
    upload_failure.side_effect = KeyboardInterrupt
    monkeypatch.setattr(upload, "_gsutil_assay_upload", upload_failure)

    # Run an interrupted upload.
    with pytest.raises(KeyboardInterrupt):
        run_upload(runner)

    mocks.assert_expected_calls(failure=True)


def test_upload_assay_exception(runner: CliRunner, monkeypatch):
    """
    Check that a failed upload call alerts the API that the job errored.
    """
    mocks = UploadMocks(monkeypatch)

    # Simulate an exception
    upload_failure = MagicMock()
    upload_failure.side_effect = Exception("bad upload")
    monkeypatch.setattr(upload, "_gsutil_assay_upload", upload_failure)

    with pytest.raises(Exception, match="bad upload"):
        run_upload(runner)

    mocks.assert_expected_calls(failure=True)
