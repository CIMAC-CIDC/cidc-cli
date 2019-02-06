| Branch | Coverage | Code Quality |
| --- | --- | --- |
| Master | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/master/) | [![Codacy Badge](https://api.codacy.com/project/badge/Grade/b705166077e84bd69000e63b7e2f0e7c)](https://www.codacy.com/app/lemccarthy/cidc-cli?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=CIMAC-CIDC/cidc-cli&amp;utm_campaign=Badge_Grade?branch=master)
| Staging | [![codecov](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/graph/badge.svg)](https://codecov.io/gh/CIMAC-CIDC/cidc-cli/branch/staging/) | [![Codacy Badge](https://api.codacy.com/project/badge/Grade/b705166077e84bd69000e63b7e2f0e7c)](https://www.codacy.com/app/lemccarthy/cidc-cli?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=CIMAC-CIDC/cidc-cli&amp;utm_campaign=Badge_Grade?branch=staging)
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
