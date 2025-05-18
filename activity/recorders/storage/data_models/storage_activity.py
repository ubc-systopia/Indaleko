"""Define the data model for storage activity."""

import enum
import os
import sys

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import AwareDatetime, Field


# Handle imports for when the module is run directly
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


# pylint: disable=wrong-import-position
from activity.data_model.activity import IndalekoActivityDataModel


# pylint: enable=wrong-import-position

class IndalekoStorageActivitySemanticType(enum.Enum):
    """Define the semantic reasons for storage activity."""
    CHANGE_REASON_CREATE = "Create"
    CHANGE_REASON_READ = "Read"
    CHANGE_REASON_WRITE = "Write"
    CHANGE_REASON_DELETE = "Delete"


class IndalekoStorageActivityDataModel(IndalekoActivityDataModel):
    """Defines the data model for storage activity."""

    ExistingObjectIdentifier:  UUID | None = Field(
        default_factory=lambda: None,
        title="ExistingObjectIdentifier",
        description="""
            The identifier of the existing object (if there is one) "
            in the storage system.  This is used to track the object
            in the storage system.""",
        )

    PeriodStart: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        title="PeriodStart",
        description="""
            The start of the period during which the activity occurred.
            This is used to track the time period of the activity.""",
        )

    PeriodEnd: AwareDatetime = Field(
        default_factory=lambda: datetime.now(UTC),
        title="PeriodEnd",
        description="""
            The end of the period during which the activity occurred.
            This is used to track the time period of the activity.""",
        )

    Reasons: list[IndalekoStorageActivitySemanticType] = Field(
        default_factory=list,
        title="Reasons",
        description="""
            The reasons for the storage activity. This is used to track
            the reasons for the activity.""",
        )

    class Config: # type: ignore  # noqa: PGH003
        """Configuration for the storage activity data model."""

        @staticmethod
        def get_example() -> dict[str, object]:
            """Get an example of the storage activity data model."""
            example = IndalekoActivityDataModel.Config.json_schema_extra["example"].copy()
            example["ExistingObjectIdentifier"] = uuid4()
            return example

        json_schema_extra = {  # noqa: RUF012
            "example": get_example(),
        }

def main() -> None:
    """Test code for the storage activity data model."""
    IndalekoStorageActivityDataModel.test_model_main() # type: ignore  # noqa: PGH003


if __name__ == "__main__":
    main()
