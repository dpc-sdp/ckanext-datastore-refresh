from unittest import mock

import ckan.model as model
import ckan.plugins as plugins
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import pytest
import requests
from ckan.views.api import API_DEFAULT_VERSION

QUANT_HEADERS = (
    '{"Quant-Token": "secret", "Quant-Customer": "org", '
    '"Quant-Project": "proj", "Quant-Url": "{path}"}'
)


def _upload(dataset, resource):
    plugin = plugins.get_plugin("datastore_refresh")
    plugin.after_upload({"ignore_auth": True}, resource, dataset)


def _refresh_record(dataset):
    sysadmin = model.User.by_name(factories.Sysadmin()["name"])
    helpers.call_action(
        "datastore_refresh_dataset_refresh_create",
        context={"auth_user_obj": sysadmin},
        package_id=dataset["id"],
        frequency="10",
    )


def _last_refreshed(dataset):
    records = helpers.call_action("datastore_refresh_dataset_refresh_list")
    return records["refresh_dataset_datastore"][0]["datastore_last_refreshed"]


@pytest.mark.usefixtures("with_plugins", "clean_db")
@mock.patch("ckanext.datastore_refresh.plugin.requests.request")
class TestAfterUpload(object):
    @pytest.mark.ckan_config(
        "ckanext.datastore_refresh.cdn_purge_url", "https://api.quantcdn.io/v1/purge"
    )
    @pytest.mark.ckan_config("ckanext.datastore_refresh.cdn_purge_headers", QUANT_HEADERS)
    def test_quant_purge_per_path(self, request):
        request.return_value.ok = True
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"])

        _upload(dataset, resource)

        paths = [
            f"/api/action/datastore_search?id={resource['id']}",
            f"/api/{API_DEFAULT_VERSION}/action/datastore_search?id={resource['id']}",
        ]
        assert request.call_args_list == [
            mock.call(
                "POST",
                "https://api.quantcdn.io/v1/purge",
                headers={
                    "Quant-Token": "secret",
                    "Quant-Customer": "org",
                    "Quant-Project": "proj",
                    "Quant-Url": path,
                },
                data=None,
                timeout=10,
            )
            for path in paths
        ]

    @pytest.mark.ckan_config("ckanext.datastore_refresh.cdn_purge_url", "https://cdn.test/purge{path}")
    @pytest.mark.ckan_config("ckanext.datastore_refresh.cdn_purge_method", "PURGE")
    @pytest.mark.ckan_config("ckanext.datastore_refresh.cdn_purge_body", '{"url": "{path}"}')
    def test_path_in_url_and_body(self, request):
        request.return_value.ok = True
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"])

        _upload(dataset, resource)

        path = f"/api/action/datastore_search?id={resource['id']}"
        assert request.call_args_list[0] == mock.call(
            "PURGE",
            f"https://cdn.test/purge{path}",
            headers={},
            data=f'{{"url": "{path}"}}',
            timeout=10,
        )

    @pytest.mark.ckan_config("ckanext.datastore_refresh.cdn_purge_url", "")
    def test_no_url_skips_purge_but_updates_record(self, request):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"])
        _refresh_record(dataset)
        assert _last_refreshed(dataset) is None

        _upload(dataset, resource)

        request.assert_not_called()
        assert _last_refreshed(dataset) is not None

    @pytest.mark.ckan_config(
        "ckanext.datastore_refresh.cdn_purge_url", "https://api.quantcdn.io/v1/purge"
    )
    def test_failing_purge_does_not_raise(self, request):
        request.side_effect = requests.ConnectionError("boom")
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"])
        _refresh_record(dataset)

        _upload(dataset, resource)

        assert request.call_count == 2
        assert _last_refreshed(dataset) is not None

    @pytest.mark.ckan_config(
        "ckanext.datastore_refresh.cdn_purge_url", "https://api.quantcdn.io/v1/purge"
    )
    def test_error_response_does_not_raise(self, request):
        request.return_value.ok = False
        request.return_value.status_code = 403
        request.return_value.text = "forbidden"
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset["id"])

        _upload(dataset, resource)

        assert request.call_count == 2
