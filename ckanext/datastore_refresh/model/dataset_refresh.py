from __future__ import annotations

import datetime
from typing import Iterable, Optional

from typing_extensions import Self

import ckan.model as model
import ckan.plugins.toolkit as tk
from ckan.lib.dictization import table_dictize
from ckan.model.types import make_uuid
from sqlalchemy import Column, ForeignKey, UnicodeText, DateTime, orm


refresh_dataset_datastore_table = None


class DatasetRefresh(tk.BaseModel):
    __tablename__ = "datastore_refresh_dataset_refresh"
    id = Column(UnicodeText, primary_key=True, default=make_uuid)
    dataset_id = Column(
        UnicodeText,
        ForeignKey(model.Package.id),
        nullable=False,
    )
    frequency = Column(UnicodeText, nullable=False)
    created_user_id = Column(
        UnicodeText,
        ForeignKey("user.id"),
        nullable=False,
    )
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
    )
    datastore_last_refreshed = Column(DateTime, nullable=True)

    dataset = orm.relationship(
        model.Package,
        backref=orm.backref(
            "refresh_dataset_datastores", cascade="all, delete-orphan"
        ),
    )

    def save(self):
        model.Session.add(self)
        model.Session.commit()

    @classmethod
    def get(cls, id: str) -> Optional[Self]:
        return model.Session.query(cls).get(id)

    @classmethod
    def delete(cls, id):
        obj = model.Session.query(cls).get(id)
        if obj:
            model.Session.delete(obj)
            model.Session.commit()

    @classmethod
    def get_all(cls) -> Iterable[Self]:
        query = model.Session.query(cls)

        return query

    @classmethod
    def get_by_frequency(cls, frequency: str) -> Iterable[Self]:
        query = model.Session.query(cls).filter(cls.frequency == frequency)

        return query

    @classmethod
    def get_by_package_id(cls, package_id: str) -> Optional[Self]:
        query = model.Session.query(cls).filter(cls.dataset_id == package_id)
        return query.first()

    def dictize(self, context):
        return table_dictize(self, context)

    @classmethod
    def dictize_collection(cls, pairs: Iterable[Self], context):
        """Returns model objects as a dictionary
        :param results: list of model objects: RefreshDatasetDatastore, Package
        :type results: list
        """
        model = context["model"]
        include_package = context.get("dataset_refresh_include_package", False)

        result = []

        for item in pairs:
            dictized = item.dictize(context.copy())
            result.append(dictized)
            if include_package:
                dictized["package"] = table_dictize(
                    item.dataset, {"model": model}
                )

        return result

    def touch(self):
        self.datastore_last_refreshed = datetime.datetime.utcnow()
