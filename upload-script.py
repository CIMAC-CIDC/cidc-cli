#!/usr/bin/env python
"""
This is a simple command-line tool that allows users to upload data to our google storage
"""

import argparse
import subprocess
import os
import os.path
import datetime
import requests

EVE_URL = "http://0.0.0.0:5000"

PARSER = argparse.ArgumentParser(description='Upload files to google.')
PARSER.add_argument('username', help='Your CIDC assigned username')
PARSER.add_argument(
    '-d',
    '--directory',
    help='Directory where files you want to upload are stored'
    )
PARSER.add_argument('-n', '--name', help='Name of the experiment')
PARSER.add_argument("-t", '--token', help='The directory of your .token file')
ARGS = PARSER.parse_args()


def jsonize(name):
    """
    Small helper function that returns a json object type from a filename

    Args:
        name (str): The name of the file.

    Returns:
        dict: A dictionary with the filename and a blank uri field.
    """
    return {'filename': name, 'google_uri': ''}


def authenticate_user(username, eve_token, file_names, experiment_name):
    """Contacts the EVE API and creates an entry for the job in the mongo
    server.

    Arguments:
        username {str} -- Name of user uploading job.
        eve_token {str} -- API token.
        file_names {[str]} -- List of names of files in job.
        experiment_name {str} -- Name under which the files are to be collected.

    Returns:
        Object -- Returns a response object with status code and data.
    """
    item_map = list(map(jsonize, file_names))
    return requests.post(
        EVE_URL + "/jobs",
        json={
            "started_by": username,
            "number_of_files": len(file_names),
            "experiment_name": experiment_name,
            "status": {
                "progress": "In Progress",
                "message": ""
            },
            "start_time": datetime.datetime.now().isoformat(),
            "files": item_map,
        },
        headers={
            "Authorization": 'token {}'.format(eve_token)
        }
    )


def map_google_urls(file_names, experiment_name, google_url, google_folder_path):
    """Function that creates google bucket URIs from file names.

    Arguments:
        file_names {[str]} -- List of strings of file names in the job.
        experiment_name {str} -- Name under which the experiment is collected.
        google_url {str} -- URL of the google bucket.
        google_folder_path {str} -- Storage path under which files are sorted.

    Returns:
        [dict] -- List of dictionaries containing the files and URIs.
    """
    return [
        {
            "filename": name,
            "google_uri": google_url + google_folder_path + experiment_name + "/" + name
        }
        for name in file_names
    ]


def update_job_status(status, google_data, mongo_data, eve_token):
    """Updates the status of the job in MongoDB, either with the URIs if the upload
    was succesfull, or with the error message if it failed.

    Arguments:
        status {str} -- Status of the job, one of three values: Aborted,
        Completed, In Progress
        google_data {[dict]} -- If successfull, list of dicts of the file
        names and their associated
        uris. If failed, contains the error message.
        mongo_data {dict} -- The response object from the mongo insert.
        eve_token {str} -- Token for accessing EVE API.
    """
    if status:
        requests.patch(
            EVE_URL + "/jobs/" + mongo_data['_id'],
            json={
                "status": {
                    "progress": "Completed",
                    "message": ""
                },
                "end_time": datetime.datetime.now().isoformat(),
                "files": list(google_data)
            },
            headers={
                "If-Match": mongo_data['_etag'],
                "Authorization": 'token {}'.format(eve_token)
            }
        )
    else:
        requests.patch(
            EVE_URL + "/jobs/" + mongo_data['_id'],
            json={
                "status": {
                    "progress": "Aborted",
                    "message": google_data
                }
            },
            headers={
                "If-Match": mongo_data['_etag'],
                "Authorization": 'token {}'.format(eve_token)
            }
        )


def upload_files(directory, files_uploaded, experiment_name, mongo_data, eve_token, headers):
    """Launches the gsutil command using subprocess and uploads files to the
    google bucket.

    Arguments:
        directory {str} -- Directory of the files you want to upload.
        files_uploaded {[str]} -- List of filenames of the uploaded files.
        experiment_name {str} -- Name of the experiment.
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
        gsutil_args.extend(
            [
                "cp", "-r",
                directory,
                google_url + google_path + experiment_name
            ]
        )
        subprocess.check_output(
            gsutil_args,
            stderr=subprocess.STDOUT
        )
        file_json = map_google_urls(files_uploaded, experiment_name, google_url, google_path)
        update_job_status(True, file_json, mongo_data, eve_token)
        return file_json
    except subprocess.CalledProcessError as error:
        print("Error: Upload to Google failed: " + error)
        update_job_status(False, error, mongo_data, eve_token)


def main():
    """
    Main execution
    """
    file_dir = ARGS.directory if ARGS.directory else '.'
    token_dir = ARGS.token if ARGS.token else "."
    eve_token = None
    for file_name in os.listdir(token_dir):
        if file_name.endswith(".token"):
            with open(file_name) as token_file:
                eve_token = token_file.read().strip()

    if not eve_token:
        raise FileNotFoundError('No valid token file was found')

    name = ARGS.name if ARGS.name else os.path.basename(
        os.path.dirname(file_dir)
        )
    # creates a list of file names in the directory specified or CWD if no path given
    files_in_job = [
        name for name in os.listdir(file_dir) if
        os.path.isfile(os.path.join(file_dir, name))
        ]
    response_data = authenticate_user(ARGS.username, eve_token, files_in_job, name)
    if response_data.status_code == 201:
        result = upload_files(
            file_dir, files_in_job, name, response_data.json(), eve_token, response_data.headers
            )
        print('''File upload has completed without error.\n
        Your files can be found in the following locations:''')
        for uploaded_file in result:
            print("File name: " + uploaded_file['filename'])
            print("Google URI: " + uploaded_file['google_uri'] + "\n")
    else:
        print(
            "There was a problem with your request: " +
            str(response_data.status_code)
            )
        print(response_data.text)

main()
