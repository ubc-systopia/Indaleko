"""
This module defines a utility for acquiring Discord data.

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

import discord
from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.collaboration.collaboration_base import CollaborationCollector

# from activity.collectors.collaboration.discord.discord_data_model import DiscordDataModel
# pylint: enable=wrong-import-position


class DiscordDataCollector(CollaborationCollector):
    """
    This class provides a utility for acquiring Discord data.
    """

    def __init__(self, token: str, **kwargs):
        """Initialize the object."""
        super().__init__(**kwargs)
        self.token = token
        self.client = discord.Client(intents=discord.Intents.default())
        self.client.event(self.on_ready)
        self.client.event(self.on_message)

    async def on_ready(self):
        """Called when the bot is ready."""
        print(f"Logged on as {self.client.user}!")
        for guild in self.client.guilds:
            print(f"\nGuild: {guild.name} (ID: {guild.id})")
            for channel in guild.text_channels:
                print(f"Channel: {channel.name} (ID: {channel.id})")
                try:
                    messages = [message async for message in channel.history(limit=100)]
                    for message in messages:
                        if message.attachments:
                            messagelink = f"https://discord.com/channels/{guild.id}/{channel.id}/{message.id}"
                            print(
                                f"Found attachment: {message.attachments[0].url} in message {messagelink}",
                            )
                            # Capture shared file information
                            shared_file_info = {
                                "SharedFileName": message.attachments[0].filename,
                                "SharedFileURI": message.attachments[0].url,
                                "GuildID": str(guild.id),
                                "ChannelID": str(channel.id),
                                "MessageURI": messagelink,
                            }
                            print(shared_file_info)
                except discord.errors.Forbidden:
                    print(f"    Cannot access channel: {channel.name}")

    async def on_message(self, message):
        """Called when a message is received."""
        print(f"Message from {message.author}: {message.content}")
        if message.attachments:
            print(f"Attachment: {message.attachments[0].url}")

    def collect_data(self) -> None:
        """Collect data from Discord."""
        self.client.run(self.token)

    def process_data(self, data: Any) -> dict[str, Any]:
        """Process the collected data."""
        ic("Processing Discord data")
        # Example: Convert processed data to a dictionary
        return data.dict()

    def store_data(self, data: dict[str, Any]) -> None:
        """Store the processed data."""
        ic("Storing Discord data")
        # Example: Print data to simulate storing
        print("Storing data:", data)

    def get_latest_db_update(self) -> dict[str, Any]:
        """Get the latest data update from the database."""
        ic("Getting latest Discord data update from the database")
        # Example: Simulate fetching the latest data
        return {
            "SharedFileName": "example.txt",
            "SharedFileURI": "https://discord.com/channels/123456789/987654321/123456789",
            "GuildID": "123456789",
            "ChannelID": "987654321",
            "MessageURI": "https://discord.com/channels/123456789/987654321/123456789",
        }

    def update_data(self) -> None:
        """Update the data in the database."""
        ic("Updating Discord data in the database")
        # Example: Simulate updating data
        latest_data = self.get_latest_db_update()
        self.store_data(latest_data)


def main():
    """Main entry point for the Discord Data Collector."""
    ic("Starting Discord Data Collector")
    token = "YOUR_DISCORD_BOT_TOKEN"
    collector = DiscordDataCollector(token=token)
    collector.collect_data()
    latest = collector.get_latest_db_update()
    ic(latest)
    ic(collector.get_description())
    ic("Finished Discord Data Collector")


if __name__ == "__main__":
    main()
