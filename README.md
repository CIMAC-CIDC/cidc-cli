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
