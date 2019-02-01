| Branch | Coverage |
| --- | --- |
| Master | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/) |
| Staging | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/) |
## CIDC-CLI

Command line tool for interfacing with the CIDC workflow pipeline

## Installation

###  Step 1:  Download the Google Cloud SDK

Follow the instructions [here](https://cloud.google.com/sdk/docs/downloads-interactive) to install the Google Cloud SDK for your particular operating system. When running `gcloud init`, be sure to use the same google account you registered on our portal with.

Make sure that the commands `gcloud` and `gsutils` are added to your path so that they can be invoked by name from the terminal you are running the CLI in.

### Step 2:  Clone the CIDC-CLI GitHub Repository

Run:

~~~
git clone https://github.com/CIMAC-CIDC/cidc-cli
~~~

### Step 3:  Install dependencies from requirements.txt

In the root of the cloned repository run:

~~~
pip3 install -r requirements.txt --user
~~~

### Step 4:  Run the CIDC-CLI

Navigate to the `cli` sub-directory (which is located in the root directory) and run:

~~~
bash cli.sh
~~~
