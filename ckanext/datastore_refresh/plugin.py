import json
import logging

import requests

import ckan.plugins as plugins
import ckan.plugins.toolkit as tk
from ckan.views.api import API_DEFAULT_VERSION

import ckanext.xloader.interfaces as xloader_interfaces

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
    plugins.implements(plugins.IConfigDeclaration)
    plugins.implements(xloader_interfaces.IXloader, inherit=True)

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

    # IClick
    def get_commands(self):
        return cli.get_commands()

    # IBlueprint
    def get_blueprint(self):
        return view.get_blueprints()

    # IConfigDeclaration
    def declare_config_options(self, declaration, key):
        section = key.ckanext.datastore_refresh
        declaration.declare(section.cdn_purge_url).set_description(
            "CDN purge endpoint; empty disables purging. {path} is replaced with the API path."
        )
        declaration.declare(section.cdn_purge_method, "POST")
        declaration.declare(section.cdn_purge_headers).set_description(
            "JSON object of request headers; {path} is substituted in values."
        )
        declaration.declare(section.cdn_purge_body)

    # IXLoader
    def after_upload(self, context, resource_dict, dataset_dict):
        try:
            tk.get_action("datastore_refresh_dataset_refresh_update")(
                context, {"package_id": dataset_dict.get("id")}
            )
        except tk.ObjectNotFound:
            # Dataset has no refresh schedule.
            pass
        except Exception:
            log.exception("Failed to update refresh record for %s", dataset_dict.get("id"))
        _purge_cdn_cache(resource_dict["id"])


def _purge_cdn_cache(resource_id):
    url = tk.config.get("ckanext.datastore_refresh.cdn_purge_url")
    if not url:
        return
    method = tk.config.get("ckanext.datastore_refresh.cdn_purge_method") or "POST"
    body = tk.config.get("ckanext.datastore_refresh.cdn_purge_body") or None
    try:
        headers = json.loads(tk.config.get("ckanext.datastore_refresh.cdn_purge_headers") or "{}")
    except ValueError:
        log.error("ckanext.datastore_refresh.cdn_purge_headers is not valid JSON")
        return

    for path in (
        f"/api/action/datastore_search?id={resource_id}",
        f"/api/{API_DEFAULT_VERSION}/action/datastore_search?id={resource_id}",
    ):
        try:
            response = requests.request(
                method,
                url.replace("{path}", path),
                headers={k: str(v).replace("{path}", path) for k, v in headers.items()},
                data=body.replace("{path}", path) if body else None,
                timeout=10,
            )
        except Exception as e:
            log.error("CDN purge failed for %s: %s", path, e)
            continue
        if response.ok:
            log.info("CDN purge %s for %s", response.status_code, path)
        else:
            log.error("CDN purge failed for %s: %s %s", path, response.status_code, response.text[:200])
