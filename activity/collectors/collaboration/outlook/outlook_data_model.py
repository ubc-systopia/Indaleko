"""
This module defines the data models for
an Outlook-specific implementation.

Project Indaleko
"""

from typing import Optional
from pydantic import Field
from activity.collectors.collaboration.data_models.collaboration_data_model import BaseCollaborationDataModel


class OutlookDataModel(BaseCollaborationDataModel):
    """
    Outlook-specific implementation of the collaboration data model.
    """

    SharedFileName: Optional[str] = Field(
        None,
        title='SharedFileName',
        description='The original name of the shared file.',
    )

    SharedFileURI: Optional[str] = Field(
        None,
        title='SharedFileURI',
        description='The URI of the shared file.',
    )

    EmailID: Optional[str] = Field(
        None,
        title='EmailID',
        description='The ID of the email where the file was attached.',
    )

    class Config:
        """Configuration and example data for the Outlook data model"""
        json_schema_extra = {
            "example": {
                **BaseCollaborationDataModel.Config.json_schema_extra["example"],
                "SharedFileName": "example.docx",
                "SharedFileURI": "https://outlook.office.com/mail/inbox/id/123456789",
                "EmailID": "123456789",
            }
        }


def main():
    """This allows testing the data models"""
    print("\nTesting Outlook-specific Ambient Data Model:")
    OutlookDataModel.test_model_main()


if __name__ == '__main__':
    main()
