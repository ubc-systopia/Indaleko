"""
This module defines the data model for the Indaleko
optimization data model.

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

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from pydantic import Field, AwareDatetime
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.i_uuid import IndalekoUUIDDataModel

# pylint: enable=wrong-import-position


class IndalekoOptimizationDataModel(IndalekoBaseModel):

    Record: IndalekoRecordDataModel = Field(
        None, title="Record", description="The record associated with the object."
    )

    OptimizationId: IndalekoUUIDDataModel = Field(
        None, title="OptimizationId", description="The UUID for the optimization."
    )

    QueryId: Optional[IndalekoUUIDDataModel] = Field(
        None,
        title="QueryId",
        description="The UUID for the query that triggered this optimization.",
    )

    Action: str = Field(
        None,
        title="Action",
        description="The action taken (e.g., add_index, remove_index).",
    )

    FieldName: Optional[str] = Field(
        None, title="FieldName", description="The field affected by the optimization."
    )

    IndexId: Optional[IndalekoUUIDDataModel] = Field(
        None, title="IndexId", description="The index affected (if applicable)."
    )

    CostBenefit: Optional[Dict[str, Any]] = Field(
        None, title="CostBenefit", description="Analysis of cost vs. benefit."
    )

    Timestamp: AwareDatetime = Field(
        datetime.now(timezone.utc),
        title="Timestamp",
        description="When the optimization was applied.",
    )

    Archived: bool = Field(
        False, title="Archived", description="Whether the optimization is archived."
    )

    class Config:
        json_schema_extra = {
            "example": {
                "Record": IndalekoRecordDataModel.Config.json_schema_extra["example"],
                "OptimizationId": IndalekoUUIDDataModel.Config.json_schema_extra[
                    "example"
                ],
                "QueryId": IndalekoUUIDDataModel.Config.json_schema_extra["example"],
                "Action": "add_index",
                "FieldName": "Name",
                "IndexId": IndalekoUUIDDataModel.Config.json_schema_extra["example"],
                "CostBenefit": {
                    "Cost": 100.0,
                    "Benefit": 200.0,
                },
            }
        }


def main():
    """This allows testing the data model."""
    ic("Testing IndalekoObjectDataModel")
    IndalekoOptimizationDataModel.test_model_main()


if __name__ == "__main__":
    main()
