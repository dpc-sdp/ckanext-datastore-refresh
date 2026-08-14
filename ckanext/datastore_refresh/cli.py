# -*- coding: utf-8 -*-

import logging

import ckan.plugins.toolkit as tk
import click
from ckanext.datapusher_plus import config as datapusher_plus_config


log = logging.getLogger(__name__)


def get_commands():
    return [datastore_refresh]


@click.group(short_help="Manage datastore-refresh commands")
def datastore_refresh():
    """Manage datastore-refresh commands"""
    pass


@datastore_refresh.command()
@click.argument("frequency")
def dataset(frequency):
    """
    Refresh the datastore for a dataset
    """
    click.echo(f"Starting refresh_dataset_datastore for frequency {frequency}")
    if not frequency:
        tk.error_shout("Please provide frequency")

    site_user = tk.get_action("get_site_user")({"ignore_auth": True}, {})
    context = {"user": site_user.get("name")}

    try:
        datasets = tk.get_action(
            "datastore_refresh_dataset_refresh_list_by_frequency"
        )(context, {"frequency": frequency})
    except tk.ValidationError as e:
        tk.error_shout(e)
        raise click.Abort()

    if not datasets:
        click.secho("No datasets with this criteria", fg="yellow")
        return []

    for dataset in datasets["refresh_dataset_datastore"]:
        pkg_id = dataset["package"]["id"]
        pkg_dict = tk.get_action("package_show")(context, {"id": pkg_id})
        click.echo(
            f'Processing dataset {pkg_dict["name"]} with'
            f' {len(pkg_dict["resources"])} resources'
        )

        for res in pkg_dict["resources"]:
            try:
                _submit_resource(pkg_dict, res, context)
            except Exception as e:
                click.secho(e, fg="red")
                click.secho(f'ERROR submitting resource {res["id"]}', fg="red")
                continue

    click.echo(f"Finished refresh_dataset_datastore for frequency {frequency}")


def _submit_resource(dataset, resource, context):
    """resource: resource dictionary"""
    can_submit = _is_datapusher_plus_format(resource.get("format"))

    if not can_submit:
        click.echo(
            f'Skipping resource {resource["id"]} because format'
            f' "{resource.get("format")}" is not configured to be loadered'
        )
        return
    if resource["url_type"] in ("datapusher", "xloader"):
        click.echo(
            f'Skipping resource {resource["id"]} because url_type'
            f' "{resource["url_type"]}" means resource.url points to the'
            " datastore already, so loading would be circular."
        )
        return

    click.echo(
        f'Submitting /dataset/{dataset["name"]}/resource/{resource["id"]}\n'
        f'url={resource["url"]}\n'
        f'format={resource.get("format")}'
    )
    data_dict = {
        "resource_id": resource["id"],
        "ignore_hash": False,
    }

    success = tk.get_action("datapusher_submit")(context, data_dict)
    if success:
        click.secho("...ok", fg="green")
        tk.get_action("datastore_refresh_dataset_refresh_update")(
            {"ignore_auth": True},
            {"package_id": dataset["id"]}
        )
    else:
        tk.error_shout("ERROR submitting resource")


def _is_datapusher_plus_format(resource_format):
    """Return true when DataPusher+ is configured to process this format."""
    supported_formats = tk.config.get("ckan.datapusher.formats", "") or tk.config.get(
        "ckanext.datapusher_plus.formats", ""
    )
    if not supported_formats:
        supported_formats = datapusher_plus_config.FORMATS
    if isinstance(supported_formats, str):
        supported_formats = supported_formats.split()

    return bool(
        resource_format
        and resource_format.lower() in [fmt.lower() for fmt in supported_formats]
    )


@datastore_refresh.command()
def available_choices():
    """Shows available choices"""
    frequency_options = []
    data = tk.h.datastore_refresh_get_frequency_options()

    for row in data:
        if row["value"] != "0":
            frequency_options.append(row["value"])
    click.secho(f"Available choices: {frequency_options}", fg="green")
