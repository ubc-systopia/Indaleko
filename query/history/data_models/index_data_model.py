"""
This module defines the data model for the Indaleko data object.

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

"""
This module defines the data model for the Indaleko data object.

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
import os
import sys

from typing import Any

from icecream import ic
from pydantic import AwareDatetime, Field


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel


# pylint: enable=wrong-import-position


class IndalekoIndexDataModel(IndalekoBaseModel):
    """
    This class defines the data model for the indices and
    relationships to queries and metadata fields.
    """

    IndexId: IndalekoUUIDDataModel = Field(
        None,
        title="IndexId",
        description="The UUID for the index.",
    )

    FieldName: str = Field(
        None,
        title="FieldName",
        description="The name of the field the index is associated with.",
    )

    IndexType: str = Field(
        None,
        title="IndexType",
        description="The type of index (e.g., single, composite, geo, full-text).",
    )

    CreationDate: AwareDatetime = Field(
        None,
        title="CreationDate",
        description="The timestamp of when the index was created.",
    )

    LastUsed: AwareDatetime | None = Field(
        None,
        title="LastUsed",
        description="The timestamp of when the index was last accessed.",
    )

    UsageCount: int = Field(
        0,
        title="UsageCount",
        description="Number of queries that used this index.",
    )

    OverheadCost: float | None = Field(
        None,
        title="OverheadCost",
        description="Overhead cost of maintaining this index.",
    )

    ArchivedImpact: dict[str, Any] | None = Field(
        default_factory=dict,
        title="ArchivedImpact",
        description="Impact on archived queries",
    )

    class Config:
        json_schema_extra = {
            "example": {
                "Record": IndalekoRecordDataModel.Config.json_schema_extra["example"],
                "IndexId": IndalekoUUIDDataModel.Config.json_schema_extra["example"],
                "FieldName": "Field1",
                "IndexType": "Single",
                "CreationDate": "2024-07-30T23:38:48.319654+00:00",
                "LastUsed": "2024-07-30T23:38:48.319654+00:00",
                "UsageCount": 0,
                "OverheadCost": 0.0,
                "ArchivedImpact": {
                    "QueryIdentifier": IndalekoUUIDDataModel.Config.json_schema_extra["example"],
                    "Impact": 0.0,
                },
            },
        }


def main() -> None:
    """This allows testing the data model."""
    ic("Testing IndalekoObjectDataModel")
    IndalekoIndexDataModel.test_model_main()


if __name__ == "__main__":
    main()
