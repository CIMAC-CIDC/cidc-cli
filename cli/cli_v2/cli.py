import os
import shutil
import functools
import subprocess

import click

from . import api
from . import auth
from ..constants import UPLOAD_WORKSPACE

#### $ cidc ####
@click.group()
def cidc():
    """The CIDC command-line interface."""


#### $ cidc login ####
@click.command()
@click.argument('portal_token', required=True, type=str)
def login(portal_token):
    """Validate and cache the given token"""
    click.echo("Validating token...")
    auth.cache_token(portal_token)
    click.echo("You are now logged in.")

#### $ cidc manifests ####
@click.group()
def manifests():
    """Manage manifest data."""

#### $ cidc assays ####
@click.group()
def assays():
    """Manage assay data."""

#### $ cidc assays list ####
@click.command("list")
def list_assays():
    """List all supported assay types."""
    assay_list = api.list_assays()
    for assay in assay_list:
        click.echo(f'* {assay}')

#### $ cidc assays upload ####
@click.command("upload")
@click.option("--assay", required=True, help="Assay type.")
@click.option("--xlsx", required=True, help="Path to the assay metadata spreadsheet.")
def upload_assay(assay, xlsx):
    """
    Upload data for an assay.

    TODO: better error-handling. Right now, if a user, e.g., throws a KeyboardInterrupt before
    reaching the try-except block wrapping the gsutil invocation, the API doesn't get alerted
    that the upload job failed.
    """

    # Read the .xlsx file and make the API call
    # that initiates the upload job and grants object-level GCS access.
    with open(xlsx, 'rb') as xlsx_file:
        upload_info = api.initiate_upload(assay, xlsx_file)

    click.echo('Initiating upload...')

    # Move to the directory containing the xlsx file,
    # since the local filepaths we get back in upload_info
    # might be relative to that directory.
    xlsx_dir = os.path.abspath(os.path.dirname(xlsx))
    os.chdir(xlsx_dir)

    # Copy the local files into a nested file structure equivalent
    # to the structure we want to create in GCS, rooted in the UPLOAD_WORKSPACE
    # directory. Having the files organized in this manner allows
    # us to upload all files in parallel using the "gsutil -m ..."
    # command below.
    for local_path, gcs_object in upload_info['url_mapping'].items():
        path = os.path.join(UPLOAD_WORKSPACE, gcs_object)
        os.makedirs(path)
        shutil.copy(local_path, path)
    os.chdir(UPLOAD_WORKSPACE)

    # Construct the upload command
    gcs_bucket_uri = 'gs://%s' % upload_info['gcs_bucket']
    gsutil_args = ["gsutil", "-m", "cp", "-r", ".", gcs_bucket_uri]

    try:
        # Run the upload command
        subprocess.check_output(gsutil_args)
    except (Exception, KeyboardInterrupt) as e:
        # Clean up the workspace
        shutil.rmtree(UPLOAD_WORKSPACE)

        # Alert the API that the upload job failed
        api.job_failed(upload_info['job_id'], upload_info['job_etag'])

        # Alert the user that the upload job failed
        raise e

    # Clean up the workspace
    shutil.rmtree(UPLOAD_WORKSPACE)

    # Alert the API that upload job succeeded
    api.job_succeeded(upload_info['job_id'], upload_info['job_etag'])


# Wire up the interface
cidc.add_command(login)
cidc.add_command(manifests)
cidc.add_command(assays)

assays.add_command(list_assays)
assays.add_command(upload_assay)

if __name__ == "__main__":
    cidc()
