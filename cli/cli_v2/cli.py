import functools

import click

from . import auth


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
def list_():
    """List all supported assay types."""
    # TODO make API call
    print("listing assays!")


#### $ cidc assays upload ####
@click.command()
@auth.requires_id_token
@click.option("--assay", required=True, help="Assay type.")
@click.option("--xlsx", required=True, help="Path to the assay metadata spreadsheet.")
def upload(id_token, assay, xlsx):
    """Upload data for an assay. """
    print(f"Uploading metadata and data from `{xlsx}` for `{assay}`.")


# Wire up the interface
cidc.add_command(login)
cidc.add_command(manifests)
cidc.add_command(assays)
assays.add_command(list_)
assays.add_command(upload)

if __name__ == "__main__":
    cidc()
