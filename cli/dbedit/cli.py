import click

from . import __version__, core, remove, list

#### $ cidc admin list ####
@click.group("list")
def list_():
    """Listing different things"""
    pass


#### $ cidc admin list clinical ####
@click.command("clinical")
@click.argument("trial_id", required=True, type=str)
def list_clinical(trial_id: str):
    """
    List clinical files for a given trial

    TRIAL_ID is the id of the trial to affect
    """
    core.connect()
    list.list_clinical(trial_id=trial_id)


#### $ cidc admin list shipments ####
@click.command("shipments")
@click.argument("trial_id", required=True, type=str)
def list_shipments(trial_id: str):
    """
    List shipments for a given trial

    TRIAL_ID is the id of the trial to affect
    """
    core.connect()
    list.list_shipments(trial_id=trial_id)


#### $ cidc admin remove ####
@click.group("remove")
def remove_():
    """Deleting different things"""
    pass


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
    core.connect()
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
    core.connect()
    remove.remove_shipment(trial_id=trial_id, target_id=target_id)


list_.add_command(list_shipments)
remove_.add_command(remove_shipment)
