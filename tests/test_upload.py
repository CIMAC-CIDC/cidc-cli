import time
from unittest.mock import MagicMock

import pytest
import click
from click.testing import CliRunner

from cli import api
from cli import upload

from .util import ExceptionCatchingThread

JOB_ID = -1
JOB_ETAG = "abcd"
GCS_BUCKET = "upload-bucket"
URL_MAPPING = {
    "local_path1.fastq.gz": "gcs/path/1234/fastq/2019-09-04T18:59:45.224099",
    "local_path2.fastq.gz": "gcs/path/4321/fastq/2019-09-04T18:59:45.224099",
}
EXTRA_METADATA = {"lp1": "uuid1"}
GCS_FILE_MAP = {
    "gcs/path/1234/fastq/2019-09-04T18:59:45.224099": "uuid2",
    "gcs/path/4321/fastq/2019-09-04T18:59:45.224099": "uuid3",
}
OPTIONAL_FILES = []
UPLOAD_TOKEN = "test-upload-token"


class UploadMocks:
    def __init__(self, monkeypatch):
        self.gcloud_login = MagicMock()
        monkeypatch.setattr("cli.gcloud.login", self.gcloud_login)

        self.api_initiate_upload = MagicMock()
        self.api_initiate_upload.return_value = api.UploadInfo(
            JOB_ID,
            JOB_ETAG,
            GCS_BUCKET,
            URL_MAPPING,
            EXTRA_METADATA,
            GCS_FILE_MAP,
            OPTIONAL_FILES,
            UPLOAD_TOKEN,
        )
        monkeypatch.setattr(api, "initiate_upload", self.api_initiate_upload)

        self.upload_succeeded = MagicMock()
        monkeypatch.setattr(api, "upload_succeeded", self.upload_succeeded)

        self.upload_failed = MagicMock()
        monkeypatch.setattr(api, "upload_failed", self.upload_failed)

        self._poll_for_upload_completion = MagicMock()
        monkeypatch.setattr(
            upload, "_poll_for_upload_completion", self._poll_for_upload_completion
        )

        self._open_file_mapping = MagicMock()
        monkeypatch.setattr(upload, "_open_file_mapping", self._open_file_mapping)

        self.insert_extra_metadata = MagicMock()
        monkeypatch.setattr("cli.api.insert_extra_metadata", self.insert_extra_metadata)

    def assert_expected_calls(self, failure=False):
        self.gcloud_login.assert_called_once()
        self.api_initiate_upload.assert_called_once()
        if failure:
            self.upload_failed.assert_called_once_with(
                JOB_ID, UPLOAD_TOKEN, JOB_ETAG, GCS_FILE_MAP
            )
        else:
            self.upload_succeeded.assert_called_once_with(
                JOB_ID, UPLOAD_TOKEN, JOB_ETAG, GCS_FILE_MAP
            )
            self._poll_for_upload_completion.assert_called_once_with(
                JOB_ID, UPLOAD_TOKEN
            )


def run_isolated_upload(runner: CliRunner):
    """Run a test upload inside an isolated filesystem"""
    with runner.isolated_filesystem():
        run_upload(runner)


def run_upload(runner: CliRunner):
    """Run a test upload"""
    files = ["wes.xlsx"] + list(URL_MAPPING.keys())
    for fname in files:
        with open(fname, "wb") as f:
            f.write(b"blah blah metadata")
    upload.run_upload("wes", "wes.xlsx")


def test_upload_success(runner: CliRunner, monkeypatch):
    """
    Check that a successful upload call follows the expected execution flow.
    """
    mocks = UploadMocks(monkeypatch)

    upload_success = MagicMock()
    upload_success.return_value = GCS_FILE_MAP
    monkeypatch.setattr(upload, "_gsutil_assay_upload", upload_success)

    # Run a successful upload.
    run_isolated_upload(runner)

    upload_success.assert_called_once()
    mocks.assert_expected_calls()


def test_upload_interrupt(runner: CliRunner, monkeypatch):
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
        run_isolated_upload(runner)

    mocks.assert_expected_calls(failure=True)


def test_upload_exception(runner: CliRunner, monkeypatch):
    """
    Check that a failed upload call alerts the API that the job errored.
    """
    mocks = UploadMocks(monkeypatch)

    # Simulate an exception
    upload_failure = MagicMock()
    upload_failure.side_effect = Exception("bad upload")
    monkeypatch.setattr(upload, "_gsutil_assay_upload", upload_failure)

    with pytest.raises(Exception, match="bad upload"):
        run_isolated_upload(runner)

    mocks.assert_expected_calls(failure=True)


def test_upload_api_initiate_exception(runner: CliRunner, monkeypatch):
    """
    Check that a failed upload call alerts the API that the job errored.
    """
    mocks = UploadMocks(monkeypatch)

    # Simulate an exception
    initiate_failure = MagicMock()
    initiate_failure.side_effect = api.ApiError("bad upload")
    monkeypatch.setattr(api, "initiate_upload", initiate_failure)

    with pytest.raises(Exception, match="bad upload"):
        run_isolated_upload(runner)

    mocks.gcloud_login.assert_called_once()


def test_poll_for_upload_completion(monkeypatch):
    """
    Check that the _poll_for_upload loop follows retry directions,
    times out, succeeds, and fails as expected.
    """
    _timeout_check = 0

    def get_did_timeout(n_tries=5):
        global _timeout_check
        _timeout_check = 0

        def did_timeout():
            global _timeout_check
            if _timeout_check == n_tries:
                return True
            _timeout_check += 1
            return False

        return did_timeout

    click_echo = MagicMock()
    monkeypatch.setattr(click, "echo", click_echo)
    monkeypatch.setattr(click, "secho", click_echo)

    def stdout():
        print(click_echo.call_args_list)
        stdout = "\n".join(
            [args[0][0] for args in click_echo.call_args_list if len(args[0])]
        )
        return stdout

    job_id = 1

    # Simulate a retry with timeout
    retry_in = 2
    retry_upload = MagicMock()
    retry_upload.return_value = api.MergeStatus(None, None, retry_in)
    monkeypatch.setattr(api, "poll_upload_merge_status", retry_upload)
    sleep = MagicMock()
    monkeypatch.setattr(time, "sleep", sleep)
    upload._poll_for_upload_completion(
        job_id, UPLOAD_TOKEN, _did_timeout_test_impl=get_did_timeout(4)
    )
    retry_upload.assert_called_with(job_id, UPLOAD_TOKEN)
    sleep.assert_called_with(1)
    assert len(sleep.call_args_list) == retry_in
    assert "timed out" in stdout()

    click_echo.reset_mock()

    # Simulate a success
    completed = MagicMock()
    completed.return_value = api.MergeStatus("merge-completed", None, None)
    monkeypatch.setattr(api, "poll_upload_merge_status", completed)
    upload._poll_for_upload_completion(
        job_id, UPLOAD_TOKEN, _did_timeout_test_impl=get_did_timeout(1)
    )
    completed.assert_called_once_with(job_id, UPLOAD_TOKEN)
    assert "succeeded" in stdout()

    click_echo.reset_mock()

    # Simulate a success
    failed = MagicMock()
    failed.return_value = api.MergeStatus("upload-failed", "some error details", None)
    monkeypatch.setattr(api, "poll_upload_merge_status", failed)
    upload._poll_for_upload_completion(
        job_id, UPLOAD_TOKEN, _did_timeout_test_impl=get_did_timeout(1)
    )
    failed.assert_called_once_with(job_id, UPLOAD_TOKEN)
    failure_stdout = stdout()
    assert "failed" in failure_stdout
    assert "some error details" in failure_stdout


def test_simultaneous_uploads(runner: CliRunner, monkeypatch):
    """
    Check that two uploads can run simultaneously without the CLI encountering
    errors. This is a smoketest, not a guarantee that the CLI robustly supports
    concurrent uploads for different assays.
    """
    UploadMocks(monkeypatch)

    gsutil_command = MagicMock()
    gsutil_command.return_value = MagicMock("subprocess")
    gsutil_command.return_value.args = ["gsutil", "arg1", "arg2"]
    gsutil_command.return_value.poll = lambda: 0
    gsutil_command.return_value.returncode = 0
    gsutil_command.return_value.stderr = MagicMock("stderr")
    gsutil_command.return_value.stderr.readline = lambda: "gsutil progress"
    monkeypatch.setattr("subprocess.Popen", gsutil_command)

    monkeypatch.setattr("cli.auth.get_id_token", lambda: "test-token")

    def do_upload():
        run_upload(runner)

    with runner.isolated_filesystem():
        t1 = ExceptionCatchingThread(do_upload)
        t2 = ExceptionCatchingThread(do_upload)
        t1.start(), t2.start()
        t1.join(), t2.join()


def test_handle_upload_exc():
    """Check that exceptions are processed correctly"""
    with pytest.raises(KeyboardInterrupt, match="Upload canceled"):
        upload._handle_upload_exc(KeyboardInterrupt())

    with pytest.raises(RuntimeError, match="failed.\nfoo"):
        upload._handle_upload_exc(RuntimeError("foo"))


def test_gsutil_assay_upload(monkeypatch):
    """Check that _gsutil_assay_upload waits for all file upload processes to complete"""
    num_procs = 13
    process_mocks = [MagicMock(name=f"mock #{n}") for n in range(num_procs)]

    def _start_procs(*args):
        """Mock the _start_procs function"""
        for proc in process_mocks:
            proc.start()
            yield proc

    def _wait_for_upload(procs, total, optional_files):
        """Mock the _wait_for_upload function"""
        assert total == num_procs
        for proc in procs:
            proc.stop()
        return []

    monkeypatch.setattr(upload, "_start_procs", _start_procs)
    monkeypatch.setattr(upload, "_wait_for_upload", _wait_for_upload)
    monkeypatch.setattr(
        upload, "_compose_file_mapping", lambda *args: ([0] * num_procs, [])
    )

    upload._gsutil_assay_upload(
        api.UploadInfo(
            JOB_ID,
            JOB_ETAG,
            GCS_BUCKET,
            URL_MAPPING,
            EXTRA_METADATA,
            GCS_FILE_MAP,
            OPTIONAL_FILES,
            UPLOAD_TOKEN,
        ),
        "",
    )

    # Ensure that _gsutil_assay_upload has started and waited for every process
    for proc in process_mocks:
        proc.start.assert_called()
        proc.stop.assert_called()


def test_compose_file_mapping(tmpdir, monkeypatch):
    xlsx = str(tmpdir.join("bar.xlsx"))

    failing_map = {str(tmpdir.join("foo.bar")): "foo.bar"}
    upload_job = api.UploadInfo(
        JOB_ID,
        JOB_ETAG,
        GCS_BUCKET,
        failing_map,
        EXTRA_METADATA,
        GCS_FILE_MAP,
        OPTIONAL_FILES,
        UPLOAD_TOKEN,
    )
    with pytest.raises(Exception, match="Could not locate"):
        upload._compose_file_mapping(upload_job, xlsx)

    # doesn't fail if passed as an optional_file
    upload_job = api.UploadInfo(
        JOB_ID,
        JOB_ETAG,
        GCS_BUCKET,
        failing_map,
        EXTRA_METADATA,
        GCS_FILE_MAP,
        OPTIONAL_FILES + list(failing_map.keys()),
        UPLOAD_TOKEN,
    )
    upload_file_map, gcs_file_map = upload._compose_file_mapping(upload_job, xlsx)
    assert gcs_file_map == ["foo.bar"]

    local_map = {
        tmpdir.join("local.path"): "test/gcs.1a",
        tmpdir.join("test.dir"): "test/gcs.1b",
    }
    input_map = {
        "gs://bucket/gcs.path": "test/gcs.2",
        "gs://bucket/[brackets]": "test/gcs.3",
    }

    # files must exist without care for content, so write garbage
    for k in local_map.keys():
        k.write("foo")

    # but must be {str: str}
    input_map.update({str(k): v for k, v in local_map.items()})
    input_map["test.dir"] = input_map.pop(str(tmpdir.join("test.dir")))

    upload_job = api.UploadInfo(
        JOB_ID,
        JOB_ETAG,
        GCS_BUCKET,
        input_map,
        EXTRA_METADATA,
        GCS_FILE_MAP,
        OPTIONAL_FILES,
        UPLOAD_TOKEN,
    )

    # mock local file check
    isfile = MagicMock()
    isfile.return_value = True
    monkeypatch.setattr("os.path.isfile", isfile)

    # mock gsutil ls file check by returning input
    monkeypatch.setattr(
        "subprocess.run", lambda args, capture_output: MagicMock(returncode=0)
    )

    output_map, skipping = upload._compose_file_mapping(upload_job, xlsx)
    assert len(skipping) == 0, skipping

    for k, v in output_map:
        if "local.path" in k:
            assert v == f"gs://{GCS_BUCKET}/test/gcs.1a"
        elif "dir" in k:
            assert k == str(tmpdir.join("test.dir"))
            assert v == f"gs://{GCS_BUCKET}/test/gcs.1b"
        elif "gcs.path" in k:
            assert v == f"gs://{GCS_BUCKET}/test/gcs.2"
        elif "brackets" in k:
            assert k == "gs://bucket/?brackets]"
            assert v == f"gs://{GCS_BUCKET}/test/gcs.3"
