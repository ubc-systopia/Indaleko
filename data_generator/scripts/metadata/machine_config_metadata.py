from data_models.machine_config import IndalekoMachineConfigDataModel
from platforms.data_models.hardware import Hardware
from platforms.data_models.software import Software
from data_models.record import IndalekoRecordDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from datetime import datetime
import uuid
from data_generator.scripts.metadata.metadata import Metadata
from typing import Any


class MachineConfigMetadata(Metadata):
    """
    Subclass for Metadata.
    Generates Machine Configuration Metadata based on the given Indaleko Records
    """

    def __init__(self, selected_md=None):
        super().__init__(selected_md)

    def generate_metadata(self, record: IndalekoRecordDataModel) -> Any:
        return self._generate_machine_metadata(record)

    def _generate_machine_metadata(
        self, record: IndalekoRecordDataModel
    ) -> IndalekoMachineConfigDataModel:
        """
        Generate the machine configuration for the given Indaleko record using the example hardware and software information
        """
        timestamp = IndalekoTimestampDataModel(
            Label=uuid.uuid4(),
            Value=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            Description="Captured Timestamp",
        )
        hardware = Hardware.Config.json_schema_extra["example"]
        software = Software.Config.json_schema_extra["example"]
        machine_config = IndalekoMachineConfigDataModel(
            Record=record, Captured=timestamp, Hardware=hardware, Software=software
        )
        return machine_config
