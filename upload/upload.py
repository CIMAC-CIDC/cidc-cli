#!/usr/bin/env python3
"""
This is a simple command-line tool that allows users to upload data to our google storage
"""
import subprocess
import datetime
from os import environ as env
from typing import List
from json import JSONDecodeError
import requests
from auth0.constants import EVE_URL


def update_job_status(status: bool, mongo_data: dict, eve_token: str, message: str=None) -> None:
    """Updates the status of the job in MongoDB, either with the URIs if the upload
    was succesfull, or with the error message if it failed.

    Arguments:
        status {bool} -- True if upload succeeds, false otherwise.
        mongo_data {dict} -- The response object from the mongo insert.
        eve_token {str} -- Token for accessing EVE API.
        google_data {[dict]} -- If successfull, list of dicts of the file
        names and their associated uris.
        message {str} -- If upload failed, contains error.
    """
    if status:
        res = requests.post(
            EVE_URL + "/ingestion/" + mongo_data["_id"],
            json={
                "status": {
                    "progress": "Completed",
                    "message": ""
                },
                "end_time": datetime.datetime.now().isoformat(),
            },
            headers={
                "If-Match": mongo_data['_etag'],
                "Authorization": 'Bearer {}'.format(eve_token),
                "X-HTTP-Method-Override": "PATCH"
            }
        )

        if not res.status_code == 200:
            print('Error! Patching unsuccesful')
            print(res.reason)
            try:
                print(res.json())
            except JSONDecodeError:
                print("No valid JSON response")

    else:
        requests.post(
            EVE_URL + "/ingestion/" + mongo_data['_id'],
            json={
                "status": {
                    "progress": "Aborted",
                    "message": message
                }
            },
            headers={
                "If-Match": mongo_data['_etag'],
                "Authorization": 'Bearer {}'.format(eve_token),
                "X-HTTP-Method-Override": "PATCH"
            }
        )


def upload_files(
        directory: str, files_uploaded: List[str], mongo_data: dict, eve_token: str, headers: dict
) -> str:
    """Launches the gsutil command using subprocess and uploads files to the
    google bucket.

    Arguments:
        directory {str} -- Directory of the files you want to upload.
        files_uploaded {[str]} -- List of filenames of the uploaded files.
        mongo_data {dict} -- Response object from the MongoDB insert.
        eve_token: {str} -- token for accessing EVE API.
        headers: {dict} -- headers from the response object.
    Returns:
        str -- Returns the google URIs of the newly uploaded files.
    """
    try:
        gsutil_args = ["gsutil"]
        google_url = headers['google_url']
        google_path = headers['google_folder_path']
        if len(files_uploaded) > 5:
            gsutil_args.append("-m")

        # Insert records into a staging area for later processing
        gsutil_args.extend(
            [
                "cp", "-r",
                directory,
                google_url + google_path + 'staging/' + mongo_data['_id']
            ]
        )
        subprocess.check_output(
            gsutil_args
        )
        update_job_status(True, mongo_data, eve_token)
        return mongo_data['_id']
    except subprocess.CalledProcessError as error:
        print("Error: Upload to Google failed: " + error)
        update_job_status(False, mongo_data, eve_token, error)
        return None
