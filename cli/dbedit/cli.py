import click

from . import __version__, core, remove, list

#### $ cidc admin list ####
@click.group("list")
def list_():
    """Listing different things"""
    pass


#### $ cidc admin list shipments ####
@click.command("shipments")
@click.argument("trial_id", required=True, type=str)
def list_shipments(trial_id: str):
    """Listing shipments for a given trial"""
    core.connect()
    list.list_shipments(trial_id=trial_id)


#### $ cidc admin remove ####
@click.group("remove")
def remove_():
    """Deleting different things"""
    pass


#### $ cidc admin remove shipment ####
@click.command("shipment")
@click.argument("trial_id", required=True, type=str)
@click.argument("target_id", required=True, type=str)
def remove_shipment(trial_id: str, target_id: str):
    """Deleting a given shipment from a given trial"""
    core.connect()
    remove.remove_shipment(trial_id=trial_id, target_id=target_id)


list_.add_command(list_shipments)
remove_.add_command(remove_shipment)
