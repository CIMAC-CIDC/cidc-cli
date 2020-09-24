"""Utilities for working with a user's gcloud installation"""
import shutil
import subprocess

import click

from . import auth

GCLOUD = "gcloud"


def check_installed():
    """Check if gcloud appears to be installed on this computer."""
    if not shutil.which(GCLOUD):
        raise click.ClickException(
            "The CIDC CLI requires an installation of the gcloud SDK. "
            "To install, please visit: https://cloud.google.com/sdk/install"
        )


def login():
    """Check if a user is logged in to gcloud, and log them in if not."""
    email = auth.get_user_email()

    # Try to log the user in to gcloud with their CIDC email
    click.secho("$ gcloud auth login --no-launch-browser --brief", dim=True)
    subprocess.call([GCLOUD, "auth", "login", email, "--no-launch-browser", "--brief"])
