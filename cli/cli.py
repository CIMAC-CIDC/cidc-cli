"""The second generation CIDC command-line interface."""
import click

from . import api, auth, gcloud, upload, config, consent, __version__
from .dbedit.cli import get_username, list_, remove_, set_username

#### $ cidc ####
@click.group()
@click.option("-i", "--ignore", default=None, hidden=True)
def cidc(ignore):
    """The CIDC command-line interface."""
    config.check_env_warning(ignore)
    if not consent.check_consent():
        exit(0)
    gcloud.check_installed()


#### $ cidc version ####
@click.command()
def version():
    """Echo version and done"""
    click.echo(f"cidc-cli {__version__}")


#### $ cidc login ####
@click.command()
@click.argument("portal_token", required=True, type=str)
def login(portal_token):
    """Validate and cache the given token"""
    click.echo("Validating token...")
    auth.validate_and_cache_token(portal_token)
    click.echo("You are now logged in.")


#### $ cidc config ####
@click.group("config", hidden=True)
def config_():
    """Manage CLI configuration."""


#### $ cidc config set-env ####
@click.command()
@click.argument(
    "environment", required=True, type=click.Choice(["prod", "staging", "dev"])
)
def set_env(environment):
    """Set the CLI environment."""
    config.set_env(environment)
    click.echo(f"Updated CLI environment to {environment}")


#### $ cidc config get-env ####
@click.command()
def get_env():
    """Get the current CLI environment."""
    click.echo(config.get_env())


#### $ cidc admin ####
@click.group("admin", hidden=True)
def admin_():
    """Manage API admin features."""


#### $ cidc admin test-csms ####
@click.command()
def test_csms():
    """A simple API hit for a test of CSMS connection"""
    api.test_csms()


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
        click.echo(f"* {assay}")


#### $ cidc assays upload ####
@click.command("upload")
@click.option("--assay", required=True, help="Assay type.")
@click.option("--xlsx", required=True, help="Path to the assay metadata spreadsheet.")
def upload_assay(assay, xlsx):
    """
    Upload data for an assay.
    """
    upload.run_upload(assay, xlsx)


#### $ cidc analyses ####
@click.group()
def analyses():
    """Manage analysis data."""


#### $ cidc analyses list ####
@click.command("list")
def list_analyses():
    """List all supported analysis types."""
    analysis_list = api.list_analyses()
    for analysis in analysis_list:
        click.echo(f"* {analysis}")


#### $ cidc analyses upload ####
@click.command("upload")
@click.option("--analysis", required=True, help="Analysis type.")
@click.option(
    "--xlsx", required=True, help="Path to the analysis metadata spreadsheet."
)
def upload_analysis(analysis, xlsx):
    """
    Upload data for an analysis.
    """
    upload.run_upload(analysis, xlsx, is_analysis=True)


# Wire up the interface
cidc.add_command(version)
cidc.add_command(login)
cidc.add_command(assays)
cidc.add_command(analyses)
cidc.add_command(config_)
cidc.add_command(admin_)

config_.add_command(set_env)
config_.add_command(get_env)

assays.add_command(list_assays)
assays.add_command(upload_assay)

analyses.add_command(list_analyses)
analyses.add_command(upload_analysis)

admin_.add_command(test_csms)
admin_.add_command(get_username)
admin_.add_command(list_)
admin_.add_command(remove_)
admin_.add_command(set_username)

if __name__ == "__main__":
    cidc()
