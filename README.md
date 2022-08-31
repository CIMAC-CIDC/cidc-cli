| Branch | Status                                                                                                                       | License                                                                                                     |
| ------ | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Master | ![Continuous Integration](https://github.com/CIMAC-CIDC/cidc-cli/workflows/Continuous%20Integration/badge.svg?branch=master) | [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) |

## CIDC-CLI

Command line tool for interfacing with the CIDC API.

## Setup

### Install the CIDC-CLI

```bash
pip3 install cidc-cli
```

### Run the CIDC-CLI

To display the help message for the CLI, run:

```bash
cidc
```

To authenticate with the CIDC API, run:

```bash
cidc login [token]
```

## Development

For local development, first install the development dependencies:

```bash
pip install -r requirements.dev.txt
```

Then, install and configure the pre-commit hooks:

```bash
pre-commit install
```

## JIRA Integration

To set-up the git hook for JIRA integration, run:

```bash
ln -s ../../.githooks/commit-msg .git/hooks/commit-msg
chmod +x .git/hooks/commit-msg
rm .git/hooks/commit-msg.sample
```

This symbolic link is necessary to correctly link files in `.githooks` to `.git/hooks`. Note that setting the `core.hooksPath` configuration variable would lead to [pre-commit failing](https://github.com/pre-commit/pre-commit/issues/1198). The `commit-msg` hook [runs after](https://git-scm.com/book/en/v2/Customizing-Git-Git-Hooks) the `pre-commit` hook, hence the two are de-coupled in this workflow.

To associate a commit with an issue, you will need to reference the JIRA Issue key (For eg 'CIDC-1111') in the corresponding commit message.

## Admin functions

Under the (hidden) `admin` are several functions meant for CIDC administators / engineers.

### CSMS

```bash
cidc admin test-csms
```

A simple API hit for a test of CSMS connection. Hits API endpoint `/admin/test_csms` which in turn gets CSMS's `/docs`.
This tests that the API is able to successfully make connection with the CSMS, as the `/docs` endpoint requires authorization.
As the API endpoint is protected, only users with role `cidc-admin` can make this request.

### dbedit suite

A set of commands to list / remove data from the database, including shipments, clinical data, and assay/analysis data.
It directly uses Google's cloud SDK to make a direct connection to the postgres cloud sql database, so it requires the user has `cloudsql.instances.connect` IAM permission.

#### Authentication

Authentication uses Application Default Credentials (ADC). Log-in is done via:

```bash
gcloud auth application-default login
```

#### Configuration

Configuration of the environment ie staging versus production is done as above using:

```bash
cidc config get-env
cidc config set-env ENV
```

Configuration of the database username is done via a pair of functions:

```bash
cidc admin get-username
cidc admin set-username USERNAME
```

The password is requested every time you issue a command so as to not store it.

#### Listing data

Under the `list` subcommand of `cidc admin`, you can get descriptions of the data available in the database.

- `cidc admin list clinical TRIAL_ID`
  - prints a table describing all shipments for the given trial
  - with the following columns:
    - `object_url`, `filename`, `num_participants`, `created`, `comment`

- `cidc admin list misc-data TRIAL_ID`
  - prints a table describing all misc_data files for the given trial
  - with the following columns:
    - `batch_id`, `object_url`, `filename`, `created`, `description`

- `cidc admin list shipments TRIAL_ID`
  - prints a table describing all shipments for the given trial
  - with the following columns:
    - `upload_type`, `manifest_id`, `num_samples`, `created`

- `cidc admin list assay TRIAL_ID ASSAY_OR_ANALYSIS`
  - prints a table listing all samples for the given assay/analysis and trial
  - any of the following values are allowed:
    - `clinical_data`, same as `cidc admin list clinical TRIAL_ID`
    - `misc_data`, same as `cidc admin list misc-data TRIAL_ID`
    - analyses: `atacseq_analysis`, `ctdna_analysis`, `cytof_analysis`, `microbiome_analysis`, `rna_level1_analysis`, `tcr_analysis`, `wes_analysis`, `wes_analysis_old`, `wes_tumor_only_analysis`, `wes_tumor_only_analysis_old`
    - assays: `atacseq`, `ctdna`, `cytof`, `hande`, `ihc`, `elisa`, `microbiome`, `mif`, `nanostring`, `olink`, `rna`, `tcr`, `wes`

#### Removing data

Under the `remove` subcommand of `cidc admin`, you can remove a wide variety of data from the JSON blobs.

- `cidc admin remove clinical TRIAL_ID TARGET_ID`
  - removes a given clinical data file from a given trial's metadata as well as the file itself from the portal
  - `TARGET_ID` is the `filename` of the clinical data to remove, as from `cidc admin list clinical TRIAL_ID`
    - special value `'*'` for all files for this trial

- `cidc admin remove shipment TRIAL_ID TARGET_ID`
  - removes a given shipment from a given trial's metadata
  - `TARGET_ID` is the `manifest_id` of the shipment to remove, as from `cidc admin list shipments TRIAL_ID`

- `cidc admin remove assay TRIAL_ID ASSAY_OR_ANALYSIS TARGET_ID`
  - removes a given clinical data file from a given trial's metadata as well as the associated files themselves from the portal
  - for `ASSAY_OR_ANALYSIS=clinical_data`, same as `cidc admin remove clinical TRIAL_ID TARGET_ID`
  - `TARGET_ID` is a tuple of the ids to find the data to remove, as from `cidc admin list assay TRIAL_ID ASSAY_OR_ANALYSIS`.
    - It cannot go past where is divisible in the data, but can end early to remove the whole section.
    - Namely:
      - `elisa`: requires only `assay_run_id`
      - `misc_data`, `olink`: require `batch_id` with an optional `filename`
      - `nanostring`: requires `batch_id` and optional `run_id`
      - `rna_level1_analysis`, `wes_tumor_only_analysis`,  `wes_tumor_only_analysis_old`: requires only `cimac_id`
      - `wes_analysis`, `wes_analysis_old`: requires only `run_id`
      - otherwise: requires `batch_id` and optional `cimac_id`
