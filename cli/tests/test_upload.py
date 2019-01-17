"""
Tets for functions in upload.py
"""
from upload.upload import parse_upload_manifest


def test_parse_upload_manifest():
    """
    Test for the parse_upload_manifest function.
    """
    results = parse_upload_manifest("./sample_data/dfci_9999_manifest.csv")
    assert len(results) == 30
