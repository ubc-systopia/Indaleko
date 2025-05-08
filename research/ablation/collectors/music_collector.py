"""Music activity collector for ablation testing."""

import random
from datetime import UTC, datetime, timedelta
from typing import Any, List, Set
from uuid import UUID

from ..base import ISyntheticCollector
from ..models.music_activity import MusicActivity
from ..ner.entity_manager import NamedEntityManager
from ..utils.uuid_utils import generate_deterministic_uuid


class MusicActivityCollector(ISyntheticCollector):
    """Synthetic collector for music listening activity."""

    def __init__(self, entity_manager: NamedEntityManager | None = None, seed_value: int = 42):
        """Initialize the music activity collector.

        Args:
            entity_manager: Optional entity manager for consistent entity identifiers.
                           If not provided, a new one will be created.
            seed_value: Random seed for deterministic data generation.
        """
        self.entity_manager = entity_manager or NamedEntityManager()
        self.seed(seed_value)

        # Sample music data
        self.artists = [
            "Taylor Swift",
            "The Beatles",
            "Beyoncé",
            "Drake",
            "Ed Sheeran",
            "Adele",
            "Kendrick Lamar",
            "Billie Eilish",
            "Queen",
            "Ariana Grande",
        ]

        self.tracks_by_artist = {
            "Taylor Swift": ["Blank Space", "Shake It Off", "Love Story", "You Belong With Me", "All Too Well"],
            "The Beatles": ["Hey Jude", "Let It Be", "Yesterday", "Come Together", "Here Comes The Sun"],
            "Beyoncé": ["Single Ladies", "Halo", "Crazy In Love", "Formation", "Irreplaceable"],
            "Drake": ["Hotline Bling", "God's Plan", "In My Feelings", "Started From The Bottom", "One Dance"],
            "Ed Sheeran": ["Shape of You", "Perfect", "Thinking Out Loud", "Photograph", "Castle on the Hill"],
            "Adele": ["Hello", "Rolling in the Deep", "Someone Like You", "Set Fire to the Rain", "Easy On Me"],
            "Kendrick Lamar": ["HUMBLE.", "DNA.", "Alright", "Swimming Pools", "King Kunta"],
            "Billie Eilish": ["bad guy", "Happier Than Ever", "when the party's over", "Ocean Eyes", "Therefore I Am"],
            "Queen": [
                "Bohemian Rhapsody",
                "We Will Rock You",
                "Don't Stop Me Now",
                "Another One Bites the Dust",
                "We Are The Champions",
            ],
            "Ariana Grande": ["Thank U, Next", "7 Rings", "Into You", "Side To Side", "No Tears Left To Cry"],
        }

        self.albums_by_artist = {
            "Taylor Swift": ["1989", "Red", "Fearless", "Lover", "Folklore"],
            "The Beatles": [
                "Abbey Road",
                "Sgt. Pepper's Lonely Hearts Club Band",
                "The White Album",
                "Revolver",
                "Let It Be",
            ],
            "Beyoncé": ["Lemonade", "Beyoncé", "I Am... Sasha Fierce", "B'Day", "Renaissance"],
            "Drake": ["Scorpion", "Views", "Take Care", "Nothing Was the Same", "Certified Lover Boy"],
            "Ed Sheeran": ["÷ (Divide)", "× (Multiply)", "+ (Plus)", "= (Equals)", "No.6 Collaborations Project"],
            "Adele": ["25", "21", "19", "30", "Adele Live at the Royal Albert Hall"],
            "Kendrick Lamar": [
                "DAMN.",
                "To Pimp a Butterfly",
                "good kid, m.A.A.d city",
                "Section.80",
                "Mr. Morale & the Big Steppers",
            ],
            "Billie Eilish": [
                "When We All Fall Asleep, Where Do We Go?",
                "Happier Than Ever",
                "Don't Smile at Me",
                "Live at Third Man Records",
                "Guitar Songs",
            ],
            "Queen": ["A Night at the Opera", "News of the World", "The Game", "A Kind of Magic", "Innuendo"],
            "Ariana Grande": ["Thank U, Next", "Sweetener", "Dangerous Woman", "My Everything", "Positions"],
        }

        self.genres_by_artist = {
            "Taylor Swift": ["Pop", "Country", "Folk", "Alternative"],
            "The Beatles": ["Rock", "Pop Rock", "Psychedelic Rock", "Experimental"],
            "Beyoncé": ["R&B", "Pop", "Hip Hop", "Soul"],
            "Drake": ["Hip Hop", "R&B", "Rap", "Pop Rap"],
            "Ed Sheeran": ["Pop", "Folk Pop", "Acoustic", "R&B"],
            "Adele": ["Pop", "Soul", "R&B", "Jazz"],
            "Kendrick Lamar": ["Hip Hop", "Rap", "West Coast Hip Hop", "Conscious Hip Hop"],
            "Billie Eilish": ["Pop", "Electropop", "Alternative", "Indie Pop"],
            "Queen": ["Rock", "Hard Rock", "Glam Rock", "Progressive Rock"],
            "Ariana Grande": ["Pop", "R&B", "Dance Pop", "Trap Pop"],
        }

        self.platforms = ["Spotify", "Apple Music", "YouTube Music", "Amazon Music", "Tidal"]

    def collect(self) -> dict:
        """Generate synthetic music activity data.

        Returns:
            Dict: The generated music activity data.
        """
        # Select a random artist
        artist = random.choice(self.artists)

        # Select a random track by the artist
        track = random.choice(self.tracks_by_artist[artist])

        # Select a random album by the artist
        album = random.choice(self.albums_by_artist[artist])

        # Select a random genre for the artist
        genre = random.choice(self.genres_by_artist[artist])

        # Generate a random duration between 2 and 5 minutes
        duration_seconds = random.randint(120, 300)

        # Select a random platform
        platform = random.choice(self.platforms)

        # Create a music activity
        activity = MusicActivity(
            artist=artist,
            track=track,
            album=album,
            genre=genre,
            duration_seconds=duration_seconds,
            platform=platform,
            # Add a created_at timestamp within the last 24 hours
            created_at=datetime.now(UTC) - timedelta(hours=random.randint(0, 24)),
        )

        # Register entities with the entity manager
        self.entity_manager.register_entity("artist", artist)

        # Return the activity as a dictionary
        return activity.dict()

    def generate_truth_data(self, query: str) -> set[UUID]:
        """Generate truth data for a music-related query.

        This method identifies which music activities should match the query.

        Args:
            query: The natural language query to generate truth data for.

        Returns:
            Set[UUID]: The set of UUIDs that should match the query.
        """
        # This is a placeholder implementation
        # In a real implementation, this would analyze the query and identify matching entities
        matching_entities = set()

        # Simple keyword matching for demonstration purposes
        query_lower = query.lower()

        # Check for artist mentions
        for artist in self.artists:
            if artist.lower() in query_lower:
                # Generate deterministic UUIDs for activities with this artist
                for i in range(5):  # Generate 5 matching activities
                    entity_id = generate_deterministic_uuid(f"music_activity:{artist}:{i}")
                    matching_entities.add(entity_id)

        # Check for track mentions
        for artist, tracks in self.tracks_by_artist.items():
            for track in tracks:
                if track.lower() in query_lower:
                    # Generate a deterministic UUID for this track
                    entity_id = generate_deterministic_uuid(f"music_activity:{artist}:{track}")
                    matching_entities.add(entity_id)

        # Check for genre mentions
        for artist, genres in self.genres_by_artist.items():
            for genre in genres:
                if genre.lower() in query_lower:
                    # Generate deterministic UUIDs for activities with this genre
                    for i in range(3):  # Generate 3 matching activities per genre
                        entity_id = generate_deterministic_uuid(f"music_activity:{genre}:{i}")
                        matching_entities.add(entity_id)

        return matching_entities
        
    def generate_batch(self, count: int) -> List[dict[str, Any]]:
        """Generate a batch of synthetic music activity data.

        Args:
            count: Number of music activity records to generate.

        Returns:
            List[Dict]: List of generated music activity data.
        """
        return [self.collect() for _ in range(count)]
        
    def generate_matching_data(self, query: str, count: int = 1) -> List[dict[str, Any]]:
        """Generate music activity data that should match a specific query.

        Args:
            query: The natural language query to generate matching data for.
            count: Number of matching records to generate.

        Returns:
            List[Dict]: List of generated music activity data that should match the query.
        """
        query_lower = query.lower()
        matching_data = []
        
        # Extract key terms from the query
        for artist in self.artists:
            if artist.lower() in query_lower:
                # Generate data for this artist
                for _ in range(count):
                    track = random.choice(self.tracks_by_artist[artist])
                    album = random.choice(self.albums_by_artist[artist])
                    genre = random.choice(self.genres_by_artist[artist])
                    
                    activity = MusicActivity(
                        artist=artist,
                        track=track,
                        album=album,
                        genre=genre,
                        duration_seconds=random.randint(120, 300),
                        platform=random.choice(self.platforms),
                        created_at=datetime.now(UTC) - timedelta(hours=random.randint(0, 24)),
                    )
                    
                    # Generate a deterministic ID
                    activity_dict = activity.dict()
                    activity_dict["id"] = generate_deterministic_uuid(
                        f"music_activity:{artist}:{track}:{len(matching_data)}"
                    )
                    
                    matching_data.append(activity_dict)
                    
                    # If we have enough matching data, return it
                    if len(matching_data) >= count:
                        return matching_data
        
        # If we didn't find any matching artists, generate generic matching data
        while len(matching_data) < count:
            data = self.collect()
            data["id"] = generate_deterministic_uuid(f"music_activity:generic_match:{len(matching_data)}")
            matching_data.append(data)
            
        return matching_data
        
    def generate_non_matching_data(self, query: str, count: int = 1) -> List[dict[str, Any]]:
        """Generate music activity data that should NOT match a specific query.

        Args:
            query: The natural language query to generate non-matching data for.
            count: Number of non-matching records to generate.

        Returns:
            List[Dict]: List of generated music activity data that should NOT match the query.
        """
        query_lower = query.lower()
        non_matching_data = []
        
        # Find artists NOT mentioned in the query
        non_matching_artists = [
            artist for artist in self.artists 
            if artist.lower() not in query_lower
        ]
        
        if not non_matching_artists:
            # Fallback if all artists are mentioned
            non_matching_artists = self.artists
        
        # Generate data for non-matching artists
        for _ in range(count):
            artist = random.choice(non_matching_artists)
            track = random.choice(self.tracks_by_artist[artist])
            album = random.choice(self.albums_by_artist[artist])
            genre = random.choice(self.genres_by_artist[artist])
            
            activity = MusicActivity(
                artist=artist,
                track=track,
                album=album,
                genre=genre,
                duration_seconds=random.randint(120, 300),
                platform=random.choice(self.platforms),
                # Make non-matching data from longer ago for temporal difference
                created_at=datetime.now(UTC) - timedelta(days=random.randint(10, 30)),
            )
            
            # Generate a deterministic ID
            activity_dict = activity.dict()
            activity_dict["id"] = generate_deterministic_uuid(
                f"music_activity:non_match:{artist}:{track}:{len(non_matching_data)}"
            )
            
            non_matching_data.append(activity_dict)
        
        return non_matching_data
    
    def seed(self, seed_value: int) -> None:
        """Set the random seed for deterministic data generation.

        Args:
            seed_value: The seed value to use.
        """
        random.seed(seed_value)
