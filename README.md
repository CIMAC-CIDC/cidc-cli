| Branch  | Coverage                                                                                                                                          | Codacy                                                                                                                                                                                                                                                           | Code Style                                                                                                        | License                                                                                                     |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Master  | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/)   | [![Codacy Badge](https://api.codacy.com/project/badge/Grade/b705166077e84bd69000e63b7e2f0e7c)](https://www.codacy.com/app/CIMAC-CIDC/cidc-cli?utm_source=github.com&utm_medium=referral&utm_content=CIMAC-CIDC/cidc-cli&utm_campaign=Badge_Grade?branch=master)  | [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black) | [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) |
| Staging | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/) | [![Codacy Badge](https://api.codacy.com/project/badge/Grade/b705166077e84bd69000e63b7e2f0e7c)](https://www.codacy.com/app/CIMAC-CIDC/cidc-cli?utm_source=github.com&utm_medium=referral&utm_content=CIMAC-CIDC/cidc-cli&utm_campaign=Badge_Grade?branch=staging) | [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black) | [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) |

## CIDC-CLI

Command line tool for interfacing with the CIDC workflow pipeline

## Installation

### Step 1: Download the Google Cloud SDK

Follow the instructions [here](https://cloud.google.com/sdk/docs/downloads-interactive) to install the Google Cloud SDK for your particular operating system. When running `gcloud init`, be sure to use the same google account you registered on our portal with.

Make sure that the commands `gcloud` and `gsutils` are added to your path so that they can be invoked by name from the terminal you are running the CLI in.

### Step 2: Clone the CIDC-CLI GitHub Repository

Run:

```bash
git clone https://github.com/CIMAC-CIDC/cidc-cli
```

### Step 3: Install dependencies from requirements.txt

In the root of the cloned repository run:

```bash
pip3 install -r requirements.txt --user
```

### Step 4: Run the CIDC-CLI

To display the help message for the new, non-interactive CLI, run:
```bash
cidc 
```

To run the old, interactive CLI, run:
```bash
cidc_cli
```