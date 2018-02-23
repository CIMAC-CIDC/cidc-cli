#!/usr/bin/env python3
"""
This is a simple command-line tool that allows users to upload data to our google storage
"""

import re
import subprocess
import os
import os.path
import datetime
import requests

EVE_URL = "http://0.0.0.0:5000"


def request_eve_endpoint(eve_token, payload_data, endpoint, method='POST'):
    """
    Generic method for running a request against the API with authorization

    Arguments:
        eve_token {str} -- API token
        payload_data {dict} -- The payload to be sent
        endpoint {str} -- Name of the endpoint the request should be sent to

    Returns:
        obj -- Returns request object
    """

    method_dictionary = {
        'GET': requests.get,
        'POST': requests.post,
        'PUT': requests.put,
        'HEAD': requests.head,
        'OPTIONS': requests.options,
        'DELETE': requests.delete
    }
    if method not in method_dictionary:
        error_string = 'Method argument ' + method + ' not a valid operation'
        raise KeyError(error_string)

    request_func = method_dictionary[method]
    if request_func == requests.get:
        return request_func(
            EVE_URL + "/" + endpoint,
            headers={"Authorization": 'token {}'.format(eve_token)},
            params=payload_data
        )
    return request_func(
        EVE_URL + "/" + endpoint,
        json=payload_data,
        headers={"Authorization": 'token {}'.format(eve_token)}
    )


def validate_and_extract(file_names, sample_ids):
    """
    Compares each file name in upload to list of valid sample IDs in trial.
    If all names are valid, returns a mapping of filename to sample id.

    Arguments:
        file_names {[str]} -- list of file names
        sample_ids {[str]} -- list of valid ids

    Returns:
        dict -- Dictionary mapping file name to sample id.
    """
    # Create RE object based on valid samples
    search_string = re.compile(str.join('|', sample_ids))
    # create a dictionary of type filename: regex search result
    name_dictionary = dict((item, re.search(search_string, item)) for item in file_names)
    # Check for any "None" types and return empty list if any found.
    if not all(name_dictionary.values()):
        return []
    # If all valid, return map of filename: sample_id
    return dict((name, name_dictionary[name].group()) for name in name_dictionary)


def create_data_entries(name_dictionary, google_url, google_folder_path, trial, assay):
    """Function that creates google bucket URIs from file names.

    Arguments:
        file_names {dict} -- Dictionary mapping filename to sample ID. 
        google_url {str} -- URL of the google bucket.
        google_folder_path {str} -- Storage path under which files are sorted.

    Returns:
        [dict] -- List of dictionaries containing the files and URIs.
    """
    return [
        {
            "filename": name,
            "gs_uri": google_url + google_folder_path + "/" + name,
            "trial": trial,
            "assay": assay,
            "date_created": datetime.datetime.now().isoformat(),
            "sample_id": name_dictionary[name]
        }
        for name in name_dictionary
    ]


def update_job_status(status, mongo_data, eve_token, google_data=None, message=None):
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
        requests.patch(
            EVE_URL + "/ingestion/" + mongo_data['_id'],
            json={
                "status": {
                    "progress": "Completed",
                    "message": ""
                },
                "end_time": datetime.datetime.now().isoformat(),
            },
            headers={
                "If-Match": mongo_data['_etag'],
                "Authorization": 'token {}'.format(eve_token)
            }
        )
    else:
        requests.patch(
            EVE_URL + "/ingestion/" + mongo_data['_id'],
            json={
                "status": {
                    "progress": "Aborted",
                    "message": message
                }
            },
            headers={
                "If-Match": mongo_data['_etag'],
                "Authorization": 'token {}'.format(eve_token)
            }
        )


def upload_files(directory, files_uploaded, mongo_data, eve_token, headers, assay, trial):
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
            gsutil_args,
            stderr=subprocess.STDOUT
        )
        update_job_status(True, mongo_data, eve_token)
        return mongo_data['_id']
    except subprocess.CalledProcessError as error:
        print("Error: Upload to Google failed: " + error)
        update_job_status(False, mongo_data, eve_token, error)
        return None


def find_eve_token(token_dir):
    """Searches for a file containing a token for the API

    Arguments:
        token_dir {str} -- directory where token is stored

    Raises:
        FileNotFoundError -- Raise error if no token file found

    Returns:
        str -- Authorization token
    """
    for file_name in os.listdir(token_dir):
        if file_name.endswith('.token'):
            with open(token_dir + '/' + file_name) as token_file:
                eve_token = token_file.read().strip()
                return eve_token
    raise FileNotFoundError('No valid token file was found')
