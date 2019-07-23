#!/usr/bin/env python
"""
Tets for functions in upload.py
"""
__author__ = "Lloyd McCarthy"
__license__ = "MIT"

import os
import unittest
from unittest.mock import patch

from cli.upload.upload import (
    RequestInfo,
    parse_upload_manifest,
    parse_upload_manifest2,
    update_job_status,
    upload_files,
    find_manifest_path,
    check_id_present,
    guess_file_ext,
    create_manifest_payload,
    upload_manifest,
)
from cli.utilities.cli_utilities import Selections

from .helper_functions import mock_with_inputs

NON_STATIC_INPUTS = {
    "FASTQ_NORMAL_1",
    "FASTQ_NORMAL_2",
    "FASTQ_TUMOR_1",
    "FASTQ_TUMOR_2",
}

SELECTIONS = Selections(
    "token",
    {
        "trial_name": "trial_1",
        "_id": "abc123",
        "samples": {
            "CIMAC_P1_S1",
            "CIMAC_P1_S2",
            "CIMAC_P2_S1",
            "CIMAC_P2_S2",
            "CIMAC_P3_S1",
            "CIMAC_P3_S2",
        },
    },
    {"assay_name": "assay_1", "assay_id": "bca231"},
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
            "cli.upload.upload.EVE_FETCHER.patch", return_value={"status_code": 200}
        ):
            request_info = RequestInfo(
                {"_id": "abcd123", "_etag": "etag"}, "token", {}, [{}]
            )
            with self.subTest():
                self.assertTrue(update_job_status(True, request_info))
            with self.subTest():
                self.assertTrue(update_job_status(False, request_info))
        with patch("cli.upload.upload.EVE_FETCHER.patch") as patch_mock:
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
            [
                {
                    "a": 1,
                    "uuid_alias": "2145512",
                    "file_name": "PD_010N.sorted.SNV_1.fq.gz",
                },
                {
                    "b": 2,
                    "uuid_alias": "2145513",
                    "file_name": "PD_010N.sorted.SNV_2.fq.gz",
                },
                {
                    "c": 3,
                    "uuid_alias": "2145123",
                    "file_name": "PD_010T.sorted.SNV_1.fq.gz",
                },
                {
                    "d": 4,
                    "uuid_alias": "455123",
                    "file_name": "PD_010T.sorted.SNV_2.fq.gz",
                },
            ],
        )
        with patch("subprocess.check_output", return_value=""):
            with patch("cli.upload.upload.update_job_status", return_value=True):
                self.assertEqual(upload_files(
                    directory, request_info), "abcd123")
                found = [
                    os.path.isfile(os.path.join(directory, item["file_name"]))
                    for item in request_info.files_uploaded
                ]
                if not all(found):
                    raise AssertionError("Files were renamed properly.")

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
            self.assertEqual(guess_file_ext("something.fa"), "FASTQ")
        with self.subTest():
            self.assertIsNone(guess_file_ext("something.foo.bar"))

    def test_upload_manifest(self):
        """
        Test upload_manifest.
        """
        with self.subTest():
            with patch(
                "builtins.input",
                return_value="./sample_data/fake_manifest_wes/manifest.csv",
            ):
                file_dir, ingestion_payload, file_names = upload_manifest(
                    NON_STATIC_INPUTS, SELECTIONS
                )
                self.assertTrue(
                    len(ingestion_payload["files"]) == 24
                    and len(file_names) == 24
                    and file_dir == "./sample_data/fake_manifest_wes"
                )
        with self.subTest():
            with patch(
                "builtins.input",
                return_value="./sample_data/testing_manifests/manifest.bad.sample_id",
            ):
                with self.assertRaises(RuntimeError):
                    upload_manifest(NON_STATIC_INPUTS, SELECTIONS)
        with self.subTest():
            with patch(
                "builtins.input",
                return_value="./sample_data/testing_manifests/manifest.csv",
            ):
                with self.assertRaises(FileNotFoundError):
                    upload_manifest(NON_STATIC_INPUTS, SELECTIONS)

    def test_upload_manifest2(self):
        """
        Test upload_manifest: redux
        """
        with self.subTest():
            with patch(
                "builtins.input",
                return_value="./sample_data/fake_manifest_wes/wes_template.xlsx",
            ):
                file_dir, ingestion_payload, file_names = upload_manifest(
                    NON_STATIC_INPUTS, SELECTIONS
                )
                self.assertTrue(
                    #len(ingestion_payload["files"]) == 24
                    #and len(file_names) == 24
                    file_dir == "./sample_data/fake_manifest_wes"
                )
        with self.subTest():
            with patch(
                "builtins.input",
                return_value="./sample_data/testing_manifests/manifest.bad.sample_id",
            ):
                with self.assertRaises(RuntimeError):
                    upload_manifest(NON_STATIC_INPUTS, SELECTIONS)
        with self.subTest():
            with patch(
                "builtins.input",
                return_value="./sample_data/testing_manifests/manifest.csv",
            ):
                with self.assertRaises(FileNotFoundError):
                    upload_manifest(NON_STATIC_INPUTS, SELECTIONS)


def test_find_manifest_path():
    """
    Test find_manifest_path
    """
    with patch(
        "builtins.input",
        return_value="./sample_data/testing_manifests/dfci_9999_manifest.csv",
    ):
        if (
            find_manifest_path()
            != "./sample_data/testing_manifests/dfci_9999_manifest.csv"
        ):
            raise AssertionError("test_find_manifest_path: Assertion Failed")
    if not mock_with_inputs(
        ["foo", "./sample_data/testing_manifests/dfci_9999_manifest.csv"],
        find_manifest_path,
        [],
    ):
        raise AssertionError("test_find_manifest_path: Assertion Failed")


def test_check_id_present():
    """
    Test check_id_present
    """
    if not check_id_present("A", ["A", "B", "C"]):
        raise AssertionError("test_check_id_present: Assertion Failed")
    if check_id_present("D", ["A", "B", "C"]):
        raise AssertionError("test_check_id_present: Assertion Failed")


def test_manifest_payload_migration():
    """
    Tests dropin replacement of "create_manifest_payload"
    """
    tumor_normal_pairs1 = parse_upload_manifest(
        "./sample_data/fake_manifest_wes/manifest.csv"
    )
    entry1 = tumor_normal_pairs1[0]

    tumor_normal_pairs2 = parse_upload_manifest2(
        "./sample_data/fake_manifest_wes/wes_template.xlsx"
    )
    entry2 = tumor_normal_pairs2[0]

    # assert equality
    assert len(entry1) == len(entry2)

    # next function using old way
    payload1, file_names1 = create_manifest_payload(
        entry1,
        NON_STATIC_INPUTS,
        SELECTIONS,
        os.path.dirname("./sample_data/fake_manifest_wes/"),
    )
    if len(file_names1) != 4 or len(payload1) != 4:
        raise AssertionError("test_create_manifest_payload: Assertion Failed")

    # new function
    payload2, file_names2 = create_manifest_payload(
        entry2,
        NON_STATIC_INPUTS,
        SELECTIONS,
        os.path.dirname("./sample_data/fake_manifest_wes/"),
    )
    if len(file_names2) != 4 or len(payload2) != 4:
        raise AssertionError("test_create_manifest_payload: Assertion Failed")