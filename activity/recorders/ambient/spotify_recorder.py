"""
This module defines a utility for acquiring Spotify data and
recording it in the database.

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
import os
import sys
import uuid

from datetime import datetime, timedelta
from typing import Any

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from activity.collectors.ambient.music.spotify import SpotifyMusicCollector
from activity.collectors.ambient.music.spotify_data_model import SpotifyAmbientData
from activity.collectors.base import CollectorBase
from activity.collectors.known_semantic_attributes import KnownSemanticAttributes
from activity.data_model.activity import IndalekoActivityDataModel
from activity.recorders.base import RecorderBase

# from activity.registration import IndalekoActivityDataRegistration
from activity.recorders.registration_service import (
    IndalekoActivityDataRegistrationService,
)
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db import IndalekoCollection, IndalekoDBConfig


class SpotifyRecorder(RecorderBase):
    """This module defines a utility for acquiring Spotify data and
    recording it in the database.
    """

    source_data = {
        "Identifier": uuid.UUID("6ea66ced-5a54-4cba-a421-50d5671021cb"),
        "Version": "1.0.0",
        "Description": "Spotify Ambient Music Recorder",
    }

    semantic_attributes_supported = {
        KnownSemanticAttributes.ACTIVITY_DATA_AMBIENT_SPOTIFY_TRACK_NAME: "track_name",
        KnownSemanticAttributes.ACTIVITY_DATA_AMBIENT_SPOTIFY_ARTIST_NAME: "artist_name",
        KnownSemanticAttributes.ACTIVITY_DATA_AMBIENT_SPOTIFY_ALBUM_NAME: "album_name",
        KnownSemanticAttributes.ACTIVITY_DATA_AMBIENT_SPOTIFY_TRACK_DURATION: "track_duration_ms",
        KnownSemanticAttributes.ACTIVITY_DATA_AMBIENT_SPOTIFY_DEVICE_TYPE: "device_type",
    }

    def __init__(self, **kwargs):

        # Boilerplate code. Referenced from windows_gps_location.py recorder. Perhaps future refactoring can be done to reduce duplicate code
        self.db_config = IndalekoDBConfig()
        assert self.db_config is not None, "Failed to get the database configuration"
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=self.source_data["Identifier"],
            Version=self.source_data["Version"],
            Description=self.source_data["Description"],
        )
        record_kwargs = {
            "Identifier": str(self.source_data["Identifier"]),
            "Version": self.source_data["Version"],
            "Description": self.source_data["Description"],
            "Record": IndalekoRecordDataModel(
                SourceIdentifier=source_identifier,
                Timestamp=datetime.now(),
                Attributes={},
                Data="",
            ),
        }
        self.provider_registrar = IndalekoActivityDataRegistrationService()
        assert self.provider_registrar is not None, "Failed to get the provider registrar"
        collector_data = self.provider_registrar.lookup_provider_by_identifier(
            str(self.source_data["Identifier"]),
        )
        if collector_data is None:
            ic("Registering the provider")
            collector_data, collection = self.provider_registrar.register_provider(
                **record_kwargs,
            )
        else:
            ic("Provider already registered")
            collection = IndalekoActivityDataRegistrationService.lookup_activity_provider_collection(
                str(self.source_data["Identifier"]),
            )

        ic(collector_data)
        ic(collection)
        self.collector_data = collector_data

        self.collector = SpotifyMusicCollector()
        self.collection = collection

    def get_recorder_characteristics(self) -> list:
        return self.collector.get_collector_characteristics()

    def get_recorder_name(self) -> str:
        return "spotify_recorder"

    def get_collector_class_model(self) -> dict[str, type]:
        return {"SpotifyAmbientData": SpotifyAmbientData}

    def get_recorder_id(self) -> uuid.UUID:
        return self.source_data["Identifier"]

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """
        Retrieve the current cursor for this data provider

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
        # Same implementation in location_data_recorder
        if hasattr(self, "provider"):
            assert isinstance(
                self.provider,
                CollectorBase,
            ), f"provider is not an CollectorBase {type(self.provider)}"
            return self.provider.get_cursor(activity_context)
        return None

    def cache_duration(self) -> timedelta | None:
        """
        Retrieve the maximum duration that data from this provider may be
        cached.
        """
        # Same implementation in location_data_recorder
        if hasattr(self, "provider"):
            assert isinstance(
                self.provider,
                CollectorBase,
            ), f"provider is not an CollectorBase {type(self.provider)}"
            return self.provider.cache_duration()
        return None

    def get_description(self) -> str:
        return self.source_data["Description"]

    def get_json_schema(self) -> dict:
        """
        Retrieve the JSON data schema to use for the database.

        Returns:
            dict: The JSON schema for the data provider.
            None: If no schema is available.
        """
        # Same implementation in location_data_recorder
        if hasattr(self, "provider"):
            assert isinstance(
                self.provider,
                CollectorBase,
            ), f"provider is not an CollectorBase {type(self.provider)}"
            return self.provider.get_json_schema()
        return None

    def process_data(self, data: Any) -> dict[str, Any]:
        return data

    def store_data(self, current_data: dict[str, Any]) -> None:

        if current_data is None:
            ic("No active Spotify music is playing")
            doc = self.build_spotify_activity_document(
                spotify_data=None,
                semantic_attributes=[],
            )

        else:
            assert isinstance(
                current_data,
                SpotifyAmbientData,
            ), "current_data is not a SpotifyAmbientData"

            latest_db_data = self.get_latest_db_update()
            if not self.has_data_changed(latest_db_data, current_data):
                ic("Data has not changed, return last DB record")
                return ic(latest_db_data)

            semantic_attributes = []
            for key, value in self.semantic_attributes_supported.items():
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=key,
                            Version="1",
                            Description=value,
                        ),
                        Data=getattr(current_data, value),
                    ),
                )

            # Build activity document
            doc = self.build_spotify_activity_document(
                spotify_data=current_data,
                semantic_attributes=semantic_attributes,
            )

        # Insert document into collection
        self.collection.insert(doc)
        return ic(current_data)

    def get_latest_db_update(self) -> SpotifyAmbientData:
        assert isinstance(
            self.collection,
            IndalekoCollection,
        ), f"collection is not an IndalekoCollection {type(self.collection)}"

        query = """
            FOR doc IN @@collection
                SORT doc.Timestamp DESC
                LIMIT 1
                RETURN doc
        """
        bind_vars = {"@collection": self.collection.name}
        results = IndalekoDBConfig()._arangodb.aql.execute(query, bind_vars=bind_vars)
        entries = [entry for entry in results]
        if len(entries) == 0:
            return None
        assert len(entries) == 1, f"Too many results {len(entries)}"
        doc = entries[0]
        if len(doc["SemanticAttributes"]) == 0:
            return None
        current_data = Indaleko.decode_binary_data(doc["Record"]["Data"])
        current_data["Record"] = doc["Record"]
        current_data["SemanticAttributes"] = doc["SemanticAttributes"]
        current_data["source"] = "spotify"
        ic(current_data)
        return SpotifyAmbientData(**current_data)

    def has_data_changed(
        self,
        data1: SpotifyAmbientData,
        data2: SpotifyAmbientData,
    ) -> bool:
        """Check if the song name has changed, or if the time difference
        between the two records is greater than the duration of the song

            Input:
                data1: the first data object
                data2: the second data object

            Output:
                True if the song has changed, False otherwise.

        """
        if data1 is None and data2 is None:
            return False
        if data1 is None or data2 is None:
            return True

        if data1.track_id != data2.track_id:
            return True
        diff = data2.Timestamp - data1.Timestamp
        if diff.total_seconds() * 1000 > data1.track_duration_ms:
            return True

        return False

    def update_data(self) -> None:
        current_data = self.collector.collect_data()
        self.store_data(current_data)

    def build_spotify_activity_document(
        self,
        spotify_data: SpotifyAmbientData | dict | None,
        semantic_attributes: list[IndalekoSemanticAttributeDataModel],
    ) -> dict:
        """
        This builds a dictionary that can be used to generate the json
        required to insert the record into the database.

        Input:
            source_data: the source of this data.
            spotify_data: Note that this is treated as
            transparent information and is simply stored in the database.

            semantic_attributes: the semantic attributes associated with the
            spotify data.  Note that this can be any combination of known and
            unknown semantic attributes.  These are indexed.

        Output:
            A dictionary that can be used to generate the json required to
            insert the record into the database.
        """
        if spotify_data is None:
            # If there is no active spotify music playing at time of collection

            timestamp = datetime.now().isoformat()
            encoded_data = ""
        else:
            assert isinstance(spotify_data, SpotifyAmbientData) or isinstance(
                spotify_data,
                dict,
            ), f"location_data is not a BaseLocationDataModel or dict {type(spotify_data)}"

            assert isinstance(
                semantic_attributes,
                list,
            ), f"semantic_attributes is not a List {type(semantic_attributes)}"

            # Note that T is captialized in Timestamp
            timestamp = spotify_data.Timestamp
            encoded_data = spotify_data.Record.Data

        activity_data_args = {
            "Record": IndalekoRecordDataModel(
                SourceIdentifier=self.source_data,
                Timestamp=timestamp,
                Data=encoded_data,
            ),
            "Timestamp": timestamp,
            "SemanticAttributes": semantic_attributes,
        }
        ic(activity_data_args)
        activity_data = IndalekoActivityDataModel(**activity_data_args)

        return json.loads(
            activity_data.model_dump_json(exclude_none=True, exclude_unset=True),
        )


def main():
    ic("Starting Spotify Ambient Music Recorder")
    recorder = SpotifyRecorder()
    recorder.update_data()
    latest = recorder.get_latest_db_update()
    # ic(latest)
    ic(recorder.get_description())
    ic("Finished Spotify Ambient Music Recorder")
    ic(recorder.get_recorder_characteristics())


if __name__ == "__main__":
    main()
