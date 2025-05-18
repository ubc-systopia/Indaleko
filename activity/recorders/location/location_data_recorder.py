"""
This module defines a common base for location data collectors.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import math
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from textwrap import dedent

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.base import CollectorBase
from activity.data_model.activity import IndalekoActivityDataModel
from activity.recorders.base import RecorderBase
from activity.semantic_attributes import KnownSemanticAttributes
from data_models.location_data_model import BaseLocationDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db import IndalekoCollection
from db.utils.query_performance import timed_aql_execute
from utils.misc.data_management import encode_binary_data


# pylint: enable=wrong-import-position


class BaseLocationDataRecorder(RecorderBase):
    """
    Common base class for location data recorders.

    This class provides a common base for location data collectors. Typically a
    location data _collector_ will be associated with a location data
    _provider_.  The latter is responsible for actually collecting the data, and
    the former is responsible for interpreting the data and storing it in the
    database.
    """

    default_min_movement_change_required = 500  # meters
    default_max_time_between_updates = 360  # seconds = 10 min

    def __init__(self, **kwargs: dict) -> None:
        """Initialize the base location data collector."""
        self.min_movement_change_required = kwargs.get(
            "min_movement_change_required",
            self.default_min_movement_change_required,
        )
        self.max_time_between_updates = kwargs.get(
            "max_time_between_updates",
            self.default_max_time_between_updates,
        )
        self.provider = kwargs.get("provider")
        if self.provider is not None and not isinstance(self.provider, CollectorBase):
            raise TypeError(f"provider is not a CollectorBase {type(self.provider)}")
        if not hasattr(self, "collection"):
            self.collection = kwargs.get("collection")

    @staticmethod
    def compute_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Compute the distance between two points.

        Input:
            lat1: the latitude of the first point
            lon1: the longitude of the first point
            lat2: the latitude of the second point
            lon2: the longitude of the second point

        Output:
            The distance between the two points in **meters**.

        Note: this is a simple implementation of the Haversine formula.
        """
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        lon1_rad = math.radians(lon1)
        lon2_rad = math.radians(lon2)

        delta_lat = lat2_rad - lat1_rad
        delta_lon = lon2_rad - lon1_rad

        a = math.sin(delta_lat / 2) ** 2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = 6371 * 1000 * c  # in meters
        ic(distance)
        return distance

    @staticmethod
    def compute_time_difference(
        time1: datetime | str,
        time2: datetime | str,
    ) -> float:
        """
        Compute the time difference between two times.

        Input:
            time1: the first time
            time2: the second time

        Output:
            The time difference in **seconds**.

        Note: this is a simple implementation of the time difference.
        """
        if not (isinstance(time1, (datetime, str))):
            raise TypeError("time1 is not a datetime or string")
        if not (isinstance(time2, (datetime, str))):
            raise TypeError("time2 is not a datetime or string")
        if isinstance(time2, str):
            time2 = datetime.fromisoformat(time2)
        delta = time2 - time1
        return delta.total_seconds()

    def has_data_changed(
        self,
        data1: BaseLocationDataModel,
        data2: BaseLocationDataModel,
    ) -> bool:
        """Check if the data has changed materially.

        Input:
            data1: the first data object
            data2: the second data object

        Output:
            True if the data has changed, False otherwise.

        Note: "changed" here means that the variation is more than the
        minimum allowed, based upon location (longitude, latitude) and time.
        """
        if data1 is None or data2 is None:
            return True
        if not isinstance(data1, BaseLocationDataModel):
            raise TypeError(f"data1 is not a BaseLocationDataModel {type(data1)}")
        if not isinstance(data2, BaseLocationDataModel):
            raise TypeError(f"data2 is not a BaseLocationDataModel {type(data2)}")
        distance = BaseLocationDataRecorder.compute_distance(
            data1.Location.latitude,
            data1.Location.longitude,
            data2.Location.latitude,
            data2.Location.longitude,
        )
        time_delta = BaseLocationDataRecorder.compute_time_difference(
            data1.Location.timestamp,
            data2.Location.timestamp,
        )
        return distance > self.min_movement_change_required or time_delta > self.max_time_between_updates

    @staticmethod
    def get_latest_db_update_dict(collection: IndalekoCollection) -> dict | None:
        """
        Get the latest update from the database.

        Input:
            collection: the collection from which to retrieve the latest update.

        Output:
            The latest update from the database, or None if no update is
            available.

        Note: this implementation assumes the timestamp field(s) are indexed.
        Collection names are passed via bind variables to allow names with
        special characters (e.g., the UUID we use).
        """
        if not isinstance(collection, IndalekoCollection):
            raise TypeError(f"collection is not an IndalekoCollection {type(collection)}")
        query = """
            FOR doc IN @@collection
                SORT doc.timestamp DESC
                LIMIT 1
                RETURN doc
        """
        bind_vars = {"@collection": collection.name}
        results = timed_aql_execute(query, bind_vars=bind_vars)
        entries = list(results)
        if len(entries) > 1:
            raise ValueError(f"Expected 1 result, received {len(entries)}")
        if len(entries) == 0:
            ic("No entries found")
            return None
        return entries[0]

    @staticmethod
    def build_location_activity_document(
        source_data: IndalekoSourceIdentifierDataModel | dict,
        location_data: BaseLocationDataModel | dict,
        semantic_attributes: list[IndalekoSemanticAttributeDataModel],
    ) -> dict:
        """
        Build the location activity document for the database.

        This builds a dictionary that can be used to generate the json
        required to insert the record into the database.

        Input:
            source_data: the source of this data.
            location_data: the location data.  Note that this is treated as
            transparent information and is simply stored in the database.

            semantic_attributes: the semantic attributes associated with the
            location data.  Note that this can be any combination of known and
            unknown semantic attributes.  These are indexed.

        Output:
            A dictionary that can be used to generate the json required to
            insert the record into the database.
        """
        if not isinstance(source_data, (IndalekoSourceIdentifierDataModel, dict)):
            raise TypeError(
                (f"source_data is not an IndalekoSourceIdentifierDataModel or dict {type(source_data)}"),
            )
        if not (isinstance(location_data, (BaseLocationDataModel, dict))):
            raise TypeError(
                f"location_data is not a BaseLocationDataModel or dict {type(location_data)}",
            )
        if not isinstance(semantic_attributes, list):
            raise TypeError(f"semantic_attributes is not a List {type(semantic_attributes)}")
        if isinstance(location_data, BaseLocationDataModel):
            location_data = json.loads(location_data.model_dump_json())
        if len(semantic_attributes) <= 0:
            raise ValueError("No semantic attributes provided")
        timestamp = location_data["Location"]["timestamp"]
        ic(location_data)
        record = IndalekoRecordDataModel(
            SourceIdentifier=source_data,
            Timestamp=timestamp,
            Data=encode_binary_data(location_data),
        )
        ic(record)
        activity_data_args = {
            "Record": IndalekoRecordDataModel(
                SourceIdentifier=source_data,
                Timestamp=timestamp,
                Data=encode_binary_data(location_data),
            ),
            "Timestamp": timestamp,
            "SemanticAttributes": semantic_attributes,
        }
        ic(activity_data_args)
        activity_data = IndalekoActivityDataModel(**activity_data_args)
        return json.loads(
            activity_data.model_dump_json(exclude_none=True, exclude_unset=True),
        )

    def retrieve_temporal_data(
        self,
        reference_time: datetime,
        prior_time_window: timedelta,
        subsequent_time_window: timedelta,
        max_entries: int = 0,
    ) -> list[dict] | None:
        """
        Retrieve temporal data from the data provider.

        This call retrieves temporal data available to the data provider within
        the specified time window.

        Args:
            reference_time (datetime): The reference time for the
            query.
            prior_time_window (timedelta): The time window before the
            reference time.
            subsequent_time_window (timedelta): The time window after
            the reference time.
            max_entries (int): The maximum number of entries to return.  If 0,
            then all entries are returned.

        Returns:
            List[Dict]: The data available within the specified time window.
        """
        raise NotImplementedError("retrieve_temporal_data is not implemented")

    # Note: the following methods map to the abstract methods in the
    # CollectorBase.  Since many of them involve interacting with the database,
    # we can interact with the provider to interpret and handle the data, while
    # we handle the database interactions.
    def get_provider_characteristics(
        self,
    ) -> list[ActivityDataCharacteristics] | None:
        """
        Get the characteristics of the data provider.

        This call returns the characteristics of the data provider.  This is
        intended to be used to help users understand the data provider and to
        help the system understand how to interact with the data provider.

        Returns:
            Dict: A dictionary containing the characteristics of the provider.
        """
        if hasattr(self, "provider"):
            if not isinstance(self.provider, CollectorBase):
                raise TypeError(f"provider is not a CollectorBase {type(self.provider)}")
            return self.provider.get_collector_characteristics()
        return None

    def get_provider_semantic_attributes(self) -> list[str] | None:
        """
        Get the semantic attributes supported by the data provider.

        This call returns the semantic attributes that the provider
        supports/uses.  It is used in prompt construction, so if you do not
        declare a semantic attribute, it will not be available for use in the
        query interface.

        Returns:
            List[str]: A list of the semantic attributes that the provider
            supports. Note that these are UUIDs, not the symbolic names.
            None: If no semantic attributes are available.

        Note:
            Given that this is in the _base class_ it defines the minimal set of
            attributes that are expected by all location data providers.  It can
            be overridden by subclasses to provide additional attributes.
        """
        return [
            KnownSemanticAttributes.ACTIVITY_DATA_LOCATION_LATITUDE,  # pylint: disable=no-member
            KnownSemanticAttributes.ACTIVITY_DATA_LOCATION_LONGITUDE,  # pylint: disable=no-member
            KnownSemanticAttributes.ACTIVITY_DATA_LOCATION_ACCURACY,  # pylint: disable=no-member
        ]

    def get_provider_name(self) -> str | None:
        """
        Get the name of the provider.

        Returns:
                str: The name of the provider
        """
        if hasattr(self, "provider"):
            if not isinstance(self.provider, CollectorBase):
                raise TypeError(f"provider is not a CollectorBase {type(self.provider)}")
            return self.provider.get_collectorr_name()
        return None

    def get_provider_id(self) -> uuid.UUID | None:
        """Get the UUID for the provider."""
        if hasattr(self, "provider"):
            if not isinstance(self.provider, CollectorBase):
                raise TypeError(f"provider is not an CollectorBase {type(self.provider)}")
            return self.provider.get_provider_id()
        return None

    def retrieve_data(self, data_id: uuid.UUID) -> dict | None:
        """
        This call retrieves the data associated with the provided data_id.

        Args:
            data_id (uuid.UUID): The UUID that represents the data to be
            retrieved.

        Returns:
            Dict: The data associated with the data_id.

        Note: this API may change (e.g., so that it includes both the activity
        context value as well as the provider value.)
        """
        if hasattr(self, "provider"):
            if not isinstance(self.provider, CollectorBase):
                raise TypeError(f"provider is not an CollectorBase {type(self.provider)}")
            return self.provider.retrieve_data(data_id)
        return None

    def cache_duration(self) -> timedelta | None:
        """Retrieve the maximum cache duration."""
        if hasattr(self, "provider"):
            if not isinstance(self.provider, CollectorBase):
                raise TypeError(f"provider is not an CollectorBase {type(self.provider)}")
            return self.provider.cache_duration()
        return None

    def get_description(self) -> str | None:
        """
        Retrieve a description of the data provider.

        Note: this is used for
        prompt construction, so please be concise and specific in your
        description.

        Returns:
            str: The description of the data provider.
            None: If no description is available.
        """
        provider_description = ""
        if hasattr(self, "provider"):
            if not isinstance(self.provider, CollectorBase):
                raise TypeError(f"provider is not an CollectorBase {type(self.provider)}")
            provider_description += self.provider.get_description()
        semantic_attributes = "\n"
        for semantic_attribute in self.get_provider_semantic_attributes():
            semantic_attributes += dedent(
                f"""\n
                {KnownSemanticAttributes.get_attribute_by_uuid(semantic_attribute)} :
                {semantic_attribute}""",
            )
        if not hasattr(self, "collection"):
            raise ValueError("collection is not set")
        provider_description += f"""\n
            It stores its data inside the
            {self.collection.name} collection. It exports semantic
            attributes with the following labels and UUIDs:
            {semantic_attributes}.
            The schema for the data in this collection is:
            {self.provider.get_json_schema()}.
            The "SemanticAttributes" field is indexed.
        """
        return provider_description

    def get_json_schema(self) -> dict | None:
        """
        Retrieve the JSON data schema to use for the database.

        Returns:
            dict: The JSON schema for the data provider.
            None: If no schema is available.
        """
        if hasattr(self, "provider"):
            if not isinstance(self.provider, CollectorBase):
                raise TypeError(f"provider is not an CollectorBase {type(self.provider)}")
            return self.provider.get_json_schema()
        return None

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID | None:
        """
        Retrieve the current cursor for this data provider.

        Input:
            activity_context: the UUID representing the activity context to
            which this cursor is being mapped.

        Output:
            The cursor for this data provider, which can be used to retrieve
            data from this provider (via the retrieve_data call).

        Returns:
            uuid.UUID: The cursor for the data provider.
            None: If no cursor is available.
        """
        if hasattr(self, "provider"):
            if not isinstance(self.provider, CollectorBase):
                raise TypeError(f"provider is not an CollectorBase {type(self.provider)}")
            return self.provider.get_cursor(activity_context)
        return None
