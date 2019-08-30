"""The second generation CIDC command-line interface."""
import click

from . import api, auth, gcloud, upload, config, consent

#### $ cidc ####
@click.group()
def cidc():
    """The CIDC command-line interface."""
    if not consent.check_consent():
        exit(0)
    gcloud.check_installed()


#### $ cidc login ####
@click.command()
@click.argument('portal_token', required=True, type=str)
def login(portal_token):
    """Validate and cache the given token"""
    click.echo("Validating token...")
    auth.cache_token(portal_token)
    click.echo("You are now logged in.")

#### $ cidc config ####
@click.group('config')
def config_():
    """Manage CLI configuration."""

#### $ cidc config set-env ####
@click.command()
@click.argument('environment', required=True, type=click.Choice(['prod', 'staging', 'dev']))
def set_env(environment):
    """Set the CLI environment."""
    config.set_env(environment)
    click.echo(f"Updated CLI environment to {environment}")

#### $ cidc config get-env ####
@click.command()
def get_env():
    """Get the current CLI environment."""
    click.echo(config.get_env())

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
cidc.add_command(config_)

config_.add_command(set_env)
config_.add_command(get_env)

assays.add_command(list_assays)
assays.add_command(upload_assay)

if __name__ == "__main__":
    cidc()
