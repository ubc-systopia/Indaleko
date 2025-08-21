"""
gmail_synthetic_collector.py.

Synthetic twin of the Gmail collector that generates realistic email metadata
without accessing real user data. Uses configurable personas to create
believable email patterns for testing and demonstration.

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
import random
import sys
import uuid

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.collaboration.collaboration_base import CollaborationCollector
from data_models import IndalekoSourceIdentifierDataModel
from db import IndalekoServiceManager
from perf.perf_collector import IndalekoPerformanceDataCollector
from perf.perf_recorder import IndalekoPerformanceDataRecorder


# pylint: enable=wrong-import-position


class EmailType(Enum):
    """Types of emails that personas generate."""

    WORK_STATUS = "work_status"
    MEETING_REQUEST = "meeting_request"
    PROJECT_UPDATE = "project_update"
    QUESTION = "question"
    ANSWER = "answer"
    SOCIAL = "social"
    NEWSLETTER = "newsletter"
    NOTIFICATION = "notification"
    CREATIVE = "creative"
    RESEARCH = "research"


@dataclass
class PersonaTrait:
    """Behavioral traits that influence email patterns."""

    name: str
    morning_person: bool = False  # Active in morning hours
    night_owl: bool = False  # Active in evening hours
    weekend_worker: bool = False  # Sends emails on weekends
    thread_starter: bool = False  # Initiates conversations
    quick_responder: bool = False  # Responds within hours
    detail_oriented: bool = False  # Writes longer emails
    emoji_user: bool = False  # Uses emojis in subjects/content
    formal_tone: bool = False  # Formal communication style


@dataclass
class EmailPersona:
    """A synthetic identity that generates emails."""

    id: str
    name: str
    email: str
    role: str  # job title or role
    department: str
    traits: PersonaTrait
    contacts: list[str] = field(default_factory=list)  # Email addresses they communicate with
    email_types: list[EmailType] = field(default_factory=list)  # Types of emails they send
    daily_volume_range: tuple[int, int] = (5, 30)  # Min/max emails per day
    signature: str = ""

    def get_active_hours(self) -> list[int]:
        """Return hours when this persona is likely to send emails."""
        if self.traits.morning_person:
            return list(range(6, 12))
        if self.traits.night_owl:
            return list(range(18, 24)) + list(range(2))
        return list(range(9, 18))  # Standard work hours

    def should_send_on_day(self, day_of_week: int) -> bool:
        """Check if persona sends emails on given day (0=Monday, 6=Sunday)."""
        if day_of_week < 5:  # Weekday
            return True
        return self.traits.weekend_worker


class SyntheticEmailGenerator:
    """Generates realistic synthetic email patterns."""

    # Subject line templates by email type
    SUBJECT_TEMPLATES = {
        EmailType.WORK_STATUS: [
            "Weekly Status Update - {date}",
            "Project {project} Status",
            "{department} Team Update",
            "EOD Report - {date}",
            "Progress Update: {project}",
        ],
        EmailType.MEETING_REQUEST: [
            "Meeting Request: {topic}",
            "Quick Sync - {topic}",
            "Can we discuss {topic}?",
            "Schedule: {topic} Review",
            "{date} - {topic} Meeting",
        ],
        EmailType.PROJECT_UPDATE: [
            "{project} - Milestone Reached",
            "Update on {project}",
            "{project}: Phase {phase} Complete",
            "Important: {project} Changes",
            "{project} Sprint Review",
        ],
        EmailType.QUESTION: [
            "Question about {topic}",
            "Quick question - {topic}",
            "Need help with {topic}",
            "RE: {topic} - clarification needed",
            "Thoughts on {topic}?",
        ],
        EmailType.ANSWER: [
            "RE: {original_subject}",
            "Answer: {original_subject}",
            "Following up on {topic}",
            "Here's what you asked about",
            "Response: {topic}",
        ],
        EmailType.SOCIAL: [
            "Coffee chat?",
            "Lunch plans - {date}",
            "Team outing reminder",
            "Birthday celebration for {name}",
            "Friday social hour",
        ],
        EmailType.NEWSLETTER: [
            "{department} Newsletter - {month}",
            "Weekly Digest - {date}",
            "Company Updates - {month}",
            "Industry News - {date}",
            "Monthly Roundup",
        ],
        EmailType.CREATIVE: [
            "Feedback on {topic}",
            "New idea: {topic}",
            "Brainstorm results - {topic}",
            "Creative brief for {project}",
            "Design review: {project}",
        ],
        EmailType.RESEARCH: [
            "Paper: {topic}",
            "Research findings - {topic}",
            "Literature review: {topic}",
            "Data analysis complete",
            "Experiment results - {date}",
        ],
    }

    # Common project names
    PROJECTS = ["Apollo", "Mercury", "Atlas", "Phoenix", "Quantum", "Nexus", "Aurora", "Titan"]

    # Common topics
    TOPICS = [
        "roadmap",
        "budget",
        "timeline",
        "requirements",
        "architecture",
        "deployment",
        "testing",
        "documentation",
        "training",
        "metrics",
        "performance",
        "security",
    ]

    # Common departments
    DEPARTMENTS = [
        "Engineering",
        "Product",
        "Design",
        "Research",
        "Operations",
        "Marketing",
        "Sales",
        "HR",
        "Finance",
        "Legal",
    ]

    def __init__(self, personas: list[EmailPersona], start_date: datetime, end_date: datetime) -> None:
        """Initialize the generator with personas and date range."""
        self.personas = {p.id: p for p in personas}
        self.start_date = start_date
        self.end_date = end_date
        self.message_counter = 0
        self.thread_counter = 0
        self.threads = {}  # thread_id -> list of message_ids

    def generate_message_id(self) -> str:
        """Generate a unique message ID."""
        self.message_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"<{timestamp}.{self.message_counter}@indaleko.synthetic>"

    def generate_thread_id(self) -> str:
        """Generate a unique thread ID."""
        self.thread_counter += 1
        return f"thread_{self.thread_counter:08d}"

    def generate_subject(self, email_type: EmailType, persona: EmailPersona) -> str:
        """Generate a subject line based on email type."""
        templates = self.SUBJECT_TEMPLATES[email_type]
        template = random.choice(templates)

        # Fill in template variables
        subject = template.format(
            date=datetime.now().strftime("%Y-%m-%d"),
            month=datetime.now().strftime("%B"),
            project=random.choice(self.PROJECTS),
            topic=random.choice(self.TOPICS),
            department=persona.department,
            phase=random.randint(1, 5),
            name=random.choice(list(self.personas.values())).name.split()[0],
            original_subject=random.choice(["Project Update", "Quick Question", "Meeting Notes"]),
        )

        # Add emoji if persona uses them
        if persona.traits.emoji_user and random.random() < 0.3:
            emojis = ["📊", "✅", "🚀", "💡", "📅", "🎯", "⚡", "🔥"]
            subject = f"{random.choice(emojis)} {subject}"

        return subject

    def generate_snippet(self, email_type: EmailType, persona: EmailPersona) -> str:
        """Generate email snippet (preview text)."""
        snippets = {
            EmailType.WORK_STATUS: [
                "This week we completed the main objectives for...",
                "Team accomplished the following milestones...",
                "Please find attached the weekly report covering...",
            ],
            EmailType.MEETING_REQUEST: [
                "I'd like to schedule some time to discuss...",
                "Are you available this week to review...",
                "Let's sync up on the latest developments...",
            ],
            EmailType.PROJECT_UPDATE: [
                "I'm pleased to announce that we've completed...",
                "Quick update on where we stand with...",
                "Some important changes to note regarding...",
            ],
            EmailType.QUESTION: [
                "I was wondering if you could help me understand...",
                "Quick question about the approach for...",
                "Do you have any thoughts on how we should...",
            ],
            EmailType.SOCIAL: [
                "Hey team! Just wanted to see if anyone's interested in...",
                "It's been a while since we all got together...",
                "Join us for some fun and relaxation...",
            ],
        }

        type_snippets = snippets.get(email_type, ["Details in this email..."])
        snippet = random.choice(type_snippets)

        # Formal personas get more formal snippets
        if persona.traits.formal_tone:
            snippet = snippet.replace("Hey", "Greetings").replace("Quick", "Brief")

        return snippet[:100]  # Gmail snippets are typically truncated

    def generate_labels(self, email_type: EmailType, is_read: bool = False) -> list[str]:
        """Generate appropriate labels for an email."""
        labels = []

        # System labels
        if not is_read:
            labels.append("UNREAD")

        # Category labels based on type
        if email_type in [EmailType.WORK_STATUS, EmailType.PROJECT_UPDATE, EmailType.MEETING_REQUEST]:
            labels.append("CATEGORY_UPDATES")
            labels.append("INBOX")
        elif email_type == EmailType.NEWSLETTER:
            labels.append("CATEGORY_PROMOTIONS")
        elif email_type == EmailType.SOCIAL:
            labels.append("CATEGORY_SOCIAL")
        elif email_type in [EmailType.QUESTION, EmailType.ANSWER]:
            labels.append("INBOX")
            labels.append("IMPORTANT")
        else:
            labels.append("INBOX")

        # Random additional labels
        if random.random() < 0.3:
            labels.append("STARRED")

        return labels

    def generate_thread(
        self,
        starter: EmailPersona,
        participants: list[EmailPersona],
        email_type: EmailType,
        start_time: datetime,
    ) -> list[dict[str, Any]]:
        """Generate a email thread with multiple messages."""
        thread_id = self.generate_thread_id()
        messages = []
        current_time = start_time

        # Initial message
        subject = self.generate_subject(email_type, starter)
        initial_msg = self.generate_message(
            sender=starter,
            recipients=participants,
            subject=subject,
            email_type=email_type,
            timestamp=current_time,
            thread_id=thread_id,
            is_reply=False,
        )
        messages.append(initial_msg)

        # Generate replies (30-70% chance of replies)
        if random.random() < 0.5:
            num_replies = random.randint(1, min(5, len(participants)))

            for _i in range(num_replies):
                # Time between replies (30 min to 4 hours)
                current_time += timedelta(minutes=random.randint(30, 240))

                # Pick a responder
                responder = random.choice(participants)

                # Reply includes all participants
                reply_recipients = [starter] + [p for p in participants if p.id != responder.id]

                reply = self.generate_message(
                    sender=responder,
                    recipients=reply_recipients,
                    subject=f"RE: {subject}",
                    email_type=EmailType.ANSWER,
                    timestamp=current_time,
                    thread_id=thread_id,
                    is_reply=True,
                    in_reply_to=messages[-1]["id"],
                )
                messages.append(reply)

        return messages

    def generate_message(
        self,
        sender: EmailPersona,
        recipients: list[EmailPersona],
        subject: str,
        email_type: EmailType,
        timestamp: datetime,
        thread_id: str | None = None,
        is_reply: bool = False,
        in_reply_to: str | None = None,
    ) -> dict[str, Any]:
        """Generate a single email message."""
        message_id = self.generate_message_id()

        if not thread_id:
            thread_id = self.generate_thread_id()

        # Build headers
        headers = {
            "From": f"{sender.name} <{sender.email}>",
            "To": ", ".join([f"{r.name} <{r.email}>" for r in recipients[:3]]),  # Limit display
            "Subject": subject,
            "Date": timestamp.strftime("%a, %d %b %Y %H:%M:%S %z"),
            "Message-ID": message_id,
        }

        if is_reply and in_reply_to:
            headers["In-Reply-To"] = in_reply_to
            headers["References"] = in_reply_to

        # Add CC for larger groups
        if len(recipients) > 3:
            headers["Cc"] = ", ".join([f"{r.name} <{r.email}>" for r in recipients[3:]])

        # Estimate size based on email type and persona traits
        base_size = random.randint(1000, 5000)
        if sender.traits.detail_oriented:
            base_size *= 2
        if email_type == EmailType.NEWSLETTER:
            base_size *= 3

        # Attachments for certain email types
        parts = []
        if email_type in [EmailType.PROJECT_UPDATE, EmailType.WORK_STATUS] and random.random() < 0.4:
            # Add attachment
            attachment_types = [
                ("report.pdf", "application/pdf", random.randint(50000, 500000)),
                ("data.xlsx", "application/vnd.ms-excel", random.randint(10000, 100000)),
                ("presentation.pptx", "application/vnd.ms-powerpoint", random.randint(100000, 1000000)),
                ("diagram.png", "image/png", random.randint(50000, 200000)),
            ]
            attachment = random.choice(attachment_types)
            parts.append(
                {
                    "partId": "1",
                    "mimeType": attachment[1],
                    "filename": attachment[0],
                    "body_size": attachment[2],
                    "isAttachment": True,
                },
            )
            base_size += attachment[2]

        # Build message
        message = {
            "id": message_id.strip("<>"),
            "threadId": thread_id,
            "labelIds": self.generate_labels(email_type, is_read=(random.random() < 0.7)),
            "snippet": self.generate_snippet(email_type, sender),
            "historyId": str(random.randint(10000, 99999)),
            "internalDate": str(int(timestamp.timestamp() * 1000)),
            "sizeEstimate": base_size,
            "headers": headers,
            "collected_at": datetime.now(UTC).isoformat(),
        }

        if parts:
            message["parts"] = parts

        return message

    def generate_daily_emails(self, date: datetime) -> list[dict[str, Any]]:
        """Generate all emails for a specific day."""
        all_messages = []

        for persona in self.personas.values():
            # Check if persona is active on this day
            if not persona.should_send_on_day(date.weekday()):
                continue

            # Determine number of emails for this persona today
            daily_count = random.randint(*persona.daily_volume_range)
            active_hours = persona.get_active_hours()

            for _ in range(daily_count):
                # Pick a random time within active hours
                hour = random.choice(active_hours)
                minute = random.randint(0, 59)
                timestamp = date.replace(hour=hour, minute=minute, second=random.randint(0, 59))

                # Pick email type
                email_type = random.choice(persona.email_types)

                # Pick recipients from contacts
                num_recipients = random.randint(1, min(5, len(persona.contacts)))
                recipient_emails = random.sample(persona.contacts, num_recipients)
                recipients = [
                    self.personas.get(
                        email,
                        EmailPersona(email, "External User", email, "External", "External", PersonaTrait("external")),
                    )
                    for email in recipient_emails
                ]

                # Decide if this starts a thread or is standalone
                if (
                    email_type in [EmailType.QUESTION, EmailType.MEETING_REQUEST, EmailType.PROJECT_UPDATE]
                    and random.random() < 0.6
                ):
                    # Generate thread
                    thread_messages = self.generate_thread(
                        starter=persona,
                        participants=[r for r in recipients if isinstance(r, EmailPersona)],
                        email_type=email_type,
                        start_time=timestamp,
                    )
                    all_messages.extend(thread_messages)
                else:
                    # Single message
                    subject = self.generate_subject(email_type, persona)
                    message = self.generate_message(
                        sender=persona,
                        recipients=recipients,
                        subject=subject,
                        email_type=email_type,
                        timestamp=timestamp,
                    )
                    all_messages.append(message)

        return all_messages

    def generate_all_emails(self) -> list[dict[str, Any]]:
        """Generate emails for entire date range."""
        all_messages = []
        current_date = self.start_date

        while current_date <= self.end_date:
            daily_messages = self.generate_daily_emails(current_date)
            all_messages.extend(daily_messages)
            current_date += timedelta(days=1)

        # Sort by internal date
        all_messages.sort(key=lambda m: int(m["internalDate"]))

        return all_messages


class IndalekoGmailSyntheticCollector(CollaborationCollector):
    """Synthetic Gmail collector that generates realistic email patterns."""

    gmail_platform = "Gmail"
    gmail_collector_name = "gmail_synthetic_collector"

    indaleko_gmail_synthetic_uuid = "b8f4e3d2-9c5d-4e6f-a7b8-3d4c5e6f7a8b"
    indaleko_gmail_synthetic_service_name = "Gmail Synthetic Collector"
    indaleko_gmail_synthetic_service_description = "Generates synthetic Gmail data for testing and demonstration."
    indaleko_gmail_synthetic_service_version = "1.0"
    indaleko_gmail_synthetic_service_type = IndalekoServiceManager.service_type_activity_collector

    def __init__(self, **kwargs) -> None:
        """Initialize the synthetic collector."""
        self.personas = []
        self.start_date = kwargs.get("start_date", datetime.now(UTC) - timedelta(days=30))
        self.end_date = kwargs.get("end_date", datetime.now(UTC))
        self.personas_file = kwargs.get("personas_file")

        # Load personas
        if self.personas_file and os.path.exists(self.personas_file):
            self.load_personas_from_file(self.personas_file)
        else:
            self.create_default_personas()

        # Statistics
        self.message_count = 0
        self.thread_count = 0
        self.label_count = 0

        super().__init__()

    def create_default_personas(self) -> None:
        """Create a default set of personas for testing."""
        # Project Manager - Sarah Chen
        sarah = EmailPersona(
            id="sarah.chen",
            name="Sarah Chen",
            email="sarah.chen@indaleko.test",
            role="Senior Project Manager",
            department="Product",
            traits=PersonaTrait(
                name="sarah",
                morning_person=True,
                thread_starter=True,
                detail_oriented=True,
                formal_tone=True,
            ),
            email_types=[
                EmailType.WORK_STATUS,
                EmailType.PROJECT_UPDATE,
                EmailType.MEETING_REQUEST,
                EmailType.QUESTION,
            ],
            daily_volume_range=(15, 40),
            signature="Best regards,\nSarah Chen\nSenior Project Manager",
        )

        # Software Engineer - Marcus Rivera
        marcus = EmailPersona(
            id="marcus.rivera",
            name="Marcus Rivera",
            email="marcus.rivera@indaleko.test",
            role="Staff Software Engineer",
            department="Engineering",
            traits=PersonaTrait(
                name="marcus",
                night_owl=True,
                weekend_worker=True,
                quick_responder=True,
                emoji_user=True,
            ),
            email_types=[EmailType.ANSWER, EmailType.PROJECT_UPDATE, EmailType.QUESTION, EmailType.RESEARCH],
            daily_volume_range=(10, 25),
            signature="- Marcus\n🚀 Building the future",
        )

        # Designer - Alex Kumar
        alex = EmailPersona(
            id="alex.kumar",
            name="Alex Kumar",
            email="alex.kumar@indaleko.test",
            role="Lead Designer",
            department="Design",
            traits=PersonaTrait(name="alex", morning_person=True, detail_oriented=True, emoji_user=True),
            email_types=[EmailType.CREATIVE, EmailType.PROJECT_UPDATE, EmailType.SOCIAL, EmailType.ANSWER],
            daily_volume_range=(8, 20),
            signature="Alex Kumar\nLead Designer\n✨ Design is thinking made visual",
        )

        # Researcher - Dr. Patricia Wong
        patricia = EmailPersona(
            id="patricia.wong",
            name="Dr. Patricia Wong",
            email="patricia.wong@indaleko.test",
            role="Principal Researcher",
            department="Research",
            traits=PersonaTrait(name="patricia", detail_oriented=True, formal_tone=True, weekend_worker=True),
            email_types=[EmailType.RESEARCH, EmailType.ANSWER, EmailType.PROJECT_UPDATE, EmailType.NEWSLETTER],
            daily_volume_range=(5, 15),
            signature="Dr. Patricia Wong\nPrincipal Researcher\nIndaleko Research Division",
        )

        # Community Manager - Jordan Bailey
        jordan = EmailPersona(
            id="jordan.bailey",
            name="Jordan Bailey",
            email="jordan.bailey@indaleko.test",
            role="Community Manager",
            department="Marketing",
            traits=PersonaTrait(name="jordan", quick_responder=True, emoji_user=True, thread_starter=True),
            email_types=[EmailType.SOCIAL, EmailType.NEWSLETTER, EmailType.ANSWER, EmailType.MEETING_REQUEST],
            daily_volume_range=(20, 50),
            signature="Jordan Bailey\nCommunity Manager\n💬 Let's connect!",
        )

        # Set up contact networks
        all_personas = [sarah, marcus, alex, patricia, jordan]
        for persona in all_personas:
            # Everyone knows everyone else
            persona.contacts = [p.email for p in all_personas if p.id != persona.id]
            # Add some external contacts
            persona.contacts.extend(
                ["external.vendor@supplier.com", "client.contact@customer.org", "partner.rep@alliance.net"],
            )

        self.personas = all_personas

    def load_personas_from_file(self, filepath: str) -> None:
        """Load personas from a JSON configuration file."""
        with open(filepath) as f:
            personas_data = json.load(f)

        self.personas = []
        for p_data in personas_data["personas"]:
            traits = PersonaTrait(**p_data.get("traits", {}))
            email_types = [EmailType[t] for t in p_data.get("email_types", ["WORK_STATUS"])]

            persona = EmailPersona(
                id=p_data["id"],
                name=p_data["name"],
                email=p_data["email"],
                role=p_data.get("role", "Employee"),
                department=p_data.get("department", "General"),
                traits=traits,
                contacts=p_data.get("contacts", []),
                email_types=email_types,
                daily_volume_range=tuple(p_data.get("daily_volume_range", [5, 20])),
                signature=p_data.get("signature", ""),
            )
            self.personas.append(persona)

    def generate_labels(self) -> list[dict[str, str]]:
        """Generate Gmail label structure."""
        system_labels = [
            {"id": "INBOX", "name": "INBOX", "type": "system"},
            {"id": "SPAM", "name": "SPAM", "type": "system"},
            {"id": "TRASH", "name": "TRASH", "type": "system"},
            {"id": "UNREAD", "name": "UNREAD", "type": "system"},
            {"id": "STARRED", "name": "STARRED", "type": "system"},
            {"id": "IMPORTANT", "name": "IMPORTANT", "type": "system"},
            {"id": "SENT", "name": "SENT", "type": "system"},
            {"id": "DRAFT", "name": "DRAFT", "type": "system"},
            {"id": "CATEGORY_PERSONAL", "name": "CATEGORY_PERSONAL", "type": "system"},
            {"id": "CATEGORY_SOCIAL", "name": "CATEGORY_SOCIAL", "type": "system"},
            {"id": "CATEGORY_PROMOTIONS", "name": "CATEGORY_PROMOTIONS", "type": "system"},
            {"id": "CATEGORY_UPDATES", "name": "CATEGORY_UPDATES", "type": "system"},
            {"id": "CATEGORY_FORUMS", "name": "CATEGORY_FORUMS", "type": "system"},
        ]

        user_labels = [
            {"id": f"Label_{i}", "name": name, "type": "user"}
            for i, name in enumerate(["Projects", "Team", "Archive", "Follow-up", "Urgent"])
        ]

        return system_labels + user_labels

    def collect(self, mode: str = "messages", query: str = "", max_results: int | None = None) -> dict[str, Any]:
        """Generate synthetic Gmail data matching the real collector's output format."""
        # Initialize generator
        generator = SyntheticEmailGenerator(self.personas, self.start_date, self.end_date)

        # Generate all messages
        all_messages = generator.generate_all_emails()

        # Apply query filter if provided (simplified - just filters by label for demo)
        if query:
            if "is:unread" in query:
                all_messages = [m for m in all_messages if "UNREAD" in m.get("labelIds", [])]
            elif "is:starred" in query:
                all_messages = [m for m in all_messages if "STARRED" in m.get("labelIds", [])]
            # Add more query parsing as needed

        # Limit results if specified
        if max_results:
            all_messages = all_messages[:max_results]

        # Build collection data matching real collector format
        collection_data = {
            "platform": self.gmail_platform,
            "collector": self.gmail_collector_name,
            "version": self.indaleko_gmail_synthetic_service_version,
            "email": "synthetic@indaleko.test",  # Synthetic identifier
            "collected_at": datetime.now(UTC).isoformat(),
            "query": query,
            "mode": mode,
            "synthetic": True,  # Mark as synthetic data
            "personas": [  # Include persona information
                {"id": p.id, "name": p.name, "email": p.email, "role": p.role, "department": p.department}
                for p in self.personas
            ],
        }

        # Generate labels
        collection_data["labels"] = self.generate_labels()
        self.label_count = len(collection_data["labels"])

        # Add messages or threads based on mode
        if mode in {"messages", "all"}:
            collection_data["messages"] = all_messages
            self.message_count = len(all_messages)

        if mode in {"threads", "all"}:
            # Group messages by thread
            threads_dict = {}
            for msg in all_messages:
                thread_id = msg["threadId"]
                if thread_id not in threads_dict:
                    threads_dict[thread_id] = {"id": thread_id, "historyId": msg["historyId"], "messages": []}
                threads_dict[thread_id]["messages"].append(msg)

            threads = list(threads_dict.values())
            for thread in threads:
                thread["message_count"] = len(thread["messages"])
                thread["collected_at"] = datetime.now(UTC).isoformat()

            collection_data["threads"] = threads
            self.thread_count = len(threads)

        # Add statistics
        collection_data["statistics"] = {
            "message_count": self.message_count,
            "thread_count": self.thread_count,
            "label_count": self.label_count,
            "error_count": 0,  # Synthetic collector has no errors
            "personas_count": len(self.personas),
            "date_range": {"start": self.start_date.isoformat(), "end": self.end_date.isoformat()},
        }

        return collection_data

    def write_data_to_file(self, data: dict[str, Any], output_file: str) -> None:
        """Write collected data to a JSON file."""
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logging.info("Synthetic data written to %s", output_file)

    def get_counts(self) -> dict[str, int]:
        """Return collection statistics."""
        return {
            "messages": self.message_count,
            "threads": self.thread_count,
            "labels": self.label_count,
            "personas": len(self.personas),
            "errors": 0,
        }

    # CollaborationCollector abstract method implementations
    def get_collector_name(self) -> str:
        return self.gmail_collector_name

    def get_provider_id(self) -> uuid.UUID:
        return uuid.UUID(self.indaleko_gmail_synthetic_uuid)

    def get_description(self) -> str:
        return self.indaleko_gmail_synthetic_service_description


def local_run(keys: dict[str, str]) -> dict | None:
    """Run the synthetic Gmail collector."""
    args = keys["args"]
    cli = keys["cli"]
    config_data = cli.get_config_data()
    debug = hasattr(args, "debug") and args.debug
    if debug:
        ic(args)
        ic(config_data)

    output_file_name = str(Path(args.datadir) / args.outputfile)

    # Parse date range
    start_date = (
        datetime.fromisoformat(args.start_date)
        if args.start_date
        else datetime.now(UTC) - timedelta(days=args.days_back)
    )
    end_date = datetime.fromisoformat(args.end_date) if args.end_date else datetime.now(UTC)

    def collect(collector: IndalekoGmailSyntheticCollector) -> None:
        """Local implementation of collect."""
        mode = getattr(args, "mode", "messages")
        query = getattr(args, "query", "")
        max_results = getattr(args, "max_results", None)

        data = collector.collect(mode=mode, query=query, max_results=max_results)
        collector.write_data_to_file(data, output_file_name)

    def extract_counters(**kwargs):
        """Local implementation of extract_counters."""
        collector = kwargs.get("collector")
        if collector:
            return collector.get_counts()
        return {}

    collector = IndalekoGmailSyntheticCollector(
        start_date=start_date,
        end_date=end_date,
        personas_file=args.personas_file,
    )

    perf_data = IndalekoPerformanceDataCollector.measure_performance(
        collect,
        source=IndalekoSourceIdentifierDataModel(
            Identifier=collector.get_provider_id(),
            Version=collector.indaleko_gmail_synthetic_service_version,
            Description=collector.get_description(),
        ),
        description=collector.get_description(),
        MachineIdentifier=None,
        process_results_func=extract_counters,
        input_file_name=None,
        output_file_name=output_file_name,
        collector=collector,
    )

    if args.performance_db or args.performance_file:
        perf_recorder = IndalekoPerformanceDataRecorder()
        if args.performance_file:
            perf_file = str(Path(args.datadir) / config_data["PerformanceDataFile"])
            perf_recorder.add_data_to_file(perf_file, perf_data)
            if debug:
                ic("Performance data written to ", config_data["PerformanceDataFile"])
        if args.performance_db:
            perf_recorder.add_data_to_db(perf_data)
            if debug:
                ic("Performance data written to the database")

    return perf_data


def main() -> None:
    """Synthetic Gmail collector main entry point."""
    from utils.cli.base import IndalekoBaseCLI, IndalekoCLIRunner

    cli_data = {
        "name": "Gmail Synthetic Data Generator",
        "description": "Generates synthetic Gmail data for testing and demonstration",
        "epilog": "Creates realistic email patterns using configurable personas",
        "arguments": [
            {
                "name": "--mode",
                "type": str,
                "default": "messages",
                "choices": ["messages", "threads", "all"],
                "help": "Collection mode: messages, threads, or all",
            },
            {
                "name": "--query",
                "type": str,
                "default": "",
                "help": "Simulated Gmail search query (limited support)",
            },
            {
                "name": "--max-results",
                "type": int,
                "help": "Maximum number of items to generate",
            },
            {
                "name": "--start-date",
                "type": str,
                "help": "Start date for email generation (ISO format)",
            },
            {
                "name": "--end-date",
                "type": str,
                "help": "End date for email generation (ISO format)",
            },
            {
                "name": "--days-back",
                "type": int,
                "default": 30,
                "help": "Number of days back to generate emails (if no start date)",
            },
            {
                "name": "--personas-file",
                "type": str,
                "help": "JSON file with persona definitions",
            },
            {
                "name": "--datadir",
                "type": str,
                "default": "./data",
                "help": "Output data directory",
            },
            {
                "name": "--outputfile",
                "type": str,
                "default": f"gmail-synthetic-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json",
                "help": "Output file name",
            },
            {
                "name": "--performance-file",
                "action": "store_true",
                "help": "Write performance data to file",
            },
            {
                "name": "--performance-db",
                "action": "store_true",
                "help": "Write performance data to database",
            },
            {
                "name": "--debug",
                "action": "store_true",
                "help": "Enable debug output",
            },
        ],
    }

    runner = IndalekoCLIRunner(
        cli_data=cli_data,
        handler_mixin=None,
        features=IndalekoBaseCLI.cli_features(),
        Run=local_run,
    )
    runner.run()


if __name__ == "__main__":
    main()
