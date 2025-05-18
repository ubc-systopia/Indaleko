"""Relationship patterns for cross-collection references in ablation testing."""

import random
import uuid
import datetime
from datetime import UTC, datetime, timedelta
from typing import Any
from enum import IntEnum

# Define the activity type as required by the schema
class ActivityType(IntEnum):
    MUSIC = 1
    LOCATION = 2
    TASK = 3
    COLLABORATION = 4
    STORAGE = 5
    MEDIA = 6

from ..registry import SharedEntityRegistry


class RelationshipPatternGenerator:
    """Base class for generating relationship patterns between collections.

    This class provides common functionality for creating realistic relationships
    between entities in different collections.
    """

    def __init__(self, entity_registry: SharedEntityRegistry | None = None):
        """Initialize the relationship pattern generator.

        Args:
            entity_registry: Optional shared entity registry. If not provided,
                            a new registry will be created.
        """
        self.entity_registry = entity_registry or SharedEntityRegistry()

    def generate_timestamp(self, days_back: int = 30) -> int:
        """Generate a random timestamp within the specified number of days.

        Args:
            days_back: Number of days back from now to generate timestamp

        Returns:
            int: Unix timestamp
        """
        now = datetime.now(UTC)
        random_days = random.randint(0, days_back)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        random_time = now - timedelta(days=random_days, hours=random_hours, minutes=random_minutes)
        return int(random_time.timestamp())

    def generate_uuid(self) -> str:
        """Generate a random UUID.

        Returns:
            str: UUID string
        """
        return str(uuid.uuid4())
        
    def prepare_for_arango(self, document: dict[str, Any]) -> dict[str, Any]:
        """Prepare a document for insertion into ArangoDB.
        
        Ensures the document has a valid _key field and references
        are properly formatted for ArangoDB.
        
        Args:
            document: The document to prepare
            
        Returns:
            Dict: The prepared document
        """
        # Make a copy to avoid modifying the original
        doc = document.copy()
        
        # Make sure the document has a _key field (derived from id if available)
        if "id" in doc and "_key" not in doc:
            doc["_key"] = doc["id"].replace("-", "")  # Remove dashes for valid ArangoDB keys
            
        # Ensure references use proper _id format if needed
        if "references" in doc:
            refs = doc["references"]
            for field, values in refs.items():
                # Skip empty references
                if not values:
                    continue
                    
                # Ensure values is a list
                if not isinstance(values, list):
                    refs[field] = [values]
        
        return doc

    def register_entities(self, entities: list[dict[str, Any]], collection_type: str) -> None:
        """Register entities in the shared registry.

        Args:
            entities: List of entity dictionaries
            collection_type: Collection type name
        """
        for entity in entities:
            entity_id = entity.get("id")
            if entity_id:
                entity_name = entity.get("title", entity.get("name", entity_id))
                # Register in the shared registry
                self.entity_registry.register_entity(collection_type, entity_name, collection_type + "Activity")


class TaskCollaborationPattern(RelationshipPatternGenerator):
    """Generator for Task+Collaboration relationship patterns.

    This class implements realistic relationships between tasks and collaboration
    activities, such as tasks assigned during meetings.
    """

    def generate_meeting_with_tasks(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Generate a meeting with assigned tasks.

        Returns:
            Tuple: (meeting_data, list_of_tasks)
        """
        # Generate a basic meeting
        meeting = self._generate_basic_meeting()
        tasks = []

        # Generate 1-5 tasks from this meeting
        for i in range(random.randint(1, 5)):
            task = {
                "id": self.generate_uuid(),
                "task_name": f"Task {i+1} from {meeting['event_type']}",
                "application": "Task Management System",
                "window_title": f"{meeting['event_type']} - Task {i+1}",
                "duration_seconds": random.randint(300, 1800),
                "active": True,
                "source": "ablation_synthetic_generator",
                "timestamp": meeting["timestamp"] + random.randint(300, 1800),
                "semantic_attributes": {},
                "references": {"created_in": [meeting["id"]]},
            }
            tasks.append(task)

        # Add references to meeting
        if "references" not in meeting:
            meeting["references"] = {}
        meeting["references"]["has_tasks"] = [t["id"] for t in tasks]

        # Register entities
        self.register_entities([meeting], "Collaboration")
        self.register_entities(tasks, "Task")

        # Add relationships in the registry
        meeting_id = uuid.UUID(meeting["id"])
        for task in tasks:
            task_id = uuid.UUID(task["id"])
            # Task was created in meeting
            self.entity_registry.add_relationship(task_id, meeting_id, "created_in")
            # Meeting has task
            self.entity_registry.add_relationship(meeting_id, task_id, "has_tasks")
            
        # Prepare documents for ArangoDB
        meeting = self.prepare_for_arango(meeting)
        prepared_tasks = [self.prepare_for_arango(task) for task in tasks]

        return meeting, prepared_tasks

    def generate_task_with_related_meetings(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Generate a task with related meetings (discussion, follow-up, etc.).

        Returns:
            Tuple: (task_data, list_of_meetings)
        """
        # Generate a basic task
        task = self._generate_basic_task()
        meetings = []

        # Generate 2-3 related meetings
        meeting_types = ["planning", "discussion", "review", "status_update"]
        used_types = random.sample(meeting_types, min(3, len(meeting_types)))

        for i, meeting_type in enumerate(used_types):
            # Create the meeting
            meeting = {
                "id": self.generate_uuid(),
                "platform": "Teams",
                "event_type": meeting_type,
                "participants": self._generate_participants(2, 5),
                "content": f"Meeting about {task['task_name']}",
                "duration_seconds": random.randint(900, 3600),  # 15-60 minutes
                "source": "ablation_synthetic_generator",
                "timestamp": task["timestamp"] + (i + 1) * random.randint(86400, 172800),  # 1-2 days after task
                "semantic_attributes": {},
                "references": {"related_to": [task["id"]]},
            }
            meetings.append(meeting)

        # Add references to task
        if "references" not in task:
            task["references"] = {}
        task["references"]["discussed_in"] = [m["id"] for m in meetings]

        # Register entities
        self.register_entities([task], "Task")
        self.register_entities(meetings, "Collaboration")

        # Add relationships in the registry
        task_id = uuid.UUID(task["id"])
        for meeting in meetings:
            meeting_id = uuid.UUID(meeting["id"])
            # Task discussed in meeting
            self.entity_registry.add_relationship(task_id, meeting_id, "discussed_in")
            # Meeting related to task
            self.entity_registry.add_relationship(meeting_id, task_id, "related_to")
            
        # Prepare documents for ArangoDB
        task = self.prepare_for_arango(task)
        prepared_meetings = [self.prepare_for_arango(meeting) for meeting in meetings]

        return task, prepared_meetings

    def _generate_basic_meeting(self) -> dict[str, Any]:
        """Generate a basic meeting entity.

        Returns:
            Dict: Meeting data
        """
        import datetime
        from enum import IntEnum
        
        # Define the activity type as required by the schema
        class ActivityType(IntEnum):
            MUSIC = 1
            LOCATION = 2
            TASK = 3
            COLLABORATION = 4
            STORAGE = 5
            MEDIA = 6
            
        meeting_types = ["standup", "planning", "retrospective", "1on1", "team_meeting", "customer_call"]
        meeting_type = random.choice(meeting_types)
        
        # Generate timestamps in ISO format for created_at and modified_at
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return {
            "id": self.generate_uuid(),
            "activity_type": ActivityType.COLLABORATION,  # Required by schema
            "created_at": now,  # Required by schema
            "modified_at": now,  # Required by schema
            "platform": random.choice(["Teams", "Zoom", "Slack", "Meet"]),
            "event_type": meeting_type,
            "participants": self._generate_participants(2, 8),
            "content": f"{meeting_type} meeting with team",
            "duration_seconds": random.randint(900, 7200),  # 15-120 minutes
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(),
            "semantic_attributes": {},
        }

    def _generate_basic_task(self) -> dict[str, Any]:
        """Generate a basic task entity.

        Returns:
            Dict: Task data
        """
        task_types = ["feature", "bug", "documentation", "research", "design", "testing"]
        task_type = random.choice(task_types)
        applications = ["JIRA", "Trello", "Asana", "Monday", "MS Project"]

        return {
            "id": self.generate_uuid(),
            "task_name": f"{task_type.title()} task",
            "application": random.choice(applications),
            "window_title": f"{task_type.title()} Task - Project XYZ",
            "duration_seconds": random.randint(300, 7200),  # 5-120 minutes
            "active": True,
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(),
            "semantic_attributes": {},
        }

    def _generate_participants(self, min_count: int = 2, max_count: int = 8) -> list[dict[str, str]]:
        """Generate a list of meeting participants.

        Args:
            min_count: Minimum number of participants
            max_count: Maximum number of participants

        Returns:
            List: Participant data
        """
        participants_list = [
            {"name": "John Smith", "email": "john.smith@example.com"},
            {"name": "Jane Doe", "email": "jane.doe@example.com"},
            {"name": "Alice Johnson", "email": "alice.johnson@example.com"},
            {"name": "Bob Brown", "email": "bob.brown@example.com"},
            {"name": "Charlie Davis", "email": "charlie.davis@example.com"},
            {"name": "Diana Wilson", "email": "diana.wilson@example.com"},
            {"name": "Edward Garcia", "email": "edward.garcia@example.com"},
            {"name": "Fiona Martinez", "email": "fiona.martinez@example.com"},
            {"name": "George Lee", "email": "george.lee@example.com"},
            {"name": "Hannah Kim", "email": "hannah.kim@example.com"},
        ]

        count = random.randint(min_count, min(max_count, len(participants_list)))
        return random.sample(participants_list, count)


class LocationCollaborationPattern(RelationshipPatternGenerator):
    """Generator for Location+Collaboration relationship patterns.

    This class implements realistic relationships between locations and collaboration
    activities, such as meetings at specific locations.
    """

    def generate_meeting_at_location(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate a meeting at a specific location.

        Returns:
            Tuple: (location_data, meeting_data)
        """
        # Generate a basic location
        location = self._generate_basic_location()

        # Generate a meeting at this location
        meeting = {
            "id": self.generate_uuid(),
            "platform": "In-person",
            "event_type": random.choice(["meeting", "workshop", "conference", "team_building"]),
            "participants": self._generate_participants(2, 8),
            "content": f"Meeting at {location['location_name']}",
            "duration_seconds": random.randint(1800, 7200),  # 30-120 minutes
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(),
            "semantic_attributes": {},
            "references": {"located_at": [location["id"]]},
        }

        # Add references to location
        if "references" not in location:
            location["references"] = {}
        if "hosted_meetings" not in location["references"]:
            location["references"]["hosted_meetings"] = []
        location["references"]["hosted_meetings"].append(meeting["id"])

        # Register entities
        self.register_entities([location], "Location")
        self.register_entities([meeting], "Collaboration")

        # Add relationships in the registry
        location_id = uuid.UUID(location["id"])
        meeting_id = uuid.UUID(meeting["id"])
        # Meeting located at location
        self.entity_registry.add_relationship(meeting_id, location_id, "located_at")
        # Location hosted meeting
        self.entity_registry.add_relationship(location_id, meeting_id, "hosted_meetings")
        
        # Prepare documents for ArangoDB
        location = self.prepare_for_arango(location)
        meeting = self.prepare_for_arango(meeting)

        return location, meeting

    def _generate_basic_location(self) -> dict[str, Any]:
        """Generate a basic location entity.

        Returns:
            Dict: Location data
        """
        location_types = ["office", "meeting_room", "conference_center", "coffee_shop", "home_office"]
        location_type = random.choice(location_types)
        location_names = {
            "office": ["Headquarters", "Downtown Office", "Tech Park Office", "Corporate Office"],
            "meeting_room": ["Board Room", "Main Conference Room", "Meeting Room A", "Collaboration Space"],
            "conference_center": ["Convention Center", "Tech Hub", "Innovation Center", "Summit Hall"],
            "coffee_shop": ["Coffee Shop", "Café Central", "Espresso Bar", "Bean & Brew"],
            "home_office": ["Home Office", "Remote Workspace", "Home Study", "Remote Setup"],
        }

        name = random.choice(location_names.get(location_type, ["Unknown Location"]))

        return {
            "id": self.generate_uuid(),
            "location_name": name,
            "location_type": location_type,
            "coordinates": {"latitude": random.uniform(30.0, 45.0), "longitude": random.uniform(-120.0, -70.0)},
            "device_name": random.choice(["iPhone", "Android", "Laptop", "Desktop"]),
            "wifi_ssid": random.choice(["Office_WiFi", "Guest_Network", "Home_Network", None]),
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(days_back=90),  # Locations exist longer
            "semantic_attributes": {},
        }

    def _generate_participants(self, min_count: int = 2, max_count: int = 8) -> list[dict[str, str]]:
        """Generate a list of meeting participants.

        Args:
            min_count: Minimum number of participants
            max_count: Maximum number of participants

        Returns:
            List: Participant data
        """
        participants_list = [
            {"name": "John Smith", "email": "john.smith@example.com"},
            {"name": "Jane Doe", "email": "jane.doe@example.com"},
            {"name": "Alice Johnson", "email": "alice.johnson@example.com"},
            {"name": "Bob Brown", "email": "bob.brown@example.com"},
            {"name": "Charlie Davis", "email": "charlie.davis@example.com"},
            {"name": "Diana Wilson", "email": "diana.wilson@example.com"},
            {"name": "Edward Garcia", "email": "edward.garcia@example.com"},
            {"name": "Fiona Martinez", "email": "fiona.martinez@example.com"},
            {"name": "George Lee", "email": "george.lee@example.com"},
            {"name": "Hannah Kim", "email": "hannah.kim@example.com"},
        ]

        count = random.randint(min_count, min(max_count, len(participants_list)))
        return random.sample(participants_list, count)


class MusicLocationPattern(RelationshipPatternGenerator):
    """Generator for Music+Location relationship patterns.

    This class implements realistic relationships between music and location
    activities, such as listening to music at specific locations.
    """

    def generate_music_at_location(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate a music activity at a specific location.

        Returns:
            Tuple: (location_data, music_data)
        """
        # Generate a basic location
        location = self._generate_basic_location()

        # Generate a music activity at this location
        music = self._generate_basic_music_activity()

        # Add references to connect entities
        if "references" not in music:
            music["references"] = {}
        music["references"]["listened_at"] = [location["id"]]

        if "references" not in location:
            location["references"] = {}
        if "music_activities" not in location["references"]:
            location["references"]["music_activities"] = []
        location["references"]["music_activities"].append(music["id"])

        # Register entities
        self.register_entities([location], "Location")
        self.register_entities([music], "Music")

        # Add relationships in the registry
        location_id = uuid.UUID(location["id"])
        music_id = uuid.UUID(music["id"])

        # Music listened at location
        self.entity_registry.add_relationship(music_id, location_id, "listened_at")

        # Location has music activity
        self.entity_registry.add_relationship(location_id, music_id, "music_activities")

        # Prepare documents for ArangoDB
        location = self.prepare_for_arango(location)
        music = self.prepare_for_arango(music)

        return location, music

    def _generate_basic_location(self) -> dict[str, Any]:
        """Generate a basic location entity.

        Returns:
            Dict: Location data
        """
        import datetime
        from enum import IntEnum
        
        # Define the activity type as required by the schema
        class ActivityType(IntEnum):
            MUSIC = 1
            LOCATION = 2
            TASK = 3
            COLLABORATION = 4
            STORAGE = 5
            MEDIA = 6
        
        location_types = ["home", "gym", "cafe", "commute", "office", "park"]
        location_type = random.choice(location_types)
        location_names = {
            "home": ["Home", "Apartment", "Living Room", "Kitchen"],
            "gym": ["Fitness Center", "Gym", "Yoga Studio", "Weight Room"],
            "cafe": ["Coffee Shop", "Café", "Bistro", "Restaurant"],
            "commute": ["Car", "Train", "Bus", "Subway"],
            "office": ["Office", "Workspace", "Co-working Space", "Conference Room"],
            "park": ["Park", "Outdoor Trail", "Beach", "Garden"],
        }

        name = random.choice(location_names.get(location_type, ["Unknown Location"]))
        
        # Generate timestamps in ISO format for created_at and modified_at
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return {
            "id": self.generate_uuid(),
            "activity_type": ActivityType.LOCATION,  # Required by schema
            "created_at": now,  # Required by schema
            "modified_at": now,  # Required by schema
            "location_name": name,
            "location_type": location_type,
            "coordinates": {"latitude": random.uniform(30.0, 45.0), "longitude": random.uniform(-120.0, -70.0)},
            "device_name": random.choice(["iPhone", "Android", "Laptop", "Desktop"]),
            "wifi_ssid": random.choice(["Home_WiFi", "Public_WiFi", "Office_Network", None]),
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(days_back=30),
            "semantic_attributes": {},
        }

    def _generate_basic_music_activity(self) -> dict[str, Any]:
        """Generate a basic music activity.

        Returns:
            Dict: Music activity data
        """
        import datetime
        from enum import IntEnum
        
        # Define the activity type as required by the schema
        class ActivityType(IntEnum):
            MUSIC = 1
            LOCATION = 2
            TASK = 3
            COLLABORATION = 4
            STORAGE = 5
            MEDIA = 6
            
        # Sample music data with popular artists and tracks
        music_samples = [
            {"artist": "Taylor Swift", "track": "Blank Space", "album": "1989", "genre": "Pop"},
            {"artist": "Ed Sheeran", "track": "Shape of You", "album": "÷", "genre": "Pop"},
            {"artist": "Drake", "track": "Hotline Bling", "album": "Views", "genre": "Hip-Hop"},
            {"artist": "Adele", "track": "Hello", "album": "25", "genre": "Pop"},
            {"artist": "The Weeknd", "track": "Blinding Lights", "album": "After Hours", "genre": "R&B"},
            {"artist": "Billie Eilish", "track": "Bad Guy", "album": "When We All Fall Asleep", "genre": "Alternative"},
            {"artist": "Kendrick Lamar", "track": "HUMBLE.", "album": "DAMN.", "genre": "Hip-Hop"},
            {"artist": "Dua Lipa", "track": "Don't Start Now", "album": "Future Nostalgia", "genre": "Pop"},
            {"artist": "Post Malone", "track": "Circles", "album": "Hollywood's Bleeding", "genre": "Pop/Hip-Hop"},
            {"artist": "BTS", "track": "Dynamite", "album": "BE", "genre": "K-Pop"},
        ]

        # Select a random sample
        music_data = random.choice(music_samples)
        
        # Generate timestamps in ISO format for created_at and modified_at
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return {
            "id": self.generate_uuid(),
            "activity_type": ActivityType.MUSIC,  # Required by schema
            "created_at": now,  # Required by schema
            "modified_at": now,  # Required by schema  
            "artist": music_data["artist"],
            "track": music_data["track"],
            "album": music_data["album"],
            "genre": music_data["genre"],
            "duration_seconds": random.randint(180, 420),  # 3-7 minutes
            "platform": random.choice(["Spotify", "Apple Music", "YouTube Music", "Amazon Music", "Pandora"]),
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(),
            "semantic_attributes": {},
        }


class MusicTaskPattern(RelationshipPatternGenerator):
    """Generator for Music+Task relationship patterns.

    This class implements realistic relationships between music and task
    activities, such as listening to music while working on tasks.
    """

    def generate_music_during_task(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Generate music listened to during a task.

        Returns:
            Tuple: (task_data, music_data)
        """
        # Generate a basic task
        task = self._generate_basic_task()

        # Generate music activity that occurred during the task
        music = self._generate_basic_music_activity()

        # Align timestamps (music during task)
        task_start = task["timestamp"]
        task_end = task_start + task["duration_seconds"]
        music["timestamp"] = random.randint(task_start, max(task_start, task_end - music["duration_seconds"]))

        # Add references to connect entities
        if "references" not in music:
            music["references"] = {}
        music["references"]["played_during"] = [task["id"]]

        if "references" not in task:
            task["references"] = {}
        if "background_music" not in task["references"]:
            task["references"]["background_music"] = []
        task["references"]["background_music"].append(music["id"])

        # Register entities
        self.register_entities([task], "Task")
        self.register_entities([music], "Music")

        # Add relationships in the registry
        task_id = uuid.UUID(task["id"])
        music_id = uuid.UUID(music["id"])

        # Music played during task
        self.entity_registry.add_relationship(music_id, task_id, "played_during")

        # Task has background music
        self.entity_registry.add_relationship(task_id, music_id, "background_music")
        
        # Prepare documents for ArangoDB
        task = self.prepare_for_arango(task)
        music = self.prepare_for_arango(music)

        return task, music

    def generate_task_playlist(self) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Generate a task with a playlist of music.

        Returns:
            Tuple: (task_data, list_of_music_activities)
        """
        # Generate a basic task
        task = self._generate_basic_task()
        music_activities = []

        # Generate 3-7 music tracks for this task
        num_tracks = random.randint(3, 7)
        task_start = task["timestamp"]
        current_time = task_start

        for i in range(num_tracks):
            music = self._generate_basic_music_activity()

            # Set timestamp to be in sequence
            music["timestamp"] = current_time
            current_time += music["duration_seconds"]

            # Add reference to task
            if "references" not in music:
                music["references"] = {}
            music["references"]["played_during"] = [task["id"]]

            music_activities.append(music)

        # Set task duration to match full playlist length if needed
        playlist_duration = sum(music["duration_seconds"] for music in music_activities)
        if playlist_duration > task["duration_seconds"]:
            task["duration_seconds"] = playlist_duration

        # Add references to task
        if "references" not in task:
            task["references"] = {}
        task["references"]["background_music"] = [m["id"] for m in music_activities]

        # Register entities
        self.register_entities([task], "Task")
        self.register_entities(music_activities, "Music")

        # Add relationships in the registry
        task_id = uuid.UUID(task["id"])
        for music in music_activities:
            music_id = uuid.UUID(music["id"])

            # Music played during task
            self.entity_registry.add_relationship(music_id, task_id, "played_during")

            # Task has background music
            self.entity_registry.add_relationship(task_id, music_id, "background_music")
            
        # Prepare documents for ArangoDB
        task = self.prepare_for_arango(task)
        prepared_music_activities = [self.prepare_for_arango(music) for music in music_activities]

        return task, prepared_music_activities

    def _generate_basic_task(self) -> dict[str, Any]:
        """Generate a basic task entity.

        Returns:
            Dict: Task data
        """
        import datetime
        from enum import IntEnum
        
        # Define the activity type as required by the schema
        class ActivityType(IntEnum):
            MUSIC = 1
            LOCATION = 2
            TASK = 3
            COLLABORATION = 4
            STORAGE = 5
            MEDIA = 6
            
        task_types = ["coding", "writing", "reading", "design", "study", "research"]
        task_type = random.choice(task_types)
        applications = ["VS Code", "Word", "Chrome", "Figma", "PDF Reader", "Excel"]
        
        # Generate timestamps in ISO format for created_at and modified_at
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        return {
            "id": self.generate_uuid(),
            "activity_type": ActivityType.TASK,  # Required by schema
            "created_at": now,  # Required by schema
            "modified_at": now,  # Required by schema
            "task_name": f"{task_type.title()} task",
            "application": random.choice(applications),
            "window_title": f"{task_type.title()} - Project Work",
            "duration_seconds": random.randint(1800, 7200),  # 30-120 minutes
            "active": True,
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(),
            "semantic_attributes": {},
        }

    def _generate_basic_music_activity(self) -> dict[str, Any]:
        """Generate a basic music activity.

        Returns:
            Dict: Music activity data
        """
        # Music genres for productivity
        productivity_music = [
            {"artist": "Lo-Fi Beats", "track": "Study Session", "album": "Focus Playlist", "genre": "Lo-Fi"},
            {"artist": "Hans Zimmer", "track": "Time", "album": "Inception", "genre": "Soundtrack"},
            {"artist": "Bonobo", "track": "Cirrus", "album": "The North Borders", "genre": "Electronic"},
            {"artist": "Tycho", "track": "Awake", "album": "Awake", "genre": "Ambient"},
            {
                "artist": "Max Richter",
                "track": "On the Nature of Daylight",
                "album": "The Blue Notebooks",
                "genre": "Classical",
            },
            {"artist": "Brian Eno", "track": "An Ending (Ascent)", "album": "Apollo", "genre": "Ambient"},
            {
                "artist": "Explosions in the Sky",
                "track": "Your Hand in Mine",
                "album": "The Earth Is Not a Cold Dead Place",
                "genre": "Post-Rock",
            },
            {"artist": "Nils Frahm", "track": "Says", "album": "Spaces", "genre": "Modern Classical"},
            {"artist": "Four Tet", "track": "Angel Echoes", "album": "There Is Love in You", "genre": "Electronic"},
            {"artist": "Ludovico Einaudi", "track": "Experience", "album": "In a Time Lapse", "genre": "Classical"},
        ]

        # Select a random sample
        music_data = random.choice(productivity_music)

        return {
            "id": self.generate_uuid(),
            "artist": music_data["artist"],
            "track": music_data["track"],
            "album": music_data["album"],
            "genre": music_data["genre"],
            "duration_seconds": random.randint(180, 600),  # 3-10 minutes
            "platform": random.choice(["Spotify", "Apple Music", "YouTube Music", "Amazon Music", "Pandora"]),
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(),
            "semantic_attributes": {},
        }
