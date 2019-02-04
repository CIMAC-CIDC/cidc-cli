| Branch | Coverage |
| --- | --- |
| Master | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/) |
| Staging | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/) |
## CIDC-CLI

Command line tool for interfacing with the CIDC workflow pipeline

## Installation

###  Download the Google Cloud SDK

Follow the instructions [here](https://cloud.google.com/sdk/docs/downloads-interactive) to install the SDK for your particular operating system. When running `gcloud init` be sure to use the same google account you registered on our portal with.

Make sure that the commands `gcloud` and `gsutils` are added to your path so that they can be invoked by name from the terminal you are running the CLI in.

### Ensure pip is installed

The easiest way to install the application is by using [pip](https://pypi.org/project/pip/) to install the requirements from the `requirements.txt` file. This project does not support Python 2, so be sure to use the Python 3 linked version of pip.

### Install dependencies from requirements.txt

If you don't want to install the package as a named command, you can simply download the dependencies and run the command line as a script.

In the root of the cloned repository run:

~~~
pip3 install -r requirements.txt --user
~~~

### Running command line tool
Navigate to the `cli` directory (which is located in the root directory) and run:

~~~
bash cli.sh
~~~