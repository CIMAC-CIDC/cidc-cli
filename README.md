| Branch  | Coverage                                                                                                                                          | Codacy                                                                                                                                                                                                                                                           | Code Style                                                                                                        | License                                                                                                     |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| Master  | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/)   | [![Codacy Badge](https://api.codacy.com/project/badge/Grade/b705166077e84bd69000e63b7e2f0e7c)](https://www.codacy.com/app/CIMAC-CIDC/cidc-cli?utm_source=github.com&utm_medium=referral&utm_content=CIMAC-CIDC/cidc-cli&utm_campaign=Badge_Grade?branch=master)  | [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black) | [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) |
| Staging | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/) | [![Codacy Badge](https://api.codacy.com/project/badge/Grade/b705166077e84bd69000e63b7e2f0e7c)](https://www.codacy.com/app/CIMAC-CIDC/cidc-cli?utm_source=github.com&utm_medium=referral&utm_content=CIMAC-CIDC/cidc-cli&utm_campaign=Badge_Grade?branch=staging) | [![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black) | [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT) |

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
