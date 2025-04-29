"""
This module defines the data model for activity context.

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
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pydantic import AwareDatetime, Field, field_validator

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (current_path / "Indaleko.py").exists():
        current_path = current_path.parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.append(str(current_path))

# pylint: disable=wrong-import-position
from activity.context.data_models.activity_data import ActivityDataModel
from data_models.base import IndalekoBaseModel

# pylint: enable=wrong-import-position


class IndalekoActivityContextDataModel(IndalekoBaseModel):
    """
    This class defines the data model for activity context.

    An _activity context_ is a reference to an object in our indexing system
    (database) that corresponds to a collection of activity data points that
    have been captured by the known activity data providers.

    Activity context thus captures information related to the users: what was
    the user experiencing at the time the activity context was created.

    Activity _data_ is an abstract concept that refers to the information that
    describes the experiential information.  Examples of this include, but are
    not limited to:

    - The user's location
    - The music the user was listening to at the time
    - The ambient temperature
    - The weather
    - The application(s) the user was accessing
    - The files the user was accessing
    - Other users with whom the user was interacting

    The activity context is a snapshot of the user's environment at a specific
    point in time. This information is used to help understand the user's state
    of mind, in order to enable Indaleko to more effectively assist the user in
    finding specific files of interest.

    This module defines the format of the data that is used by the Activity
    Context service.

    An _activity handle_ is a UUID, which serves as a reference to the data
    object ("activity context") in the database.
    """

    Handle: uuid.UUID = Field(
        ...,
        title="Handle",
        description="The activity context handle.",
    )

    Timestamp: AwareDatetime = Field(
        ...,
        title="Timestamp",
        description="The timestamp when the activity context was created.",
    )

    Cursors: list[ActivityDataModel] = Field(
        ...,
        title="ActivityData",
        description="The activity data associated with the activity context.",
    )

    @classmethod
    @field_validator("Timestamp", mode="before")
    def ensure_timezone(cls, value: datetime) -> datetime:
        """ "Ensure that the timestamp is timezone-aware."""
        if isinstance(value, str):
            value = datetime.fromisoformat(value)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)  # noqa: UP017
        return value

    class Config:
        """Configuration for the class."""

        json_schema_extra = {  # noqa: RUF012
            "example": {
                "Handle": uuid.uuid4(),
                "Timestamp": "2024-01-01T00:00:00Z",
                "Cursors": [
                    ActivityDataModel.Config.json_schema_extra["example"],
                    ActivityDataModel.Config.json_schema_extra["example"],
                    ActivityDataModel.Config.json_schema_extra["example"],
                ],
            },
        }


def main() -> None:
    """Test code for IndalekoActivityContextDataModel."""
    IndalekoActivityContextDataModel.test_model_main()


if __name__ == "__main__":
    main()
