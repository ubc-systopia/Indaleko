"""Task activity collector for ablation testing."""

import random
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from ..base import ISyntheticCollector
from ..models.task_activity import TaskActivity
from ..ner.entity_manager import NamedEntityManager
from ..utils.uuid_utils import generate_deterministic_uuid


class TaskActivityCollector(ISyntheticCollector):
    """Synthetic collector for task activity."""

    def __init__(self, entity_manager: NamedEntityManager | None = None, seed_value: int | None = None):
        """Initialize the task activity collector.

        Args:
            entity_manager: Optional entity manager for consistent entity identifiers.
                           If not provided, a new one will be created.
            seed_value: Optional seed for random number generation to ensure reproducibility.
        """
        self.entity_manager = entity_manager or NamedEntityManager()
        if seed_value is not None:
            self.seed(seed_value)

        # Sample applications
        self.applications = [
            "Microsoft Word",
            "Microsoft Excel",
            "Microsoft PowerPoint",
            "Google Chrome",
            "Mozilla Firefox",
            "Visual Studio Code",
            "Slack",
            "Zoom",
            "Adobe Photoshop",
            "Outlook",
        ]

        # Map each application to sample task names
        self.tasks_by_application = {
            "Microsoft Word": [
                "Document editing",
                "Report writing",
                "Thesis drafting",
                "Letter composition",
                "Note taking",
            ],
            "Microsoft Excel": [
                "Data analysis",
                "Budget planning",
                "Spreadsheet creation",
                "Chart generation",
                "Financial modeling",
            ],
            "Microsoft PowerPoint": [
                "Presentation design",
                "Slide editing",
                "Presentation rehearsal",
                "Template creation",
                "Graphics insertion",
            ],
            "Google Chrome": ["Web browsing", "Research", "Social media", "Video streaming", "Online shopping"],
            "Mozilla Firefox": ["Web browsing", "Research", "Online banking", "Email checking", "News reading"],
            "Visual Studio Code": [
                "Code editing",
                "Debugging",
                "Git operations",
                "Terminal usage",
                "Extension management",
            ],
            "Slack": ["Team messaging", "File sharing", "Channel discussion", "Direct messaging", "Video call"],
            "Zoom": ["Video meeting", "Screen sharing", "Webinar hosting", "Conference call", "Virtual classroom"],
            "Adobe Photoshop": [
                "Image editing",
                "Photo retouching",
                "Graphic design",
                "Logo creation",
                "Banner design",
            ],
            "Outlook": [
                "Email management",
                "Calendar scheduling",
                "Meeting organization",
                "Contact management",
                "Task tracking",
            ],
        }

        # Map each application to sample window titles
        self.window_titles_by_application = {
            "Microsoft Word": [
                "Document1 - Word",
                "Annual Report 2024 - Word",
                "Project Proposal - Word",
                "Meeting Notes - Word",
                "Resume - Word",
            ],
            "Microsoft Excel": [
                "Book1 - Excel",
                "Q2 Budget - Excel",
                "Sales Data 2024 - Excel",
                "Financial Projections - Excel",
                "Inventory Tracking - Excel",
            ],
            "Microsoft PowerPoint": [
                "Presentation1 - PowerPoint",
                "Quarterly Review - PowerPoint",
                "Marketing Strategy - PowerPoint",
                "Project Overview - PowerPoint",
                "Training Materials - PowerPoint",
            ],
            "Google Chrome": [
                "Google - Google Chrome",
                "YouTube - Google Chrome",
                "GitHub - Google Chrome",
                "Stack Overflow - Google Chrome",
                "Gmail - Google Chrome",
            ],
            "Mozilla Firefox": [
                "Google - Mozilla Firefox",
                "Wikipedia - Mozilla Firefox",
                "Reddit - Mozilla Firefox",
                "Amazon - Mozilla Firefox",
                "Twitter - Mozilla Firefox",
            ],
            "Visual Studio Code": [
                "index.js - Visual Studio Code",
                "main.py - Visual Studio Code",
                "README.md - Visual Studio Code",
                "package.json - Visual Studio Code",
                "styles.css - Visual Studio Code",
            ],
            "Slack": [
                "general | Indaleko | Slack",
                "development | Indaleko | Slack",
                "random | Indaleko | Slack",
                "Direct Message | Slack",
                "Slack | Indaleko",
            ],
            "Zoom": [
                "Zoom Meeting",
                "Zoom Webinar",
                "Team Standup - Zoom",
                "Client Meeting - Zoom",
                "Weekly Review - Zoom",
            ],
            "Adobe Photoshop": [
                "Untitled-1 @ 100% (RGB/8) - Adobe Photoshop",
                "logo.psd @ 200% (RGB/8) - Adobe Photoshop",
                "banner.psd @ 75% (RGB/8) - Adobe Photoshop",
                "profile_pic.psd @ 100% (RGB/8) - Adobe Photoshop",
                "mockup.psd @ 50% (RGB/8) - Adobe Photoshop",
            ],
            "Outlook": [
                "Inbox - Outlook",
                "Sent Items - Outlook",
                "Calendar - Outlook",
                "Meeting Invitation - Outlook",
                "Contacts - Outlook",
            ],
        }

        # Task sources
        self.sources = [
            "windows_task_manager",
            "mac_activity_monitor",
            "linux_process_monitor",
            "application_telemetry",
        ]

        # User names
        self.users = ["alice", "bob", "charlie", "dave", "emma", "frank", "grace"]

    def seed(self, seed_value: int) -> None:
        """Set the random seed for deterministic data generation.

        Args:
            seed_value: The seed value to use.
        """
        random.seed(seed_value)

    def collect(self) -> dict:
        """Generate synthetic task activity data.

        Returns:
            Dict: The generated task activity data.
        """
        # Select a random application
        application = random.choice(self.applications)

        # Select a random task for the application
        task_name = random.choice(self.tasks_by_application[application])

        # Select a random window title for the application
        window_title = random.choice(self.window_titles_by_application[application])

        # Generate a random duration between 1 and 120 minutes (in seconds)
        duration_seconds = random.randint(60, 7200)

        # Random active status (90% chance of being active)
        active = random.random() < 0.9

        # Select a random source
        source = random.choice(self.sources)

        # Select a random user
        user = random.choice(self.users)

        # Create a task activity
        activity = TaskActivity(
            task_name=task_name,
            application=application,
            window_title=window_title,
            duration_seconds=duration_seconds,
            active=active,
            source=source,
            user=user,
            # Add a created_at timestamp within the last 24 hours
            created_at=datetime.now(UTC) - timedelta(hours=random.randint(0, 24)),
        )

        # Register entities with the entity manager
        self.entity_manager.register_entity("application", application)

        # Return the activity as a dictionary
        return activity.dict()

    def generate_batch(self, count: int) -> list[dict[str, Any]]:
        """Generate a batch of synthetic task activity data.

        Args:
            count: Number of activity records to generate.

        Returns:
            List[Dict]: List of generated task activity data.
        """
        return [self.collect() for _ in range(count)]

    def generate_truth_data(self, query: str) -> set[UUID]:
        """Generate truth data for a task-related query.

        This method identifies which task activities should match the query.

        Args:
            query: The natural language query to generate truth data for.

        Returns:
            Set[UUID]: The set of UUIDs that should match the query.
        """
        # Generate matching data with the exact same IDs to ensure consistency
        matching_data = self.generate_matching_data(query, count=10)
        matching_entities = set()
        
        # Extract IDs from the generated matching data
        for data in matching_data:
            if "id" in data:
                if isinstance(data["id"], UUID):
                    matching_entities.add(data["id"])
                else:
                    matching_entities.add(UUID(data["id"]) if isinstance(data["id"], str) else data["id"])
        
        # If there's no query terms that match anything, create at least 5 matching entities
        # This ensures we have data to measure recall against
        if not matching_entities:
            for i in range(5):
                matching_entities.add(generate_deterministic_uuid(f"task_activity:generic:{query}:{i}"))
        
        return matching_entities

    def generate_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate task activity data that should match a specific query.

        Args:
            query: The natural language query to generate matching data for.
            count: Number of matching records to generate.

        Returns:
            List[Dict]: List of generated task activity data that should match the query.
        """
        matching_data = []
        query_lower = query.lower()

        # Extract key terms from the query
        applications_in_query = [app for app in self.applications if app.lower() in query_lower]
        tasks_in_query = []
        for app, tasks in self.tasks_by_application.items():
            for task in tasks:
                if task.lower() in query_lower:
                    tasks_in_query.append((app, task))

        users_in_query = [user for user in self.users if user.lower() in query_lower]

        # Look for window title mentions
        window_titles_in_query = []
        for app, titles in self.window_titles_by_application.items():
            for title in titles:
                title_parts = title.lower().split()
                for part in title_parts:
                    if len(part) > 3 and part in query_lower:  # Only match significant words
                        window_titles_in_query.append((app, title))
                        break  # Match once per title

        for i in range(count):
            # Start with a base activity that we'll modify to match the query
            base_activity = self.collect()
            activity_dict = base_activity.copy()

            # Make the activity match the query based on extracted terms
            if applications_in_query:
                application = random.choice(applications_in_query)
                activity_dict["application"] = application

                # Update task name to match the application
                activity_dict["task_name"] = random.choice(self.tasks_by_application[application])

                # Update window title to match the application
                activity_dict["window_title"] = random.choice(self.window_titles_by_application[application])
                
                # Generate a deterministic UUID for this application activity
                activity_dict["id"] = generate_deterministic_uuid(f"task_activity:{application}:{i}")

            # If query mentions specific tasks, ensure we match
            elif tasks_in_query:
                app, task = random.choice(tasks_in_query)
                activity_dict["application"] = app
                activity_dict["task_name"] = task
                activity_dict["window_title"] = random.choice(self.window_titles_by_application[app])
                
                # Generate a deterministic UUID for this task activity
                activity_dict["id"] = generate_deterministic_uuid(f"task_activity:{app}:{task}:{i}")

            # If query mentions window titles, ensure we match
            elif window_titles_in_query:
                app, title = random.choice(window_titles_in_query)
                activity_dict["application"] = app
                activity_dict["window_title"] = title
                activity_dict["task_name"] = random.choice(self.tasks_by_application[app])
                
                # Generate a deterministic UUID for this window title activity
                activity_dict["id"] = generate_deterministic_uuid(f"task_activity:{app}:{title}:{i}")

            # If query mentions users, ensure we match
            if users_in_query:
                user = random.choice(users_in_query)
                activity_dict["user"] = user
                
                # Update ID to include user if no application/task was matched
                if "id" not in activity_dict:
                    activity_dict["id"] = generate_deterministic_uuid(f"task_activity:user:{user}:{i}")

            # Make sure created time is recent (within last 24 hours)
            activity_dict["created_at"] = (datetime.now(UTC) - timedelta(hours=random.randint(1, 24))).isoformat()
            
            # Ensure every activity has an ID
            if "id" not in activity_dict:
                # Fallback UUID if no specific entity was matched
                activity_dict["id"] = generate_deterministic_uuid(f"task_activity:generic:{i}")

            matching_data.append(activity_dict)

        return matching_data

    def generate_non_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate task activity data that should NOT match a specific query.

        Args:
            query: The natural language query to generate non-matching data for.
            count: Number of non-matching records to generate.

        Returns:
            List[Dict]: List of generated task activity data that should NOT match the query.
        """
        non_matching_data = []
        query_lower = query.lower()

        # Extract key terms from the query
        applications_in_query = [app for app in self.applications if app.lower() in query_lower]
        users_in_query = [user for user in self.users if user.lower() in query_lower]

        for _ in range(count):
            # Generate a base activity
            base_activity = self.collect()
            activity_dict = base_activity.copy()

            # Ensure application doesn't match query
            if applications_in_query:
                excluded_applications = [app for app in self.applications if app not in applications_in_query]
                if excluded_applications:
                    application = random.choice(excluded_applications)
                    activity_dict["application"] = application

                    # Update task name to match the application
                    activity_dict["task_name"] = random.choice(self.tasks_by_application[application])

                    # Update window title to match the application
                    activity_dict["window_title"] = random.choice(self.window_titles_by_application[application])

            # Ensure user doesn't match query
            if users_in_query:
                excluded_users = [user for user in self.users if user not in users_in_query]
                if excluded_users:
                    activity_dict["user"] = random.choice(excluded_users)

            # Set created_at to a time outside the typical query window (much older)
            activity_dict["created_at"] = (datetime.now(UTC) - timedelta(days=random.randint(30, 180))).isoformat()

            non_matching_data.append(activity_dict)

        return non_matching_data
