"""Collaboration activity collector for ablation testing."""

import random
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from ..base import ISyntheticCollector
from ..models.collaboration_activity import CollaborationActivity, Participant
from ..ner.entity_manager import NamedEntityManager
from ..utils.uuid_utils import generate_deterministic_uuid


class CollaborationActivityCollector(ISyntheticCollector):
    """Synthetic collector for collaboration activity."""

    def __init__(self, entity_manager: NamedEntityManager | None = None, seed_value: int | None = None):
        """Initialize the collaboration activity collector.

        Args:
            entity_manager: Optional entity manager for consistent entity identifiers.
                           If not provided, a new one will be created.
            seed_value: Optional seed for random number generation to ensure reproducibility.
        """
        self.entity_manager = entity_manager or NamedEntityManager()
        if seed_value is not None:
            self.seed(seed_value)

        # Sample platforms
        self.platforms = [
            "Microsoft Teams",
            "Zoom",
            "Slack",
            "Discord",
            "Outlook",
            "Google Meet",
            "WebEx",
            "Email",
            "Jira",
            "GitHub",
        ]

        # Sample event types
        self.event_types = [
            "Meeting",
            "Call",
            "Chat",
            "File Share",
            "Email",
            "Code Review",
            "Task Assignment",
            "Project Update",
            "Presentation",
            "Workshop",
        ]

        # Sample participants
        self.participants = [
            {"name": "John Smith", "email": "john.smith@example.com", "user_id": "john.smith"},
            {"name": "Jane Doe", "email": "jane.doe@example.com", "user_id": "jane.doe"},
            {"name": "Michael Johnson", "email": "michael.johnson@example.com", "user_id": "michael.johnson"},
            {"name": "Emily Davis", "email": "emily.davis@example.com", "user_id": "emily.davis"},
            {"name": "David Wilson", "email": "david.wilson@example.com", "user_id": "david.wilson"},
            {"name": "Sarah Brown", "email": "sarah.brown@example.com", "user_id": "sarah.brown"},
            {"name": "Robert Miller", "email": "robert.miller@example.com", "user_id": "robert.miller"},
            {"name": "Jennifer Anderson", "email": "jennifer.anderson@example.com", "user_id": "jennifer.anderson"},
            {"name": "Thomas Taylor", "email": "thomas.taylor@example.com", "user_id": "thomas.taylor"},
            {"name": "Lisa Martinez", "email": "lisa.martinez@example.com", "user_id": "lisa.martinez"},
        ]

        # Sample meeting topics
        self.topics = [
            "Weekly team sync",
            "Project kickoff",
            "Sprint planning",
            "Product review",
            "Design review",
            "Budget discussion",
            "Status update",
            "Customer feedback",
            "Release planning",
            "Technical discussion",
            "Architecture review",
            "Stakeholder presentation",
            "Quarterly review",
            "Feature planning",
            "Post-mortem analysis",
        ]

        # Sample projects
        self.projects = [
            "Indaleko",
            "Market Analysis",
            "Customer Portal",
            "Mobile App",
            "Website Redesign",
            "Database Migration",
            "Cloud Migration",
            "Security Audit",
            "Performance Optimization",
            "New Product Launch",
        ]

        # Sample content templates
        self.content_templates = [
            "Discussing {topic} for {project}",
            "Reviewing progress on {project}",
            "Sharing updates about {topic}",
            "Planning next steps for {project}",
            "Collaborating on {topic} for {project}",
            "Addressing issues with {project}",
            "Brainstorming ideas for {topic}",
            "Presenting findings on {project}",
            "Organizing tasks for {topic}",
            "Documenting requirements for {project}",
        ]

        # Sample sources (like applications)
        self.sources = [
            "outlook",
            "teams",
            "slack",
            "zoom",
            "discord",
            "gmail",
            "jira",
            "github",
            "confluence",
            "google_calendar",
        ]

    def seed(self, seed_value: int) -> None:
        """Set the random seed for deterministic data generation.

        Args:
            seed_value: The seed value to use.
        """
        random.seed(seed_value)

    def collect(self) -> dict:
        """Generate synthetic collaboration activity data.

        Returns:
            Dict: The generated collaboration activity data.
        """
        # Select random attributes for this collaboration
        platform = random.choice(self.platforms)
        event_type = random.choice(self.event_types)

        # Select 2-5 participants
        num_participants = random.randint(2, 5)
        participants = random.sample(self.participants, num_participants)
        participant_objects = [Participant(**p) for p in participants]

        # Generate a topic and project
        topic = random.choice(self.topics)
        project = random.choice(self.projects)

        # Generate content based on template
        content_template = random.choice(self.content_templates)
        content = content_template.format(topic=topic, project=project)

        # Generate a random duration (10-120 minutes for meetings)
        duration_seconds = random.randint(10, 120) * 60

        # Select a source
        source = random.choice(self.sources)

        # Create a collaboration activity
        activity = CollaborationActivity(
            platform=platform,
            event_type=event_type,
            participants=participant_objects,
            content=content,
            duration_seconds=duration_seconds,
            source=source,
            # Add a created_at timestamp within the last 24 hours
            created_at=datetime.now(UTC) - timedelta(hours=random.randint(0, 24)),
        )

        # Register entities with the entity manager
        self.entity_manager.register_entity("platform", platform)
        self.entity_manager.register_entity("event_type", event_type)
        self.entity_manager.register_entity("project", project)
        self.entity_manager.register_entity("topic", topic)
        for participant in participants:
            self.entity_manager.register_entity("person", participant["name"])

        # Return the activity as a dictionary
        return activity.dict()

    def generate_batch(self, count: int) -> list[dict[str, Any]]:
        """Generate a batch of synthetic collaboration activity data.

        Args:
            count: Number of activity records to generate.

        Returns:
            List[Dict]: List of generated collaboration activity data.
        """
        return [self.collect() for _ in range(count)]

    def generate_truth_data(self, query: str) -> set[UUID]:
        """Generate truth data for a collaboration-related query.

        This method identifies which collaboration activities should match the query.

        Args:
            query: The natural language query to generate truth data for.

        Returns:
            Set[UUID]: The set of UUIDs that should match the query.
        """
        matching_entities = set()
        query_lower = query.lower()

        # Check for platform mentions
        for platform in self.platforms:
            if platform.lower() in query_lower:
                # Generate deterministic UUIDs for activities on this platform
                for i in range(5):  # Generate 5 matching activities
                    entity_id = generate_deterministic_uuid(f"collaboration_activity:{platform}:{i}")
                    matching_entities.add(entity_id)

        # Check for event type mentions
        for event_type in self.event_types:
            if event_type.lower() in query_lower:
                # Generate deterministic UUIDs for activities with this event type
                for i in range(3):  # Generate 3 matching activities per type
                    entity_id = generate_deterministic_uuid(f"collaboration_activity:{event_type}:{i}")
                    matching_entities.add(entity_id)

        # Check for participant mentions
        for participant in self.participants:
            if participant["name"].lower() in query_lower or (
                participant["email"] and participant["email"].lower() in query_lower
            ):
                # Generate deterministic UUIDs for activities with this participant
                for i in range(2):  # Generate 2 matching activities per participant
                    entity_id = generate_deterministic_uuid(f"collaboration_activity:{participant['name']}:{i}")
                    matching_entities.add(entity_id)

        # Check for topic mentions
        for topic in self.topics:
            if topic.lower() in query_lower:
                # Generate deterministic UUIDs for activities with this topic
                for i in range(2):  # Generate 2 matching activities per topic
                    entity_id = generate_deterministic_uuid(f"collaboration_activity:{topic}:{i}")
                    matching_entities.add(entity_id)

        # Check for project mentions
        for project in self.projects:
            if project.lower() in query_lower:
                # Generate deterministic UUIDs for activities with this project
                for i in range(3):  # Generate 3 matching activities per project
                    entity_id = generate_deterministic_uuid(f"collaboration_activity:{project}:{i}")
                    matching_entities.add(entity_id)

        # Check for source mentions
        for source in self.sources:
            if source.lower() in query_lower:
                # Generate deterministic UUIDs for activities with this source
                for i in range(2):  # Generate 2 matching activities per source
                    entity_id = generate_deterministic_uuid(f"collaboration_activity:{source}:{i}")
                    matching_entities.add(entity_id)

        return matching_entities

    def generate_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate collaboration activity data that should match a specific query.

        Args:
            query: The natural language query to generate matching data for.
            count: Number of matching records to generate.

        Returns:
            List[Dict]: List of generated collaboration activity data that should match the query.
        """
        matching_data = []
        query_lower = query.lower()

        # Extract key terms from the query
        platforms_in_query = [platform for platform in self.platforms if platform.lower() in query_lower]
        event_types_in_query = [event_type for event_type in self.event_types if event_type.lower() in query_lower]
        participants_in_query = [
            p
            for p in self.participants
            if p["name"].lower() in query_lower or (p["email"] and p["email"].lower() in query_lower)
        ]
        topics_in_query = [topic for topic in self.topics if topic.lower() in query_lower]
        projects_in_query = [project for project in self.projects if project.lower() in query_lower]
        sources_in_query = [source for source in self.sources if source.lower() in query_lower]

        for _ in range(count):
            # Start with a base activity that we'll modify to match the query
            base_activity = self.collect()
            activity_dict = base_activity.copy()

            # Make the activity match the query based on extracted terms
            if platforms_in_query:
                activity_dict["platform"] = random.choice(platforms_in_query)

            if event_types_in_query:
                activity_dict["event_type"] = random.choice(event_types_in_query)

            if participants_in_query:
                # Ensure at least one of the selected participants is in the participants list
                participant = random.choice(participants_in_query)

                # Keep some existing participants and add the matching one
                existing_participants = activity_dict.get("participants", [])
                if isinstance(existing_participants, list) and existing_participants:
                    # Keep only 1-2 existing participants
                    if len(existing_participants) > 2:
                        existing_participants = random.sample(existing_participants, random.randint(1, 2))

                # Add the matching participant
                if isinstance(existing_participants[0], dict):
                    # If participants are dictionaries
                    if participant not in existing_participants:
                        existing_participants.append(participant)
                else:
                    # If participants are already Participant objects
                    participant_obj = Participant(**participant)
                    participant_exists = any(p.name == participant_obj.name for p in existing_participants)
                    if not participant_exists:
                        existing_participants.append(participant_obj)

                activity_dict["participants"] = existing_participants

            # Generate content that includes topics or projects from the query
            if topics_in_query or projects_in_query:
                topic = random.choice(topics_in_query) if topics_in_query else random.choice(self.topics)
                project = random.choice(projects_in_query) if projects_in_query else random.choice(self.projects)

                content_template = random.choice(self.content_templates)
                activity_dict["content"] = content_template.format(topic=topic, project=project)

            # If query mentions sources, ensure we match
            if sources_in_query:
                activity_dict["source"] = random.choice(sources_in_query)

            matching_data.append(activity_dict)

        return matching_data

    def generate_non_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate collaboration activity data that should NOT match a specific query.

        Args:
            query: The natural language query to generate non-matching data for.
            count: Number of non-matching records to generate.

        Returns:
            List[Dict]: List of generated collaboration activity data that should NOT match the query.
        """
        non_matching_data = []
        query_lower = query.lower()

        # Extract key terms from the query
        platforms_in_query = [platform for platform in self.platforms if platform.lower() in query_lower]
        event_types_in_query = [event_type for event_type in self.event_types if event_type.lower() in query_lower]
        participants_in_query = [
            p
            for p in self.participants
            if p["name"].lower() in query_lower or (p["email"] and p["email"].lower() in query_lower)
        ]
        topics_in_query = [topic for topic in self.topics if topic.lower() in query_lower]
        projects_in_query = [project for project in self.projects if project.lower() in query_lower]
        sources_in_query = [source for source in self.sources if source.lower() in query_lower]

        for _ in range(count):
            # Generate a base activity
            base_activity = self.collect()
            activity_dict = base_activity.copy()

            # Ensure platform doesn't match query
            if platforms_in_query:
                excluded_platforms = [p for p in self.platforms if p not in platforms_in_query]
                if excluded_platforms:
                    activity_dict["platform"] = random.choice(excluded_platforms)

            # Ensure event type doesn't match query
            if event_types_in_query:
                excluded_event_types = [e for e in self.event_types if e not in event_types_in_query]
                if excluded_event_types:
                    activity_dict["event_type"] = random.choice(excluded_event_types)

            # Ensure participants don't match query
            if participants_in_query:
                excluded_participants = [p for p in self.participants if p not in participants_in_query]
                if excluded_participants:
                    # Select 2-4 non-matching participants
                    num_participants = random.randint(2, 4)
                    selected_participants = random.sample(
                        excluded_participants,
                        min(num_participants, len(excluded_participants)),
                    )
                    activity_dict["participants"] = [Participant(**p) for p in selected_participants]

            # Ensure content doesn't reference topics or projects in query
            if topics_in_query or projects_in_query:
                excluded_topics = [t for t in self.topics if t not in topics_in_query]
                excluded_projects = [p for p in self.projects if p not in projects_in_query]

                if excluded_topics and excluded_projects:
                    topic = random.choice(excluded_topics)
                    project = random.choice(excluded_projects)

                    content_template = random.choice(self.content_templates)
                    activity_dict["content"] = content_template.format(topic=topic, project=project)

            # Ensure source doesn't match query
            if sources_in_query:
                excluded_sources = [s for s in self.sources if s not in sources_in_query]
                if excluded_sources:
                    activity_dict["source"] = random.choice(excluded_sources)

            # Set created_at to a time outside the typical query window (much older)
            activity_dict["created_at"] = (datetime.now(UTC) - timedelta(days=random.randint(30, 180))).isoformat()

            non_matching_data.append(activity_dict)

        return non_matching_data
