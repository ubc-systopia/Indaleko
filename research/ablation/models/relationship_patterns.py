"""Relationship patterns for cross-collection references in ablation testing."""

import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Any, Optional

from ..registry import SharedEntityRegistry
from ..utils.semantic_attributes import SemanticAttributeRegistry


class RelationshipPatternGenerator:
    """Base class for generating relationship patterns between collections.
    
    This class provides common functionality for creating realistic relationships
    between entities in different collections.
    """
    
    def __init__(self, entity_registry: Optional[SharedEntityRegistry] = None):
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
        now = datetime.now(timezone.utc)
        random_days = random.randint(0, days_back)
        random_hours = random.randint(0, 23)
        random_minutes = random.randint(0, 59)
        random_time = now - timedelta(
            days=random_days,
            hours=random_hours,
            minutes=random_minutes
        )
        return int(random_time.timestamp())
    
    def generate_uuid(self) -> str:
        """Generate a random UUID.
        
        Returns:
            str: UUID string
        """
        return str(uuid.uuid4())
    
    def register_entities(self, entities: List[Dict[str, Any]], collection_type: str) -> None:
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
                self.entity_registry.register_entity(
                    collection_type, 
                    entity_name, 
                    collection_type + "Activity"
                )


class TaskCollaborationPattern(RelationshipPatternGenerator):
    """Generator for Task+Collaboration relationship patterns.
    
    This class implements realistic relationships between tasks and collaboration
    activities, such as tasks assigned during meetings.
    """
    
    def generate_meeting_with_tasks(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
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
                "references": {
                    "created_in": [meeting["id"]]
                }
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
            self.entity_registry.add_relationship(
                task_id, 
                meeting_id, 
                "created_in"
            )
            # Meeting has task
            self.entity_registry.add_relationship(
                meeting_id, 
                task_id, 
                "has_tasks"
            )
        
        return meeting, tasks
    
    def generate_task_with_related_meetings(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
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
                "timestamp": task["timestamp"] + (i+1) * random.randint(86400, 172800),  # 1-2 days after task
                "semantic_attributes": {},
                "references": {
                    "related_to": [task["id"]]
                }
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
            self.entity_registry.add_relationship(
                task_id, 
                meeting_id, 
                "discussed_in"
            )
            # Meeting related to task
            self.entity_registry.add_relationship(
                meeting_id, 
                task_id, 
                "related_to"
            )
        
        return task, meetings
    
    def _generate_basic_meeting(self) -> Dict[str, Any]:
        """Generate a basic meeting entity.
        
        Returns:
            Dict: Meeting data
        """
        meeting_types = ["standup", "planning", "retrospective", "1on1", "team_meeting", "customer_call"]
        meeting_type = random.choice(meeting_types)
        
        return {
            "id": self.generate_uuid(),
            "platform": random.choice(["Teams", "Zoom", "Slack", "Meet"]),
            "event_type": meeting_type,
            "participants": self._generate_participants(2, 8),
            "content": f"{meeting_type} meeting with team",
            "duration_seconds": random.randint(900, 7200),  # 15-120 minutes
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(),
            "semantic_attributes": {}
        }
    
    def _generate_basic_task(self) -> Dict[str, Any]:
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
            "semantic_attributes": {}
        }
    
    def _generate_participants(self, min_count: int = 2, max_count: int = 8) -> List[Dict[str, str]]:
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
    
    def generate_meeting_at_location(self) -> Tuple[Dict[str, Any], Dict[str, Any]]:
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
            "references": {
                "located_at": [location["id"]]
            }
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
        self.entity_registry.add_relationship(
            meeting_id, 
            location_id, 
            "located_at"
        )
        # Location hosted meeting
        self.entity_registry.add_relationship(
            location_id, 
            meeting_id, 
            "hosted_meetings"
        )
        
        return location, meeting
    
    def _generate_basic_location(self) -> Dict[str, Any]:
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
            "home_office": ["Home Office", "Remote Workspace", "Home Study", "Remote Setup"]
        }
        
        name = random.choice(location_names.get(location_type, ["Unknown Location"]))
        
        return {
            "id": self.generate_uuid(),
            "location_name": name,
            "location_type": location_type,
            "coordinates": {
                "latitude": random.uniform(30.0, 45.0),
                "longitude": random.uniform(-120.0, -70.0)
            },
            "device_name": random.choice(["iPhone", "Android", "Laptop", "Desktop"]),
            "wifi_ssid": random.choice(["Office_WiFi", "Guest_Network", "Home_Network", None]),
            "source": "ablation_synthetic_generator",
            "timestamp": self.generate_timestamp(days_back=90),  # Locations exist longer
            "semantic_attributes": {}
        }
    
    def _generate_participants(self, min_count: int = 2, max_count: int = 8) -> List[Dict[str, str]]:
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