from typing import Dict, Any
import random
import uuid
from datetime import datetime
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
import string
from activity.collectors.ambient.data_models.smart_thermostat import ThermostatSensorData
from activity.collectors.ambient.smart_thermostat.ecobee_data_model import EcobeeAmbientDataModel
from data_generator.scripts.metadata.activity_metadata import ActivityMetadata

class TempActivityData(ActivityMetadata):
    """
    Subclass for ActivityMetadata.
    Used to generate Temperature Activity Context based on EcobeeAmbientData
    """

    LOWER_TEMP, UPPER_TEMP = -50.0, 100.0
    LOWER_HUMIDITY, UPPER_HUMIDITY = 0.0, 100.0
    NUMBER_SENSOR_MIN, NUMBER_SENSOR_MAX = 0, 5
     
    CURRENT_STATE = ['home','away','sleep', 'custom']
    HVAC_MODES = ["heat", "cool", "auto", "off"]
    HVAC_STATES = ["heating", "cooling", "fan", "idle"]
    FAN_MODES = ["auto", "on", "scheduled"]

    def __init__(self, selected_AC_md):
        super().__init__(selected_AC_md)

    def generate_metadata(self, record_kwargs: IndalekoRecordDataModel, timestamps: Dict[str, datetime], \
        is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str]) -> Any:
        is_truth_file=self._define_truth_attribute("ecobee_temp", is_truth_file, truth_like, truthlike_attributes)
        return self._generate_temp_metadata(record_kwargs, timestamps, is_truth_file)

    # Helper functions for creating ambient temperature activity context within generate_metadata():
    def _generate_temp_metadata(self, record_kwargs: IndalekoRecordDataModel, timestamps: Dict[str, datetime], \
        is_truth_file: bool) -> EcobeeAmbientDataModel:

        allowed_chars = string.ascii_letters + string.digits
        device_id = ''.join(random.choices(allowed_chars, k=12))
        smart_thermostat_data = self._generate_thermostat_sensor_data(is_truth_file, record_kwargs, timestamps)
        ecobee_ac_md = EcobeeAmbientDataModel(
            **smart_thermostat_data.dict(),
            device_id= device_id,
            device_name= "ecobee",
            current_climate=random.choice(self.CURRENT_STATE),
            connected_sensors=random.randint(self.NUMBER_SENSOR_MIN, self.NUMBER_SENSOR_MAX)
        )
        return ecobee_ac_md

    def _generate_thermostat_sensor_data(self, is_truth_file: bool, record_kwargs: IndalekoRecordDataModel, \
        timestamps: Dict[str, datetime]) -> ThermostatSensorData:
        """
        Returns the thermostat sensor data
        """
        timestamp = self._generate_ac_timestamp(is_truth_file, timestamps, "ecobee_temp")

        temperature = round(random.uniform(self.LOWER_TEMP, self.UPPER_TEMP), 1)
        humidity = round(random.uniform(self.LOWER_HUMIDITY, self.UPPER_HUMIDITY), 1)
        target_temp = round(random.uniform(self.LOWER_TEMP, self.UPPER_TEMP), 1)
        hvac_mode = random.choice(self.HVAC_MODES)
        hvac_state = random.choice(self.HVAC_STATES)
        fan_mode = random.choice(self.FAN_MODES)

        if "ecobee_temp" in self.selected_md:
            ecobee_dict = self.selected_md["ecobee_temp"]
            if "temperature" in ecobee_dict:
                temperature = self._generate_number(
                    is_truth_file, ecobee_dict["temperature"], self.LOWER_TEMP, self.UPPER_TEMP
                )
            if "humidity" in ecobee_dict:
                humidity = self._generate_number(
                    is_truth_file, ecobee_dict["humidity"], self.LOWER_HUMIDITY, self.UPPER_HUMIDITY
                )
            if "target_temperature" in ecobee_dict:
                target_temp = self._generate_number(
                    is_truth_file, ecobee_dict["target_temperature"], self.LOWER_TEMP, self.UPPER_TEMP
                )
            if "hvac_mode" in ecobee_dict:
                hvac_mode = self._choose_random_element(
                    is_truth_file, ecobee_dict["hvac_mode"], self.HVAC_MODES
                )
            if "hvac_state" in ecobee_dict:
                hvac_state = self._choose_random_element(
                    is_truth_file, ecobee_dict["hvac_state"], self.HVAC_STATES
                )
            if "fan_mode" in ecobee_dict:
                fan_mode = self._choose_random_element(
                    is_truth_file, ecobee_dict["fan_mode"], self.FAN_MODES
                )

        temperature_identifier = IndalekoUUIDDataModel(Identifier=uuid.uuid4(), Label="temperature")
        humidity_identifier = IndalekoUUIDDataModel(Identifier=uuid.uuid4(), Label="humidity")
        semantic_attributes = [
                IndalekoSemanticAttributeDataModel(Identifier=temperature_identifier, Data=temperature),
                IndalekoSemanticAttributeDataModel(Identifier=humidity_identifier, Data=humidity)
                ]

        return ThermostatSensorData(
            Record=record_kwargs,
            Timestamp= timestamp,
            source = "ecobee",
            SemanticAttributes= semantic_attributes,
            temperature= round(temperature, 1),
            humidity= round(humidity, 1),
            hvac_mode= hvac_mode,
            fan_mode= fan_mode,
            hvac_state=hvac_state,
            target_temperature=round(target_temp,1)
        )
