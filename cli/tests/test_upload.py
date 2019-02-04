"""
Tets for functions in upload.py
"""
import unittest
from unittest.mock import patch
from subprocess import CalledProcessError

from upload.upload import (
    RequestInfo,
    confirm_manifest_files,
    parse_upload_manifest,
    update_job_status,
    upload_files,
    find_manifest_path,
    check_id_present,
    guess_file_ext,
)


class TestUploadFunctions(unittest.TestCase):
    """Test class for the update job status function

    Arguments:
        unittest {[type]} -- [description]
    """

    def test_update_job_status(self):
        """
        Test update_job_status
        """
        with patch(
            "upload.upload.EVE_FETCHER.patch", return_value={"status_code": 200}
        ):
            request_info = RequestInfo(
                {"_id": "abcd123", "_etag": "etag"}, "token", {}, [{}]
            )
            with self.subTest():
                self.assertTrue(update_job_status(True, request_info))
            with self.subTest():
                self.assertTrue(update_job_status(False, request_info))
        with patch("upload.upload.EVE_FETCHER.patch") as patch_mock:
            with self.subTest():
                patch_mock.side_effect = RuntimeError("Test Error")
                self.assertFalse(update_job_status(True, request_info))

    def test_upload_files(self):
        """
        Test upload_files
        """
        directory = "./sample_data/fake_manifest_wes/"
        request_info = RequestInfo(
            {"_id": "abcd123", "_etag": "etag"},
            "token",
            {"google_folder_path": "somepath"},
            [{"a": 1}, {"b": 2}, {"c": 3}, {"d": 4}],
        )
        with patch("subprocess.check_output", return_value=""):
            with patch("upload.upload.update_job_status", return_value=True):
                self.assertEqual(upload_files(directory, request_info), "abcd123")
                with patch("subprocess.check_output") as subprocess_mock:
                    subprocess_mock.side_effect = CalledProcessError(
                        returncode=1, cmd="gsutil", output="error"
                    )
                    self.assertFalse(upload_files(directory, request_info))

    def test_parse_upload_manifest(self):
        """
        Test for the parse_upload_manifest function.
        """
        with self.subTest():
            results = parse_upload_manifest(
                "./sample_data/testing_manifests/dfci_9999_manifest.csv"
            )
            self.assertEqual(len(results), 30)
        with self.subTest():
            results = parse_upload_manifest(
                "./sample_data/testing_manifests/manifest.tsv"
            )
            self.assertEqual(len(results), 6)
        with self.subTest():
            with self.assertRaises(TypeError):
                results = parse_upload_manifest(
                    "./sample_data/testing_manifests/manifest.bad"
                )
        with self.subTest():
            with self.assertRaises(IndexError):
                results = parse_upload_manifest(
                    "./sample_data/testing_manifests/manifest.extra_column.csv"
                )
    def test_guess_file_ext(self):
        """
        Test guess_file_ext
        """
        with self.subTest():
            self.assertEqual(guess_file_ext("something.fa.gz"), "FASTQ")
        with self.subTest():
            self.assertRaises(KeyError, guess_file_ext("something.foo.bar"))


def test_confirm_manifest_files():
    """
    Test confirm_manifest_files
    """
    directory = "sample_data/testing_manifests/"
    file_names = ["dfci_9999_manifest.csv"]
    assert confirm_manifest_files(directory, file_names)


def test_bad_confirm_manifest_files():
    """
    Test fails when not found
    """
    assert not confirm_manifest_files("foo", ["bar"])


def test_find_manifest_path():
    """
    Test find_manifest_path
    """
    with patch(
        "builtins.input",
        return_value="./sample_data/testing_manifests/dfci_9999_manifest.csv",
    ):
        assert (
            find_manifest_path()
            == "./sample_data/testing_manifests/dfci_9999_manifest.csv"
        )

def test_check_id_present():
    """
    Test check_id_present
    """
    assert check_id_present("A", ["A", "B", "C"])
    assert not check_id_present("D", ["A", "B", "C"])
