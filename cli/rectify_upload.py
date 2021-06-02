from typing import List

from .api import UploadInfo
from . import upload

from cidc_schemas.prism import prismify, set_prism_encrypt_key
from cidc_schemas.template import Template
from cidc_schemas.template_reader import XlTemplateReader

set_prism_encrypt_key("")

# will be prepend to calculated GCS URIs to find current data
CURRENT_GCS_BUCKET = "gs://cidc-data-staging"


def gsutil_assay_overwrite(template: Template, xlsx_path: str):
    xlsx, errs = XlTemplateReader.from_excel(xlsx_path)
    assert len(errs) == 0, "\n".join([str(e) for e in errs])

    upload._old_compose_file_mapping = upload._compose_file_mapping

    def compose_file_mapping_overwrite(*args, **kwargs):

        res, missing_optional_files = upload._old_compose_file_mapping(*args, **kwargs)
        res = [r[::-1] for r in res]
        return res, missing_optional_files

    upload._compose_file_mapping = (
        compose_file_mapping_overwrite  # this is the reversal
    )

    _, files, errs = prismify(xlsx, template)
    assert len(errs) == 0, "\n".join([str(e) for e in errs])
    if not all(f.local_path.startswith("gs://") for f in files):
        raise Exception("All 'local' files must be on GCS")

    url_mapping = {
        f"{CURRENT_GCS_BUCKET}/{file.gs_key}": file.local_path for file in files
    }
    # all local_path's are gs:// from check above, so will use cidc_cli.upload._check_for_gs_files

    optional_files = [
        f.gs_key
        for f in files
        if (
            f.allow_empty
            or "haplotyper.vcf.gz" in f.gs_key
            or "vcf_tnscope_filter_neoantigen.vcf" in f.gs_key
        )
    ]  # use gs_key instead of local_path

    upload_info = UploadInfo(
        job_id=-1,
        job_etag="",
        gcs_bucket=CURRENT_GCS_BUCKET,
        url_mapping=url_mapping,
        extra_metadata=[],
        gcs_file_map=url_mapping.copy(),
        optional_files=optional_files,
        token="",
    )

    # returns gcs_file_map without missing optional files
    return upload._gsutil_assay_upload(upload_info, xlsx_path)


if __name__ == "__main__":
    template = Template.from_type("wes_analysis")
    gsutil_assay_overwrite(
        template,
        "/mnt/c/Users/vannost/Documents/Filled Templates/10021 WES Paired Analysis/CNTZ4ZJYN.01.xlsx",
    )
