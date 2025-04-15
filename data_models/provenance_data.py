"""
This module defines the base data model for provenance information.

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

from datetime import datetime, timezone
import os
import sys
from uuid import UUID

from pydantic import Field, AwareDatetime
from typing import Union

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.provenance_operations import ProvenanceOperations
from data_models.record import IndalekoRecordDataModel

# pylint: enable=wrong-import-position

class BaseProvenanceDataModel(IndalekoBaseModel):
    """This is the base data model for provenance information"""

    Record: IndalekoRecordDataModel = Field(
        ...,
        title="Record",
        description="The record associated with the provenance information.",
    )

    Source: UUID = Field(
        ...,
        title="From",
        description="The UUID of the object describing the data source.",
    )

    Target: UUID = Field(
        ...,
        title="To",
        description="The UUID of the object describing the data destination.",
    )

    Operation: ProvenanceOperations = Field(
        ...,
        title="Operation",
        description="The operation that was performed on the data.",
    )

    Timestamp: Union[AwareDatetime, None] = Field(
        None,
        title="Timestamp",
        description="The timestamp of the operation.",
    )

    class Config:
        """Sample configuration for the data model"""

        @staticmethod
        def generate_example():
            """Generate an example for the data model"""
            example = IndalekoRecordDataModel.Config.json_schema_extra["example"]
            example.update({
                "Source": str(UUID(int=0)),
                "Target": str(UUID(int=0)),
                "Operation": "copy",
                "Timestamp": datetime.now(timezone.utc).isoformat(),
            })
            return example

        json_schema_extra = {
            # Note: this example
            "example": generate_example(),
        }


def main():
    """This allows testing the data model"""
    ic(BaseProvenanceDataModel.Config.json_schema_extra)
    BaseProvenanceDataModel.test_model_main()


if __name__ == "__main__":
    main()
