"""Generate Machine Configuration Metadata."""
import uuid

from datetime import UTC, datetime

from data_generator.scripts.metadata.metadata import Metadata
from data_models.machine_config import IndalekoMachineConfigDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from platforms.data_models.hardware import Hardware
from platforms.data_models.software import Software


class MachineConfigMetadata(Metadata):
    """
    Subclass for Metadata.

    Generates Machine Configuration Metadata based on the given Indaleko Records.
    """

    def __init__(self, selected_md=None) -> None:
        """Initialize the object."""
        super().__init__(selected_md)

    def generate_metadata(self, **kwargs: dict) -> IndalekoMachineConfigDataModel:
        """Generate the machine configuration metadata."""
        return self._generate_machine_metadata(kwargs.get("record"))

    def _generate_machine_metadata(
        self,
        record: IndalekoRecordDataModel,
    ) -> IndalekoMachineConfigDataModel:
        """Generate the machine configuration for the given Indaleko record."""
        timestamp = IndalekoTimestampDataModel(
            Label=uuid.uuid4(),
            Value=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            Description="Captured Timestamp",
        )

        hardware = Hardware.Config.json_schema_extra["example"]
        software = Software.Config.json_schema_extra["example"]

        return IndalekoMachineConfigDataModel(
            Record=record,
            Captured=timestamp,
            Hardware=hardware,
            Software=software,
        )
