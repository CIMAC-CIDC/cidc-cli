from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .core import (
    DownloadableFiles,
    get_clinical_downloadable_files,
    get_shipments,
    get_trial_if_exists,
    Session,
    TrialMetadata,
    UploadJobs,
)
from .list import SUPPORTED_ASSAYS_AND_ANALYSES


def _get_all_object_urls(target: dict) -> List[str]:
    ret = []
    for key, value in target.items():
        if key == "object_url":
            ret.append(value)
        if isinstance(value, dict):
            ret.extend(_get_all_object_urls(value))
        if isinstance(value, list):
            for each in value:
                if isinstance(each, dict):
                    ret.extend(_get_all_object_urls(each))
                # no second-level lists
    return ret


def _remove_misc_data_from_blob(
    metadata_json: dict,
    trial_id: str,
    batch_id: str,
    filename: str = None,
) -> Tuple[Optional[dict], List[str]]:
    try:
        batch_id: int = int(batch_id)
    except ValueError:
        print(f"Error: for misc_data, batch_id must be an integer, not {batch_id}")
        return None, []

    if batch_id >= len(metadata_json.get("assays", {}).get("misc_data", [])):
        print(f"Cannot find misc_data batch {batch_id} for trial {trial_id}")
        return None, []

    object_urls_to_delete: List[str] = []
    if filename:
        filenames: List[str] = [
            file["file"]["object_url"].split("/misc_data/")[1]
            for file in metadata_json["assays"]["misc_data"][batch_id]["files"]
        ]
        if filename not in filenames:
            print(
                f"Cannot find file {filename} in batch {batch_id} for trial {trial_id}"
            )
        else:
            record: dict = metadata_json["assays"]["misc_data"][batch_id]["files"].pop(
                filenames.index(filename)
            )
            object_urls_to_delete.extend(_get_all_object_urls(record))

    else:
        batch: dict = metadata_json["assays"]["misc_data"].pop(batch_id)
        object_urls_to_delete.extend(_get_all_object_urls(batch))

    return metadata_json, object_urls_to_delete


def _remove_olink_from_blob(
    metadata_json: dict, trial_id: str, batch_id: str, filename: str = None
) -> Tuple[Optional[dict], List[str]]:
    batch_ids: List[str] = [
        batch["batch_id"]
        for batch in metadata_json.get("assays", {}).get("olink", {"batches": []})[
            "batches"
        ]
    ]
    if batch_id != "study" and batch_id not in batch_ids:
        print(f"Cannot find olink batch {batch_id} for trial {trial_id}")
        return None, []

    object_urls_to_delete: List[str] = []
    batch_idx: int = batch_ids.index(batch_id) if batch_id != "study" else None
    if filename:
        if filename == "combined":
            if "combined" not in metadata_json["assays"]["olink"]["batches"][batch_idx]:
                print(
                    f"Cannot find a combined file for olink batch {batch_id} for trial {trial_id}"
                )
                return None, []
            else:
                # otherwise just the one file
                target: dict = metadata_json["assays"]["olink"]["batches"][
                    batch_idx
                ].pop("combined")
                object_urls_to_delete.extend(_get_all_object_urls(target))
        else:
            object_urls: List[str] = [
                record["files"]["assay_npx"]["object_url"]
                for record in metadata_json["assays"]["olink"]["batches"][batch_idx][
                    "records"
                ]
            ]
            if filename not in object_urls:
                print(
                    f"Cannot find a file {filename} in olink batch {batch_id} for trial {trial_id}"
                )
                return None, []
            else:
                target: dict = metadata_json["assays"]["olink"]["batches"][batch_idx][
                    "records"
                ].pop(object_urls.index(filename))
                object_urls_to_delete.extend(_get_all_object_urls(target))

    elif batch_id == "study":
        # batch_idx is None
        target: dict = metadata_json["assays"]["olink"].pop("study")
        object_urls_to_delete.extend(_get_all_object_urls(target))

    else:
        target: dict = metadata_json["assays"]["olink"]["batches"].pop(batch_idx)
        object_urls_to_delete.extend(_get_all_object_urls(target))

    # also remove hanging structures
    target = dict()
    if filename:
        # if we didn't pop the batch but might have left it hanging
        # if we DID pop, batch_idx would either not exist or point to the following entry
        batch: dict = metadata_json["assays"]["olink"]["batches"][
            batch_idx
        ]  # for convenience
        if "combined" not in batch and not batch["records"]:
            # if no combined or any records, remove the whole batch
            target["batch"] = metadata_json["assays"]["olink"]["batches"].pop(batch_idx)
    if "study" not in metadata_json and not metadata_json["assays"]["olink"]["batches"]:
        # if no batches, remove the whole assay
        target["assay"] = metadata_json["assays"].pop("olink")
    if target:
        object_urls_to_delete.extend(_get_all_object_urls(target))

    return metadata_json, object_urls_to_delete


def _remove_elisa_from_blob(
    metadata_json: dict,
    trial_id: str,
    assay_run_id: str,
) -> Tuple[Optional[dict], List[str]]:
    assay_run_ids: List[str] = [
        assay_run["assay_run_id"]
        for assay_run in metadata_json.get("assays", {}).get("elisa", [])
    ]
    if assay_run_id not in assay_run_ids:
        print(f"Cannot find elisa batch {assay_run_id} for trial {trial_id}")
        return None, []

    object_urls_to_delete: List[str] = []
    assay_run_idx: int = assay_run_ids.index(assay_run_id)

    assay_run: dict = metadata_json["assays"]["elisa"].pop(assay_run_idx)
    object_urls_to_delete.extend(_get_all_object_urls(assay_run))

    # also remove hanging structures
    target = dict()
    if not metadata_json["assays"]["elisa"]:
        # if no batches, remove the whole assay
        target: dict = metadata_json["assays"].pop("elisa")
    if target:
        object_urls_to_delete.extend(_get_all_object_urls(target))

    return metadata_json, object_urls_to_delete


def _remove_nanostring_from_blob(
    metadata_json: dict,
    trial_id: str,
    batch_id: str,
    run_id: str = None,
) -> Tuple[Optional[dict], List[str]]:
    batch_ids: List[str] = [
        batch["batch_id"]
        for batch in metadata_json.get("assays", {}).get("nanostring", [])
    ]
    if batch_id not in batch_ids:
        print(f"Cannot find nanostring batch {batch_id} for trial {trial_id}")
        return None, []

    object_urls_to_delete: List[str] = []
    batch_idx: int = batch_ids.index(batch_id)
    if run_id:
        run_ids: List[str] = [
            run["run_id"]
            for run in metadata_json["assays"]["nanostring"][batch_idx]["runs"]
        ]
        if run_id not in run_ids:
            print(
                f"Cannot find a run {run_id} in nanostring batch {batch_id} for trial {trial_id}"
            )
            return None, []
        else:
            record: dict = metadata_json["assays"]["nanostring"][batch_idx]["runs"].pop(
                run_ids.index(run_id)
            )
            object_urls_to_delete.extend(_get_all_object_urls(record))
    else:
        batch: dict = metadata_json["assays"]["nanostring"].pop(batch_idx)
        object_urls_to_delete.extend(_get_all_object_urls(batch))

    # also remove hanging structures
    target = dict()
    if run_id:
        # if we didn't pop the batch but might have left it hanging
        # if we DID pop, batch_idx would either not exist or point to the following entry
        batch: dict = metadata_json["assays"]["nanostring"][
            batch_idx
        ]  # for convenience
        if not batch["runs"]:
            # if no combined or any runs, remove the whole batch
            target["batch"] = metadata_json["assays"]["nanostring"].pop(batch_idx)
    if not metadata_json["assays"]["nanostring"]:
        # if no batches, remove the whole assay
        target["assay"] = metadata_json["assays"].pop("nanostring")
    if target:
        object_urls_to_delete.extend(_get_all_object_urls(target))

    return metadata_json, object_urls_to_delete


def _remove_rna_analysis_from_blob(
    metadata_json: dict,
    trial_id: str,
    cimac_id: str,
) -> Tuple[Optional[dict], List[str]]:
    cimac_ids: List[str] = [
        record["cimac_id"]
        for record in metadata_json.get("analysis", {}).get(
            "rna_analysis", {"level_1": []}
        )["level_1"]
    ]
    if cimac_id not in cimac_ids:
        print(f"Cannot find RNA analysis for {cimac_id} for trial {trial_id}")
        return None, []

    object_urls_to_delete: List[str] = []
    record_idx: int = cimac_ids.index(cimac_id)

    record: dict = metadata_json["analysis"]["rna_analysis"]["level_1"].pop(record_idx)
    object_urls_to_delete.extend(_get_all_object_urls(record))

    # also remove hanging structures
    target = dict()
    if not metadata_json["analysis"]["rna_analysis"]["level_1"]:
        # if no batches, remove the whole assay
        target: dict = metadata_json["analysis"].pop("rna_analysis")
    if target:
        object_urls_to_delete.extend(_get_all_object_urls(target))

    return metadata_json, object_urls_to_delete


def _remove_cytof_analysis_from_blob(
    metadata_json: dict,
    trial_id: str,
    batch_id: str,
    cimac_id: str = None,
) -> Tuple[Optional[dict], List[str]]:
    batch_ids: List[str] = [
        batch["batch_id"]
        for batch in metadata_json.get("assays", {}).get("cytof", [])
        if "astrolabe_analysis" in batch
    ]
    if batch_id not in batch_ids:
        print(f"Cannot find cytof analysis batch {batch_id} for trial {trial_id}")
        return None, []
    else:
        batch_idx: int = batch_ids.index(batch_id)

    object_urls_to_delete: List[str] = []
    if cimac_id:
        cimac_ids: List[str] = [
            record["cimac_id"]
            for record in metadata_json["assays"]["cytof"][batch_idx]["records"]
            if "output_files" in record
        ]
        if cimac_id not in cimac_ids:
            print(
                f"Cannot find cytof analysis for sample {cimac_id} in batch {batch_id} for trial {trial_id}"
            )
            return None, []
        else:
            record_idx: int = cimac_ids.index(cimac_id)
            output_files: dict = metadata_json["assays"]["cytof"][batch_idx]["records"][
                record_idx
            ].pop("output_files")
            object_urls_to_delete.extend(_get_all_object_urls(output_files))

    else:
        batch: dict = {
            key: metadata_json["assays"]["cytof"][batch_idx].pop(key, {})
            for key in [
                "astrolabe_reports",
                "astrolabe_analysis",
                "control_files_analysis",
            ]
        }
        object_urls_to_delete.extend(_get_all_object_urls(batch))

        # remove analysis from all samples in this batch as well
        for record_idx, record in enumerate(
            metadata_json["assays"]["cytof"][batch_idx]["records"]
        ):
            if "output_files" in record:
                output_files: dict = metadata_json["assays"]["cytof"][batch_idx][
                    "records"
                ][record_idx].pop("output_files")
                object_urls_to_delete.extend(_get_all_object_urls(output_files))

    # there cannot be any hanging structure to remove
    return metadata_json, object_urls_to_delete


def _remove_wes_analysis_from_blob(
    metadata_json: dict,
    trial_id: str,
    run_id: str,
    just_old: bool = False,
) -> Tuple[Optional[dict], List[str]]:
    object_urls_to_delete: List[str] = []
    for subkey in ["wes_analysis", "wes_analysis_old"]:
        if just_old and "old" not in subkey:
            continue

        run_ids: List[str] = [
            run["run_id"]
            for run in metadata_json.get("analysis", {}).get(subkey, {"pair_runs": []})[
                "pair_runs"
            ]
        ]
        if run_id not in run_ids:
            # has to be missing from both to be an issue
            continue

        record_idx: int = run_ids.index(run_id)

        record: dict = metadata_json["analysis"][subkey]["pair_runs"].pop(record_idx)
        object_urls_to_delete.extend(_get_all_object_urls(record))

    if not len(object_urls_to_delete):
        print(
            f"Cannot find "
            + ("old " if just_old else "")
            + f"WES paired analysis for {run_id} for trial {trial_id}"
        )
        return None, []

    # also remove hanging structures
    for subkey in ["wes_analysis", "wes_analysis_old"]:
        target = dict()
        if (
            subkey in metadata_json["analysis"]
            and not metadata_json["analysis"][subkey]["pair_runs"]
        ):
            # if no batches, remove the whole assay
            target: dict = metadata_json["analysis"].pop(subkey)
        if target:
            object_urls_to_delete.extend(_get_all_object_urls(target))

    return metadata_json, object_urls_to_delete


def _remove_wes_tumor_only_analysis_from_blob(
    metadata_json: dict,
    trial_id: str,
    cimac_id: str,
    just_old: bool = False,
) -> Tuple[Optional[dict], List[str]]:
    object_urls_to_delete: List[str] = []
    for subkey in ["wes_tumor_only_analysis", "wes_tumor_only_analysis_old"]:
        if just_old and "old" not in subkey:
            continue

        cimac_ids: List[str] = [
            run["tumor"]["cimac_id"]
            for run in metadata_json.get("analysis", {}).get(subkey, {"runs": []})[
                "runs"
            ]
        ]
        if cimac_id not in cimac_ids:
            # has to be missing from both to be an issue
            continue

        record_idx: int = cimac_ids.index(cimac_id)

        record: dict = metadata_json["analysis"][subkey]["runs"].pop(record_idx)
        object_urls_to_delete.extend(_get_all_object_urls(record))

    if not len(object_urls_to_delete):
        print(
            f"Cannot find "
            + ("old " if just_old else "")
            + f"WES tumor-only analysis for {cimac_id} for trial {trial_id}"
        )
        return None, []

    # also remove hanging structures
    for subkey in ["wes_tumor_only_analysis", "wes_tumor_only_analysis_old"]:
        target = dict()
        if (
            subkey in metadata_json["analysis"]
            and not metadata_json["analysis"][subkey]["runs"]
        ):
            # if no batches, remove the whole assay
            target: dict = metadata_json["analysis"].pop(subkey)
        if target:
            object_urls_to_delete.extend(_get_all_object_urls(target))

    return metadata_json, object_urls_to_delete


def _remove_microbiome_analysis_from_blob(
    metadata_json: dict,
    trial_id: str,
    batch_id: str,
) -> Tuple[Optional[dict], List[str]]:
    batch_ids: List[str] = [
        batch["batch_id"]
        for batch in metadata_json.get("analysis", {}).get(
            "microbiome_analysis", {"batches": []}
        )["batches"]
    ]
    if batch_id not in batch_ids:
        print(f"Cannot find microbiome analysis batch {batch_id} for trial {trial_id}")
        return None, []

    object_urls_to_delete: List[str] = []
    batch_idx: int = batch_ids.index(batch_id)
    batch: dict = metadata_json["analysis"]["microbiome_analysis"]["batches"].pop(
        batch_idx
    )
    object_urls_to_delete.extend(_get_all_object_urls(batch))

    # also remove hanging structures
    target = dict()
    if not metadata_json["analysis"]["microbiome_analysis"]["batches"]:
        # if no batches, remove the whole assay/analysis
        target["analysis"] = metadata_json["analysis"].pop("microbiome_analysis")
    if target:
        object_urls_to_delete.extend(_get_all_object_urls(target))

    return metadata_json, object_urls_to_delete


def _remove_batched_assay_from_blob(
    metadata_json: dict,
    trial_id: str,
    assay_or_analysis: str,
    batch_id: str,
    cimac_id: str = None,
) -> Tuple[Optional[dict], List[str]]:
    subkey: str = "analysis" if "analysis" in assay_or_analysis else "assays"
    batch_ids: List[str] = [
        batch["batch_id"]
        for batch in metadata_json.get(subkey, {}).get(
            assay_or_analysis, {"batches": []}
        )["batches"]
    ]
    if batch_id not in batch_ids:
        print(f"Cannot find {assay_or_analysis} batch {batch_id} for trial {trial_id}")
        return None, []

    object_urls_to_delete: List[str] = []
    batch_idx: int = batch_ids.index(batch_id)
    if cimac_id:
        cimac_ids: List[str] = [
            record["cimac_id"]
            for record in metadata_json[subkey][assay_or_analysis]["batches"][
                batch_idx
            ]["records"]
        ]
        if cimac_id not in cimac_ids:
            print(
                f"Cannot find {assay_or_analysis} for sample {cimac_id} in batch {batch_id} for trial {trial_id}"
            )
            return None, []
        else:
            record: dict = metadata_json[subkey][assay_or_analysis]["batches"][
                batch_idx
            ]["records"].pop(cimac_ids.index(cimac_id))
            object_urls_to_delete.extend(_get_all_object_urls(record))

    else:
        batch: dict = metadata_json[subkey][assay_or_analysis]["batches"].pop(batch_idx)
        object_urls_to_delete.extend(_get_all_object_urls(batch))

    # also remove hanging structures
    target = dict()
    if cimac_id:
        # if we didn't pop the batch but might have left it hanging
        # if we DID pop, batch_idx would either not exist or point to the following entry
        batch: dict = metadata_json[subkey][assay_or_analysis]["batches"][
            batch_idx
        ]  # for convenience
        if not batch["records"]:
            # if no combined or any records, remove the whole batch
            target["batch"] = metadata_json[subkey][assay_or_analysis]["batches"].pop(
                batch_idx
            )
    if not metadata_json[subkey][assay_or_analysis]["batches"]:
        # if no batches, remove the whole assay/analysis
        target[subkey] = metadata_json[subkey].pop(assay_or_analysis)
    if target:
        object_urls_to_delete.extend(_get_all_object_urls(target))

    return metadata_json, object_urls_to_delete


def _remove_generic_assay_from_blob(
    metadata_json: dict,
    trial_id: str,
    assay_or_analysis: str,
    batch_id: str,
    cimac_id: str = None,
) -> Tuple[Optional[dict], List[str]]:
    subkey: str = "analysis" if "analysis" in assay_or_analysis else "assays"
    batch_ids: List[str] = [
        batch["batch_id"]
        for batch in metadata_json.get(subkey, {}).get(assay_or_analysis, [])
        if "batch_id" in batch
    ]
    if batch_id not in batch_ids:
        if (
            batch_id.isnumeric()
            and "." not in batch_id
            and int(batch_id) >= 0
            and int(batch_id)
            < len(metadata_json.get(subkey, {}).get(assay_or_analysis, []))
        ):
            # only convert if if possible and not in batch_ids
            batch_idx: int = int(batch_id)
        else:
            print(
                f"Cannot find {assay_or_analysis} batch {batch_id} for trial {trial_id}"
            )
            return None, []
    else:
        batch_idx: int = batch_ids.index(batch_id)

    object_urls_to_delete: List[str] = []
    if cimac_id:
        cimac_ids: List[str] = [
            record["cimac_id"]
            for record in metadata_json[subkey][assay_or_analysis][batch_idx]["records"]
        ]
        if cimac_id not in cimac_ids:
            print(
                f"Cannot find {assay_or_analysis} for sample {cimac_id} in batch {batch_id} for trial {trial_id}"
            )
            return None, []
        else:
            record: dict = metadata_json[subkey][assay_or_analysis][batch_idx][
                "records"
            ].pop(cimac_ids.index(cimac_id))
            object_urls_to_delete.extend(_get_all_object_urls(record))

    else:
        batch: dict = metadata_json[subkey][assay_or_analysis].pop(batch_idx)
        object_urls_to_delete.extend(_get_all_object_urls(batch))

    # also remove hanging structures
    target = dict()
    if cimac_id:
        # if we didn't pop the batch but might have left it hanging
        # if we DID pop, batch_idx would either not exist or point to the following entry
        batch: dict = metadata_json[subkey][assay_or_analysis][
            batch_idx
        ]  # for convenience
        if not batch["records"]:
            # if no combined or any records, remove the whole batch
            target["batch"] = metadata_json[subkey][assay_or_analysis].pop(batch_idx)
    if not metadata_json[subkey][assay_or_analysis]:
        # if no batches, remove the whole assay/analysis
        target[subkey] = metadata_json[subkey].pop(assay_or_analysis)
    if target:
        object_urls_to_delete.extend(_get_all_object_urls(target))

    return metadata_json, object_urls_to_delete


def remove_data(trial_id: str, assay_or_analysis: str, target_id: Tuple[str]) -> None:
    """
    Removes a data section completely, include its downloadle_files entries

    Parameters
    ----------
    trial_id: str
        the id of the trial to investigate
    assay_or_analysis: str
        the name of the assay / analysis to investigate
        must be in SUPPORTED_ASSAYS_AND_ANALYSES
    target_id: Tuple[str]
        the ids to find the data to remove
        it cannot go past where is divisible in the data
            eg if ASSAY_OR_ANALYSIS == "clinical_data", only `filename` is accepted
            eg if ASSAY_OR_ANALYSIS == "elisa", only `assay_run_id` is accepted
            eg if ASSAY_OR_ANALYSIS == "wes_analysis", only `run_id` is accepted
            eg if ASSAY_OR_ANALYSIS == "olink", `batch_id [file]` is assumed
                ie `batch_id` is required but `file` is optional
    """

    if assay_or_analysis not in SUPPORTED_ASSAYS_AND_ANALYSES:
        print("Assay / analysis not supported:", assay_or_analysis)
        return

    elif assay_or_analysis == "clinical_data":
        if len(target_id) == 1:
            remove_clinical(trial_id=trial_id, target_id=target_id[0])
        else:
            print(
                "Error: if ASSAY_OR_ANALYSIS == 'clinical_data', only `filename` is accepted"
            )
            print(
                "You can also directly use the command $ cidc admin remove clinical TRIAL_ID FILE_NAME"
            )
        return

    with Session.begin() as session:
        trial: TrialMetadata = get_trial_if_exists(
            trial_id, with_for_update=True, session=session
        )

        metadata_json, object_urls_to_delete = None, []
        if assay_or_analysis == "misc_data":
            if len(target_id) and len(target_id) <= 2:
                metadata_json, object_urls_to_delete = _remove_misc_data_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    batch_id=target_id[0],
                    filename=None if len(target_id) == 1 else target_id[1],
                )
            else:
                print(
                    "Error: if ASSAY_OR_ANALYSIS == 'misc_data', only `batch_id [filename]` is accepted"
                )
        elif assay_or_analysis == "olink":
            if len(target_id) and len(target_id) <= 2:
                metadata_json, object_urls_to_delete = _remove_olink_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    batch_id=target_id[0],
                    filename=None if len(target_id) == 1 else target_id[1],
                )
            else:
                print(
                    "Error: if ASSAY_OR_ANALYSIS == 'olink', only `batch_id [file]` is accepted"
                )
        elif assay_or_analysis == "elisa":
            if len(target_id) == 1:
                metadata_json, object_urls_to_delete = _remove_elisa_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    assay_run_id=target_id[0],
                )
            else:
                print(
                    "Error: if ASSAY_OR_ANALYSIS == 'elisa', only `assay_run_id` is accepted"
                )
        elif assay_or_analysis == "nanostring":
            if len(target_id) and len(target_id) <= 2:
                metadata_json, object_urls_to_delete = _remove_nanostring_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    batch_id=target_id[0],
                    run_id=None if len(target_id) == 1 else target_id[1],
                )
            else:
                print(
                    "Error: if ASSAY_OR_ANALYSIS == 'olink', only `batch_id [file]` is accepted"
                )
        elif assay_or_analysis == "rna_level1_analysis":
            if len(target_id) == 1:
                metadata_json, object_urls_to_delete = _remove_rna_analysis_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    cimac_id=target_id[0],
                )
            else:
                print(
                    "Error: if ASSAY_OR_ANALYSIS == 'rna_level1_analysis', only `cimac_id` is accepted"
                )

        elif assay_or_analysis == "cytof_analysis":
            if len(target_id) <= 2:
                metadata_json, object_urls_to_delete = _remove_cytof_analysis_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    batch_id=target_id[0],
                    cimac_id=None if len(target_id) == 1 else target_id[1],
                )
            else:
                print(
                    "Error: if ASSAY_OR_ANALYSIS == 'cytof_analysis', only `batch_id [cimac_id]` is accepted"
                )
        elif assay_or_analysis in ["wes_analysis", "wes_analysis_old"]:
            if len(target_id) == 1:
                metadata_json, object_urls_to_delete = _remove_wes_analysis_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    run_id=target_id[0],
                    just_old="old" in assay_or_analysis,
                )
            else:
                print(
                    f"Error: if ASSAY_OR_ANALYSIS == '{assay_or_analysis}', only `run_id` is accepted"
                )
        elif assay_or_analysis in [
            "wes_tumor_only_analysis",
            "wes_tumor_only_analysis_old",
        ]:
            if len(target_id) == 1:
                (
                    metadata_json,
                    object_urls_to_delete,
                ) = _remove_wes_tumor_only_analysis_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    cimac_id=target_id[0],
                    just_old="old" in assay_or_analysis,
                )
            else:
                print(
                    f"Error: if ASSAY_OR_ANALYSIS == '{assay_or_analysis}', only `cimac_id` is accepted"
                )

        elif assay_or_analysis == "microbiome_analysis":

            if len(target_id) == 1:
                (
                    metadata_json,
                    object_urls_to_delete,
                ) = _remove_microbiome_analysis_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    batch_id=target_id[0],
                )
            else:
                print(
                    f"Error: if ASSAY_OR_ANALYSIS == microbiome_analysis, only `btach_id` is accepted"
                )

        elif assay_or_analysis in [
            "ctdna_analysis",
            "tcr_analysis",
        ]:
            if len(target_id) and len(target_id) <= 2:
                metadata_json, object_urls_to_delete = _remove_batched_assay_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    assay_or_analysis=assay_or_analysis,
                    batch_id=target_id[0],
                    cimac_id=None if len(target_id) == 1 else target_id[1],
                )
            else:
                print(
                    f"Error: if ASSAY_OR_ANALYSIS == '{assay_or_analysis}', only `batch_id [cimac_id]` is accepted"
                )
        else:
            if len(target_id) and len(target_id) <= 2:
                metadata_json, object_urls_to_delete = _remove_generic_assay_from_blob(
                    metadata_json=trial.metadata_json,
                    trial_id=trial_id,
                    assay_or_analysis=assay_or_analysis,
                    batch_id=target_id[0],
                    cimac_id=None if len(target_id) == 1 else target_id[1],
                )
            else:
                print(
                    f"Error: if ASSAY_OR_ANALYSIS == '{assay_or_analysis}', only `batch_id [cimac_id]` is accepted"
                )

        if metadata_json is not None:
            # update the `trial_metadata`
            session.query(TrialMetadata).filter(
                TrialMetadata.trial_id == trial_id
            ).update(
                {
                    TrialMetadata.metadata_json: metadata_json,
                    TrialMetadata._updated: datetime.now(),
                }
            )

            # remove the `downloadable_files`
            num_deleted: int = (
                session.query(DownloadableFiles)
                .filter(DownloadableFiles.object_url.in_(object_urls_to_delete))
                .delete()
            )

            print(
                f"Updated trial {trial_id}, removing {assay_or_analysis} values {target_id}",
                f"along with {num_deleted} files",
            )


def remove_clinical(trial_id: str, target_id: str) -> None:
    """
    Removes a clinical file completely, include its downloadle_files entry

    Parameters
    ----------
    trial_id: str
        the id of the trial to affect
    target_id: str
        the object_url of the file to remove
        not including {trial_id}/clinical/
        special value * for all files for this trial
    """
    with Session.begin() as session:
        trial: TrialMetadata = get_trial_if_exists(
            trial_id, with_for_update=True, session=session
        )

        if target_id == "*":
            # get all of the clinical files
            targets: List[DownloadableFiles] = get_clinical_downloadable_files(
                trial_id, session=session
            )
        else:
            # get just the one(s) we're looking for
            targets: List[DownloadableFiles] = (
                session.query(DownloadableFiles)
                .filter(
                    DownloadableFiles.trial_id == trial_id,
                    DownloadableFiles.object_url == f"{trial_id}/clinical/{target_id}",
                )
                .all()
            )
        target_urls = [f.object_url for f in targets]

        if not len(targets):
            if target_id == "*":
                print(f"No clinical data files found for trial {trial_id}")
            else:
                print(f"Clinical data file {target_id} not found for trial {trial_id}")
            exit()

        # remove the file(s)
        trial.metadata_json["clinical_data"]["records"] = [
            r
            for r in trial.metadata_json.get("clinical_data", {}).get("records", [])
            if r["clinical_file"]["object_url"] not in target_urls
        ]

        # remove any hanging structure
        if not len(trial.metadata_json["clinical_data"]["records"]):
            trial.metadata_json.pop("clinical_data")

        # update the `trial_metadata`
        session.query(TrialMetadata).filter(TrialMetadata.trial_id == trial_id).update(
            {
                TrialMetadata.metadata_json: trial.metadata_json,
                TrialMetadata._updated: datetime.now(),
            }
        )

        # remove the `downloadable_files`
        for t in targets:
            session.delete(t)

        print(f"Updated trial {trial_id}, removing {len(targets)} clinical data files")


def _remove_samples_from_blob(
    metadata_json: dict,
    samples_to_remove: Dict[str, List[str]],
) -> dict:
    """
    Removes a participant completely if removing all of its samples

    Parameters
    ----------
    metadata_json: dict
        the full clinical trial metadata blob
    samples_to_remove: Dict[str, List[str]]
        map from `cimac_participant_id`s to a list of `cimac_id`s to remove
    """
    n: int = 0
    while n < len(metadata_json["participants"]):
        partic = metadata_json["participants"][n]
        cimac_partic_id = partic["cimac_participant_id"]
        if cimac_partic_id in samples_to_remove:
            if len(partic["samples"]) == len(samples_to_remove[cimac_partic_id]):
                metadata_json["participants"].pop(n)
                # don't increment because we popped
                continue

            else:
                to_remove = samples_to_remove[cimac_partic_id]
                metadata_json["participants"][n]["samples"] = [
                    s for s in partic["samples"] if s["cimac_id"] not in to_remove
                ]
        n += 1

    return metadata_json


def remove_shipment(trial_id: str, target_id: str) -> None:
    """
    Removes a shipment completely with all of its samples, including its upload_jobs entry
    Removes a participant completely if removing all of its samples

    Parameters
    ----------
    trial_id: str
        the id of the trial to affect
    target_id: str
        the manifest_id of the shipment to remove
    """
    with Session.begin() as session:
        trial: TrialMetadata = get_trial_if_exists(
            trial_id, with_for_update=True, session=session
        )

        # get all of the shipments
        shipments: List[UploadJobs] = get_shipments(trial_id, session=session)
        # find the one(s) we're looking for
        targets = [
            s
            for s in shipments
            if s.metadata_patch["shipments"][0]["manifest_id"] == target_id
        ]

        if not len(targets):
            print(f"Shipment {target_id} not found for trial {trial_id}")
            exit()

        # get all the associated samples
        samples_to_remove = {
            partic["cimac_participant_id"]: [
                sample["cimac_id"] for sample in partic["samples"]
            ]
            for upload in targets
            for partic in upload.metadata_patch.get("participants", [])
        }
        if not len(samples_to_remove):
            print(f"Shipment {target_id} for trial {trial_id} has no samples")
            exit()

        # remove the samples
        trial.metadata_json = _remove_samples_from_blob(
            metadata_json=trial.metadata_json,
            samples_to_remove=samples_to_remove,
        )
        # remove the shipment(s)
        trial.metadata_json["shipments"] = [
            s for s in trial.metadata_json["shipments"] if s["manifest_id"] != target_id
        ]

        # update the `trial_metadata`
        session.query(TrialMetadata).filter(TrialMetadata.trial_id == trial_id).update(
            {
                TrialMetadata.metadata_json: trial.metadata_json,
                TrialMetadata._updated: datetime.now(),
            }
        )

        # remove the `upload_jobs`
        for t in targets:
            session.delete(t)

        num_samples: int = sum(len(samples) for samples in samples_to_remove.values())
        num_partic: int = len(samples_to_remove)

        print(
            f"Updated trial {trial_id}, removing shipment {target_id}",
            f"along with {num_samples} samples across {num_partic} participants",
        )
