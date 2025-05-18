"""
This module defines a common base for storage activity data recorders.

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

from pathlib import Path


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from activity.collectors.storage.base import StorageActivityCollector
from activity.recorders.base import RecorderBase
from activity.recorders.storage.data_models.storage_activity import IndalekoStorageActivityDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from utils.misc.data_management import encode_binary_data


# pylint: enable=wrong-import-position


class StorageBaseActivityDataRecorder(RecorderBase):
    """Common Base class for storage activity data recorders."""

    def __init__(self, *args: dict[str, object], **kwargs: dict) -> None:
        """Initialize the storage activity data recorder."""
        super().__init__(*args, **kwargs)
        self._collector = kwargs.get("collector")
        if (
            self._collector is
            not None
            and
            not isinstance(self._collector, StorageActivityCollector)
        ):
            raise TypeError(f"provider is not a StorageActivityCollector {type(self._collector)}")
        if not hasattr(self, "_collection"):
            self._collector = kwargs.get("collection")

    @staticmethod
    def build_storage_activity_document(
        source_data: IndalekoSourceIdentifierDataModel | dict,
        storage_activity_data: IndalekoStorageActivityDataModel | dict,
        semantic_attributes: list[IndalekoSemanticAttributeDataModel],
    ) -> dict[str, str]:
        """
        Build a storage activity document from the source data and storage activity data.

        Args:
            source_data: The source data for the storage activity.
            storage_activity_data: The storage activity data.
            semantic_attributes: The semantic attributes for the storage activity.

        Returns:
            A dictionary representing the storage activity document.
        """
        if not isinstance(source_data, (IndalekoSourceIdentifierDataModel, dict)):
            raise TypeError(f"source_data is not a IndalekoSourceIdentifierDataModel {type(source_data)}")
        if not isinstance(storage_activity_data, (IndalekoStorageActivityDataModel, dict)):
            raise TypeError(f"storage_activity_data is not a IndalekoStorageActivityDataModel {type(storage_activity_data)}")
        if not isinstance(semantic_attributes, list):
            raise TypeError(f"semantic_attributes is not a list {type(semantic_attributes)}")
        if len(semantic_attributes) == 0:
            raise ValueError("No semantic attributes provided")
        if isinstance(source_data, dict):
            source_data = IndalekoSourceIdentifierDataModel(**source_data)
        if isinstance(storage_activity_data, dict):
            storage_activity_data = IndalekoStorageActivityDataModel(**storage_activity_data)
        record = IndalekoRecordDataModel(
            SourceIdentifier=source_data,
            Timestamp=storage_activity_data.PeriodEnd,
            Data=encode_binary_data(storage_activity_data), # type: ignore[call-arg]
        )
        activity_data = IndalekoStorageActivityDataModel(
            Record=record,
            Timestamp=storage_activity_data.PeriodEnd,
            SemanticAttributes=semantic_attributes,
            ExistingObjectIdentifier=storage_activity_data.ExistingObjectIdentifier,
        )
        return json.loads(
            activity_data.model_dump_json(
                exclude_none=True,
                exclude_unset=True,
            ),
        )
