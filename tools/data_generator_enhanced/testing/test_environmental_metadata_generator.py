"""
Unit tests for the EnvironmentalMetadataGeneratorTool.

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
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from tools.data_generator_enhanced.agents.data_gen.tools.environmental_metadata_generator import (
    EnvironmentalMetadataGenerator,
    EnvironmentalMetadataGeneratorTool,
    WeatherCondition,
    WeatherData,
    IndoorClimateData,
    WEATHER_CONDITION_UUID,
    TEMPERATURE_OUTDOOR_UUID,
    TEMPERATURE_INDOOR_UUID,
    HUMIDITY_OUTDOOR_UUID,
    HUMIDITY_INDOOR_UUID,
    WIND_SPEED_UUID,
    PRECIPITATION_UUID,
    AIR_QUALITY_UUID
)


class TestWeatherClasses(unittest.TestCase):
    """Test the weather and climate data classes."""
    
    def test_weather_condition_class(self):
        """Test the WeatherCondition class."""
        # Test the constants
        self.assertIn("clear", WeatherCondition.ALL_CONDITIONS)
        self.assertIn("rain", WeatherCondition.ALL_CONDITIONS)
        self.assertIn("snow", WeatherCondition.ALL_CONDITIONS)
        
        # Test temperature ranges
        self.assertEqual(WeatherCondition.TEMP_RANGES["clear"], (-5, 35))
        self.assertEqual(WeatherCondition.TEMP_RANGES["snow"], (-20, 5))
        
        # Test seasonal probabilities
        self.assertGreater(WeatherCondition.SEASONAL_PROBABILITY["winter"]["snow"], 
                            WeatherCondition.SEASONAL_PROBABILITY["summer"]["snow"])
        self.assertGreater(WeatherCondition.SEASONAL_PROBABILITY["summer"]["clear"], 
                            WeatherCondition.SEASONAL_PROBABILITY["winter"]["clear"])
        
        # Test get_seasonal_condition
        # Test northern hemisphere winter
        winter_date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        northern_lat = 40.0
        condition = WeatherCondition.get_seasonal_condition(winter_date, northern_lat)
        self.assertIn(condition, WeatherCondition.ALL_CONDITIONS)
        
        # Test southern hemisphere summer (same date)
        southern_lat = -40.0
        condition = WeatherCondition.get_seasonal_condition(winter_date, southern_lat)
        self.assertIn(condition, WeatherCondition.ALL_CONDITIONS)
        
        # Test get_condition_attributes
        attributes = WeatherCondition.get_condition_attributes("rain")
        self.assertIn("temperature", attributes)
        self.assertIn("precipitation", attributes)
        self.assertIn("humidity", attributes)
        self.assertIn("wind_speed", attributes)
        
        # Rain should have precipitation
        self.assertGreater(attributes["precipitation"], 0)
        
        # Test a non-existent condition (should use defaults)
        attributes = WeatherCondition.get_condition_attributes("non_existent")
        self.assertIn("temperature", attributes)
        self.assertIn("precipitation", attributes)
        self.assertIn("humidity", attributes)
        self.assertIn("wind_speed", attributes)
    
    def test_weather_data_class(self):
        """Test the WeatherData class."""
        # Create a weather data instance
        timestamp = datetime.now(timezone.utc)
        location = {"latitude": 40.7128, "longitude": -74.0060, "label": "Test Location"}
        condition = "clear"
        temperature = 22.5
        humidity = 45.0
        precipitation = 0.0
        wind_speed = 8.5
        
        weather = WeatherData(
            timestamp=timestamp,
            location=location,
            condition=condition,
            temperature=temperature,
            humidity=humidity,
            precipitation=precipitation,
            wind_speed=wind_speed
        )
        
        # Test attributes
        self.assertEqual(weather.timestamp, timestamp)
        self.assertEqual(weather.location, location)
        self.assertEqual(weather.condition, condition)
        self.assertEqual(weather.temperature, temperature)
        self.assertEqual(weather.humidity, humidity)
        self.assertEqual(weather.precipitation, precipitation)
        self.assertEqual(weather.wind_speed, wind_speed)
        
        # Test to_dict method
        weather_dict = weather.to_dict()
        self.assertEqual(weather_dict["timestamp"], timestamp.isoformat())
        self.assertEqual(weather_dict["location"], location)
        self.assertEqual(weather_dict["condition"], condition)
        self.assertEqual(weather_dict["temperature"], temperature)
        self.assertEqual(weather_dict["humidity"], humidity)
        self.assertEqual(weather_dict["precipitation"], precipitation)
        self.assertEqual(weather_dict["wind_speed"], wind_speed)
    
    def test_indoor_climate_data_class(self):
        """Test the IndoorClimateData class."""
        # Create an indoor climate data instance
        timestamp = datetime.now(timezone.utc)
        location = {"room": "Living Room"}
        temperature = 21.5
        humidity = 40.0
        hvac_mode = "heat"
        hvac_state = "heating"
        target_temperature = 22.0
        device_id = "ecobee123"
        device_name = "Living Room Thermostat"
        occupancy_detected = True
        air_quality = 85
        
        climate = IndoorClimateData(
            timestamp=timestamp,
            location=location,
            temperature=temperature,
            humidity=humidity,
            hvac_mode=hvac_mode,
            hvac_state=hvac_state,
            target_temperature=target_temperature,
            device_id=device_id,
            device_name=device_name,
            occupancy_detected=occupancy_detected,
            air_quality=air_quality
        )
        
        # Test attributes
        self.assertEqual(climate.timestamp, timestamp)
        self.assertEqual(climate.location, location)
        self.assertEqual(climate.temperature, temperature)
        self.assertEqual(climate.humidity, humidity)
        self.assertEqual(climate.hvac_mode, hvac_mode)
        self.assertEqual(climate.hvac_state, hvac_state)
        self.assertEqual(climate.target_temperature, target_temperature)
        self.assertEqual(climate.device_id, device_id)
        self.assertEqual(climate.device_name, device_name)
        self.assertEqual(climate.occupancy_detected, occupancy_detected)
        self.assertEqual(climate.air_quality, air_quality)
        
        # Fan mode should be auto for heating state
        self.assertEqual(climate.fan_mode, "auto")
        
        # Test to_dict method
        climate_dict = climate.to_dict()
        self.assertEqual(climate_dict["timestamp"], timestamp.isoformat())
        self.assertEqual(climate_dict["location"], location)
        self.assertEqual(climate_dict["temperature"], temperature)
        self.assertEqual(climate_dict["humidity"], humidity)
        self.assertEqual(climate_dict["hvac_mode"], hvac_mode)
        self.assertEqual(climate_dict["hvac_state"], hvac_state)
        self.assertEqual(climate_dict["target_temperature"], target_temperature)
        self.assertEqual(climate_dict["device_id"], device_id)
        self.assertEqual(climate_dict["device_name"], device_name)
        self.assertEqual(climate_dict["occupancy_detected"], occupancy_detected)
        self.assertEqual(climate_dict["air_quality"], air_quality)
        self.assertEqual(climate_dict["fan_mode"], "auto")


class TestEnvironmentalMetadataGenerator(unittest.TestCase):
    """Test cases for the EnvironmentalMetadataGenerator class."""

    def setUp(self):
        """Set up test environment."""
        self.generator = EnvironmentalMetadataGenerator()
        self.test_start_date = datetime.now(timezone.utc) - timedelta(days=3)
        self.test_end_date = datetime.now(timezone.utc)
        
        # Test locations
        self.test_locations = [
            {
                "latitude": 40.7128, 
                "longitude": -74.0060, 
                "label": "Home"
            },
            {
                "latitude": 37.7749,
                "longitude": -122.4194,
                "label": "Work"
            }
        ]

    def test_init(self):
        """Test initialization of the generator."""
        self.assertIsNotNone(self.generator)
        self.assertIsNotNone(self.generator.faker)
        self.assertIsNotNone(self.generator.weather_source_data)
        self.assertIsNotNone(self.generator.climate_source_data)
        self.assertIsNotNone(self.generator.indoor_locations)
        self.assertIsNotNone(self.generator.hvac_modes)
        self.assertIsNotNone(self.generator.hvac_states)
        self.assertIsNotNone(self.generator.weather_semantic_attributes)
        self.assertIsNotNone(self.generator.climate_semantic_attributes)
        
        # Check mappings
        self.assertEqual(self.generator.weather_semantic_attributes[WEATHER_CONDITION_UUID], "condition")
        self.assertEqual(self.generator.weather_semantic_attributes[TEMPERATURE_OUTDOOR_UUID], "temperature")
        self.assertEqual(self.generator.climate_semantic_attributes[TEMPERATURE_INDOOR_UUID], "temperature")

    def test_generate_weather_forecast(self):
        """Test generation of weather forecast."""
        # Generate a small forecast for a day
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=1)
        
        forecast = self.generator._generate_weather_forecast(
            start_date=start_date,
            end_date=end_date,
            locations=self.test_locations
        )
        
        # Check forecast structure
        self.assertIsInstance(forecast, dict)
        self.assertGreater(len(forecast), 0)
        
        # Check a sample entry
        sample_key = next(iter(forecast))
        sample_weather = forecast[sample_key]
        
        self.assertIsInstance(sample_weather, WeatherData)
        self.assertIsInstance(sample_weather.timestamp, datetime)
        self.assertIsInstance(sample_weather.condition, str)
        self.assertIsInstance(sample_weather.temperature, float)
        self.assertIsInstance(sample_weather.humidity, float)
        self.assertIsInstance(sample_weather.precipitation, float)
        self.assertIsInstance(sample_weather.wind_speed, float)
        
        # Check location label and time constraints
        location_label, timestamp = sample_key
        self.assertIn(location_label, ["Home", "Work"])
        self.assertGreaterEqual(timestamp, start_date)
        self.assertLessEqual(timestamp, end_date)

    def test_generate_indoor_climate_data(self):
        """Test generation of indoor climate data."""
        # First generate a weather forecast
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=1)
        
        forecast = self.generator._generate_weather_forecast(
            start_date=start_date,
            end_date=end_date,
            locations=[{"latitude": 40.7128, "longitude": -74.0060, "label": "Home"}]
        )
        
        # Generate indoor climate data based on the forecast
        climate_data = self.generator._generate_indoor_climate_data(
            start_date=start_date,
            end_date=end_date,
            weather_forecast=forecast
        )
        
        # Check climate data structure
        self.assertIsInstance(climate_data, dict)
        
        # Should have entries for each room
        expected_room_count = len(self.generator.indoor_locations)
        room_keys = set()
        for key in climate_data:
            room, _ = key
            room_keys.add(room)
        
        self.assertEqual(len(room_keys), expected_room_count)
        
        # Check a sample entry if available
        if climate_data:
            sample_key = next(iter(climate_data))
            sample_climate = climate_data[sample_key]
            
            self.assertIsInstance(sample_climate, IndoorClimateData)
            self.assertIsInstance(sample_climate.timestamp, datetime)
            self.assertIsInstance(sample_climate.temperature, float)
            self.assertIsInstance(sample_climate.humidity, float)
            self.assertIsInstance(sample_climate.hvac_mode, str)
            self.assertIsInstance(sample_climate.hvac_state, str)
            self.assertIsInstance(sample_climate.target_temperature, float)
            self.assertIsInstance(sample_climate.device_id, str)
            self.assertIsInstance(sample_climate.device_name, str)
            self.assertIsInstance(sample_climate.occupancy_detected, bool)
            self.assertIsInstance(sample_climate.air_quality, int)
            
            # Check room and time constraints
            room, timestamp = sample_key
            self.assertIn(room, [loc["room"] for loc in self.generator.indoor_locations])
            self.assertGreaterEqual(timestamp, start_date)
            self.assertLessEqual(timestamp, end_date)

    def test_create_weather_data_model(self):
        """Test creation of structured weather data model."""
        # Create a sample weather data
        timestamp = datetime.now(timezone.utc)
        weather_data = WeatherData(
            timestamp=timestamp,
            location={"latitude": 40.7128, "longitude": -74.0060, "label": "Test"},
            condition="clear",
            temperature=22.5,
            humidity=45.0,
            precipitation=0.0,
            wind_speed=8.5
        )
        
        # Convert to activity data model
        activity_data = self.generator.create_weather_data_model(weather_data)
        
        # Verify structure
        self.assertEqual(activity_data.Timestamp, timestamp)
        self.assertIsNotNone(activity_data.Record)
        self.assertIsNotNone(activity_data.SemanticAttributes)
        
        # Verify Record field
        self.assertEqual(activity_data.Record.SourceIdentifier.Identifier, 
                         self.generator.weather_source_data["Identifier"])
        self.assertEqual(activity_data.Record.Timestamp, timestamp)
        
        # Verify Data contains encoded weather data
        data_dict = json.loads(activity_data.Record.Data)
        self.assertEqual(data_dict["condition"], "clear")
        self.assertEqual(data_dict["temperature"], 22.5)
        
        # Verify SemanticAttributes
        self.assertGreater(len(activity_data.SemanticAttributes), 0)
        
        # Check for specific semantic attributes
        condition_attr = None
        temperature_attr = None
        
        for attr in activity_data.SemanticAttributes:
            if attr.Identifier.Identifier == WEATHER_CONDITION_UUID:
                condition_attr = attr
            elif attr.Identifier.Identifier == TEMPERATURE_OUTDOOR_UUID:
                temperature_attr = attr
                
        # Attributes should contain the correct data
        self.assertIsNotNone(condition_attr)
        self.assertIsNotNone(temperature_attr)

    def test_create_climate_data_model(self):
        """Test creation of structured climate data model."""
        # Create a sample climate data
        timestamp = datetime.now(timezone.utc)
        climate_data = IndoorClimateData(
            timestamp=timestamp,
            location={"room": "Living Room"},
            temperature=21.5,
            humidity=40.0,
            hvac_mode="heat",
            hvac_state="heating",
            target_temperature=22.0,
            device_id="ecobee123",
            device_name="Living Room",
            occupancy_detected=True,
            air_quality=85
        )
        
        # Convert to activity data model
        activity_data = self.generator.create_climate_data_model(climate_data)
        
        # Verify structure
        self.assertEqual(activity_data.Timestamp, timestamp)
        self.assertIsNotNone(activity_data.Record)
        self.assertIsNotNone(activity_data.SemanticAttributes)
        
        # Verify Record field
        self.assertEqual(activity_data.Record.SourceIdentifier.Identifier, 
                         self.generator.climate_source_data["Identifier"])
        self.assertEqual(activity_data.Record.Timestamp, timestamp)
        
        # Verify Data contains encoded climate data
        data_dict = json.loads(activity_data.Record.Data)
        self.assertEqual(data_dict["temperature"], 21.5)
        self.assertEqual(data_dict["hvac_mode"], "heat")
        self.assertEqual(data_dict["device_id"], "ecobee123")
        
        # Verify SemanticAttributes
        self.assertGreater(len(activity_data.SemanticAttributes), 0)
        
        # Check for specific semantic attributes
        temperature_attr = None
        humidity_attr = None
        
        for attr in activity_data.SemanticAttributes:
            if attr.Identifier.Identifier == TEMPERATURE_INDOOR_UUID:
                temperature_attr = attr
            elif attr.Identifier.Identifier == HUMIDITY_INDOOR_UUID:
                humidity_attr = attr
                
        # Temperature attribute should exist
        self.assertIsNotNone(temperature_attr)

    def test_prepare_for_database(self):
        """Test preparation of data for database insertion."""
        # Create a sample weather data
        timestamp = datetime.now(timezone.utc)
        weather_data = WeatherData(
            timestamp=timestamp,
            location={"latitude": 40.7128, "longitude": -74.0060, "label": "Test"},
            condition="clear",
            temperature=22.5,
            humidity=45.0,
            precipitation=0.0,
            wind_speed=8.5
        )
        
        # Convert to activity data and then to database format
        activity_data = self.generator.create_weather_data_model(weather_data)
        db_record = self.generator.prepare_for_database(activity_data)
        
        # Verify dictionary format
        self.assertIsInstance(db_record, dict)
        
        # Verify essential fields
        self.assertIn("Record", db_record)
        self.assertIn("Timestamp", db_record)
        self.assertIn("SemanticAttributes", db_record)
        
        # Verify Record structure
        self.assertIn("SourceIdentifier", db_record["Record"])
        self.assertIn("Timestamp", db_record["Record"])
        self.assertIn("Data", db_record["Record"])
        
        # Verify SemanticAttributes structure
        self.assertIsInstance(db_record["SemanticAttributes"], list)
        
        # The semantic attributes structure may vary - we just need to verify there are attributes
        self.assertGreater(len(db_record["SemanticAttributes"]), 0)

    def test_generate_weather_data(self):
        """Test generation of weather data."""
        # Generate a small batch with fixed count
        records = self.generator.generate_weather_data(
            start_date=self.test_start_date,
            end_date=self.test_end_date,
            locations=self.test_locations,
            count=5
        )
        
        # Verify count
        self.assertEqual(len(records), 5)
        
        # Verify structure of each record
        for record in records:
            self.assertIn("Record", record)
            self.assertIn("Timestamp", record)
            self.assertIn("SemanticAttributes", record)
            
            # Verify Record field
            self.assertIn("SourceIdentifier", record["Record"])
            self.assertIn("Data", record["Record"])
            
            # Verify SemanticAttributes
            self.assertIsInstance(record["SemanticAttributes"], list)

    def test_generate_indoor_climate_data(self):
        """Test generation of indoor climate data."""
        # Generate a small batch with fixed count
        records = self.generator.generate_indoor_climate_data(
            start_date=self.test_start_date,
            end_date=self.test_end_date,
            count=5
        )
        
        # Verify count
        self.assertEqual(len(records), 5)
        
        # Verify structure of each record
        for record in records:
            self.assertIn("Record", record)
            self.assertIn("Timestamp", record)
            self.assertIn("SemanticAttributes", record)
            
            # Verify Record field
            self.assertIn("SourceIdentifier", record["Record"])
            self.assertIn("Data", record["Record"])
            
            # Verify SemanticAttributes
            self.assertIsInstance(record["SemanticAttributes"], list)
            
            # Check the Data field structure
            if "Data" in record["Record"] and record["Record"]["Data"]:
                data = json.loads(record["Record"]["Data"])
                self.assertIn("temperature", data)
                self.assertIn("humidity", data)
                self.assertIn("hvac_mode", data)
                self.assertIn("location", data)
                self.assertIn("room", data["location"])


class TestEnvironmentalMetadataGeneratorTool(unittest.TestCase):
    """Test cases for the EnvironmentalMetadataGeneratorTool class."""

    def setUp(self):
        """Set up test environment."""
        self.generator_tool = EnvironmentalMetadataGeneratorTool()
        self.test_start_date = datetime.now(timezone.utc) - timedelta(days=3)
        self.test_end_date = datetime.now(timezone.utc)

    def test_init(self):
        """Test initialization of the EnvironmentalMetadataGeneratorTool."""
        self.assertIsNotNone(self.generator_tool)
        self.assertIsNotNone(self.generator_tool.generator)
        self.assertIsInstance(self.generator_tool.generator, EnvironmentalMetadataGenerator)

    def test_generate_environmental_data(self):
        """Test generation of environmental data through the tool interface."""
        # Generate a small batch of records
        result = self.generator_tool.generate_environmental_data(
            start_date=self.test_start_date,
            end_date=self.test_end_date,
            count_weather=5,
            count_climate=5,
            insert_to_db=False
        )
        
        # Verify result structure
        self.assertIn("total_weather_records", result)
        self.assertIn("total_climate_records", result)
        self.assertIn("weather_db_inserts", result)
        self.assertIn("climate_db_inserts", result)
        self.assertIn("date_range", result)
        self.assertIn("top_weather_conditions", result)
        self.assertIn("location_distribution", result)
        self.assertIn("indoor_room_distribution", result)
        self.assertIn("indoor_hvac_modes", result)
        self.assertIn("hourly_distribution", result)
        self.assertIn("sample_weather_record", result)
        self.assertIn("sample_climate_record", result)
        
        # Verify counts
        self.assertEqual(result["total_weather_records"], 5)
        self.assertEqual(result["total_climate_records"], 5)
        self.assertEqual(result["weather_db_inserts"], 0)  # insert_to_db was False
        self.assertEqual(result["climate_db_inserts"], 0)  # insert_to_db was False
        
        # Verify date range
        self.assertIn("start", result["date_range"])
        self.assertIn("end", result["date_range"])
        
        # Verify hourly distribution includes all hours
        self.assertEqual(len(result["hourly_distribution"]), 24)
        
        # Verify sample records
        if result["sample_weather_record"]:
            sample = result["sample_weather_record"]
            self.assertIn("Record", sample)
            self.assertIn("Timestamp", sample)
            self.assertIn("SemanticAttributes", sample)
            
        if result["sample_climate_record"]:
            sample = result["sample_climate_record"]
            self.assertIn("Record", sample)
            self.assertIn("Timestamp", sample)
            self.assertIn("SemanticAttributes", sample)


if __name__ == "__main__":
    unittest.main()