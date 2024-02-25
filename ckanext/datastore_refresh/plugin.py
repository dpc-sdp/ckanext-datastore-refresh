from __future__ import annotations

import logging

import requests

from typing import Any

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.views.api import API_DEFAULT_VERSION

try:
    import ckanext.xloader.interfaces as loader_interfaces

    use_xloader = True
except ImportError:
    import ckanext.datapusher.interfaces as loader_interfaces

    use_xloader = False

from . import cli, helpers, view
from .logic import auth, action


log = logging.getLogger(__name__)


class DatastoreRefreshPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.IClick)
    plugins.implements(plugins.IBlueprint)

    if use_xloader:
        plugins.implements(loader_interfaces.IXloader, inherit=True)
    else:
        plugins.implements(loader_interfaces.IDataPusher, inherit=True)

    # ITemplateHelpers
    def get_helpers(self):
        return helpers.get_helpers()

    # IActions
    def get_actions(self):
        return action.get_actions()

    # IAuthFunctions
    def get_auth_functions(self):
        return auth.get_auth_functions()

    # IConfigurer
    def update_config(self, config_):
        tk.add_template_directory(config_, "templates")
        tk.add_public_directory(config_, "public")

        # Add a new ckan-admin tabs for our extension
        tk.add_ckan_admin_tab(
            tk.config,
            "datastore_refresh.datastore_refresh_config",
            "Datastore refresh",
            config_var="ckan.admin_tabs",
        )

    # IClick
    def get_commands(self):
        return cli.get_commands()

    # IBlueprint
    def get_blueprint(self):
        return view.get_blueprints()

    if use_xloader:
        # IXLoader
        def after_upload(
            self,
            context: dict[str, Any],
            resource_dict: dict[str, Any],
            dataset_dict: dict[str, Any],
        ) -> None:
            _purge_section_cache(context, resource_dict, dataset_dict)

    else:
        # IDataPusher
        def after_upload(
            self,
            context: dict[str, Any],
            resource_dict: dict[str, Any],
            dataset_dict: dict[str, Any],
        ) -> None:
            _purge_section_cache(context, resource_dict, dataset_dict)


def _purge_section_cache(context, resource_dict, dataset_dict):
    cache_ban_url = tk.config.get("ckanext.datastore_refresh.cache_ban_url")
    if not cache_ban_url:
        return
    try:
        rdd = tk.get_action("datastore_refresh_dataset_refresh_update")(
            context, {"package_id": dataset_dict.get("id")}
        )
    except Exception as ex:
        log.error(ex)
        return

    cache_user = tk.config.get("ckanext.datastore_refresh.cache_user")
    cache_pass = tk.config.get("ckanext.datastore_refresh.cache_pass")
    cache_account_id = tk.config.get(
        "ckanext.datastore_refresh.cache_account_id"
    )
    cache_application_id = tk.config.get(
        "ckanext.datastore_refresh.cache_application_id"
    )
    cache_environment_id = tk.config.get(
        "ckanext.datastore_refresh.cache_environment_id"
    )

    cache_url = (
        f"{cache_ban_url}/account/{cache_account_id}/application/{cache_application_id}/environment/{cache_environment_id}/proxy/varnish/state?banExpression=req.url ~ "
    )
    auth = (cache_user, cache_pass)
    headers = {"Content-Type": "application/json"}

    # There could be two api paths to clear. One with api version and one with out
    api_noversion_endpoint = (
        f"/api/action/datastore_search?id={resource_dict.get('id')}"
    )
    api_default_version_endpoint = f"/api/{API_DEFAULT_VERSION}/action/datastore_search?id={resource_dict.get('id')}"
    api_endpoints = [
        api_noversion_endpoint,
        api_default_version_endpoint,
    ]

    for api_endpoint in api_endpoints:
        url = f"{cache_url}{api_endpoint}"
        # Ping CDN to purge/clear cache
        try:
            response = requests.post(url, auth=auth, headers=headers)
        except Exception as ex:
            log.error(ex)
            continue

        if response.ok:
            log.info(f"Successfully purged cache for api {api_endpoint}")
        else:
            log.error(
                f"Failed to purged cache for api {api_endpoint}:"
                f" {response.reason}"
            )
