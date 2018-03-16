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


def validate_and_extract(file_names, sample_ids, non_static_inputs):
    """
    Compares each file name in upload to list of valid sample IDs in trial.
    If all names are valid, returns a mapping of filename to sample id.

    Arguments:
        file_names {[str]} -- list of file names
        sample_ids {[str]} -- list of valid ids

    Returns:
        dict -- Dictionary mapping file name to sample id. Format:
        {
            file_name: {
                sample_id: "sample_id",
                mapped_input: "mapping"
            }
        }
    """
    # Create RE object based on valid samples
    search_string = re.compile(str.join('|', sample_ids))
    # create a dictionary of type filename: regex search result
    name_dictionary = dict((item, re.search(search_string, item)) for item in file_names)
    # Check for any "None" types and return empty list if any found.
    if not all(name_dictionary.values()):
        return []
    # If all valid, return map of filename: sample_id
    mapped_names = dict((name, name_dictionary[name].group()) for name in name_dictionary)

    # Create dictionary of involved sampleIDS
    sample_id_dict = {}

    # Group filenames under associated sampleIDs.
    # Format: sample_id: [list, of, files, with, that, id]
    for key, value in mapped_names.items():
        if value in sample_id_dict:
            sample_id_dict[value].append(key)
        else:
            sample_id_dict[value] = [key]

    # Guide for associating file names with sample ids, and later, inputs
    upload_guide = dict((item, {"sample_id": mapped_names[item]}) for item in mapped_names)

    for sample_id in sample_id_dict:

        # Copy list by value for manipulation
        nsi = non_static_inputs[:]

        print(
            "These files are associated with SampleID: " + sample_id + ", please map them to the \
            assay inputs"
        )
        files_to_map = sample_id_dict[sample_id]

        # Sanity check number of files per ID
        if len(files_to_map) > len(nsi):
            print("Error! Too many files for this sampleID")
            return []

        # Loop over files and make the user map them.
        for filename in files_to_map:
            selection = option_select_framework(
                nsi,
                "Please choose which input " + filename + " maps to."
            )
            # save selection, then delete from list.
            upload_guide[filename]['mapping'] = nsi[selection - 1]
            del nsi[selection - 1]

    return upload_guide


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


def update_job_status(status, mongo_data, eve_token, message=None):
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
        res = requests.patch(
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
                "Authorization": 'token {}'.format(eve_token),
                "Content-Type": "application/json"
            }
        )
        if res.json:
            print(res.json())
            print(res.reason)
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


def upload_files(directory, files_uploaded, mongo_data, eve_token, headers):
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

from utilities.cli_utilities import option_select_framework
