#!/usr/bin/env python3
"""
A script that mocks the CLI to run an end-to-end workflow test.
"""
import subprocess
import time
from os import environ as env, listdir, path
import requests
from cidc_utils.requests import SmartFetch
from utilities.cli_utilities import validate_and_extract, create_payload_objects
from upload.upload import upload_files

DOMAIN = env.get('DOMAIN')
CLIENT_SECRET = env.get('CLIENT_SECRET')
CLIENT_ID = env.get('CLIENT_ID')
AUDIENCE = env.get('AUDIENCE')


def get_token() -> None:
    """
    Fetches a token from the auth server.

    Returns:
        dict -- Server response.
    """
    payload = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'audience': AUDIENCE
    }
    res = requests.post("https://cidc-test.auth0.com/oauth/token", json=payload)
    return {
        'access_token': res.json()['access_token'],
        'expires_in': res.json()['expires_in'],
        'time_fetched': time.time()
    }

# Get token from ENV
EVE_TOKEN = get_token()['access_token']

# Set up connection to API
EVE_FETCHER = SmartFetch(
    env.get('INGESTION_API_SERVICE_HOST') + ':' + env.get('INGESTION_API_SERVICE_PORT')
    )

# Mock Trial
HELLO_TRIAL = {
    "_id": "5ac674521e478003ad494cd0",
    "trial_name": "test_trial",
    "principal_investigator": "lloyd",
    "start_date": "2018-04-05T19:09:06.062Z",
    "samples": ["FOO"],
    "assays": [
        {
            "assay_name": "hello.wdl",
            "assay_id": "5ac674d81e478003ad494cd1"
        }
    ],
    "collaborators": ["mccarthy@bcb-mail.dfci.harvard.edu"]
}

# Mock Assay
HELLO_ASSAY = {
    "_id": "5ac674d81e478003ad494cd1",
    "assay_name": "hello.wdl",
    "non_static_inputs": ["wf_hello.hello.addressee"],
    "static_inputs": [
        {"key_name": "foo", "key_value": "bar"}
    ],
    "wdl_location": "wdl/wes/hello.wdl"
}

UPLOAD_DIR = 'sample_data/test'

FILES_TO_UPLOAD = [
    name for name in listdir(UPLOAD_DIR) if
    path.isfile(path.join(UPLOAD_DIR, name))
]

UPLOAD_GUIDE = validate_and_extract(
    FILES_TO_UPLOAD,
    HELLO_TRIAL['samples'],
    HELLO_ASSAY['non_static_inputs']
)

# Create upload payload
UPLOAD_PAYLOAD = {
    'number_of_files': len(UPLOAD_GUIDE),
    'status': {
        'PROGRESS': 'In PROGRESS'
    },
    'files': create_payload_objects(UPLOAD_GUIDE, HELLO_TRIAL, HELLO_ASSAY)
}

RESPONSE_UPLOAD = EVE_FETCHER.post(
    token=EVE_TOKEN, endpoint='ingestion', json=UPLOAD_PAYLOAD, code=201
)

JOB_ID = upload_files(
    UPLOAD_DIR,
    [UPLOAD_GUIDE[key] for key in UPLOAD_GUIDE],
    RESPONSE_UPLOAD.json(),
    EVE_TOKEN,
    RESPONSE_UPLOAD.headers
)

DONE = False
COUNTER = 0
while not DONE and COUNTER < 200:
    STATUD_RESPONSE = EVE_FETCHER.get(token=EVE_TOKEN, endpoint='ingestion/' + JOB_ID, code=200)
    PROGRESS = STATUD_RESPONSE.json()['status']['PROGRESS']
    if PROGRESS == 'In PROGRESS':
        print('Job is still in PROGRESS, check back later')
    elif PROGRESS == 'Completed':
        print('Job is completed.')
        DONE = True
    elif PROGRESS == 'Aborted':
        print('Job was aborted: ' + STATUD_RESPONSE.json()['status']['message'])
        DONE = True
    time.sleep(30)
    COUNTER += 1
