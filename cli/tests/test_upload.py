"""
Tets for functions in upload.py
"""
from upload.upload import parse_upload_manifest, confirm_manifest_files


def test_parse_upload_manifest():
    """
    Test for the parse_upload_manifest function.
    """
    results = parse_upload_manifest("./sample_data/dfci_9999_manifest.csv")
    assert len(results) == 30


def test_confirm_manifest_files():
    """
    Test confirm_manifest_files
    """
    directory = "sample_data/"
    file_names = ["dfci_9999_manifest.csv"]
    assert confirm_manifest_files(directory, file_names)


def test_bad_confirm_manifest_files():
    """
    Test fails when not found
    """
    assert not confirm_manifest_files("foo", ["bar"])
