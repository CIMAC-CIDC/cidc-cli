#!/bin/bash
gcloud auth activate-service-account --key-file=../auth/.google_auth.json
gcloud config set project cidc-dfci
cat
