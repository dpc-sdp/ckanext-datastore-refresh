import datetime

import ckan.logic as logic
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import pytest
from ckan.plugins.toolkit import Invalid, ValidationError, url_for

from ckanext.datastore_refresh.model import DatasetRefresh as DatasetRefresh


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRefreshDatastoreDatasetCreate(object):
    frequency = "10"

    def create_test_data(self):
        dataset = factories.Dataset()
        sysadmin = factories.Sysadmin()
        sysadmin_obj = model.User.by_name(sysadmin["name"])

        return dataset, sysadmin_obj

    def test_refresh_datastore_dataset_create(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        results = helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )
        assert dataset["id"] in results["dataset_id"]
        assert self.frequency in results["frequency"]
        assert sysadmin_obj.id in results["created_user_id"]
        assert results["datastore_last_refreshed"] is None

    def test_refresh_datastore_dataset_create_no_frequency(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": ""}

        with pytest.raises(ValidationError):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_create",
                context={"auth_user_obj": sysadmin_obj},
                **data_dict,
            )

    def test_refresh_datastore_dataset_create_no_dataset_id(self):
        _, sysadmin_obj = self.create_test_data()
        data_dict = {"frequency": self.frequency}

        with pytest.raises(ValidationError):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_create",
                context={"auth_user_obj": sysadmin_obj},
                **data_dict,
            )

    def test_refresh_datastore_dataset_create_fake_dataset_id(self):
        _, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": "fakeid", "frequency": self.frequency}

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_create",
                context={"auth_user_obj": sysadmin_obj},
                **data_dict,
            )

    def test_refresh_datastore_dataset_create_empty_data_dict(self):
        _, sysadmin_obj = self.create_test_data()

        with pytest.raises(ValidationError):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_create",
                context={"auth_user_obj": sysadmin_obj},
                data_dict={},
            )

    def test_refresh_datastore_dataset_create_wrong_frequency(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": "10m"}

        with pytest.raises(ValidationError):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_create",
                context={"auth_user_obj": sysadmin_obj},
                **data_dict,
            )

    def test_refresh_datastore_dataset_create_anonymous(self):
        dataset, _ = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": "10"}

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_create",
                context={"auth_user_obj": "anonymous", "ignore_auth": False},
                **data_dict,
            )

    def test_refresh_datastore_dataset_create_normal_user(self):
        dataset, _ = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": "10"}
        normal_user = factories.User()
        normal_user_obj = model.User.by_name(normal_user["name"])

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_create",
                context={
                    "auth_user_obj": normal_user_obj,
                    "ignore_auth": False,
                },
                **data_dict,
            )


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRefreshDatastoreDatasetUpdate(object):
    frequency = "10"

    def create_test_data(self):
        dataset = factories.Dataset()
        sysadmin = factories.Sysadmin()
        sysadmin_obj = model.User.by_name(sysadmin["name"])

        return dataset, sysadmin_obj

    @pytest.mark.freez_time
    def test_refresh_datastore_dataset_update(self, freezer):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )
        rdd_obj = DatasetRefresh.get_by_package_id(data_dict["package_id"])
        assert rdd_obj.datastore_last_refreshed is None

        freezer.move_to(datetime.datetime.utcnow())
        helpers.call_action(
            "datastore_refresh_dataset_refresh_update",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )
        rdd_obj = DatasetRefresh.get_by_package_id(data_dict["package_id"])

        assert rdd_obj.datastore_last_refreshed == datetime.datetime.utcnow()

    def test_refresh_datastore_dataset_update_no_id(self):
        _, sysadmin_obj = self.create_test_data()
        data_dict = {"frequency": self.frequency}

        with pytest.raises(ValidationError):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_update",
                context={"auth_user_obj": sysadmin_obj},
                **data_dict,
            )

    def test_refresh_datastore_dataset_update_wrong_id(self):
        _, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": "worngid", "frequency": self.frequency}

        with pytest.raises(logic.NotFound):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_update",
                context={"auth_user_obj": sysadmin_obj},
                **data_dict,
            )

    def test_refresh_datastore_dataset_update_annonymous(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_update",
                context={"auth_user_obj": "anon_user", "ignore_auth": False},
                **data_dict,
            )

    def test_refresh_datastore_dataset_update_normal_user(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )

        normal_user = factories.User()
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_update",
                context={"auth_user_obj": normal_user, "ignore_auth": False},
                **data_dict,
            )


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRefreshDatastoreDatasetList(object):
    frequency = "10"

    def create_test_data(self):
        dataset = factories.Dataset()
        sysadmin = factories.Sysadmin()
        sysadmin_obj = model.User.by_name(sysadmin["name"])

        return dataset, sysadmin_obj

    def test_refresh_dataset_datastore_list(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )

        results = helpers.call_action(
            "datastore_refresh_dataset_refresh_list",
            context={"auth_user_obj": sysadmin_obj},
        )
        dataset_datastore_list = results["refresh_dataset_datastore"][0]

        assert dataset["id"] in dataset_datastore_list["dataset_id"]
        assert data_dict["frequency"] in dataset_datastore_list["frequency"]
        assert sysadmin_obj.id in dataset_datastore_list["created_user_id"]

    def test_refresh_dataset_datastore_list_no_dataset_datastore_created(self):
        _, sysadmin_obj = self.create_test_data()

        results = helpers.call_action(
            "datastore_refresh_dataset_refresh_list",
            context={"auth_user_obj": sysadmin_obj},
        )
        assert results == {"refresh_dataset_datastore": []}

    def test_refresh_dataset_datastore_list_anonymous(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_list",
                context={"auth_user_obj": "", "ignore_auth": False},
            )

    def test_refresh_dataset_datastore_list_normal_user(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )
        normal_user = factories.User()

        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_list",
                context={
                    "auth_user_obj": normal_user["name"],
                    "ignore_auth": False,
                },
            )


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRefreshDatastoreDatasetByFrequency(object):
    frequency = "10"

    def create_test_data(self):
        dataset = factories.Dataset()
        sysadmin = factories.Sysadmin()
        sysadmin_obj = model.User.by_name(sysadmin["name"])

        return dataset, sysadmin_obj

    def test_refresh_dataset_datastore_by_frequency(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )

        results = helpers.call_action(
            "datastore_refresh_dataset_refresh_list_by_frequency",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )
        refresh_dataset_datastore = results["refresh_dataset_datastore"][0]

        assert dataset["id"] in refresh_dataset_datastore["dataset_id"]
        assert data_dict["frequency"] in refresh_dataset_datastore["frequency"]
        assert sysadmin_obj.id in refresh_dataset_datastore["created_user_id"]
        assert bool(refresh_dataset_datastore["package"]) == True

    def test_refresh_dataset_datastore_by_frequency_no_frequency(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )

        with pytest.raises(ValidationError):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_list_by_frequency",
                context={"auth_user_obj": sysadmin_obj},
            )

    def test_refresh_dataset_datastore_by_frequency_wrong_frequency(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )

        with pytest.raises(ValidationError):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_list_by_frequency",
                context={"auth_user_obj": sysadmin_obj},
                frequency="36",
            )

    def test_refresh_dataset_datastore_by_frequency_anonymous(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_list_by_frequency",
                context={"auth_user_obj": "", "ignore_auth": False},
                frequency=data_dict["frequency"],
            )

    def test_refresh_dataset_datastore_by_frequency_normal_user(self):
        dataset, sysadmin_obj = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"auth_user_obj": sysadmin_obj},
            **data_dict,
        )
        normal_user = factories.User()
        with pytest.raises(logic.NotAuthorized):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_list_by_frequency",
                context={
                    "auth_user_obj": normal_user["name"],
                    "ignore_auth": False,
                },
                frequency=data_dict["frequency"],
            )


@pytest.mark.usefixtures("with_plugins", "clean_db")
class TestRefreshDatastoreDatasetDelete(object):
    frequency = "10"

    def create_test_data(self):
        dataset = factories.Dataset()
        sysadmin = factories.SysadminWithToken()

        return dataset, sysadmin

    def test_refresh_dataset_datastore_delete(self, app):
        dataset, sysadmin = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"user": sysadmin["name"]},
            **data_dict,
        )

        _list = helpers.call_action(
            "datastore_refresh_dataset_refresh_list",
            context={"user": sysadmin["name"]},
        )

        res = app.post(
            url_for("datastore_refresh.datastore_refresh_config"),
            data={"delete_config": _list["refresh_dataset_datastore"][0]["id"]},
            headers={"Authorization": sysadmin["token"]},
            status=200,
        )

        assert "Succesfully deleted configuration" in res

    def test_refresh_dataset_datastore_delete_anonymous(self, app):
        dataset, sysadmin = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"user": sysadmin["name"]},
            **data_dict,
        )

        _list = helpers.call_action(
            "datastore_refresh_dataset_refresh_list",
            context={"user": sysadmin["name"]},
        )
        _id = _list["refresh_dataset_datastore"][0]["id"]
        env = {"REMOTE_USER": "anonymous"}
        url = url_for("datastore_refresh.datastore_refresh_config")
        postparams = {"delete_config": _id}

        app.post(url, data=postparams, environ_overrides=env, status=403)

    def test_refresh_dataset_datastore_delete_normal_user(self, app):
        dataset, sysadmin = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"user": sysadmin["name"]},
            **data_dict,
        )

        _list = helpers.call_action(
            "datastore_refresh_dataset_refresh_list",
            context={"user": sysadmin["name"]},
        )
        normal_user = factories.User()
        _id = _list["refresh_dataset_datastore"][0]["id"]
        env = {"REMOTE_USER": str(normal_user["name"])}
        url = url_for("datastore_refresh.datastore_refresh_config")
        postparams = {"delete_config": _id}

        app.post(url, data=postparams, environ_overrides=env, status=403)

    def test_refresh_dataset_datastore_delete_wrong_id(self):
        dataset, sysadmin = self.create_test_data()
        data_dict = {"package_id": dataset["id"], "frequency": self.frequency}

        helpers.call_action(
            "datastore_refresh_dataset_refresh_create",
            context={"user": sysadmin["name"]},
            **data_dict,
        )

        with pytest.raises(ValidationError):
            helpers.call_action(
                "datastore_refresh_dataset_refresh_delete",
                context={"user": sysadmin["name"]},
                id="wrong_id",
            )
