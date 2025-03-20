from typing import Dict
import random
import uuid
from datetime import datetime
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
import string
from typing import Any
from activity.collectors.ambient.data_models.smart_thermostat import (
    ThermostatSensorData,
)
from activity.collectors.ambient.smart_thermostat.ecobee_data_model import (
    EcobeeAmbientDataModel,
)
from data_generator.scripts.metadata.activity_metadata import ActivityMetadata


class TempActivityData(ActivityMetadata):
    """
    Subclass for ActivityMetadata.
    Used to generate Temperature Activity Context based on EcobeeAmbientData
    """

    def __init__(self, selected_AC_md):
        super().__init__(selected_AC_md)

    def generate_metadata(
        self,
        record_kwargs: IndalekoRecordDataModel,
        timestamps: Dict[str, datetime],
        is_truth_file: bool,
        truth_like: bool,
        truthlike_attributes: list[str],
    ) -> Any:
        is_truth_file = self._define_truth_attribute(
            "ecobee_temp", is_truth_file, truth_like, truthlike_attributes
        )
        return self._generate_temp_metadata(record_kwargs, timestamps, is_truth_file)

    # Helper functions for creating ambient temperature activity context within generate_metadata():
    def _generate_temp_metadata(
        self,
        record_kwargs: IndalekoRecordDataModel,
        timestamps: Dict[str, datetime],
        is_truth_file: bool,
    ) -> EcobeeAmbientDataModel:
        allowed_chars = string.ascii_letters + string.digits
        device_id = "".join(random.choices(allowed_chars, k=12))
        current_state = ["home", "away", "sleep", "custom"]
        smart_thermostat_data = self._generate_thermostat_sensor_data(
            is_truth_file, record_kwargs, timestamps
        )
        ecobee_ac_md = EcobeeAmbientDataModel(
            **smart_thermostat_data.dict(),
            device_id=device_id,
            device_name="ecobee",
            current_climate=random.choice(current_state),
            connected_sensors=random.randint(0, 5),
        )
        return ecobee_ac_md

    def _generate_thermostat_sensor_data(
        self,
        is_truth_file: bool,
        record_kwargs: IndalekoRecordDataModel,
        timestamps: Dict[str, datetime],
    ) -> ThermostatSensorData:
        """returns the thermostat sensor data"""
        temp_lower_bound, temp_upper_bound = -50.0, 100.0
        humidity_lower_bound, humidity_upper_bound = 0.0, 100.0
        hvac_modes = ["heat", "cool", "auto", "off"]
        hvac_states = ["heating", "cooling", "fan", "idle"]
        fan_modes = ["auto", "on", "scheduled"]
        timestamp = self._generate_ac_timestamp(
            is_truth_file, timestamps, "ecobee_temp"
        )

        temperature = round(random.uniform(temp_lower_bound, temp_upper_bound), 1)
        humidity = round(random.uniform(humidity_lower_bound, humidity_upper_bound), 1)
        target_temp = round(random.uniform(temp_lower_bound, temp_upper_bound), 1)
        hvac_mode = random.choice(hvac_modes)
        hvac_state = random.choice(hvac_states)
        fan_mode = random.choice(fan_modes)

        if "ecobee_temp" in self.selected_md:
            ecobee_dict = self.selected_md["ecobee_temp"]
            if "temperature" in ecobee_dict:
                temperature = self._generate_number(
                    is_truth_file,
                    ecobee_dict["temperature"],
                    temp_lower_bound,
                    temp_upper_bound,
                )
            if "humidity" in ecobee_dict:
                humidity = self._generate_number(
                    is_truth_file,
                    ecobee_dict["humidity"],
                    humidity_lower_bound,
                    humidity_upper_bound,
                )
            if "target_temperature" in ecobee_dict:
                target_temp = self._generate_number(
                    is_truth_file,
                    ecobee_dict["target_temperature"],
                    temp_lower_bound,
                    temp_upper_bound,
                )
            if "hvac_mode" in ecobee_dict:
                hvac_mode = self._choose_random_element(
                    is_truth_file, ecobee_dict["hvac_mode"], hvac_modes
                )
            if "hvac_state" in ecobee_dict:
                hvac_state = self._choose_random_element(
                    is_truth_file, ecobee_dict["hvac_state"], hvac_states
                )
            if "fan_mode" in ecobee_dict:
                fan_mode = self._choose_random_element(
                    is_truth_file, ecobee_dict["fan_mode"], fan_modes
                )

        temperature_identifier = IndalekoUUIDDataModel(
            Identifier=uuid.uuid4(), Label="temperature"
        )
        humidity_identifier = IndalekoUUIDDataModel(
            Identifier=uuid.uuid4(), Label="humidity"
        )
        semantic_attributes = [
            IndalekoSemanticAttributeDataModel(
                Identifier=temperature_identifier, Value=temperature
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=humidity_identifier, Value=humidity
            ),
        ]

        return ThermostatSensorData(
            Record=record_kwargs,
            Timestamp=timestamp,
            source="ecobee",
            SemanticAttributes=semantic_attributes,
            temperature=round(temperature, 1),
            humidity=round(humidity, 1),
            hvac_mode=hvac_mode,
            fan_mode=fan_mode,
            hvac_state=hvac_state,
            target_temperature=round(target_temp, 1),
        )
