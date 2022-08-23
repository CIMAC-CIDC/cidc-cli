TEST_CLINICAL_FILE_URL: str = "clinical_file.xlsx"
TEST_MANIFEST_ID: str = "test_upload"
TEST_PASSWORD: str = "password"
TEST_TRIAL_ID: str = "test_prism_trial_id"
TEST_USER: str = "test_user"

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
                    "object_url": f"{TEST_TRIAL_ID}/clinical/clinical1.xlsx",
                    "number_of_participants": 5,
                },
            },
            {
                "clinical_file": {
                    "object_url": f"{TEST_TRIAL_ID}/clinical/clinical2.csv",
                    "number_of_participants": 3,
                },
            },
        ],
    },
    "analysis": {
        "atacseq_analysis": [
            {
                "batch_id": "atacseq_analysis_batch",
                "records": [
                    {"cimac_id": "CTTTPP101.00"},
                    {"cimac_id": "CTTTPP201.00"},
                ],
            },
            {
                "batch_id": "atacseq_analysis_batch_2",
                "records": [
                    {"cimac_id": "CTTTPP102.00"},
                ],
            },
        ],
        "ctdna_analysis": {
            "batches": [
                {
                    "batch_id": "ctdna_analysis_batch",
                    "records": [
                        {"cimac_id": "CTTTPP101.00"},
                        {"cimac_id": "CTTTPP201.00"},
                    ],
                },
                {
                    "batch_id": "ctdna_analysis_batch_2",
                    "records": [
                        {"cimac_id": "CTTTPP102.00"},
                    ],
                },
            ],
        },
        "rna_analysis": {
            "level_1": [
                {"cimac_id": "CTTTPP101.00"},
                {"cimac_id": "CTTTPP201.00"},
                {"cimac_id": "CTTTPP102.00"},
            ],
        },
        "wes_analysis": {
            "pair_runs": [
                {
                    "run_id": "CTTTPP101.00",  # tumor cimac_id
                    "normal": {"cimac_id": "CTTTPP10N.00"},  # cimac_id
                    "tumor": {"cimac_id": "CTTTPP101.00"},  # cimac_id
                },
                {
                    "run_id": "CTTTPP102.00",  # tumor cimac_id
                    "normal": {"cimac_id": "CTTTPP10N.00"},  # cimac_id
                    "tumor": {"cimac_id": "CTTTPP102.00"},  # cimac_id
                },
            ],
        },
        "wes_analysis_old": {
            "pair_runs": [
                {
                    "run_id": "CTTTPP201.00",  # tumor cimac_id
                    "normal": {"cimac_id": "CTTTPP20N.00"},  # cimac_id
                    "tumor": {"cimac_id": "CTTTPP201.00"},  # cimac_id
                },
            ],
        },
        "wes_tumor_only_analysis": {
            "runs": [
                {"tumor": {"cimac_id": "CTTTPP101.00"}},
                {"tumor": {"cimac_id": "CTTTPP201.00"}},
            ],
        },
        "wes_tumor_only_analysis_old": {
            "runs": [
                {"tumor": {"cimac_id": "CTTTPP102.00"}},
            ],
        },
    },
    "assays": {
        "olink": {
            # first priority, just this if exists
            "study": {
                "npx_file": {
                    "samples": [
                        "CTTTPP101.00",
                        "CTTTPP201.00",
                        "CTTTPP102.00",
                    ],  # cimac_ids
                }
            },
            "batches": [
                {
                    "batch_id": "olink_batch",
                    # second priority, combines across batches
                    "combined": {
                        "npx_file": {
                            "samples": ["CTTTPP101.00"],
                        },
                    },
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
                },
            },
            {
                "assay_run_id": "elisa_batch_2",
                "assay_xlsx": {
                    "samples": ["CTTTPP102.00"],
                },
            },
        ],
        "nanostring": [
            {
                "batch_id": "nanostring_batch",
                "runs": [
                    {
                        "run_id": "nanostring_batch_run",
                        "samples": [
                            {"cimac_id": "CTTTPP101.00"},
                        ],
                    },
                    {
                        "run_id": "nanostring_batch_run_2",
                        "samples": [
                            {"cimac_id": "CTTTPP201.00"},
                        ],
                    },
                ],
            },
            {
                "batch_id": "nanostring_batch_2",
                "runs": [
                    {
                        "run_id": "nanostring_batch_2_run",
                        "samples": [
                            {"cimac_id": "CTTTPP102.00"},
                        ],
                    },
                ],
            },
        ],
        "wes": [
            {
                "records": [
                    {"cimac_id": "CTTTPP101.00"},
                    {"cimac_id": "CTTTPP201.00"},
                ],
            },
            {
                "records": [
                    {"cimac_id": "CTTTPP102.00"},
                ],
            },
        ],
    },
}
