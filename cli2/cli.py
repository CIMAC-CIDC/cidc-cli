"""The second generation CIDC command-line interface."""
import os
import shutil
import subprocess

import click

from . import api
from . import auth
from . import gcloud
from . import upload

#### $ cidc ####
@click.group()
def cidc():
    """The CIDC command-line interface."""
    gcloud.check_installed()


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
    """
    upload.upload_assay(assay, xlsx)


# Wire up the interface
cidc.add_command(login)
cidc.add_command(manifests)
cidc.add_command(assays)

assays.add_command(list_assays)
assays.add_command(upload_assay)

if __name__ == "__main__":
    cidc()
