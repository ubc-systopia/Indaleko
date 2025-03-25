"""
This module defines the data models for
a Spotify-specific implementation.

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

from typing import Optional, Union
from pydantic import Field, HttpUrl, AwareDatetime

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.collaboration.data_models.shared_file import SharedFileData
from activity.collectors.collaboration.data_models.collaboration_data_model import (
    BaseCollaborationDataModel,
)

# pylint: enable=wrong-import-position


class DiscordDataModel(BaseCollaborationDataModel):
    """
    Discord-specific implementation of the collaboration data model.
    """
    GuildName: Union[str, None] = Field(
        None,
        description="Name of the Discord server (guild)"
    )

    GuildID: Union[str, None] = Field(
        None,
        description="ID of the Discord server"
    )

    ChannelName: Union[str, None] = Field(
        None,
        description="Name of the Discord channel"
    )

    ChannelID: Union[str, None] = Field(
        None,
        description="ID of the Discord channel"
    )

    MessageID: Union[str, None] = Field(
        None,
        description="ID of the Discord message"
    )

    MessageURI: Union[HttpUrl, None] = Field(
        None,
        description="Link to the original message"
    )

    Sender: Union[str, None] = Field(
        None,
        description="Username or handle of the sender"
    )

    Timestamp: Union[AwareDatetime, None] = Field(
        None,
        description="When the message was sent"
    )

    MessageContent: Union[str, None] = Field(
        None,
        description="Text content of the message"
    )

    Files: list[SharedFileData] = Field(
        ...,
        description="List of files shared in the message"
    )


    class Config:
        """Configuration and example data for the Discord data model"""

        @staticmethod
        def generate_example():
            """Generate an example for the data model"""
            example = BaseCollaborationDataModel.Config.generate_example()
            sfd_example = SharedFileData.Config.json_schema_extra["example"]
            example.update({
                "CollaborationType": "discord",
                "GuildName": "Indaleko",
                "GuildID": "123456789",
                "ChannelName": "general",
                "ChannelID": "987654321",
                "MessageID": "123456789",
                "MessageURI": "https://discord.com/channels/123456789/987654321/123456789",
                "Sender": "Aki#1234",
                "Timestamp": "2025-01-01T12:00:00Z",
                "MessageContent": "Hello, World!",
                "Files": [{
                    "filename": "example.pdf",
                    "url": "https://cdn.discordapp.com/...",
                    "size_bytes": 1048576,
                    "content_type": "application/pdf"
                }]
            })
            return example

        json_schema_extra = {
            "example": generate_example()
        }


def main():
    """This allows testing the data models"""
    print("\nTesting Spotify-specific Discord Data Model:")
    # ic(DiscordDataModel.Config.json_schema_extra)
    SharedFileData.test_model_main()
    # DiscordDataModel.test_model_main()


if __name__ == "__main__":
    main()
