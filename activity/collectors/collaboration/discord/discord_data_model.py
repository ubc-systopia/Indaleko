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

from typing import Optional
from pydantic import Field

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.collaboration.data_models.collaboration_data_model import BaseCollaborationDataModel
# pylint: enable=wrong-import-position


class DiscordDataModel(BaseCollaborationDataModel):
    """
    Discord-specific implementation of the collaboration data model.
    """

    SharedFileName: Optional[str] = Field(
        None,
        title='SharedFileName',
        description='The original name of the shared file.',
    )

    SharedFileURI: Optional[str] = Field(
        None,
        title='SharedFileURI',
        description='The URI of the shared file.',
    )

    GuildID: Optional[str] = Field(
        None,
        title='GuildID',
        description='The ID of the guild where the message was posted.',
    )

    ChannelID: Optional[str] = Field(
        None,
        title='ChannelID',
        description='The ID of the channel where the message was posted.',
    )

    MessageURI: Optional[str] = Field(
        None,
        title='MessageURI',
        description='The URI of the original message.',
    )

    class Config:
        """Configuration and example data for the Discord data model"""
        json_schema_extra = {
            "example": {
                **BaseCollaborationDataModel.Config.json_schema_extra["example"],
                "SharedFileName": "example.txt",
                "SharedFileURI": "https://discord.com/channels/123456789/987654321/123456789",
                "GuildID": "123456789",
                "ChannelID": "987654321",
                "MessageURI": "https://discord.com/channels/123456789/987654321/123456789",
            }
        }


def main():
    """This allows testing the data models"""
    print("\nTesting Spotify-specific Ambient Data Model:")
    DiscordDataModel.test_model_main()


if __name__ == '__main__':
    main()
