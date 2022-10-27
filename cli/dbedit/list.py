import pandas as pd
from typing import Dict, List, Set

from .core import (
    DownloadableFiles,
    get_clinical_downloadable_files,
    get_misc_data_files,
    get_trial_if_exists,
    get_shipments,
    Session,
    TrialMetadata,
    UploadJobs,
)

# copied from cidc_schemas.prism.constants
# Windows doesn't handle current jsonschemas RefResolver configuration
SUPPORTED_ANALYSES: List[str] = [
    "atacseq_analysis",
    "cytof_analysis",
    "rna_level1_analysis",
    "tcr_analysis",
    "wes_analysis",
    "wes_tumor_only_analysis",
]
SUPPORTED_ASSAYS: List[str] = [
    "atacseq_fastq",
    "wes_fastq",
    "wes_bam",
    "olink",
    "cytof",
    "ihc",
    "elisa",
    "rna_fastq",
    "rna_bam",
    "mif",
    "tcr_adaptive",
    "tcr_fastq",
    "hande",
    "nanostring",
    "clinical_data",
    "misc_data",
    "ctdna",
    "microbiome",
    "mibi",
]

SUPPORTED_ASSAYS_AND_ANALYSES: Set[str] = {
    # everything once, without file type specifiers
    a.split("_fastq")[0].split("_bam")[0].split("_adaptive")[0]
    for a in SUPPORTED_ASSAYS + SUPPORTED_ANALYSES
} | {"wes_analysis_old", "wes_tumor_only_analysis_old"}


pd.set_option("display.max_columns", None)
pd.set_option("display.max_colwidth", None)
pd.set_option("display.max_rows", None)


def _describe_olink(metadata_json: dict) -> pd.DataFrame:
    ret = pd.DataFrame(columns=["batch_id", "file", "cimac_id"])
    for batch in metadata_json.get("assays", {}).get("olink", {"batches": []})[
        "batches"
    ]:
        if "combined" not in batch:
            for record in batch["records"]:
                ret = ret.append(
                    pd.DataFrame(
                        [
                            {
                                "batch_id": batch["batch_id"],
                                "file": record["files"]["assay_npx"]["object_url"],
                                "cimac_id": sample,
                            }
                            for sample in record["files"]["assay_npx"]["samples"]
                        ]
                    )
                )
        else:
            ret = ret.append(
                pd.DataFrame(
                    [
                        {
                            "batch_id": batch["batch_id"],
                            "file": "combined",
                            "cimac_id": sample,
                        }
                        for sample in batch["combined"]["npx_file"]["samples"]
                    ]
                )
            )

    return ret.reset_index(drop=True)


def _describe_elisa(metadata_json: dict) -> pd.DataFrame:
    # elisa is special case
    ret = pd.DataFrame(columns=["assay_run_id", "cimac_id"])
    for batch in metadata_json.get("assays", {}).get("elisa", []):
        ret = ret.append(
            pd.DataFrame(
                [
                    {"cimac_id": sample, "assay_run_id": batch["assay_run_id"]}
                    for sample in batch["assay_xlsx"]["samples"]
                ]
            )
        )
    return ret.reset_index(drop=True)


def _describe_nanostring(metadata_json: dict) -> pd.DataFrame:
    # nanostring is special case
    ret = pd.DataFrame(columns=["batch_id", "run_id", "cimac_id"])
    for batch in metadata_json.get("assays", {}).get("nanostring", []):
        for run in batch["runs"]:
            ret = ret.append(
                pd.DataFrame(
                    [
                        {
                            "batch_id": batch["batch_id"],
                            "run_id": run["run_id"],
                            "cimac_id": sample["cimac_id"],
                        }
                        for sample in run["samples"]
                    ]
                )
            )
    return ret.reset_index(drop=True)


def _describe_rna_analysis(metadata_json: dict) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"cimac_id": record["cimac_id"]}
            for record in metadata_json.get("analysis", {}).get(
                "rna_analysis", {"level_1": []}
            )["level_1"]
        ]
    )


def _describe_cytof_analysis(
    metadata_json: dict,
) -> pd.DataFrame:
    ret = pd.DataFrame(columns=["batch_id", "cimac_id"])
    for batch in metadata_json.get("assays", {}).get("cytof", []):
        if "astrolabe_analysis" in batch:
            ret = ret.append(
                pd.DataFrame(
                    [
                        {
                            "batch_id": batch["batch_id"],
                            "cimac_id": record["cimac_id"],
                        }
                        for record in batch["records"]
                        if "output_files" in record
                    ]
                )
            )
    return ret.reset_index(drop=True)


def _describe_wes_analysis(metadata_json: dict, just_old: bool = False) -> pd.DataFrame:
    ret = pd.DataFrame(columns=["run_id", "tumor_cimac_id", "normal_cimac_id"])

    for subkey in ["wes_analysis", "wes_analysis_old"]:
        if just_old and "old" not in subkey:
            continue

        ret = ret.append(
            pd.DataFrame(
                [
                    {
                        "run_id": run["run_id"],
                        "tumor_cimac_id": run["tumor"]["cimac_id"],
                        "normal_cimac_id": run["normal"]["cimac_id"],
                    }
                    for run in metadata_json.get("analysis", {}).get(
                        subkey, {"pair_runs": []}
                    )["pair_runs"]
                ]
            )
        )
    return ret.reset_index(drop=True)


def _describe_wes_tumor_only_analysis(
    metadata_json: dict, just_old: bool = False
) -> pd.DataFrame:
    ret = pd.DataFrame(columns=["cimac_id"])

    for subkey in ["wes_tumor_only_analysis", "wes_tumor_only_analysis_old"]:
        if just_old and "old" not in subkey:
            continue

        ret = ret.append(
            pd.DataFrame(
                [
                    {"cimac_id": run["tumor"]["cimac_id"]}
                    for run in metadata_json.get("analysis", {}).get(
                        subkey, {"runs": []}
                    )["runs"]
                ]
            )
        )
    return ret.reset_index(drop=True)


def _describe_batched(metadata_json: dict, assay_or_analysis: str) -> pd.DataFrame:
    ret = pd.DataFrame(columns=["batch_id", "cimac_id"])
    for batch in metadata_json.get(
        "analysis" if "analysis" in assay_or_analysis else "assays", {}
    ).get(assay_or_analysis, {"batches": []})["batches"]:
        ret = ret.append(
            pd.DataFrame(
                [
                    {
                        "batch_id": batch["batch_id"],
                        "cimac_id": record["cimac_id"],
                    }
                    for record in batch["records"]
                ]
            )
        )
    return ret.reset_index(drop=True)


def _describe_generic(metadata_json: dict, assay_or_analysis: str) -> pd.DataFrame:
    ret = pd.DataFrame(columns=["batch_id", "cimac_id"])
    for batch_num, batch in enumerate(
        metadata_json.get(
            "analysis" if "analysis" in assay_or_analysis else "assays", {}
        ).get(assay_or_analysis, [])
    ):
        ret = ret.append(
            pd.DataFrame(
                [
                    {
                        "batch_id": batch.get("batch_id", str(batch_num)),
                        "cimac_id": record["cimac_id"],
                    }
                    for record in batch["records"]
                ]
            )
        )
    return ret.reset_index(drop=True)


def list_data_cimac_ids(trial_id: str, assay_or_analysis: str) -> None:
    """
    Prints a table listing all samples for the given assay/analysis and trial

    Parameters
    ----------
    trial_id: str
        the id of the trial to investigate
    assay_or_analysis: str
        the name of the assay / analysis to investigate
        must be in SUPPORTED_ASSAYS_AND_ANALYSES
    """
    if assay_or_analysis not in SUPPORTED_ASSAYS_AND_ANALYSES:
        print("Assay / analysis not supported:", assay_or_analysis)
        return

    elif assay_or_analysis == "clinical_data":
        list_clinical(trial_id)
        return
    elif assay_or_analysis == "misc_data":
        list_misc_data(trial_id)
        return

    with Session.begin() as session:
        trial: TrialMetadata = get_trial_if_exists(trial_id, session=session)
        cimac_ids: pd.DataFrame

        if assay_or_analysis == "olink":
            cimac_ids: pd.DataFrame = _describe_olink(metadata_json=trial.metadata_json)
        elif assay_or_analysis == "elisa":
            cimac_ids: pd.DataFrame = _describe_elisa(metadata_json=trial.metadata_json)
        elif assay_or_analysis == "nanostring":
            cimac_ids: pd.DataFrame = _describe_nanostring(
                metadata_json=trial.metadata_json
            )

        elif assay_or_analysis == "rna_level1_analysis":
            cimac_ids: pd.DataFrame = _describe_rna_analysis(
                metadata_json=trial.metadata_json
            )

        elif assay_or_analysis == "cytof_analysis":
            cimac_ids: pd.DataFrame = _describe_cytof_analysis(
                metadata_json=trial.metadata_json
            )

        elif assay_or_analysis in ["wes_analysis", "wes_analysis_old"]:
            cimac_ids: pd.DataFrame = _describe_wes_analysis(
                metadata_json=trial.metadata_json,
                just_old="old" in assay_or_analysis,
            )

        elif assay_or_analysis in [
            "wes_tumor_only_analysis",
            "wes_tumor_only_analysis_old",
        ]:
            cimac_ids: pd.DataFrame = _describe_wes_tumor_only_analysis(
                metadata_json=trial.metadata_json,
                just_old="old" in assay_or_analysis,
            )

        elif assay_or_analysis in [
            "mibi",
            "tcr_analysis",
        ]:
            cimac_ids: pd.DataFrame = _describe_batched(
                metadata_json=trial.metadata_json, assay_or_analysis=assay_or_analysis
            )

        else:
            cimac_ids: pd.DataFrame = _describe_generic(
                metadata_json=trial.metadata_json, assay_or_analysis=assay_or_analysis
            )

        # business print
        print(cimac_ids)


def list_clinical(trial_id: str) -> None:
    """
    Prints a table describing all clinical files for the given trial

    Parameters
    ----------
    trial_id: str
        the id of the trial to investigate
    """
    with Session.begin() as session:
        trial: TrialMetadata = get_trial_if_exists(trial_id, session=session)
        clinical_files: List[DownloadableFiles] = get_clinical_downloadable_files(
            trial_id, session=session
        )

        number_of_participants: Dict[str, int] = dict()
        comments: Dict[str, str] = dict()
        for record in trial.metadata_json.get("clinical_data", {}).get("records", []):
            object_url: str = record["clinical_file"]["object_url"]
            number_of_participants[object_url] = record["clinical_file"][
                "number_of_participants"
            ]
            if "comment" in record:
                comments[object_url] = record["comment"]

        print(
            pd.DataFrame(
                {
                    "object_url": f.object_url,
                    "filename": f.object_url.split("/clinical/")[1],
                    "num_participants": number_of_participants.get(f.object_url),
                    "created": f._created,
                    "comment": comments.get(f.object_url, pd.NA),
                }
                for f in clinical_files
            )
        )


def list_misc_data(trial_id: str) -> None:
    """
    Prints a table describing all misc_data files for the given trial

    Parameters
    ----------
    trial_id: str
        the id of the trial to investigate
    """
    with Session.begin() as session:
        trial: TrialMetadata = get_trial_if_exists(trial_id, session=session)
        misc_data_files: List[DownloadableFiles] = get_misc_data_files(
            trial_id, session=session
        )

        descriptions: Dict[str, str] = dict()
        batch_numbers: Dict[str, int] = dict()
        for batch_idx, batch in enumerate(
            trial.metadata_json.get("assays", {}).get("misc_data", [])
        ):
            for file in batch["files"]:
                object_url = file["file"]["object_url"]
                batch_numbers[object_url] = batch_idx

                if "description" in file:
                    descriptions[object_url] = file["description"]

        print(
            pd.DataFrame(
                {
                    "batch_id": batch_numbers.get(f.object_url, pd.NA),
                    "object_url": f.object_url,
                    "filename": f.object_url.split("/misc_data/")[1],
                    "created": f._created,
                    "description": descriptions.get(f.object_url, pd.NA),
                }
                for f in misc_data_files
            )
        )


def list_shipments(trial_id: str) -> None:
    """
    Prints a table describing all shipments for the given trial

    Parameters
    ----------
    trial_id: str
        the id of the trial to investigate
    """
    with Session.begin() as session:
        shipments: List[UploadJobs] = get_shipments(trial_id, session=session)
        print(
            pd.DataFrame(
                {
                    "upload_type": u.upload_type,
                    "manifest_id": u.metadata_patch["shipments"][0]["manifest_id"],
                    "num_samples": sum(
                        len(p["samples"]) for p in u.metadata_patch["participants"]
                    ),
                    "created": u._created,
                }
                for u in shipments
            )
        )
