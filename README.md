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
