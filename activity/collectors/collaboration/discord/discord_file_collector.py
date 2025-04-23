"""
This module implements a Discord file sharing collector for Indaleko.

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
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import Any

import requests

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.characteristics import ActivityDataCharacteristics
from activity.collectors.collaboration.collaboration_base import CollaborationCollector
from activity.collectors.collaboration.data_models.shared_file import SharedFileData
from activity.collectors.collaboration.discord.data_models.file_share_data_model import (
    DiscordDataModel,
)

# pylint: enable=wrong-import-position


class DiscordFileShareCollector(CollaborationCollector):
    """
    Discord file sharing collector for Indaleko.

    This collector connects to Discord using a user token to scan direct messages (DMs)
    and server messages for file attachments. It identifies shared files and captures
    their metadata, including original filenames and Discord CDN URLs.
    """

    def __init__(
        self, token_file: str | None = None, token: str | None = None, **kwargs,
    ):
        """
        Initialize the Discord file sharing collector.

        Args:
            token_file: Path to a JSON file containing the Discord token
            token: Discord user token (alternative to token_file)
            **kwargs: Additional arguments
        """
        super().__init__(**kwargs)

        # Set up basic properties
        self._provider_id = uuid.UUID("f1e2d3c4-b5a6-7890-1234-567890abcdef")
        self._name = "Discord File Share Collector"
        self._description = "Collects file sharing activity from Discord"

        # Set up logging
        self.logger = logging.getLogger("DiscordFileShareCollector")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

        # Initialize token
        self.token = token
        if token_file and not token:
            self.token = self._load_token(token_file)

        # Initialize data storage
        self.dm_channels = []
        self.guild_channels = []
        self.file_attachments = []

    def _load_token(self, file_path: str) -> str:
        """
        Load Discord token from a JSON file.

        Args:
            file_path: Path to the token JSON file

        Returns:
            The Discord token
        """
        try:
            with open(file_path, encoding="utf-8") as f:
                data = json.load(f)
                if "token" not in data:
                    raise ValueError("No token found in the token file")
                return data["token"]
        except Exception as e:
            self.logger.error(f"Failed to load token from {file_path}: {e}")
            raise

    def _get_discord_api_headers(self) -> dict[str, str]:
        """
        Get headers for Discord API requests.

        Returns:
            Headers dictionary for API requests
        """
        return {
            "Authorization": self.token,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Discord Collector",
        }

    def get_dm_channels(self) -> list[dict]:
        """
        Retrieve the user's DM channels.

        Returns:
            List of DM channel data
        """
        url = "https://discord.com/api/v9/users/@me/channels"
        headers = self._get_discord_api_headers()

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            self.dm_channels = response.json()
            return self.dm_channels
        except Exception as e:
            self.logger.error(f"Failed to retrieve DM channels: {e}")
            return []

    def get_guilds(self) -> list[dict]:
        """
        Retrieve the user's guild (server) data.

        Returns:
            List of guild data
        """
        url = "https://discord.com/api/v9/users/@me/guilds"
        headers = self._get_discord_api_headers()

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Failed to retrieve guilds: {e}")
            return []

    def get_guild_channels(self, guild_id: str) -> list[dict]:
        """
        Retrieve channels from a specific guild.

        Args:
            guild_id: ID of the guild

        Returns:
            List of channel data
        """
        url = f"https://discord.com/api/v9/guilds/{guild_id}/channels"
        headers = self._get_discord_api_headers()

        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            channels = response.json()
            # Filter to just text channels
            text_channels = [c for c in channels if c.get("type") == 0]
            for channel in text_channels:
                channel["guild_id"] = guild_id
            self.guild_channels.extend(text_channels)
            return text_channels
        except Exception as e:
            self.logger.error(f"Failed to retrieve channels for guild {guild_id}: {e}")
            return []

    def get_channel_messages(self, channel_id: str, limit: int = 100) -> list[dict]:
        """
        Retrieve messages from a specific channel.

        Args:
            channel_id: ID of the channel
            limit: Maximum number of messages to retrieve

        Returns:
            List of message data
        """
        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        headers = self._get_discord_api_headers()
        params = {"limit": limit}

        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve messages for channel {channel_id}: {e}",
            )
            return []

    def extract_file_attachments(
        self, messages: list[dict], channel_data: dict,
    ) -> list[dict]:
        """
        Extract file attachments from messages.

        Args:
            messages: List of message data
            channel_data: Data about the channel the messages are from

        Returns:
            List of file attachment data
        """
        attachments = []
        guild_id = channel_data.get("guild_id")
        channel_id = channel_data.get("id")
        channel_name = channel_data.get("name", "Direct Message")

        for message in messages:
            # Skip messages without attachments
            if not message.get("attachments"):
                continue

            message_id = message.get("id")
            sender = message.get("author", {}).get("username")
            sender_id = message.get("author", {}).get("id")
            timestamp = message.get("timestamp")
            content = message.get("content", "")

            # Process each attachment
            for attachment in message.get("attachments", []):
                file_data = {
                    "filename": attachment.get("filename"),
                    "url": attachment.get("url"),
                    "proxy_url": attachment.get("proxy_url"),
                    "size_bytes": attachment.get("size"),
                    "content_type": attachment.get("content_type"),
                    "message_id": message_id,
                    "message_content": content,
                    "channel_id": channel_id,
                    "channel_name": channel_name,
                    "sender": sender,
                    "sender_id": sender_id,
                    "timestamp": timestamp,
                }

                # Add guild info if available
                if guild_id:
                    file_data["guild_id"] = guild_id
                    # Create a message link
                    file_data["message_link"] = (
                        f"https://discord.com/channels/{guild_id}/{channel_id}/{message_id}"
                    )
                else:
                    # DM channel
                    file_data["message_link"] = (
                        f"https://discord.com/channels/@me/{channel_id}/{message_id}"
                    )

                attachments.append(file_data)

        return attachments

    def scan_dm_channels(self) -> list[dict]:
        """
        Scan DM channels for file attachments.

        Returns:
            List of file attachment data from DMs
        """
        dm_attachments = []

        # Get DM channels if not already fetched
        if not self.dm_channels:
            self.get_dm_channels()

        # Scan each DM channel
        for channel in self.dm_channels:
            channel_id = channel.get("id")
            recipient = channel.get("recipients", [{}])[0].get("username", "Unknown")

            self.logger.info(f"Scanning DM channel with {recipient} (ID: {channel_id})")

            # Get messages from the channel
            messages = self.get_channel_messages(channel_id)

            # Add recipient name to channel data
            channel_data = {"id": channel_id, "name": f"DM with {recipient}"}

            # Extract attachments
            attachments = self.extract_file_attachments(messages, channel_data)
            dm_attachments.extend(attachments)

            self.logger.info(
                f"Found {len(attachments)} attachments in DM with {recipient}",
            )

        return dm_attachments

    def scan_guild_channels(self) -> list[dict]:
        """
        Scan guild channels for file attachments.

        Returns:
            List of file attachment data from guild channels
        """
        guild_attachments = []

        # Get guilds
        guilds = self.get_guilds()

        # Scan each guild
        for guild in guilds:
            guild_id = guild.get("id")
            guild_name = guild.get("name")

            self.logger.info(f"Scanning guild {guild_name} (ID: {guild_id})")

            # Get channels for this guild
            channels = self.get_guild_channels(guild_id)

            # Scan each channel
            for channel in channels:
                channel_id = channel.get("id")
                channel_name = channel.get("name")

                self.logger.info(f"Scanning channel #{channel_name} (ID: {channel_id})")

                # Get messages from the channel
                messages = self.get_channel_messages(channel_id)

                # Extract attachments
                attachments = self.extract_file_attachments(messages, channel)
                guild_attachments.extend(attachments)

                self.logger.info(
                    f"Found {len(attachments)} attachments in #{channel_name}",
                )

        return guild_attachments

    def collect_file_attachments(self) -> list[dict]:
        """
        Collect file attachments from Discord.

        Returns:
            Combined list of file attachment data
        """
        # Reset current data
        self.file_attachments = []

        # Scan DM channels
        dm_attachments = self.scan_dm_channels()
        self.file_attachments.extend(dm_attachments)

        # Scan guild channels
        guild_attachments = self.scan_guild_channels()
        self.file_attachments.extend(guild_attachments)

        self.logger.info(
            f"Collected a total of {len(self.file_attachments)} file attachments",
        )

        return self.file_attachments

    def convert_attachment_to_model(self, attachment: dict) -> DiscordDataModel:
        """
        Convert a raw attachment dict to a DiscordDataModel.

        Args:
            attachment: Raw attachment data

        Returns:
            DiscordDataModel instance
        """
        # Create the shared file data
        shared_file = SharedFileData(
            url=attachment["url"],
            filename=attachment["filename"],
            size_bytes=attachment.get("size_bytes"),
            content_type=attachment.get("content_type"),
            CollaborationType="discord",
        )

        # Create the Discord data model
        return DiscordDataModel(
            GuildName=attachment.get("guild_name"),
            GuildID=attachment.get("guild_id"),
            ChannelName=attachment.get("channel_name"),
            ChannelID=attachment.get("channel_id"),
            MessageID=attachment.get("message_id"),
            MessageURI=attachment.get("message_link"),
            Sender=attachment.get("sender"),
            Timestamp=attachment.get("timestamp"),
            MessageContent=attachment.get("message_content"),
            Files=[shared_file],
            CollaborationType="discord",
        )

    # CollaborationCollector interface methods
    def collect_data(self) -> list[dict]:
        """
        Collect Discord file sharing data.

        Returns:
            List of file attachment data
        """
        if not self.token:
            self.logger.error("Discord token is not set")
            return []

        return self.collect_file_attachments()

    def process_data(self, data: Any) -> dict[str, Any]:
        """
        Process the collected data.

        Args:
            data: Raw collected data

        Returns:
            Processed data
        """
        if isinstance(data, list):
            # Return the first attachment as a model if data is a list
            if data:
                model = self.convert_attachment_to_model(data[0])
                return model.model_dump()
            return {}

        # Process a single attachment
        if isinstance(data, dict):
            model = self.convert_attachment_to_model(data)
            return model.model_dump()

        return {}

    def get_all_processed_data(self) -> list[dict]:
        """
        Get all collected data as processed models.

        Returns:
            List of processed Discord data models
        """
        return [
            self.convert_attachment_to_model(attachment).model_dump()
            for attachment in self.file_attachments
        ]

    def get_collector_characteristics(self) -> list[ActivityDataCharacteristics]:
        """Get the characteristics of the collector"""
        return [
            ActivityDataCharacteristics.ACTIVITY_DATA_FILE_SHARE,
            ActivityDataCharacteristics.ACTIVITY_DATA_COLLABORATION,
            ActivityDataCharacteristics.PROVIDER_COLLABORATION_DATA,
        ]

    def get_collectorr_name(self) -> str:
        """Get the name of the collector"""
        return self._name

    def get_provider_id(self) -> uuid.UUID:
        """Get the ID of the collector"""
        return self._provider_id

    def retrieve_data(self, data_id: str) -> dict:
        """
        Retrieve specific data by ID.

        Args:
            data_id: The ID of the data to retrieve

        Returns:
            The requested data
        """
        # In this simple implementation, just return an empty dict
        # A real implementation would look up the data in a database
        return {}

    def retrieve_temporal_data(
        self,
        reference_time: datetime,
        prior_time_window: timedelta,
        subsequent_time_window: timedelta,
        max_entries: int = 0,
    ) -> list[dict]:
        """
        Retrieve data within a time window.

        Args:
            reference_time: The reference time
            prior_time_window: Time window before reference
            subsequent_time_window: Time window after reference
            max_entries: Maximum number of entries to return

        Returns:
            List of data within the time window
        """
        # This method is not implemented for this proof of concept
        return []

    def get_cursor(self, activity_context: uuid.UUID) -> uuid.UUID:
        """
        Get a cursor for the activity context.

        Args:
            activity_context: The activity context

        Returns:
            A cursor UUID
        """
        # Generate a random UUID as a cursor
        return uuid.uuid4()

    def cache_duration(self) -> timedelta:
        """
        Get the cache duration for data.

        Returns:
            The cache duration
        """
        return timedelta(minutes=30)

    def get_description(self) -> str:
        """
        Get the description of the collector.

        Returns:
            The collector description
        """
        return self._description

    def get_json_schema(self) -> dict:
        """
        Get the JSON schema for the data.

        Returns:
            The JSON schema
        """
        return DiscordDataModel.model_json_schema()


def main():
    """Main function for testing the collector"""
    # Set up logging
    logging.basicConfig(level=logging.INFO)

    # Create the collector
    # This needs a valid Discord token to work
    try:
        collector = DiscordFileShareCollector(token_file="./config/discord-token.json")

        # Collect data
        attachments = collector.collect_data()

        # Print summary
        print(f"\nCollected {len(attachments)} file attachments from Discord")

        # Print the first few attachments
        for i, attachment in enumerate(attachments[:5]):
            print(f"\nAttachment {i+1}:")
            print(f"  Filename: {attachment['filename']}")
            print(f"  URL: {attachment['url']}")
            print(f"  Size: {attachment.get('size_bytes', 'Unknown')} bytes")
            print(f"  From: {attachment.get('sender', 'Unknown')}")

        # Process the data
        if attachments:
            processed = collector.process_data(attachments[0])
            print("\nExample processed data:")
            print(json.dumps(processed, indent=2, default=str))

    except Exception as e:
        logging.exception(f"Error in main: {e}")


if __name__ == "__main__":
    main()
