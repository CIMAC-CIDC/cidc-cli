TEST_MANIFEST_ID: str = "test_upload"
TEST_PASSWORD: str = "password"
TEST_TRIAL_ID: str = "test_prism_trial_id"
TEST_USER: str = "test_user"

TEST_CLINICAL_URL_XLSX: str = "clinical_file1.xlsx"
TEST_CLINICAL_URL_CSV: str = "clinical_file2.csv"
TEST_MISC_DATA_URL1: str = "misc_data1.foo"
TEST_MISC_DATA_URL2: str = "misc_data2.bar"

TEST_METADATA_JSON: dict = {
    "shipments": [
        {"manifest_id": TEST_MANIFEST_ID},
        {"manifest_id": TEST_MANIFEST_ID + "2"},
    ],
    "participants": [
        {
            "cimac_participant_id": "CTTTPP1",
            "samples": [
                {"cimac_id": "CTTTPP101.00"},
                {"cimac_id": "CTTTPP102.00"},
            ],
        },
        {
            "cimac_participant_id": "CTTTPP2",
            "samples": [
                {"cimac_id": "CTTTPP201.00"},
                {"cimac_id": "CTTTPP202.00"},
            ],
        },
        {
            "cimac_participant_id": "CTTTPP3",
            "samples": [
                {"cimac_id": "CTTTPP301.00"},
                {"cimac_id": "CTTTPP302.00"},
                {"cimac_id": "CTTTPP303.00"},
            ],
        },
    ],
    "clinical_data": {
        "records": [
            {
                "clinical_file": {
                    "object_url": f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_URL_XLSX}",
                    "number_of_participants": 5,
                },
                "comment": "comment",
            },
            {
                "clinical_file": {
                    "object_url": f"{TEST_TRIAL_ID}/clinical/{TEST_CLINICAL_URL_CSV}",
                    "number_of_participants": 3,
                },
            },
        ],
    },
    "analysis": {
        "atacseq_analysis": [
            {
                "batch_id": "atacseq_analysis_batch",
                "report": {
                    "object_url": f"{TEST_TRIAL_ID}/atacseq/analysis/atacseq_analysis_batch/report.zip",
                },
                "records": [
                    {
                        "cimac_id": "CTTTPP101.00",
                        "aligned_sorted_bam": {
                            "object_url": f"{TEST_TRIAL_ID}/atacseq/CTTTPP101.00/analysis/aligned_sorted.bam",
                        },
                    },
                    {
                        "cimac_id": "CTTTPP201.00",
                        "aligned_sorted_bam": {
                            "object_url": f"{TEST_TRIAL_ID}/atacseq/CTTTPP201.00/analysis/aligned_sorted.bam",
                        },
                    },
                ],
            },
            {
                "batch_id": "atacseq_analysis_batch_2",
                "report": {
                    "object_url": f"{TEST_TRIAL_ID}/atacseq/analysis/atacseq_analysis_batch_2/report.zip",
                },
                "records": [
                    {
                        "cimac_id": "CTTTPP102.00",
                        "aligned_sorted_bam": {
                            "object_url": f"{TEST_TRIAL_ID}/atacseq/CTTTPP102.00/analysis/aligned_sorted.bam",
                        },
                    },
                ],
            },
        ],
        "tcr_analysis": {
            "batches": [
                {
                    "batch_id": "tcr_analysis_batch",
                    "report_trial": {
                        "object_url": f"{TEST_TRIAL_ID}/tcr_analysis/tcr_analysis_batch/report_trial.tar.gz",
                    },
                    "records": [
                        {
                            "cimac_id": "CTTTPP101.00",
                            "tra_clone": {
                                "object_url": f"{TEST_TRIAL_ID}/tcr_analysis/tcr_analysis_batch/CTTTPP101.00/tra_clone.csv",
                            },
                        },
                        {
                            "cimac_id": "CTTTPP201.00",
                            "tra_clone": {
                                "object_url": f"{TEST_TRIAL_ID}/tcr_analysis/tcr_analysis_batch/CTTTPP201.00/tra_clone.csv",
                            },
                        },
                    ],
                },
                {
                    "batch_id": "tcr_analysis_batch_2",
                    "report_trial": {
                        "object_url": f"{TEST_TRIAL_ID}/tcr_analysis/tcr_analysis_batch_2/report_trial.tar.gz",
                    },
                    "records": [
                        {
                            "cimac_id": "CTTTPP102.00",
                            "tra_clone": {
                                "object_url": f"{TEST_TRIAL_ID}/tcr_analysis/tcr_analysis_batch_2/CTTTPP102.00/tra_clone.csv",
                            },
                        },
                    ],
                },
            ],
        },
        "rna_analysis": {
            "level_1": [
                {
                    "cimac_id": "CTTTPP101.00",
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/rna/CTTTPP101.00/analysis/error.yaml",
                    },
                },
                {
                    "cimac_id": "CTTTPP201.00",
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/rna/CTTTPP201.00/analysis/error.yaml",
                    },
                },
                {
                    "cimac_id": "CTTTPP102.00",
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/rna/CTTTPP102.00/analysis/error.yaml",
                    },
                },
            ],
        },
        "wes_analysis": {
            "pair_runs": [
                {
                    "run_id": "CTTTPP101.00",  # tumor cimac_id
                    "normal": {"cimac_id": "CTTTPP10N.00"},  # cimac_id
                    "tumor": {"cimac_id": "CTTTPP101.00"},  # cimac_id
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes/CTTTPP101.00/analysis/error.yaml",
                    },
                },
                {
                    "run_id": "CTTTPP102.00",  # tumor cimac_id
                    "normal": {"cimac_id": "CTTTPP10N.00"},  # cimac_id
                    "tumor": {"cimac_id": "CTTTPP102.00"},  # cimac_id
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes/CTTTPP102.00/analysis/error.yaml",
                    },
                },
                {
                    "run_id": "CTTTPP201.00",  # tumor cimac_id
                    "normal": {"cimac_id": "CTTTPP20N.00"},  # cimac_id
                    "tumor": {"cimac_id": "CTTTPP201.00"},  # cimac_id
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes/CTTTPP201.00/analysis/error.yaml",
                    },
                },
            ],
        },
        "wes_analysis_old": {
            "pair_runs": [
                {
                    "run_id": "CTTTPP201.00",  # tumor cimac_id
                    "normal": {"cimac_id": "CTTTPP20N.00"},  # cimac_id
                    "tumor": {"cimac_id": "CTTTPP201.00"},  # cimac_id
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes/CTTTPP201.00/analysis/error.yaml",
                    },
                },
                {
                    "run_id": "CTTTPP102.00",  # tumor cimac_id
                    "normal": {"cimac_id": "CTTTPP10N.00"},  # cimac_id
                    "tumor": {"cimac_id": "CTTTPP102.00"},  # cimac_id
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes/CTTTPP102.00/analysis/error.yaml",
                    },
                },
            ],
        },
        "wes_tumor_only_analysis": {
            "runs": [
                {
                    "tumor": {"cimac_id": "CTTTPP101.00"},
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes_tumor_only/CTTTPP101.00/analysis/error.yaml",
                    },
                },
                {
                    "tumor": {"cimac_id": "CTTTPP102.00"},
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes_tumor_only/CTTTPP102.00/analysis/error.yaml",
                    },
                },
                {
                    "tumor": {"cimac_id": "CTTTPP201.00"},
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes_tumor_only/CTTTPP201.00/analysis/error.yaml",
                    },
                },
            ],
        },
        "wes_tumor_only_analysis_old": {
            "runs": [
                {
                    "tumor": {"cimac_id": "CTTTPP201.00"},
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes_tumor_only/CTTTPP201.00/analysis/error.yaml",
                    },
                },
                {
                    "tumor": {"cimac_id": "CTTTPP102.00"},
                    "error": {
                        "object_url": f"{TEST_TRIAL_ID}/wes_tumor_only/CTTTPP102.00/analysis/error.yaml",
                    },
                },
            ],
        },
    },
    "assays": {
        "cytof": [
            {
                "assay_run_id": "cytof_run",
                "batch_id": "cytof_batch",
                "astrolabe_analysis": {
                    "object_url": f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch/reports.zip",
                },
                "source_fcs": [
                    {
                        "object_url": f"{TEST_TRIAL_ID}/cytof/cytof_batch/source_0.fcs",
                    },
                ],
                "records": [
                    {
                        "cimac_id": "CTTTPP101.00",
                        "input_files": {
                            "processed_fcs": {
                                "object_url": f"{TEST_TRIAL_ID}/cytof/CTTTPP101.00/processed.fcs",
                            },
                        },
                        "output_files": {
                            "assignment": {
                                "object_url": f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch/CTTTPP101.00/assignment.csv",
                            },
                            "fcs_file": {
                                "object_url": f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch/CTTTPP101.00/source.fcs",
                            },
                        },
                    },
                    {
                        "cimac_id": "CTTTPP201.00",
                        "output_files": {
                            "assignment": {
                                "object_url": f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch/CTTTPP201.00/assignment.csv",
                            },
                            "fcs_file": {
                                "object_url": f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch/CTTTPP201.00/source.fcs",
                            },
                        },
                    },
                ],
            },
            {
                "assay_run_id": "cytof_run",
                "batch_id": "cytof_batch_2",
                "astrolabe_analysis": {
                    "object_url": f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch_2/reports.zip",
                },
                "records": [
                    {
                        "cimac_id": "CTTTPP102.00",
                        "output_files": {
                            "assignment": {
                                "object_url": f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch_2/CTTTPP102.00/assignment.csv",
                            },
                            "fcs_file": {
                                "object_url": f"{TEST_TRIAL_ID}/cytof_analysis/cytof_run/cytof_batch_2/CTTTPP102.00/source.fcs",
                            },
                        },
                    },
                ],
            },
            {
                "assay_run_id": "cytof_run_2",
                "batch_id": "cytof_batch_3",
                "records": [
                    {
                        "cimac_id": "CTTTPP301.00",
                    },
                ],
            },
        ],
        "misc_data": [
            {
                "files": [
                    {
                        "file": {
                            "object_url": f"{TEST_TRIAL_ID}/misc_data/{TEST_MISC_DATA_URL1}"
                        },
                        "description": "description",
                    },
                ],
            },
            {
                "files": [
                    {
                        "file": {
                            "object_url": f"{TEST_TRIAL_ID}/misc_data/{TEST_MISC_DATA_URL2}"
                        },
                    },
                ],
            },
        ],
        "olink": {
            "dummy_file": {
                "object_url": f"{TEST_TRIAL_ID}/olink/ALL object_urls",
            },
            # first priority, just this if exists
            "study": {
                "npx_file": {
                    "samples": [
                        "CTTTPP101.00",
                        "CTTTPP201.00",
                        "CTTTPP102.00",
                    ],  # cimac_ids
                    "object_url": f"{TEST_TRIAL_ID}/olink/study_npx.xlsx",
                },
                "dummy_file": {
                    "object_url": f"{TEST_TRIAL_ID}/olink/ALL object_urls",
                },
            },
            "batches": [
                {
                    "batch_id": "olink_batch",
                    "dummy_file": {
                        "object_url": f"{TEST_TRIAL_ID}/olink/batch_olink_batch/ALL object_urls",
                    },
                    # second priority, combines across batches
                    "combined": {
                        "npx_file": {
                            "samples": ["CTTTPP101.00"],
                            "object_url": f"{TEST_TRIAL_ID}/olink/batch_olink_batch/combined_npx.xlsx",
                        },
                    },
                    "records": [
                        {
                            # ignored
                            "files": {
                                "assay_npx": {
                                    "samples": ["CTTTPP101.00"],
                                    "object_url": f"{TEST_TRIAL_ID}/olink/batch_olink_batch/chip_0/assay_npx.xlsx",
                                },
                                "dummy_file": {
                                    "object_url": f"{TEST_TRIAL_ID}/olink/batch_olink_batch/chip_0/ALL object_urls",
                                },
                            },
                        },
                    ],
                },
                {
                    "batch_id": "olink_batch_2",
                    "records": [
                        {
                            # third priority, combines across batches
                            "files": {
                                "assay_npx": {
                                    "samples": ["CTTTPP201.00"],
                                    "object_url": f"{TEST_TRIAL_ID}/olink/batch_olink_batch_2/chip_0/assay_npx.xlsx",
                                },
                            },
                        },
                        {
                            # third priority, combines across batches
                            "files": {
                                "assay_npx": {
                                    "samples": ["CTTTPP102.00"],
                                    "object_url": f"{TEST_TRIAL_ID}/olink/batch_olink_batch_2/chip_1/assay_npx.xlsx",
                                },
                            },
                        },
                    ],
                },
            ],
        },
        "elisa": [
            {
                "assay_run_id": "elisa_batch",
                "assay_xlsx": {
                    "samples": ["CTTTPP101.00", "CTTTPP201.00"],
                    "object_url": f"{TEST_TRIAL_ID}/elisa/elisa_batch/assay.xlsx",
                },
            },
            {
                "assay_run_id": "elisa_batch_2",
                "assay_xlsx": {
                    "samples": ["CTTTPP102.00"],
                    "object_url": f"{TEST_TRIAL_ID}/elisa/elisa_batch_2/assay.xlsx",
                },
                "dummy_file": {
                    "object_url": f"{TEST_TRIAL_ID}/elisa/elisa_batch_2/ALL object_urls",
                },
            },
        ],
        "nanostring": [
            {
                "batch_id": "nanostring_batch",
                "data": {
                    "normalized": {
                        "object_url": f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/normalized_data.csv",
                    },
                },
                "runs": [
                    {
                        "run_id": "nanostring_batch_run",
                        "control_raw_rcc": {
                            "object_url": f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/nanostring_batch_run/control.rcc",
                        },
                        "samples": [
                            {
                                "cimac_id": "CTTTPP101.00",
                                "raw_rcc": {
                                    "object_url": f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/nanostring_batch_run/CTTTPP101.00.rcc",
                                },
                            },
                        ],
                    },
                    {
                        "run_id": "nanostring_batch_run_2",
                        "control_raw_rcc": {
                            "object_url": f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/nanostring_batch_run_2/control.rcc",
                        },
                        "samples": [
                            {
                                "cimac_id": "CTTTPP201.00",
                                "raw_rcc": {
                                    "object_url": f"{TEST_TRIAL_ID}/nanostring/nanostring_batch/nanostring_batch_run_2/CTTTPP201.00.rcc",
                                },
                            },
                        ],
                    },
                ],
            },
            {
                "batch_id": "nanostring_batch_2",
                "data": {
                    "normalized": {
                        "object_url": f"{TEST_TRIAL_ID}/nanostring/nanostring_batch_2/normalized_data.csv",
                    },
                },
                "runs": [
                    {
                        "run_id": "nanostring_batch_2_run",
                        "control_raw_rcc": {
                            "object_url": f"{TEST_TRIAL_ID}/nanostring/nanostring_batch_2/nanostring_batch_2_run/control.rcc",
                        },
                        "samples": [
                            {
                                "cimac_id": "CTTTPP102.00",
                                "raw_rcc": {
                                    "object_url": f"{TEST_TRIAL_ID}/nanostring/nanostring_batch_2/nanostring_batch_2_run/CTTTPP102.00.rcc",
                                },
                            },
                        ],
                    },
                ],
            },
        ],
        "wes": [
            {
                "records": [
                    {
                        "cimac_id": "CTTTPP101.00",
                        "files": {
                            "bam": [
                                {
                                    "object_url": f"{TEST_TRIAL_ID}/wes/CTTTPP101.00/reads_0.bam",
                                },
                                {
                                    "object_url": f"{TEST_TRIAL_ID}/wes/CTTTPP101.00/reads_1.bam",
                                },
                            ],
                        },
                    },
                    {
                        "cimac_id": "CTTTPP201.00",
                        "files": {
                            "bam": [
                                {
                                    "object_url": f"{TEST_TRIAL_ID}/wes/CTTTPP201.00/reads_0.bam",
                                },
                            ],
                        },
                    },
                ],
            },
            {
                "records": [
                    {
                        "cimac_id": "CTTTPP102.00",
                        "files": {
                            "bam": [
                                {
                                    "object_url": f"{TEST_TRIAL_ID}/wes/CTTTPP102.00/reads_0.bam",
                                },
                            ],
                        },
                    },
                ],
            },
        ],
    },
}
