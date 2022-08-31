from typing import Tuple
import click

from . import core, remove, list as dblist
from . import config


#### $ cidc admin get-username ####
@click.command()
def get_username():
    """Get the current database username."""
    click.echo(" ".join(["database username:", config.get_username()]))


#### $ cidc admin set-username ####
@click.command()
@click.argument("username", required=True, type=str)
def set_username(username: str):
    """Set the database username."""
    config.set_username(username)
    click.echo(f"Updated database username to {username}")


#### $ cidc admin list ####
@click.group("list")
def list_():
    """Listing different things"""
    pass


#### $ cidc admin list supported ####
@click.command("supported")
def list_supported():
    """List assays and analyses that are supported for listing"""
    print(", ".join(sorted(list(dblist.SUPPORTED_ASSAYS_AND_ANALYSES))))


#### $ cidc admin list assay ####
@click.command("assay")
@click.argument("trial_id", required=True, type=str)
@click.argument("assay_or_analysis", required=True, type=str)
def list_assay(trial_id: str, assay_or_analysis: str):
    """
    List CIMAC IDs for a given assay or analysis for a given trial
    Same as `cidc admin list analysis`

    TRIAL_ID is the id of the trial to affect
    ASSAY_OR_ANALYSIS is the assay or analysis to list CIMAC IDs for
    """
    core.connect(dblist)
    dblist.list_data_cimac_ids(trial_id=trial_id, assay_or_analysis=assay_or_analysis)


#### $ cidc admin list clinical ####
@click.command("clinical")
@click.argument("trial_id", required=True, type=str)
def list_clinical(trial_id: str):
    """
    List clinical files for a given trial

    TRIAL_ID is the id of the trial to affect
    """
    core.connect(dblist)
    dblist.list_clinical(trial_id=trial_id)


#### $ cidc admin list misc-data ####
@click.command("misc-data")
@click.argument("trial_id", required=True, type=str)
def list_misc_data(trial_id: str):
    """
    List files from misc_data uploads for a given trial

    TRIAL_ID is the id of the trial to affect
    """
    core.connect(dblist)
    dblist.list_misc_data(trial_id=trial_id)


#### $ cidc admin list shipments ####
@click.command("shipments")
@click.argument("trial_id", required=True, type=str)
def list_shipments(trial_id: str):
    """
    List shipments for a given trial

    TRIAL_ID is the id of the trial to affect
    """
    core.connect(dblist)
    dblist.list_shipments(trial_id=trial_id)


#### $ cidc admin remove ####
@click.group("remove")
def remove_():
    """Deleting different things"""
    pass


#### $ cidc admin remove assay ####
@click.command("assay")
@click.argument("trial_id", required=True, type=str)
@click.argument("assay_or_analysis", required=True, type=str)
@click.argument("target_id", required=True, nargs=-1)
def remove_assay(trial_id: str, assay_or_analysis: str, target_id: Tuple[str]):
    """
    Remove a given clinical data file from a given trial's metadata
    as well as remove the associated files themselves from the portal.

    TRIAL_ID is the id of the trial to affect
    ASSAY_OR_ANALYSIS is the assay or analysis to affect
    TARGET_ID is a tuple of the ids to find the data to remove
        it cannot go past where is divisible in the data
        eg if ASSAY_OR_ANALYSIS == "elisa", only `assay_run_id` is accepted
        eg if ASSAY_OR_ANALYSIS == "wes_analysis", only `run_id` is accepted
        eg if ASSAY_OR_ANALYSIS == "olink", `batch_id [file]` is assumed
    """
    core.connect(remove)
    remove.remove_data(
        trial_id=trial_id, assay_or_analysis=assay_or_analysis, target_id=target_id
    )


#### $ cidc admin remove clinical ####
@click.command("clinical")
@click.argument("trial_id", required=True, type=str)
@click.argument("target_id", required=True, type=str)
def remove_clinical(trial_id: str, target_id: str):
    """
    Remove a given clinical data file from a given trial's metadata
    as well as remove the file itself from the portal.

    TRIAL_ID is the id of the trial to affect
    TARGET_ID is the object_url of the clinical data to remove
        not including {trial_id}/clinical/
        special value * for all files for this trial
    """
    core.connect(remove)
    remove.remove_clinical(trial_id=trial_id, target_id=target_id)


#### $ cidc admin remove shipment ####
@click.command("shipment")
@click.argument("trial_id", required=True, type=str)
@click.argument("target_id", required=True, type=str)
def remove_shipment(trial_id: str, target_id: str):
    """
    Remove a given shipment from a given trial's metadata

    TRIAL_ID is the id of the trial to affect
    TARGET_ID is the manifest_id of the shipment to remove
    """
    core.connect(remove)
    remove.remove_shipment(trial_id=trial_id, target_id=target_id)


list_.add_command(list_assay)
list_.add_command(list_clinical)
list_.add_command(list_misc_data)
list_.add_command(list_shipments)
list_.add_command(list_supported)
remove_.add_command(remove_assay)
remove_.add_command(remove_clinical)
remove_.add_command(remove_shipment)
