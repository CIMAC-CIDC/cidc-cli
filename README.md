[![Build Status](http://35.196.130.201/jenk/buildStatus/icon?job=sample-test/master)](http://35.196.130.201/jenk/job/sample-test/job/master/)

## CIDC-CLI

Command line tool for interfacing with the CIDC workflow pipeline

### Installation

You need to install the [google cloud SDK](https://cloud.google.com/sdk/install) and then log in to the google account that you used to register with our portal using the
following command:

`gcloud auth application-default login`


Install pipenv if you do not have it installed `pip install pipenv`

Run `pipenv install` or `pipenv run upload-script.py`

Next, run `pip3 install . --user` inside the package directory to install the package on your system

### Running command line tool

To start the command line tool, run the following command:

`CIDC-CLI`

Then enter `upload_data` to begin the upload process. Follow the prompts as they are given, directories should be given in relative path form to the execution directory (e.g. if you want to search the current directory, type './')

