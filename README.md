| Branch | Coverage |
| --- | --- |
| Master | [![codecov](https://codecov.io/gh/dfci/cidc-cli/branch/master/graph/badge.svg)](https://codecov.io/gh/dfci/cidc-cli/branch/master/) |
| Staging | [![codecov](https://codecov.io/gh/dfci/cidc-cli/branch/staging/graph/badge.svg)](https://codecov.io/gh/dfci/cidc-cli/branch/staging/) |
## CIDC-CLI

Command line tool for interfacing with the CIDC workflow pipeline

## Installation

###  Download the Google Cloud SDK

Follow the instructions [here](https://cloud.google.com/sdk/docs/downloads-interactive) to install the SDK for your particular operating system. When running `gcloud init` be sure to use the same google account you registered on our portal with.

Make sure that the commands `gcloud` and `gsutils` are added to your path so that they can be invoked by name from the terminal you are running the CLI in.

### Ensure pip is installed

The easiest way to install the application is by using [pip](https://pypi.org/project/pip/). This project does not support Pyhon 2, so be sure to use the Python 3 linked version of pip.

### Pip install

You can either install locally from the cloned repo using:
~~~
pip3 install . --user
~~~

Or install directly from the repo with:

~~~
pip3 install git+https://github.com/dfci/cidc-cli#egg=cidc-cli
~~~

### Install dependencies from requirements.txt

If you don't want to install the package as a named command, you can simply download the dependencies and run the command line as a script.

In the root of the cloned repository run:

~~~
pip3 install -r requirements.txt --user
~~~

### Running command line tool

If you installed the package using pip, the cli should be runnable with the command `cidc-cli`.

If you installed the dependencies, navigate to the `cli` directory and run:

~~~
bash cli.sh
~~~

To log in, use the `jwt-login` command to enter the token you got from our website.

~~~
jwt-login MyTokenHere...
~~~


