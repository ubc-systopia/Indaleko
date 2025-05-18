"""Media activity collector for ablation testing."""

import logging
import random
from typing import Any
from uuid import UUID

from ..base import ISyntheticCollector
from ..models.media_activity import MediaActivity, MediaType
from ..utils.uuid_utils import generate_deterministic_uuid


class MediaActivityCollector(ISyntheticCollector):
    """Synthetic collector for media activity."""

    def __init__(self, seed_value: int = 42):
        """Initialize the media activity collector.

        Args:
            seed_value: Random seed for deterministic data generation.
        """
        self.seed(seed_value)
        self.logger = logging.getLogger(__name__)

        # Sample video titles and creators
        self.video_entries = [
            {"title": "Understanding Deep Learning Fundamentals", "creator": "Tech Explained", "platform": "YouTube"},
            {"title": "The Dawn of Quantum Computing", "creator": "Science Today", "platform": "YouTube"},
            {"title": "Stranger Things Season 4", "creator": "Netflix", "platform": "Netflix"},
            {"title": "The Last of Us", "creator": "HBO", "platform": "HBO Max"},
            {"title": "Inception: Director's Cut", "creator": "Christopher Nolan", "platform": "Prime Video"},
            {"title": "The Marvel Universe: A Documentary", "creator": "FilmInsight", "platform": "Disney+"},
            {"title": "How to Code in Python", "creator": "Programming Made Easy", "platform": "Udemy"},
            {"title": "The Earth at Night", "creator": "National Geographic", "platform": "Disney+"},
        ]

        # Sample audio titles and creators
        self.audio_entries = [
            {"title": "The Future of AI", "creator": "TechTalk Podcast", "platform": "Spotify"},
            {"title": "Classical Symphony No. 9", "creator": "London Philharmonic", "platform": "Apple Music"},
            {"title": "Mindfulness Meditation Guide", "creator": "Calm Living", "platform": "Calm"},
            {"title": "History of Ancient Rome", "creator": "HistoryCast", "platform": "Audible"},
            {"title": "Midnight Jazz Collection", "creator": "Jazz Masters", "platform": "Spotify"},
            {"title": "Modern Psychology", "creator": "Mind Matters", "platform": "Audible"},
            {"title": "Top 40 Hits", "creator": "Various Artists", "platform": "Apple Music"},
            {"title": "Sleep Sounds: Ocean Waves", "creator": "Sleep Aid", "platform": "Calm"},
        ]

        # Sample stream titles and creators
        self.stream_entries = [
            {"title": "Live Coding: Building a Web App", "creator": "CodeWithMe", "platform": "Twitch"},
            {"title": "World Cup Finals Live", "creator": "SportsCentral", "platform": "YouTube Live"},
            {"title": "Gaming Marathon: Elden Ring", "creator": "GameMaster", "platform": "Twitch"},
            {"title": "Ask Me Anything: Science Edition", "creator": "ScienceExplorer", "platform": "Instagram Live"},
            {"title": "Live Music Festival Coverage", "creator": "MusicToday", "platform": "YouTube Live"},
            {"title": "Community Gaming Night", "creator": "GamerSquad", "platform": "Facebook Gaming"},
            {"title": "Space Launch Live Feed", "creator": "SpaceX", "platform": "YouTube Live"},
            {"title": "Cooking Live: Italian Pasta", "creator": "ChefCooking", "platform": "TikTok Live"},
        ]

        # Sample image titles and creators
        self.image_entries = [
            {"title": "Sunset over Mountain Range", "creator": "NatureLens", "platform": "Instagram"},
            {"title": "Abstract Art Collection", "creator": "ModernArtist", "platform": "Flickr"},
            {"title": "Wildlife Photography: Lions", "creator": "WildLife", "platform": "500px"},
            {"title": "Urban Architecture", "creator": "CityScapes", "platform": "Pinterest"},
            {"title": "Minimalist Design Portfolio", "creator": "DesignMinimal", "platform": "Behance"},
            {"title": "Food Photography: Desserts", "creator": "FoodLens", "platform": "Instagram"},
            {"title": "Travel Moments: Italy", "creator": "Wanderlust", "platform": "Instagram"},
            {"title": "Portrait Photography Collection", "creator": "FaceFocus", "platform": "500px"},
        ]

        # Sample game titles and creators
        self.game_entries = [
            {"title": "The Legend of Zelda: Breath of the Wild", "creator": "Nintendo", "platform": "Nintendo Switch"},
            {"title": "Cyberpunk 2077", "creator": "CD Projekt Red", "platform": "PlayStation"},
            {"title": "Minecraft", "creator": "Mojang", "platform": "PC"},
            {"title": "Call of Duty: Modern Warfare", "creator": "Activision", "platform": "Xbox"},
            {"title": "FIFA 2023", "creator": "EA Sports", "platform": "PlayStation"},
            {"title": "Fortnite", "creator": "Epic Games", "platform": "PC"},
            {"title": "Animal Crossing: New Horizons", "creator": "Nintendo", "platform": "Nintendo Switch"},
            {"title": "Elden Ring", "creator": "FromSoftware", "platform": "PlayStation"},
        ]

        # Source options
        self.sources = ["browser_extension", "app", "smart_tv", "mobile", "desktop", "console"]

    def collect(self) -> dict:
        """Generate synthetic media activity data.

        Returns:
            Dict: The generated media activity data.
        """
        # Select a random media type
        media_type = random.choice(list(MediaType))

        # Select content based on media type
        if media_type == MediaType.VIDEO:
            entry = random.choice(self.video_entries)
            duration_seconds = random.randint(60, 7200)  # 1 minute to 2 hours
            activity = MediaActivity.create_video_activity(
                title=entry["title"],
                platform=entry["platform"],
                duration_seconds=duration_seconds,
                creator=entry["creator"],
                url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                source=random.choice(self.sources),
            )
        elif media_type == MediaType.AUDIO:
            entry = random.choice(self.audio_entries)
            duration_seconds = random.randint(60, 3600)  # 1 minute to 1 hour
            activity = MediaActivity.create_audio_activity(
                title=entry["title"],
                platform=entry["platform"],
                duration_seconds=duration_seconds,
                creator=entry["creator"],
                url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                source=random.choice(self.sources),
            )
        elif media_type == MediaType.STREAM:
            entry = random.choice(self.stream_entries)
            duration_seconds = random.randint(300, 10800)  # 5 minutes to 3 hours
            activity = MediaActivity.create_stream_activity(
                title=entry["title"],
                platform=entry["platform"],
                duration_seconds=duration_seconds,
                creator=entry["creator"],
                url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                source=random.choice(self.sources),
            )
        elif media_type == MediaType.IMAGE:
            entry = random.choice(self.image_entries)
            activity = MediaActivity.create_image_activity(
                title=entry["title"],
                platform=entry["platform"],
                creator=entry["creator"],
                url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                source=random.choice(self.sources),
            )
        elif media_type == MediaType.GAME:
            entry = random.choice(self.game_entries)
            duration_seconds = random.randint(900, 14400)  # 15 minutes to 4 hours
            activity = MediaActivity.create_game_activity(
                title=entry["title"],
                platform=entry["platform"],
                duration_seconds=duration_seconds,
                creator=entry["creator"],
                source=random.choice(self.sources),
            )

        # Return the activity as a dictionary
        return activity.model_dump()

    def generate_truth_data(self, query: str) -> set[UUID]:
        """Generate truth data for a media-related query.

        Args:
            query: The natural language query to generate truth data for.

        Returns:
            Set[UUID]: The set of UUIDs that should match the query.
        """
        matching_entities = set()
        query_lower = query.lower()

        # Check for media type mentions
        for media_type in MediaType:
            if media_type.value.lower() in query_lower:
                for i in range(5):  # Generate 5 matching activities
                    entity_id = generate_deterministic_uuid(f"media_activity:{media_type.value}:{i}")
                    matching_entities.add(entity_id)

        # Check for platform mentions
        platforms = set()
        for entries in [
            self.video_entries,
            self.audio_entries,
            self.stream_entries,
            self.image_entries,
            self.game_entries,
        ]:
            for entry in entries:
                platforms.add(entry["platform"])

        for platform in platforms:
            if platform.lower() in query_lower:
                for i in range(3):  # Generate 3 matching activities
                    entity_id = generate_deterministic_uuid(f"media_activity:platform:{platform}:{i}")
                    matching_entities.add(entity_id)

        # Check for creator mentions
        creators = set()
        for entries in [
            self.video_entries,
            self.audio_entries,
            self.stream_entries,
            self.image_entries,
            self.game_entries,
        ]:
            for entry in entries:
                creators.add(entry["creator"])

        for creator in creators:
            if creator.lower() in query_lower:
                for i in range(2):  # Generate 2 matching activities
                    entity_id = generate_deterministic_uuid(f"media_activity:creator:{creator}:{i}")
                    matching_entities.add(entity_id)

        # Check for title mentions
        titles = set()
        for entries in [
            self.video_entries,
            self.audio_entries,
            self.stream_entries,
            self.image_entries,
            self.game_entries,
        ]:
            for entry in entries:
                titles.add(entry["title"])

        for title in titles:
            # Check if any word in the title is in the query
            title_words = title.lower().split()
            for word in title_words:
                if len(word) > 3 and word in query_lower:  # Only match on significant words
                    for i in range(1):  # Generate 1 matching activity
                        entity_id = generate_deterministic_uuid(f"media_activity:title:{title}:{i}")
                        matching_entities.add(entity_id)
                    break  # Only match once per title

        return matching_entities

    def generate_batch(self, count: int) -> list[dict[str, Any]]:
        """Generate a batch of synthetic media activity data.

        Args:
            count: Number of media activity records to generate.

        Returns:
            List[Dict]: List of generated media activity data.
        """
        return [self.collect() for _ in range(count)]

    def generate_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate media activity data that should match a specific query.

        Args:
            query: The natural language query to generate matching data for.
            count: Number of matching records to generate.

        Returns:
            List[Dict]: List of generated media activity data that should match the query.
        """
        query_lower = query.lower()
        matching_data = []

        # Check for media type mentions
        for media_type in MediaType:
            if media_type.value.lower() in query_lower:
                # Generate matching data for this media type
                matching_count = min(count, 5)  # Generate up to 5 matching activities

                for i in range(matching_count):
                    # Choose appropriate content based on media type
                    if media_type == MediaType.VIDEO:
                        entry = random.choice(self.video_entries)
                        duration_seconds = random.randint(60, 7200)
                        activity = MediaActivity.create_video_activity(
                            title=entry["title"],
                            platform=entry["platform"],
                            duration_seconds=duration_seconds,
                            creator=entry["creator"],
                            url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                            source=random.choice(self.sources),
                        )
                    elif media_type == MediaType.AUDIO:
                        entry = random.choice(self.audio_entries)
                        duration_seconds = random.randint(60, 3600)
                        activity = MediaActivity.create_audio_activity(
                            title=entry["title"],
                            platform=entry["platform"],
                            duration_seconds=duration_seconds,
                            creator=entry["creator"],
                            url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                            source=random.choice(self.sources),
                        )
                    elif media_type == MediaType.STREAM:
                        entry = random.choice(self.stream_entries)
                        duration_seconds = random.randint(300, 10800)
                        activity = MediaActivity.create_stream_activity(
                            title=entry["title"],
                            platform=entry["platform"],
                            duration_seconds=duration_seconds,
                            creator=entry["creator"],
                            url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                            source=random.choice(self.sources),
                        )
                    elif media_type == MediaType.IMAGE:
                        entry = random.choice(self.image_entries)
                        activity = MediaActivity.create_image_activity(
                            title=entry["title"],
                            platform=entry["platform"],
                            creator=entry["creator"],
                            url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                            source=random.choice(self.sources),
                        )
                    elif media_type == MediaType.GAME:
                        entry = random.choice(self.game_entries)
                        duration_seconds = random.randint(900, 14400)
                        activity = MediaActivity.create_game_activity(
                            title=entry["title"],
                            platform=entry["platform"],
                            duration_seconds=duration_seconds,
                            creator=entry["creator"],
                            source=random.choice(self.sources),
                        )

                    # Generate a deterministic ID
                    activity_dict = activity.model_dump()
                    activity_dict["id"] = generate_deterministic_uuid(f"media_activity:{media_type.value}:{i}")

                    matching_data.append(activity_dict)

                count -= matching_count
                if count <= 0:
                    return matching_data

        # Check for platform mentions
        all_entries = (
            self.video_entries + self.audio_entries + self.stream_entries + self.image_entries + self.game_entries
        )

        platform_matches = {}
        for entry in all_entries:
            platform = entry["platform"]
            if platform.lower() in query_lower:
                if platform not in platform_matches:
                    platform_matches[platform] = []
                platform_matches[platform].append(entry)

        for platform, entries in platform_matches.items():
            if count <= 0:
                break

            matching_count = min(count, 3)  # Generate up to 3 matching activities

            for i in range(matching_count):
                entry = random.choice(entries)

                # Determine media type based on which list this entry belongs to
                if entry in self.video_entries:
                    media_type = MediaType.VIDEO
                    duration_seconds = random.randint(60, 7200)
                    activity = MediaActivity.create_video_activity(
                        title=entry["title"],
                        platform=entry["platform"],
                        duration_seconds=duration_seconds,
                        creator=entry["creator"],
                        url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                        source=random.choice(self.sources),
                    )
                elif entry in self.audio_entries:
                    media_type = MediaType.AUDIO
                    duration_seconds = random.randint(60, 3600)
                    activity = MediaActivity.create_audio_activity(
                        title=entry["title"],
                        platform=entry["platform"],
                        duration_seconds=duration_seconds,
                        creator=entry["creator"],
                        url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                        source=random.choice(self.sources),
                    )
                elif entry in self.stream_entries:
                    media_type = MediaType.STREAM
                    duration_seconds = random.randint(300, 10800)
                    activity = MediaActivity.create_stream_activity(
                        title=entry["title"],
                        platform=entry["platform"],
                        duration_seconds=duration_seconds,
                        creator=entry["creator"],
                        url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                        source=random.choice(self.sources),
                    )
                elif entry in self.image_entries:
                    media_type = MediaType.IMAGE
                    activity = MediaActivity.create_image_activity(
                        title=entry["title"],
                        platform=entry["platform"],
                        creator=entry["creator"],
                        url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                        source=random.choice(self.sources),
                    )
                elif entry in self.game_entries:
                    media_type = MediaType.GAME
                    duration_seconds = random.randint(900, 14400)
                    activity = MediaActivity.create_game_activity(
                        title=entry["title"],
                        platform=entry["platform"],
                        duration_seconds=duration_seconds,
                        creator=entry["creator"],
                        source=random.choice(self.sources),
                    )

                # Generate a deterministic ID
                activity_dict = activity.model_dump()
                activity_dict["id"] = generate_deterministic_uuid(f"media_activity:platform:{platform}:{i}")

                matching_data.append(activity_dict)

            count -= matching_count
            if count <= 0:
                return matching_data

        # If we couldn't generate specific matching data, create generic matches
        while len(matching_data) < count:
            data = self.collect()
            data["id"] = generate_deterministic_uuid(f"media_activity:generic_match:{len(matching_data)}")
            matching_data.append(data)

        return matching_data

    def generate_non_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate media activity data that should NOT match a specific query.

        Args:
            query: The natural language query to generate non-matching data for.
            count: Number of non-matching records to generate.

        Returns:
            List[Dict]: List of generated media activity data that should NOT match the query.
        """
        query_lower = query.lower()
        non_matching_data = []

        # Determine which media types to avoid
        avoid_media_types = []
        for media_type in MediaType:
            if media_type.value.lower() in query_lower:
                avoid_media_types.append(media_type)

        # Determine which platforms to avoid
        avoid_platforms = []
        for entry in (
            self.video_entries + self.audio_entries + self.stream_entries + self.image_entries + self.game_entries
        ):
            platform = entry["platform"]
            if platform.lower() in query_lower and platform not in avoid_platforms:
                avoid_platforms.append(platform)

        # Generate non-matching data
        for i in range(count):
            # Choose a media type that doesn't match the query
            if len(avoid_media_types) < len(MediaType):
                media_type = random.choice([mt for mt in MediaType if mt not in avoid_media_types])
            else:
                # If all media types are in the query, just pick one randomly
                media_type = random.choice(list(MediaType))

            # Choose content that doesn't match the platforms in the query
            if media_type == MediaType.VIDEO:
                valid_entries = [e for e in self.video_entries if e["platform"] not in avoid_platforms]
                if not valid_entries:
                    valid_entries = self.video_entries  # Fallback if all platforms are avoided

                entry = random.choice(valid_entries)
                duration_seconds = random.randint(60, 7200)
                activity = MediaActivity.create_video_activity(
                    title=entry["title"],
                    platform=entry["platform"],
                    duration_seconds=duration_seconds,
                    creator=entry["creator"],
                    url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                    source=random.choice(self.sources),
                )
            elif media_type == MediaType.AUDIO:
                valid_entries = [e for e in self.audio_entries if e["platform"] not in avoid_platforms]
                if not valid_entries:
                    valid_entries = self.audio_entries

                entry = random.choice(valid_entries)
                duration_seconds = random.randint(60, 3600)
                activity = MediaActivity.create_audio_activity(
                    title=entry["title"],
                    platform=entry["platform"],
                    duration_seconds=duration_seconds,
                    creator=entry["creator"],
                    url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                    source=random.choice(self.sources),
                )
            elif media_type == MediaType.STREAM:
                valid_entries = [e for e in self.stream_entries if e["platform"] not in avoid_platforms]
                if not valid_entries:
                    valid_entries = self.stream_entries

                entry = random.choice(valid_entries)
                duration_seconds = random.randint(300, 10800)
                activity = MediaActivity.create_stream_activity(
                    title=entry["title"],
                    platform=entry["platform"],
                    duration_seconds=duration_seconds,
                    creator=entry["creator"],
                    url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                    source=random.choice(self.sources),
                )
            elif media_type == MediaType.IMAGE:
                valid_entries = [e for e in self.image_entries if e["platform"] not in avoid_platforms]
                if not valid_entries:
                    valid_entries = self.image_entries

                entry = random.choice(valid_entries)
                activity = MediaActivity.create_image_activity(
                    title=entry["title"],
                    platform=entry["platform"],
                    creator=entry["creator"],
                    url=f"https://example.com/{entry['platform'].lower()}/{random.randint(10000, 99999)}",
                    source=random.choice(self.sources),
                )
            elif media_type == MediaType.GAME:
                valid_entries = [e for e in self.game_entries if e["platform"] not in avoid_platforms]
                if not valid_entries:
                    valid_entries = self.game_entries

                entry = random.choice(valid_entries)
                duration_seconds = random.randint(900, 14400)
                activity = MediaActivity.create_game_activity(
                    title=entry["title"],
                    platform=entry["platform"],
                    duration_seconds=duration_seconds,
                    creator=entry["creator"],
                    source=random.choice(self.sources),
                )

            # Generate a deterministic ID
            activity_dict = activity.model_dump()
            activity_dict["id"] = generate_deterministic_uuid(f"media_activity:non_match:{media_type.value}:{i}")

            non_matching_data.append(activity_dict)

        return non_matching_data

    def seed(self, seed_value: int) -> None:
        """Set the random seed for deterministic data generation.

        Args:
            seed_value: The seed value to use.
        """
        random.seed(seed_value)
