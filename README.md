![circleci](https://circleci.com/gh/dfci/cidc-cli.svg?style=shield&circle-token=f1cc21bf7abc3bddd43d1ed02bc2d24849d18f0f|alt=circleci)

[![Build Status](http://35.196.130.201/jenk/buildStatus/icon?job=sample-test/PR-17)](http://35.196.130.201/jenk/job/sample-test/view/change-requests/job/PR-17/)

## CIDC-CLI

Command line tool for interfacing with the CIDC workflow pipeline

### Installation

Install pipenv if you do not have it installed `pip install pipenv`

Run `pipenv install` or `pipenv run upload-script.py`

Next, run `pip3 install . --user` inside the package directory to install the package on your system

### Running command line tool

To start the command line tool, run the following command:

`CIDC-CLI`

Then enter `upload_data` to begin the upload process. Follow the prompts as they are given, directories should be given in relative path form to the execution directory (e.g. if you want to search the current directory, type './')
