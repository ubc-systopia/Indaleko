"""
This module defines the base data model for e-mail file
sharing.

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

from pydantic import Field, HttpUrl, EmailStr
from typing import Union

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.collaboration.data_models.shared_file import SharedFileData
from activity.collectors.collaboration.data_models.collaboration_data_model import (
    BaseCollaborationDataModel,
)

# pylint: enable=wrong-import-position

class EmailFileShareCollaborationDataModel(BaseCollaborationDataModel):
    MessageID: Union[str, None] = Field(None, description="Email message ID (if known)")
    Subject: Union[str, None] = Field(None, description="Subject line of the email")
    From: Union[EmailStr, None] = Field(None, description="Sender email address")
    To: Union[list[EmailStr], None] = Field(None, description="Primary recipients")
    CC: Union[list[EmailStr], None] = Field(None, description="CC’d recipients")
    BCC: Union[list[EmailStr], None] = Field(None, description="BCC’d recipients (if visible)")
    Date: Union[AwareDatetime, None] = Field(None, description="Date and time of the email")
    ThreadID: Union[str, None] = Field(None, description="Conversation/thread identifier, if extractable")
    Files : list[SharedFileData] = Field([], description="Files attached to the email")

    class Config:
        @staticmethod
        def generate_example():
            base = BaseCollaborationDataModel.Config.generate_example()
            base.update({
                "Source": "email",
                "MessageID": "CA+4aG3=Na+XYZ@mail.gmail.com",
                "Subject": "Updated project timeline",
                "From": "tony.mason@example.com",
                "To": ["dr.jones@university.edu"],
                "CC": ["admin@ubc.ca"],
                "BCC": [],
                "ThreadID": "project-timeline-thread"
            })
            return base

        json_schema_extra = {
            "example": generate_example()
        }
