"""
Activity metadata generator agent.

This module provides an agent for generating realistic activity
metadata records for the Indaleko system, including user activities,
locations, application usage, and cross-device interactions.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

from db.db_collections import IndalekoDBCollections

from ..core.llm import LLMProvider
from ..core.tools import ToolRegistry
from .base import DomainAgent


class ActivityGeneratorAgent(DomainAgent):
    """Agent for generating activity metadata."""

    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry, config: Optional[Dict[str, Any]] = None):
        """Initialize the activity generator agent.

        Args:
            llm_provider: LLM provider instance
            tool_registry: Tool registry instance
            config: Optional agent configuration
        """
        super().__init__(llm_provider, tool_registry, config)
        self.collection_name = IndalekoDBCollections.Indaleko_ActivityContext_Collection
        self.logger = logging.getLogger(self.__class__.__name__)

        # Activity types
        self.activity_types = [
            "FileAccess", "FileEdit", "FileCreation", "FileShare",
            "EmailSend", "EmailReceive", "MeetingAttend", "MeetingCreate",
            "ApplicationUse", "WebBrowsing", "DeviceConnect", "LocationChange",
            "MediaConsumption", "Search", "MusicListening", "VideoWatching"
        ]

        # Common applications
        self.applications = {
            "Productivity": ["Microsoft Word", "Microsoft Excel", "Microsoft PowerPoint", "Google Docs", "Google Sheets", "LibreOffice Writer"],
            "Development": ["Visual Studio Code", "PyCharm", "IntelliJ IDEA", "Sublime Text", "Atom", "Eclipse"],
            "Communication": ["Microsoft Outlook", "Gmail", "Slack", "Microsoft Teams", "Zoom", "Discord"],
            "Design": ["Adobe Photoshop", "Adobe Illustrator", "Figma", "Sketch", "GIMP", "Inkscape"],
            "Browsers": ["Google Chrome", "Mozilla Firefox", "Microsoft Edge", "Safari", "Opera", "Brave"],
            "Entertainment": ["Spotify", "Netflix", "YouTube", "Twitch", "VLC Media Player", "Steam"]
        }

        # Locations (cities and their coordinates)
        self.locations = {
            "New York": {"lat": 40.7128, "lon": -74.0060},
            "San Francisco": {"lat": 37.7749, "lon": -122.4194},
            "Los Angeles": {"lat": 34.0522, "lon": -118.2437},
            "Chicago": {"lat": 41.8781, "lon": -87.6298},
            "Boston": {"lat": 42.3601, "lon": -71.0589},
            "Seattle": {"lat": 47.6062, "lon": -122.3321},
            "Austin": {"lat": 30.2672, "lon": -97.7431},
            "London": {"lat": 51.5074, "lon": -0.1278},
            "Paris": {"lat": 48.8566, "lon": 2.3522},
            "Tokyo": {"lat": 35.6762, "lon": 139.6503},
            "Sydney": {"lat": -33.8688, "lon": 151.2093},
            "Toronto": {"lat": 43.6532, "lon": -79.3832}
        }

        # Popular websites for web browsing activities
        self.websites = [
            "google.com", "youtube.com", "facebook.com", "amazon.com", "wikipedia.org",
            "twitter.com", "instagram.com", "linkedin.com", "github.com", "stackoverflow.com",
            "reddit.com", "netflix.com", "nytimes.com", "bbc.com", "cnn.com",
            "apple.com", "microsoft.com", "adobe.com", "spotify.com", "medium.com"
        ]

        # Common search queries
        self.search_queries = [
            "how to fix wifi issues", "best restaurants near me", "weather forecast",
            "python tutorial", "javascript frameworks comparison", "latest tech news",
            "covid statistics", "flight tickets to New York", "best laptop 2023",
            "how to make pasta carbonara", "netflix new shows", "project management tools",
            "digital marketing strategies", "remote work tips", "home office setup ideas",
            "data science courses online", "machine learning tutorial", "cloud computing basics",
            "cybersecurity best practices", "healthy meal prep ideas"
        ]

        # Music artists and songs
        self.music = {
            "Taylor Swift": ["Blank Space", "Love Story", "Shake It Off", "Anti-Hero"],
            "Ed Sheeran": ["Shape of You", "Perfect", "Thinking Out Loud", "Bad Habits"],
            "Drake": ["Hotline Bling", "God's Plan", "One Dance", "Started From the Bottom"],
            "Billie Eilish": ["Bad Guy", "Ocean Eyes", "Happier Than Ever", "When The Party's Over"],
            "The Weeknd": ["Blinding Lights", "Starboy", "Save Your Tears", "The Hills"],
            "Adele": ["Hello", "Someone Like You", "Rolling in the Deep", "Easy On Me"],
            "Kendrick Lamar": ["HUMBLE.", "DNA.", "Alright", "Swimming Pools"],
            "Beyoncé": ["Formation", "Halo", "Single Ladies", "Crazy In Love"]
        }

        # Video content
        self.videos = {
            "Educational": ["Machine Learning Tutorial", "History of Ancient Rome", "Python Programming Basics", "Quantum Physics Explained"],
            "Entertainment": ["Movie Trailer: Avengers", "Concert Highlights", "Stand-up Comedy Special", "Gaming Walkthrough"],
            "News": ["Daily News Update", "Financial Market Analysis", "Climate Change Report", "Tech Industry News"],
            "Lifestyle": ["Cooking Tutorial", "Travel Vlog: Paris", "Workout Routine", "Home Renovation Project"]
        }

        # Device types
        self.devices = [
            {"type": "Laptop", "os": "Windows", "model": "Dell XPS 15"},
            {"type": "Laptop", "os": "macOS", "model": "MacBook Pro"},
            {"type": "Desktop", "os": "Windows", "model": "HP Pavilion"},
            {"type": "Desktop", "os": "macOS", "model": "iMac"},
            {"type": "Phone", "os": "iOS", "model": "iPhone 14"},
            {"type": "Phone", "os": "Android", "model": "Samsung Galaxy S22"},
            {"type": "Tablet", "os": "iPadOS", "model": "iPad Pro"},
            {"type": "Tablet", "os": "Android", "model": "Samsung Galaxy Tab S8"}
        ]

    def generate(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate activity metadata records.

        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation

        Returns:
            List of generated records
        """
        self.logger.info(f"Generating {count} activity metadata records")

        # Use direct generation for small counts or basic criteria
        if count <= 50 or (criteria and "direct_generation" in criteria):
            return self._direct_generation(count, criteria)

        # Use LLM-powered generation for larger counts or complex criteria
        instruction = f"Generate {count} realistic activity metadata records"
        if criteria:
            instruction += f" matching these criteria: {json.dumps(criteria)}"

        input_data = {
            "count": count,
            "criteria": criteria or {},
            "config": self.config,
            "collection_name": self.collection_name
        }

        # Check if we need to generate for specific storage objects
        if criteria and "storage_objects" in criteria:
            self.logger.info(f"Generating activities for {len(criteria['storage_objects'])} storage objects")
            input_data["storage_objects"] = criteria["storage_objects"]

        # Generate in batches to avoid overwhelming the LLM
        results = []
        batch_size = min(count, 50)
        remaining = count

        while remaining > 0:
            current_batch = min(batch_size, remaining)
            self.logger.info(f"Generating batch of {current_batch} activity records")

            # Update input data for this batch
            batch_input = input_data.copy()
            batch_input["count"] = current_batch

            # Run the agent
            response = self.run(instruction, batch_input)

            # Extract the generated records
            if "actions" in response:
                for action in response["actions"]:
                    if action["tool"] == "database_insert" or action["tool"] == "database_bulk_insert":
                        # If records were inserted directly, we need to query them
                        tool = self.tools.get_tool("database_query")
                        if tool:
                            query_result = tool.execute({
                                "query": f"FOR doc IN {self.collection_name} SORT doc.Timestamp DESC LIMIT {current_batch} RETURN doc"
                            })
                            results.extend(query_result)

            remaining -= current_batch

        return results

    def _direct_generation(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate activity metadata records directly without LLM.

        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation

        Returns:
            List of generated records
        """
        self.logger.info(f"Direct generation of {count} activity records")

        # Use the model-based ActivityGeneratorTool if available
        tool = self.tools.get_tool("activity_generator")
        if tool:
            self.logger.info("Using model-based activity generator tool")
            result = tool.execute({
                "count": count,
                "criteria": criteria or {}
            })
            
            activity_records = result.get("records", [])
            
            # Transform the records into the format expected by the database
            transformed_records = [self._transform_to_db_format(record) for record in activity_records]
            
            # Store the records if needed
            if self.config.get("store_directly", False):
                bulk_tool = self.tools.get_tool("database_bulk_insert")
                if bulk_tool:
                    bulk_tool.execute({
                        "collection": self.collection_name,
                        "documents": transformed_records
                    })
            
            return transformed_records
            
        # Fall back to legacy generation if tool is not available
        self.logger.warning("Activity generator tool not available, using legacy generation")
        
        # Create sequences of related activities if requested
        if criteria and criteria.get("create_sequences", False):
            return self._generate_activity_sequences(count, criteria)

        activity_records = []

        # Generate individual activity records
        for _ in range(count):
            activity_record = self._generate_activity_record(criteria)
            activity_records.append(activity_record)

        # Store the records if needed
        if self.config.get("store_directly", False):
            bulk_tool = self.tools.get_tool("database_bulk_insert")
            if bulk_tool:
                bulk_tool.execute({
                    "collection": self.collection_name,
                    "documents": activity_records
                })

        return activity_records

    def _generate_activity_sequences(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate sequences of related activity records.

        Args:
            count: Total number of activity records to generate
            criteria: Optional criteria for generation

        Returns:
            List of generated activity records
        """
        self.logger.info(f"Generating {count} activity records in sequences")

        activity_records = []

        # Determine number of sequences
        seq_count = criteria.get("sequence_count", max(1, count // 10))
        records_per_seq = count // seq_count

        for seq_idx in range(seq_count):
            # Generate a sequence of related activities
            sequence = self._generate_single_sequence(records_per_seq, criteria)
            activity_records.extend(sequence)

        # Generate remaining records
        remaining = count - len(activity_records)
        if remaining > 0:
            for _ in range(remaining):
                activity_record = self._generate_activity_record(criteria)
                activity_records.append(activity_record)

        # Store the records if needed
        if self.config.get("store_directly", False):
            bulk_tool = self.tools.get_tool("database_bulk_insert")
            if bulk_tool:
                bulk_tool.execute({
                    "collection": self.collection_name,
                    "documents": activity_records
                })

        return activity_records

    def _generate_single_sequence(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate a sequence of related activity records.

        Args:
            count: Number of records in the sequence
            criteria: Optional criteria for generation

        Returns:
            List of activity records in the sequence
        """
        # Choose a sequence type
        seq_type = criteria.get("sequence_type") if criteria else None
        if not seq_type:
            seq_type = random.choice([
                "file_workflow", "meeting_sequence", "location_movement",
                "application_session", "multi_device", "media_consumption"
            ])

        # Get base parameters for the sequence
        base_time = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 30))
        sequence_id = str(uuid.uuid4())
        user_id = criteria.get("user_id", f"user_{random.randint(1000, 9999)}")

        sequence = []

        if seq_type == "file_workflow":
            # Generate a sequence of file-related activities
            file_name = f"Project_{random.randint(100, 999)}.docx"
            file_path = f"/Users/{user_id}/Documents/Projects/"
            file_id = str(uuid.uuid4())

            # Create file
            creation = self._create_file_activity(
                "FileCreation",
                base_time,
                user_id,
                file_name,
                file_path,
                file_id,
                sequence_id
            )
            sequence.append(creation)

            # Edit file multiple times
            for i in range(min(count - 3, 5)):
                edit_time = base_time + timedelta(hours=random.randint(1, 4) * (i + 1))
                edit = self._create_file_activity(
                    "FileEdit",
                    edit_time,
                    user_id,
                    file_name,
                    file_path,
                    file_id,
                    sequence_id
                )
                sequence.append(edit)

            # Share file
            share_time = base_time + timedelta(hours=random.randint(12, 24))
            share = self._create_file_activity(
                "FileShare",
                share_time,
                user_id,
                file_name,
                file_path,
                file_id,
                sequence_id,
                recipient=f"colleague_{random.randint(100, 999)}@example.com"
            )
            sequence.append(share)

            # Access file again
            access_time = share_time + timedelta(hours=random.randint(2, 8))
            access = self._create_file_activity(
                "FileAccess",
                access_time,
                user_id,
                file_name,
                file_path,
                file_id,
                sequence_id
            )
            sequence.append(access)

        elif seq_type == "meeting_sequence":
            # Generate a sequence of meeting-related activities
            meeting_name = f"Team Meeting - {random.choice(['Planning', 'Review', 'Status Update', 'Kickoff'])}"
            meeting_id = str(uuid.uuid4())

            # Create meeting
            create_time = base_time - timedelta(days=random.randint(3, 7))
            creation = self._create_meeting_activity(
                "MeetingCreate",
                create_time,
                user_id,
                meeting_name,
                meeting_id,
                sequence_id,
                invitees=[f"team_{random.randint(1, 5)}@example.com" for _ in range(3)]
            )
            sequence.append(creation)

            # Email about meeting
            email_time = create_time + timedelta(hours=random.randint(1, 12))
            email = self._create_email_activity(
                "EmailSend",
                email_time,
                user_id,
                f"Agenda for: {meeting_name}",
                sequence_id,
                recipients=[f"team_{random.randint(1, 5)}@example.com" for _ in range(3)],
                related_entity=meeting_id
            )
            sequence.append(email)

            # Attend meeting
            attend_time = base_time
            attend = self._create_meeting_activity(
                "MeetingAttend",
                attend_time,
                user_id,
                meeting_name,
                meeting_id,
                sequence_id
            )
            sequence.append(attend)

            # Follow-up email
            followup_time = attend_time + timedelta(hours=random.randint(1, 4))
            followup = self._create_email_activity(
                "EmailSend",
                followup_time,
                user_id,
                f"Follow-up: {meeting_name}",
                sequence_id,
                recipients=[f"team_{random.randint(1, 5)}@example.com" for _ in range(3)],
                related_entity=meeting_id
            )
            sequence.append(followup)

        elif seq_type == "location_movement":
            # Generate a sequence of location changes
            locations = random.sample(list(self.locations.keys()), min(count, len(self.locations)))

            for i, location in enumerate(locations):
                loc_time = base_time + timedelta(hours=i * random.randint(2, 8))
                loc_activity = self._create_location_activity(
                    "LocationChange",
                    loc_time,
                    user_id,
                    location,
                    self.locations[location],
                    sequence_id
                )
                sequence.append(loc_activity)

                # Add an activity at each location
                app_activity = self._create_application_activity(
                    "ApplicationUse",
                    loc_time + timedelta(minutes=random.randint(15, 60)),
                    user_id,
                    random.choice(list(self.applications.values())[0]),
                    sequence_id,
                    location=location
                )
                sequence.append(app_activity)

        elif seq_type == "application_session":
            # Generate a sequence of application usage
            app_category = random.choice(list(self.applications.keys()))
            app_name = random.choice(self.applications[app_category])

            # Start application
            start_time = base_time
            start = self._create_application_activity(
                "ApplicationUse",
                start_time,
                user_id,
                app_name,
                sequence_id,
                action="start"
            )
            sequence.append(start)

            # Use application for various tasks
            for i in range(min(count - 2, 6)):
                use_time = start_time + timedelta(minutes=random.randint(10, 30) * (i + 1))
                task = random.choice(["edit", "save", "export", "import", "search", "analyze", "format"])
                use = self._create_application_activity(
                    "ApplicationUse",
                    use_time,
                    user_id,
                    app_name,
                    sequence_id,
                    action=task
                )
                sequence.append(use)

            # Close application
            end_time = start_time + timedelta(hours=random.randint(1, 3))
            end = self._create_application_activity(
                "ApplicationUse",
                end_time,
                user_id,
                app_name,
                sequence_id,
                action="close"
            )
            sequence.append(end)

        elif seq_type == "multi_device":
            # Generate a sequence of activities across multiple devices
            devices = random.sample(self.devices, min(count, len(self.devices)))

            for i, device in enumerate(devices):
                # Connect to device
                connect_time = base_time + timedelta(hours=i * random.randint(1, 4))
                connect = self._create_device_activity(
                    "DeviceConnect",
                    connect_time,
                    user_id,
                    device,
                    sequence_id
                )
                sequence.append(connect)

                # Do some activity on the device
                activity_type = random.choice(self.activity_types)
                if "File" in activity_type:
                    file_name = f"Document_{random.randint(100, 999)}.docx"
                    file_path = f"/{device['os']}/Documents/"
                    file_id = str(uuid.uuid4())
                    activity = self._create_file_activity(
                        activity_type,
                        connect_time + timedelta(minutes=random.randint(15, 60)),
                        user_id,
                        file_name,
                        file_path,
                        file_id,
                        sequence_id,
                        device=device
                    )
                elif "Email" in activity_type:
                    activity = self._create_email_activity(
                        activity_type,
                        connect_time + timedelta(minutes=random.randint(15, 60)),
                        user_id,
                        f"Email from {device['type']}",
                        sequence_id,
                        device=device
                    )
                else:
                    app_name = random.choice(list(self.applications.values())[0])
                    activity = self._create_application_activity(
                        "ApplicationUse",
                        connect_time + timedelta(minutes=random.randint(15, 60)),
                        user_id,
                        app_name,
                        sequence_id,
                        device=device
                    )

                sequence.append(activity)

        elif seq_type == "media_consumption":
            # Generate a sequence of media consumption activities
            if random.choice([True, False]):
                # Music sequence
                artist = random.choice(list(self.music.keys()))
                songs = self.music[artist]

                for i, song in enumerate(songs):
                    play_time = base_time + timedelta(minutes=i * random.randint(3, 5))
                    music_activity = self._create_media_activity(
                        "MusicListening",
                        play_time,
                        user_id,
                        f"{song} by {artist}",
                        sequence_id
                    )
                    sequence.append(music_activity)
            else:
                # Video sequence
                category = random.choice(list(self.videos.keys()))
                videos = self.videos[category]

                for i, video in enumerate(videos):
                    play_time = base_time + timedelta(minutes=i * random.randint(15, 45))
                    video_activity = self._create_media_activity(
                        "VideoWatching",
                        play_time,
                        user_id,
                        video,
                        sequence_id,
                        category=category
                    )
                    sequence.append(video_activity)

        # Limit to the requested count
        return sequence[:count]

    def _generate_activity_record(self, criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a single activity record.

        Args:
            criteria: Optional criteria for generation

        Returns:
            Activity record
        """
        # Determine activity type
        activity_type = criteria.get("activity_type") if criteria else None
        if not activity_type:
            activity_type = random.choice(self.activity_types)

        # Get base timestamp
        days_ago = criteria.get("days_ago", random.randint(0, 30))
        base_time = datetime.now(timezone.utc) - timedelta(days=days_ago)

        # Get user ID
        user_id = criteria.get("user_id", f"user_{random.randint(1000, 9999)}")

        # Generate activity based on type
        if "File" in activity_type:
            # Generate file-related activity
            file_name = criteria.get("file_name", f"Document_{random.randint(100, 999)}.{random.choice(['docx', 'pdf', 'txt', 'xlsx'])}")
            file_path = criteria.get("file_path", f"/Users/{user_id}/Documents/")
            file_id = criteria.get("file_id", str(uuid.uuid4()))

            return self._create_file_activity(activity_type, base_time, user_id, file_name, file_path, file_id)

        elif "Email" in activity_type:
            # Generate email-related activity
            subject = criteria.get("subject", f"Subject_{random.randint(100, 999)}")
            return self._create_email_activity(activity_type, base_time, user_id, subject)

        elif "Meeting" in activity_type:
            # Generate meeting-related activity
            meeting_name = criteria.get("meeting_name", f"Meeting_{random.randint(100, 999)}")
            meeting_id = criteria.get("meeting_id", str(uuid.uuid4()))

            return self._create_meeting_activity(activity_type, base_time, user_id, meeting_name, meeting_id)

        elif activity_type == "ApplicationUse":
            # Generate application usage activity
            app_category = random.choice(list(self.applications.keys()))
            app_name = criteria.get("application", random.choice(self.applications[app_category]))

            return self._create_application_activity(activity_type, base_time, user_id, app_name)

        elif activity_type == "WebBrowsing":
            # Generate web browsing activity
            website = criteria.get("website", random.choice(self.websites))

            return self._create_web_activity(activity_type, base_time, user_id, website)

        elif activity_type == "DeviceConnect":
            # Generate device connection activity
            device = criteria.get("device", random.choice(self.devices))

            return self._create_device_activity(activity_type, base_time, user_id, device)

        elif activity_type == "LocationChange":
            # Generate location change activity
            location_name = criteria.get("location", random.choice(list(self.locations.keys())))
            coordinates = self.locations.get(location_name, {"lat": 0, "lon": 0})

            return self._create_location_activity(activity_type, base_time, user_id, location_name, coordinates)

        elif activity_type == "Search":
            # Generate search activity
            query = criteria.get("query", random.choice(self.search_queries))

            return self._create_search_activity(activity_type, base_time, user_id, query)

        elif activity_type in ["MusicListening", "VideoWatching"]:
            # Generate media consumption activity
            if activity_type == "MusicListening":
                artist = random.choice(list(self.music.keys()))
                song = random.choice(self.music[artist])
                media_name = criteria.get("media_name", f"{song} by {artist}")
            else:
                category = random.choice(list(self.videos.keys()))
                media_name = criteria.get("media_name", random.choice(self.videos[category]))

            return self._create_media_activity(activity_type, base_time, user_id, media_name)

        # Default activity for any other type
        return self._create_default_activity(activity_type, base_time, user_id)

    def _create_file_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                             file_name: str, file_path: str, file_id: str,
                             sequence_id: Optional[str] = None,
                             recipient: Optional[str] = None,
                             device: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a file-related activity record.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            file_name: File name
            file_path: File path
            file_id: File ID
            sequence_id: Optional sequence ID
            recipient: Optional recipient for file share
            device: Optional device information

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"file_{activity_type.lower()}_{uuid.uuid4().hex[:8]}"

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"{activity_type} of {file_name}",
            "EntityID": file_id,
            "Data": {
                "FileName": file_name,
                "FilePath": file_path,
                "FileType": file_name.split(".")[-1] if "." in file_name else "unknown"
            },
            "Tags": [activity_type, "file", file_name.split(".")[-1] if "." in file_name else "document"]
        }

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        # Add recipient for file share
        if activity_type == "FileShare" and recipient:
            activity["Data"]["Recipient"] = recipient
            activity["Description"] = f"Shared {file_name} with {recipient}"
            activity["Tags"].append("sharing")

        # Add device information if provided
        if device:
            activity["Device"] = {
                "Type": device.get("type", "Unknown"),
                "OS": device.get("os", "Unknown"),
                "Model": device.get("model", "Unknown")
            }
            activity["Tags"].append(device.get("type", "device").lower())

        # Add specific details based on activity type
        if activity_type == "FileCreation":
            activity["Data"]["CreationTime"] = timestamp.isoformat()
            activity["Tags"].append("creation")
        elif activity_type == "FileEdit":
            activity["Data"]["EditTime"] = timestamp.isoformat()
            activity["Data"]["Changes"] = random.randint(1, 50)
            activity["Tags"].append("edit")
        elif activity_type == "FileAccess":
            activity["Data"]["AccessTime"] = timestamp.isoformat()
            activity["Tags"].append("access")

        return activity

    def _create_email_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                              subject: str, sequence_id: Optional[str] = None,
                              recipients: Optional[List[str]] = None,
                              related_entity: Optional[str] = None,
                              device: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create an email-related activity record.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            subject: Email subject
            sequence_id: Optional sequence ID
            recipients: Optional list of recipients
            related_entity: Optional related entity ID
            device: Optional device information

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"email_{activity_type.lower()}_{uuid.uuid4().hex[:8]}"

        # Default recipients if not provided
        if not recipients:
            recipients = [f"recipient_{random.randint(100, 999)}@example.com" for _ in range(random.randint(1, 3))]

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"{activity_type}: {subject}",
            "EntityID": f"email_{uuid.uuid4().hex[:12]}",
            "Data": {
                "Subject": subject,
                "Recipients": recipients,
                "MessageID": f"<{uuid.uuid4().hex}@example.com>"
            },
            "Tags": [activity_type, "email", "communication"]
        }

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        # Add related entity if provided
        if related_entity:
            activity["Data"]["RelatedEntityID"] = related_entity
            activity["Tags"].append("related")

        # Add device information if provided
        if device:
            activity["Device"] = {
                "Type": device.get("type", "Unknown"),
                "OS": device.get("os", "Unknown"),
                "Model": device.get("model", "Unknown")
            }
            activity["Tags"].append(device.get("type", "device").lower())

        # Add specific details based on activity type
        if activity_type == "EmailSend":
            activity["Data"]["SentTime"] = timestamp.isoformat()
            activity["Tags"].append("sent")
        elif activity_type == "EmailReceive":
            activity["Data"]["ReceivedTime"] = timestamp.isoformat()
            activity["Data"]["Sender"] = f"sender_{random.randint(100, 999)}@example.com"
            activity["Tags"].append("received")

        return activity

    def _create_meeting_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                                meeting_name: str, meeting_id: str, sequence_id: Optional[str] = None,
                                invitees: Optional[List[str]] = None,
                                device: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a meeting-related activity record.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            meeting_name: Meeting name
            meeting_id: Meeting ID
            sequence_id: Optional sequence ID
            invitees: Optional list of invitees
            device: Optional device information

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"meeting_{activity_type.lower()}_{uuid.uuid4().hex[:8]}"

        # Default invitees if not provided
        if not invitees:
            invitees = [f"invitee_{random.randint(100, 999)}@example.com" for _ in range(random.randint(2, 5))]

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"{activity_type}: {meeting_name}",
            "EntityID": meeting_id,
            "Data": {
                "MeetingName": meeting_name,
                "Duration": random.randint(15, 90),  # in minutes
                "Platform": random.choice(["Microsoft Teams", "Zoom", "Google Meet", "Webex"])
            },
            "Tags": [activity_type, "meeting", "calendar"]
        }

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        # Add device information if provided
        if device:
            activity["Device"] = {
                "Type": device.get("type", "Unknown"),
                "OS": device.get("os", "Unknown"),
                "Model": device.get("model", "Unknown")
            }
            activity["Tags"].append(device.get("type", "device").lower())

        # Add specific details based on activity type
        if activity_type == "MeetingCreate":
            activity["Data"]["CreationTime"] = timestamp.isoformat()
            activity["Data"]["Invitees"] = invitees
            activity["Tags"].append("organization")
        elif activity_type == "MeetingAttend":
            activity["Data"]["AttendTime"] = timestamp.isoformat()
            activity["Data"]["Attendees"] = random.randint(2, len(invitees) if invitees else 10)
            activity["Tags"].append("attendance")

        return activity

    def _create_application_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                                    app_name: str, sequence_id: Optional[str] = None,
                                    action: Optional[str] = None,
                                    location: Optional[str] = None,
                                    device: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create an application usage activity record.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            app_name: Application name
            sequence_id: Optional sequence ID
            action: Optional application action
            location: Optional location
            device: Optional device information

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"app_use_{uuid.uuid4().hex[:8]}"

        # Default action if not provided
        if not action:
            action = random.choice(["start", "use", "close"])

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"Using {app_name} - {action}",
            "EntityID": f"app_{app_name.lower().replace(' ', '_')}",
            "Data": {
                "ApplicationName": app_name,
                "Action": action,
                "Duration": random.randint(1, 120) if action != "start" else 0  # in minutes
            },
            "Tags": [activity_type, "application", app_name.lower().replace(' ', '_')]
        }

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        # Add location if provided
        if location:
            activity["Location"] = location
            if location in self.locations:
                activity["Coordinates"] = self.locations[location]
            activity["Tags"].append("location")

        # Add device information if provided
        if device:
            activity["Device"] = {
                "Type": device.get("type", "Unknown"),
                "OS": device.get("os", "Unknown"),
                "Model": device.get("model", "Unknown")
            }
            activity["Tags"].append(device.get("type", "device").lower())

        return activity

    def _create_web_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                           website: str, sequence_id: Optional[str] = None,
                           device: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a web browsing activity record.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            website: Website URL
            sequence_id: Optional sequence ID
            device: Optional device information

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"web_{uuid.uuid4().hex[:8]}"

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"Browsing {website}",
            "EntityID": f"web_{website.replace('.', '_')}",
            "Data": {
                "URL": f"https://{website}",
                "Browser": random.choice(self.applications["Browsers"]),
                "Duration": random.randint(1, 30),  # in minutes
                "PageTitle": f"{website.split('.')[0].capitalize()} Home Page"
            },
            "Tags": [activity_type, "web", "browsing", website.split('.')[0]]
        }

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        # Add device information if provided
        if device:
            activity["Device"] = {
                "Type": device.get("type", "Unknown"),
                "OS": device.get("os", "Unknown"),
                "Model": device.get("model", "Unknown")
            }
            activity["Tags"].append(device.get("type", "device").lower())

        return activity

    def _create_device_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                              device: Dict[str, str], sequence_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a device connection activity record.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            device: Device information
            sequence_id: Optional sequence ID

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"device_{uuid.uuid4().hex[:8]}"

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"Connected to {device['type']} ({device['model']})",
            "EntityID": f"device_{device['model'].lower().replace(' ', '_')}",
            "Device": {
                "Type": device["type"],
                "OS": device["os"],
                "Model": device["model"],
                "DeviceID": f"dev_{uuid.uuid4().hex[:8]}"
            },
            "Data": {
                "ConnectionType": random.choice(["USB", "Bluetooth", "WiFi", "Cloud"]),
                "Duration": random.randint(1, 120)  # in minutes
            },
            "Tags": [activity_type, "device", device["type"].lower(), device["os"].lower()]
        }

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        return activity

    def _create_location_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                                location_name: str, coordinates: Dict[str, float],
                                sequence_id: Optional[str] = None,
                                device: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a location change activity record.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            location_name: Location name
            coordinates: Location coordinates
            sequence_id: Optional sequence ID
            device: Optional device information

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"location_{uuid.uuid4().hex[:8]}"

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"Location changed to {location_name}",
            "EntityID": f"location_{location_name.lower().replace(' ', '_')}",
            "Location": location_name,
            "Coordinates": coordinates,
            "Data": {
                "Accuracy": random.randint(5, 50),  # in meters
                "Method": random.choice(["GPS", "WiFi", "Cell Tower", "IP"]),
                "Speed": random.randint(0, 120) if random.random() < 0.5 else None  # in km/h
            },
            "Tags": [activity_type, "location", "geolocation", location_name.lower().replace(' ', '_')]
        }

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        # Add device information if provided
        if device:
            activity["Device"] = {
                "Type": device.get("type", "Unknown"),
                "OS": device.get("os", "Unknown"),
                "Model": device.get("model", "Unknown")
            }
            activity["Tags"].append(device.get("type", "device").lower())

        return activity

    def _create_search_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                              query: str, sequence_id: Optional[str] = None,
                              device: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a search activity record.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            query: Search query
            sequence_id: Optional sequence ID
            device: Optional device information

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"search_{uuid.uuid4().hex[:8]}"

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"Searched for: {query}",
            "EntityID": f"search_{uuid.uuid4().hex[:12]}",
            "Data": {
                "Query": query,
                "Engine": random.choice(["Google", "Bing", "DuckDuckGo", "Yahoo"]),
                "ResultCount": random.randint(100, 1000000),
                "ResultSelected": random.choice([True, False])
            },
            "Tags": [activity_type, "search", "query"] + [word.lower() for word in query.split() if len(word) > 3]
        }

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        # Add device information if provided
        if device:
            activity["Device"] = {
                "Type": device.get("type", "Unknown"),
                "OS": device.get("os", "Unknown"),
                "Model": device.get("model", "Unknown")
            }
            activity["Tags"].append(device.get("type", "device").lower())

        return activity

    def _create_media_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                             media_name: str, sequence_id: Optional[str] = None,
                             category: Optional[str] = None,
                             device: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Create a media consumption activity record.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            media_name: Media name
            sequence_id: Optional sequence ID
            category: Optional media category
            device: Optional device information

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"media_{uuid.uuid4().hex[:8]}"

        # Determine media type and platform
        if activity_type == "MusicListening":
            media_type = "music"
            platform = random.choice(["Spotify", "Apple Music", "YouTube Music", "Amazon Music"])
            duration = random.randint(2, 5)  # in minutes
        else:  # VideoWatching
            media_type = "video"
            platform = random.choice(["YouTube", "Netflix", "Hulu", "Amazon Prime"])
            duration = random.randint(5, 120)  # in minutes

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"{activity_type}: {media_name}",
            "EntityID": f"media_{uuid.uuid4().hex[:12]}",
            "Data": {
                "MediaName": media_name,
                "MediaType": media_type,
                "Platform": platform,
                "Duration": duration,
                "Completed": random.choice([True, False])
            },
            "Tags": [activity_type, media_type, platform.lower().replace(' ', '_')]
        }

        # Add category if provided or for videos
        if category:
            activity["Data"]["Category"] = category
            activity["Tags"].append(category.lower())

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        # Add device information if provided
        if device:
            activity["Device"] = {
                "Type": device.get("type", "Unknown"),
                "OS": device.get("os", "Unknown"),
                "Model": device.get("model", "Unknown")
            }
            activity["Tags"].append(device.get("type", "device").lower())

        return activity

    def _create_default_activity(self, activity_type: str, timestamp: datetime, user_id: str,
                               sequence_id: Optional[str] = None) -> Dict[str, Any]:
        """Create a default activity record for any other type.

        Args:
            activity_type: Type of activity
            timestamp: Activity timestamp
            user_id: User ID
            sequence_id: Optional sequence ID

        Returns:
            Activity record
        """
        # Generate a random handle for the activity
        handle = f"activity_{uuid.uuid4().hex[:8]}"

        # Create the activity record
        activity = {
            "Handle": handle,
            "Timestamp": timestamp.isoformat(),
            "ActivityType": activity_type,
            "UserID": user_id,
            "Description": f"Activity of type {activity_type}",
            "EntityID": f"entity_{uuid.uuid4().hex[:12]}",
            "Data": {
                "ActivitySource": "Synthetic data generator",
                "Details": f"Generic {activity_type} activity"
            },
            "Tags": [activity_type, "generic"]
        }

        # Add sequence ID if provided
        if sequence_id:
            activity["SequenceID"] = sequence_id

        return activity
        
    def _transform_to_db_format(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a generated record to the database format.

        Args:
            record: Generated record from ActivityGeneratorTool

        Returns:
            Transformed record in database format
        """
        # Check if this is already an IndalekoActivityDataModel record format
        if "Record" in record and "Timestamp" in record and "SemanticAttributes" in record:
            # Record is already in IndalekoActivityDataModel format, return as is
            self.logger.debug("Record is already in database format")
            return record
            
        # For legacy format, convert to the expected database format
        # Generate a handle if not provided
        handle = record.get("Handle", f"activity_{uuid.uuid4().hex[:8]}")
        
        # Get timestamp, ensure ISO format with timezone
        timestamp = record.get("Timestamp")
        if isinstance(timestamp, str) and 'Z' not in timestamp and '+' not in timestamp:
            timestamp = f"{timestamp}Z"
            
        # Create semantic attributes from data fields
        semantic_attributes = []
        if "Data" in record:
            for key, value in record.get("Data", {}).items():
                semantic_attributes.append({
                    "AttributeIdentifier": str(uuid.uuid4()),
                    "AttributeName": f"ACTIVITY_DATA_{key.upper()}",
                    "AttributeValue": str(value)
                })
                
        # Add standard attributes
        activity_type = record.get("ActivityType", "unknown")
        semantic_attributes.append({
            "AttributeIdentifier": str(uuid.uuid4()),
            "AttributeName": "ACTIVITY_DATA_TYPE",
            "AttributeValue": activity_type.upper()
        })
        
        user_id = record.get("UserID")
        if user_id:
            semantic_attributes.append({
                "AttributeIdentifier": str(uuid.uuid4()),
                "AttributeName": "ACTIVITY_DATA_USER",
                "AttributeValue": user_id
            })
            
        entity_id = record.get("EntityID")
        if entity_id:
            semantic_attributes.append({
                "AttributeIdentifier": str(uuid.uuid4()),
                "AttributeName": "ACTIVITY_DATA_OBJECT_ID",
                "AttributeValue": entity_id
            })
            
        # Create source identifier
        source_identifier = {
            "Source": "activity_generator",
            "CreationTime": timestamp,
            "LastUpdateTime": timestamp
        }
        
        # Create the record in database format
        db_record = {
            "Handle": handle,
            "Timestamp": timestamp,
            "Description": record.get("Description", f"Activity: {activity_type}"),
            "Record": {
                "RecordIdentifier": str(uuid.uuid4()),
                "SourceIdentifier": source_identifier
            },
            "SemanticAttributes": semantic_attributes
        }
        
        # Add any tags
        if "Tags" in record:
            db_record["Tags"] = record["Tags"]
            
        # Add sequence ID if present
        if "SequenceID" in record:
            db_record["SequenceID"] = record["SequenceID"]
            
        return db_record

    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth activity records with specific characteristics.

        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy

        Returns:
            List of generated truth records
        """
        self.logger.info(f"Generating {count} truth activity records with criteria: {criteria}")

        # Always use direct generation for truth records
        activity_records = []

        # Generate individual activity records
        for _ in range(count):
            activity_record = self._generate_activity_record(criteria)
            activity_records.append(activity_record)

            # Track the truth records
            self.truth_list.append(activity_record.get("Handle"))

        # Store truth characteristics for later verification
        self.state["truth_criteria"] = criteria
        self.state["truth_count"] = count
        self.state["truth_handles"] = self.truth_list

        # Store the records if needed
        if self.config.get("store_directly", False):
            bulk_tool = self.tools.get_tool("database_bulk_insert")
            if bulk_tool:
                bulk_tool.execute({
                    "collection": self.collection_name,
                    "documents": activity_records
                })

        return activity_records

    def _build_context(self, instruction: str, input_data: Optional[Dict[str, Any]] = None) -> str:
        """Build the context for the LLM.

        Args:
            instruction: The instruction for the agent
            input_data: Optional input data

        Returns:
            Context string for the LLM
        """
        context = f"""
        You are a specialized agent for generating realistic activity metadata records for the Indaleko system.

        Your task: {instruction}

        Generate activity metadata that follows these guidelines:
        1. Create realistic timestamps that follow natural patterns of user activity
        2. Include appropriate user identifiers and entity references
        3. Generate detailed descriptions of activities
        4. Include relevant tags and categorizations
        5. Ensure all records have required fields for database insertion

        Activity metadata should include the following fields:
        - Handle: Unique identifier for the activity
        - Timestamp: ISO format datetime with timezone
        - ActivityType: Type of activity (FileAccess, EmailSend, MeetingAttend, etc.)
        - UserID: User identifier
        - Description: Human-readable description of the activity
        - EntityID: Identifier for the primary entity involved
        - Data: Additional data specific to the activity type
        - Tags: List of relevant tags for the activity

        You can generate activities of the following types:
        - File activities: FileAccess, FileEdit, FileCreation, FileShare
        - Email activities: EmailSend, EmailReceive
        - Meeting activities: MeetingAttend, MeetingCreate
        - Application activities: ApplicationUse
        - Web activities: WebBrowsing
        - Device activities: DeviceConnect
        - Location activities: LocationChange
        - Media activities: MusicListening, VideoWatching
        - Search activities: Search

        """

        if input_data:
            # Don't include the full storage objects in the context to avoid token limits
            input_data_copy = input_data.copy()
            if "storage_objects" in input_data_copy:
                storage_count = len(input_data_copy["storage_objects"])
                input_data_copy["storage_objects"] = f"[{storage_count} storage objects available]"

            context += f"Input data: {json.dumps(input_data_copy, indent=2)}\n\n"

        # Add tips for specific criteria if provided
        if input_data and "criteria" in input_data and input_data["criteria"]:
            context += "Special instructions for the criteria:\n"

            for key, value in input_data["criteria"].items():
                if key == "activity_type":
                    context += f"- All records must have activity type '{value}'\n"
                elif key == "user_id":
                    context += f"- All activities should be for user '{value}'\n"
                elif key == "days_ago":
                    context += f"- Activities should have occurred approximately {value} days ago\n"
                elif key == "location":
                    context += f"- Activities should be associated with location '{value}'\n"
                elif key == "device":
                    context += f"- Activities should be associated with a {value.get('type', 'device')} running {value.get('os', 'unknown OS')}\n"
                elif key == "create_sequences":
                    context += f"- Generate sequences of related activities\n"
                elif key == "sequence_type":
                    context += f"- Activities should form a {value} sequence\n"
                elif key != "storage_objects":
                    context += f"- Apply the criterion '{key}': '{value}'\n"

        # If we have storage objects, provide instructions for using them
        if input_data and "storage_objects" in input_data:
            context += "\nYou have storage objects available. For each storage object, you should generate appropriate file-related activities such as FileAccess, FileEdit, or FileShare.\n"

            # Provide a sample of one storage object if available
            if isinstance(input_data["storage_objects"], list) and len(input_data["storage_objects"]) > 0:
                sample_obj = input_data["storage_objects"][0]
                context += f"\nHere's a sample storage object:\n{json.dumps(sample_obj, indent=2)}\n"

        # If generating truth records, add special instructions
        if input_data and input_data.get("truth", False):
            context += "\nIMPORTANT: You are generating TRUTH records. These records must EXACTLY match the criteria provided. These records will be used for testing and validation, so their properties must match the criteria precisely.\n"

        return context
