import pytest
from unittest.mock import MagicMock

from cli import rectify_upload
from cidc_ngs_pipeline_api import OUTPUT_APIS


def test_cidc_schemas(monkeypatch):
    monkeypatch.setattr(
        "cli.upload._gsutil_assay_upload", lambda upload_info, xlsx: upload_info
    )
    upload_info = rectify_upload.gsutil_assay_overwrite(
        rectify_upload.Template.from_type("wes_analysis"),
        "tests/data/wes_analysis_template.xlsx",
    )

    # make sure that the url_mapping is generated correctly
    # new should be a valid formatted file_path_template's from the WES output API
    # old will be checked for existence by upload._check_for_gs_files within upload._gsutil_assay_upload
    values = {
        "run id": ["CTTTPP111.00", "CTTTPP121.00"],
        "normal cimac id": ["CTTTPP112.00", "CTTTPP122.00"],
        "tumor cimac id": ["CTTTPP111.00", "CTTTPP121.00"],
    }
    target_names = [
        file["file_path_template"].replace(f"{{{value_name}}}", value)
        for value_name, section in OUTPUT_APIS["wes"].items()
        for file in section
        for value in values[value_name]
    ]
    for old, new in upload_info.url_mapping.items():
        assert old.startswith(rectify_upload.CURRENT_GCS_BUCKET)

        assert new.startswith("gs://cidc-data-staging/10021_wes_test/wes_redo/")
        new_path = new.replace("gs://cidc-data-staging/10021_wes_test/wes_redo/", "")
        assert new_path in target_names


def test_file_map_patching(monkeypatch):
    old_file_mapping = MagicMock()
    old_file_mapping.return_value = ([("a", 0), ("b", 1)], [])
    monkeypatch.setattr("cli.upload._old_compose_file_mapping", old_file_mapping)
    assert rectify_upload.upload._compose_file_mapping(None, None)[0] == [
        (0, "a"),
        (1, "b"),
    ]
    old_file_mapping.assert_called_once()
