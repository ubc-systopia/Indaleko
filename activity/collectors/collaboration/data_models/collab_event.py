"""
This module defines the base data model for collaboration events.

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
from datetime import UTC, datetime

from icecream import ic
from pydantic import AwareDatetime, HttpUrl

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.collaboration.data_models.shared_file import SharedFileData
from activity.data_model.activity import IndalekoActivityDataModel

# pylint: enable=wrong-import-position


class CollaborationEvent(IndalekoActivityDataModel):
    source: str  # e.g., "discord", "slack", "email"
    event_type: str  # e.g., "file_shared", "message", "comment"
    timestamp: AwareDatetime
    sender: str
    recipients: list[str] | None = None
    channel_name: str | None = None
    guild_name: str | None = None
    message_id: str | None = None
    message_uri: HttpUrl | None = None
    message_content: str | None = None
    files: list[SharedFileData]

    class Config:
        @staticmethod
        def generate_example():
            """Generate an example for the data model"""
            example = IndalekoActivityDataModel.Config.json_schema_extra["example"]
            example["source"] = "discord"
            example["event_type"] = "file_shared"
            example["timestamp"] = datetime.now(UTC).isoformat()
            example["sender"] = "Aki#1234"
            example["channel_name"] = "general"
            example["guild_name"] = "Indaleko"
            example["message_id"] = "1234567890"
            example["message_uri"] = "https://discord.com/channels/1234567890/1234567890/1234567890"
            example["files"] = [SharedFileData.Config.json_schema_extra["example"]]
            return example

        json_schema_extra = {"example": generate_example()}


def main():
    """This allows testing the data model"""
    ic(CollaborationEvent.Config.json_schema_extra)
    CollaborationEvent.test_model_main()


if __name__ == "__main__":
    main()
