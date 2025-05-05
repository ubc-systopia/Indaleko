"""
Environmental Metadata Generator for creating weather and indoor climate data.

This tool generates realistic environmental data including:
1. Weather conditions with temporal and location consistency
2. Indoor climate data from smart thermostats
3. Proper semantic attributes for environmental context queries

The generated data integrates with other metadata generators to enable
queries like "photos taken on rainy days" or "documents worked on during hot weather".

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
import random
import string
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union

import faker

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from activity.collectors.ambient.data_models.smart_thermostat import ThermostatSensorData
from activity.collectors.ambient.smart_thermostat.ecobee_data_model import EcobeeAmbientDataModel
from activity.data_model.activity import IndalekoActivityDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections


# Define semantic attribute UUIDs for weather and climate data
WEATHER_CONDITION_UUID = "69f7a1b0-5c4c-4a7f-8d3e-cd6cb0e6a129"
TEMPERATURE_OUTDOOR_UUID = "53c3e8d7-aa21-4b5f-9f3c-5b8a6f91e0a2"
TEMPERATURE_INDOOR_UUID = "c5e2c8d0-6b7e-4d8f-a1c2-f0d2a5e7b9c3"
HUMIDITY_OUTDOOR_UUID = "2a7c1e95-6d3f-4b0a-9c1d-8e6f4a2b5c3d"
HUMIDITY_INDOOR_UUID = "7d8e9f0a-1b2c-3d4e-5f6g-7h8i9j0k1l2m"
WIND_SPEED_UUID = "4b5c6d7e-8f9g-0h1i-2j3k-4l5m6n7o8p9"
PRECIPITATION_UUID = "9a8b7c6d-5e4f-3g2h-1i0j-9k8l7m6n5o"
AIR_QUALITY_UUID = "0p9o8n7m-6l5k-4j3h-2g1f-0e9d8c7b6a"


class WeatherCondition:
    """Enumeration of weather conditions used in our model."""
    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    RAIN = "rain"
    THUNDERSTORM = "thunderstorm"
    SNOW = "snow"
    FOG = "fog"
    WINDY = "windy"
    HAIL = "hail"
    SLEET = "sleet"
    FREEZING_RAIN = "freezing_rain"
    
    ALL_CONDITIONS = [
        CLEAR, PARTLY_CLOUDY, CLOUDY, RAIN, 
        THUNDERSTORM, SNOW, FOG, WINDY, HAIL, 
        SLEET, FREEZING_RAIN
    ]
    
    # Map weather conditions to temperature ranges (in Celsius)
    TEMP_RANGES = {
        CLEAR: (-5, 35),
        PARTLY_CLOUDY: (-5, 33),
        CLOUDY: (-10, 30),
        RAIN: (0, 25),
        THUNDERSTORM: (5, 32),
        SNOW: (-20, 5),
        FOG: (-5, 20),
        WINDY: (-10, 25),
        HAIL: (0, 25),
        SLEET: (-5, 5),
        FREEZING_RAIN: (-10, 2)
    }
    
    # Map weather conditions to precipitation ranges (in mm)
    PRECIP_RANGES = {
        CLEAR: (0, 0),
        PARTLY_CLOUDY: (0, 0),
        CLOUDY: (0, 1),
        RAIN: (1, 25),
        THUNDERSTORM: (5, 50),
        SNOW: (1, 20),  # snow water equivalent
        FOG: (0, 1),
        WINDY: (0, 1),
        HAIL: (5, 15),
        SLEET: (2, 10),
        FREEZING_RAIN: (1, 15)
    }
    
    # Map weather conditions to humidity ranges (in %)
    HUMIDITY_RANGES = {
        CLEAR: (20, 60),
        PARTLY_CLOUDY: (30, 70),
        CLOUDY: (40, 80),
        RAIN: (70, 95),
        THUNDERSTORM: (65, 95),
        SNOW: (65, 95),
        FOG: (80, 100),
        WINDY: (30, 70),
        HAIL: (60, 90),
        SLEET: (70, 95),
        FREEZING_RAIN: (75, 95)
    }
    
    # Map weather conditions to wind speed ranges (in km/h)
    WIND_RANGES = {
        CLEAR: (0, 15),
        PARTLY_CLOUDY: (0, 20),
        CLOUDY: (5, 25),
        RAIN: (5, 30),
        THUNDERSTORM: (15, 60),
        SNOW: (5, 35),
        FOG: (0, 10),
        WINDY: (25, 80),
        HAIL: (10, 40),
        SLEET: (10, 35),
        FREEZING_RAIN: (5, 30)
    }
    
    # Map weather conditions to seasonal probabilities
    SEASONAL_PROBABILITY = {
        "winter": {
            CLEAR: 0.15, PARTLY_CLOUDY: 0.15, CLOUDY: 0.2, RAIN: 0.05,
            THUNDERSTORM: 0.01, SNOW: 0.25, FOG: 0.08, WINDY: 0.05,
            HAIL: 0.01, SLEET: 0.03, FREEZING_RAIN: 0.02
        },
        "spring": {
            CLEAR: 0.25, PARTLY_CLOUDY: 0.25, CLOUDY: 0.15, RAIN: 0.15,
            THUNDERSTORM: 0.07, SNOW: 0.03, FOG: 0.05, WINDY: 0.03,
            HAIL: 0.01, SLEET: 0.01, FREEZING_RAIN: 0.0
        },
        "summer": {
            CLEAR: 0.35, PARTLY_CLOUDY: 0.3, CLOUDY: 0.1, RAIN: 0.1,
            THUNDERSTORM: 0.1, SNOW: 0.0, FOG: 0.02, WINDY: 0.02,
            HAIL: 0.01, SLEET: 0.0, FREEZING_RAIN: 0.0
        },
        "fall": {
            CLEAR: 0.25, PARTLY_CLOUDY: 0.25, CLOUDY: 0.2, RAIN: 0.15,
            THUNDERSTORM: 0.03, SNOW: 0.02, FOG: 0.06, WINDY: 0.03,
            HAIL: 0.0, SLEET: 0.01, FREEZING_RAIN: 0.0
        }
    }
    
    @staticmethod
    def get_seasonal_condition(date: datetime, latitude: float) -> str:
        """
        Get a weather condition based on season and latitude.
        
        Args:
            date: The date to determine the season
            latitude: The latitude to adjust seasonal determinations
            
        Returns:
            A weather condition string
        """
        # Determine season based on month and latitude
        # Northern and Southern hemispheres have opposite seasons
        month = date.month
        
        if latitude >= 0:  # Northern hemisphere
            if 3 <= month <= 5:
                season = "spring"
            elif 6 <= month <= 8:
                season = "summer"
            elif 9 <= month <= 11:
                season = "fall"
            else:
                season = "winter"
        else:  # Southern hemisphere
            if 3 <= month <= 5:
                season = "fall"
            elif 6 <= month <= 8:
                season = "winter"
            elif 9 <= month <= 11:
                season = "spring"
            else:
                season = "summer"
        
        # Get probability distribution for this season
        probabilities = WeatherCondition.SEASONAL_PROBABILITY[season]
        
        # Choose a condition based on probabilities
        conditions = list(probabilities.keys())
        weights = list(probabilities.values())
        
        return random.choices(conditions, weights=weights, k=1)[0]
    
    @staticmethod
    def get_condition_attributes(condition: str) -> Dict[str, Any]:
        """
        Get reasonable attributes for a given weather condition.
        
        Args:
            condition: The weather condition string
            
        Returns:
            Dictionary of weather attributes
        """
        # Get ranges for this condition
        temp_range = WeatherCondition.TEMP_RANGES.get(condition, (-10, 30))
        precip_range = WeatherCondition.PRECIP_RANGES.get(condition, (0, 0))
        humidity_range = WeatherCondition.HUMIDITY_RANGES.get(condition, (30, 70))
        wind_range = WeatherCondition.WIND_RANGES.get(condition, (0, 20))
        
        # Generate random values within ranges
        temperature = round(random.uniform(temp_range[0], temp_range[1]), 1)
        precipitation = round(random.uniform(precip_range[0], precip_range[1]), 1)
        humidity = round(random.uniform(humidity_range[0], humidity_range[1]), 1)
        wind_speed = round(random.uniform(wind_range[0], wind_range[1]), 1)
        
        return {
            "temperature": temperature,
            "precipitation": precipitation,
            "humidity": humidity,
            "wind_speed": wind_speed
        }


class WeatherData:
    """Class representing weather data for a specific location and time."""
    
    def __init__(
        self,
        timestamp: datetime,
        location: Dict[str, Any],
        condition: str,
        temperature: float,
        humidity: float,
        precipitation: float,
        wind_speed: float
    ):
        """
        Initialize weather data.
        
        Args:
            timestamp: Date and time of the weather observation
            location: Dictionary with latitude, longitude, and location info
            condition: Weather condition (clear, partly_cloudy, etc.)
            temperature: Temperature in Celsius
            humidity: Humidity percentage (0-100)
            precipitation: Precipitation amount in mm
            wind_speed: Wind speed in km/h
        """
        self.timestamp = timestamp
        self.location = location
        self.condition = condition
        self.temperature = temperature
        self.humidity = humidity
        self.precipitation = precipitation
        self.wind_speed = wind_speed
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert weather data to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "condition": self.condition,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "precipitation": self.precipitation,
            "wind_speed": self.wind_speed
        }


class IndoorClimateData:
    """Class representing indoor climate data from smart thermostats."""
    
    def __init__(
        self,
        timestamp: datetime,
        location: Dict[str, Any],
        temperature: float,
        humidity: float,
        hvac_mode: str,
        hvac_state: str,
        target_temperature: float,
        device_id: str,
        device_name: str,
        occupancy_detected: Optional[bool] = None,
        air_quality: Optional[int] = None
    ):
        """
        Initialize indoor climate data.
        
        Args:
            timestamp: Date and time of the climate observation
            location: Dictionary with room location info
            temperature: Indoor temperature in Celsius
            humidity: Indoor humidity percentage (0-100)
            hvac_mode: HVAC mode (heat, cool, auto, off)
            hvac_state: HVAC state (heating, cooling, fan, idle)
            target_temperature: Target temperature in Celsius
            device_id: ID of the thermostat device
            device_name: Name of the thermostat device
            occupancy_detected: Whether the room is occupied (optional)
            air_quality: Air quality index (optional)
        """
        self.timestamp = timestamp
        self.location = location
        self.temperature = temperature
        self.humidity = humidity
        self.hvac_mode = hvac_mode
        self.hvac_state = hvac_state
        self.target_temperature = target_temperature
        self.device_id = device_id
        self.device_name = device_name
        self.occupancy_detected = occupancy_detected
        self.air_quality = air_quality
        
        # Generate a fan mode based on HVAC state
        if hvac_state in ["heating", "cooling"]:
            self.fan_mode = "auto"
        elif hvac_state == "fan":
            self.fan_mode = "on"
        else:
            self.fan_mode = random.choice(["auto", "on", "scheduled"])
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert indoor climate data to dictionary."""
        result = {
            "timestamp": self.timestamp.isoformat(),
            "location": self.location,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "hvac_mode": self.hvac_mode,
            "hvac_state": self.hvac_state,
            "fan_mode": self.fan_mode,
            "target_temperature": self.target_temperature,
            "device_id": self.device_id,
            "device_name": self.device_name
        }
        
        if self.occupancy_detected is not None:
            result["occupancy_detected"] = self.occupancy_detected
            
        if self.air_quality is not None:
            result["air_quality"] = self.air_quality
            
        return result


class EnvironmentalMetadataGenerator:
    """
    Generator for environmental metadata including weather and indoor climate data.
    """
    
    def __init__(self):
        """Initialize the environmental metadata generator."""
        self.faker = faker.Faker()
        
        # Source identifier for weather data
        self.weather_source_data = {
            "Identifier": uuid.UUID("51e7c8d2-4a3f-45b9-8d1e-9c2a5b3f7e6d"),
            "Version": "1.0.0",
            "Description": "Weather Data Generator"
        }
        
        # Source identifier for indoor climate data
        self.climate_source_data = {
            "Identifier": uuid.UUID("6ea66ced-5a54-4cba-a421-50d5671021cb"),
            "Version": "1.0.0",
            "Description": "Smart Thermostat Data Generator"
        }
        
        # Indoor locations with their thermostat devices
        self.indoor_locations = [
            {"room": "Living Room", "device_id": "ecobee123abc", "device_name": "Living Room"},
            {"room": "Bedroom", "device_id": "ecobee456def", "device_name": "Bedroom"},
            {"room": "Office", "device_id": "ecobee789ghi", "device_name": "Office"},
            {"room": "Kitchen", "device_id": "ecobee012jkl", "device_name": "Kitchen"}
        ]
        
        # HVAC modes and states
        self.hvac_modes = ["heat", "cool", "auto", "off"]
        self.hvac_states = ["heating", "cooling", "fan", "idle"]
        
        # Create mappings for semantic attributes for weather data
        self.weather_semantic_attributes = {
            WEATHER_CONDITION_UUID: "condition",
            TEMPERATURE_OUTDOOR_UUID: "temperature",
            HUMIDITY_OUTDOOR_UUID: "humidity",
            WIND_SPEED_UUID: "wind_speed",
            PRECIPITATION_UUID: "precipitation"
        }
        
        # Create mappings for semantic attributes for indoor climate data
        self.climate_semantic_attributes = {
            TEMPERATURE_INDOOR_UUID: "temperature",
            HUMIDITY_INDOOR_UUID: "humidity",
            AIR_QUALITY_UUID: "air_quality"
        }
    
    def _generate_weather_forecast(
        self, 
        start_date: datetime,
        end_date: datetime,
        locations: List[Dict[str, Any]]
    ) -> Dict[Tuple[str, datetime.date], WeatherData]:
        """
        Generate a continuous weather forecast for the given timeframe and locations.
        
        Args:
            start_date: Start date for the forecast
            end_date: End date for the forecast
            locations: List of location dictionaries with lat/lon/label
            
        Returns:
            Dictionary of weather data keyed by (location_label, date)
        """
        weather_forecast = {}
        
        # For each location
        for location in locations:
            location_label = location.get("label", "Unknown")
            latitude = location.get("latitude", 0)
            longitude = location.get("longitude", 0)
            
            # Create a continuous forecast
            current_date = start_date
            previous_condition = None
            previous_attributes = None
            
            while current_date < end_date:
                # For new days or initial condition, generate a new base condition
                if previous_condition is None or current_date.date() != (current_date - timedelta(hours=1)).date():
                    condition = WeatherCondition.get_seasonal_condition(current_date, latitude)
                    attributes = WeatherCondition.get_condition_attributes(condition)
                    previous_condition = condition
                    previous_attributes = attributes
                else:
                    # 80% chance to maintain similar weather as previous hour
                    if random.random() < 0.8:
                        condition = previous_condition
                        
                        # Slightly vary the attributes for continuity
                        attributes = {
                            "temperature": previous_attributes["temperature"] + random.uniform(-1.0, 1.0),
                            "precipitation": max(0, previous_attributes["precipitation"] + random.uniform(-1.0, 1.0)),
                            "humidity": max(0, min(100, previous_attributes["humidity"] + random.uniform(-3.0, 3.0))),
                            "wind_speed": max(0, previous_attributes["wind_speed"] + random.uniform(-2.0, 2.0))
                        }
                    else:
                        # Weather change - choose a new condition
                        # Bias toward similar conditions with weather patterns
                        if previous_condition in [WeatherCondition.CLEAR, WeatherCondition.PARTLY_CLOUDY]:
                            possible_conditions = [
                                WeatherCondition.CLEAR, WeatherCondition.PARTLY_CLOUDY, 
                                WeatherCondition.CLOUDY, WeatherCondition.WINDY
                            ]
                        elif previous_condition in [WeatherCondition.CLOUDY, WeatherCondition.FOG]:
                            possible_conditions = [
                                WeatherCondition.CLOUDY, WeatherCondition.PARTLY_CLOUDY, 
                                WeatherCondition.FOG, WeatherCondition.RAIN
                            ]
                        elif previous_condition in [WeatherCondition.RAIN, WeatherCondition.THUNDERSTORM]:
                            possible_conditions = [
                                WeatherCondition.RAIN, WeatherCondition.THUNDERSTORM, 
                                WeatherCondition.CLOUDY, WeatherCondition.PARTLY_CLOUDY
                            ]
                        elif previous_condition in [WeatherCondition.SNOW, WeatherCondition.SLEET, WeatherCondition.FREEZING_RAIN]:
                            possible_conditions = [
                                WeatherCondition.SNOW, WeatherCondition.SLEET,
                                WeatherCondition.FREEZING_RAIN, WeatherCondition.CLOUDY
                            ]
                        else:
                            possible_conditions = WeatherCondition.ALL_CONDITIONS
                            
                        condition = random.choice(possible_conditions)
                        attributes = WeatherCondition.get_condition_attributes(condition)
                
                # Create weather data for this hour
                weather_data = WeatherData(
                    timestamp=current_date,
                    location=location,
                    condition=condition,
                    temperature=round(attributes["temperature"], 1),
                    humidity=round(attributes["humidity"], 1),
                    precipitation=round(attributes["precipitation"], 1),
                    wind_speed=round(attributes["wind_speed"], 1)
                )
                
                # Store in forecast keyed by location label and date hour
                key = (location_label, current_date)
                weather_forecast[key] = weather_data
                
                # Update for next iteration
                previous_condition = condition
                previous_attributes = attributes
                current_date += timedelta(hours=1)
        
        return weather_forecast
    
    def _generate_indoor_climate_data(
        self,
        start_date: datetime,
        end_date: datetime,
        weather_forecast: Dict[Tuple[str, datetime.date], WeatherData]
    ) -> Dict[Tuple[str, datetime.date], IndoorClimateData]:
        """
        Generate indoor climate data that correlates with outdoor weather.
        
        Args:
            start_date: Start date for the data
            end_date: End date for the data
            weather_forecast: Dictionary of weather data
            
        Returns:
            Dictionary of indoor climate data keyed by (room, date)
        """
        indoor_climate_data = {}
        
        # For each indoor location
        for location in self.indoor_locations:
            room = location["room"]
            device_id = location["device_id"]
            device_name = location["device_name"]
            
            # Create user's temperature preferences (21-24°C typically)
            preferred_temp_winter = random.uniform(20.0, 22.0)
            preferred_temp_summer = random.uniform(22.0, 25.0)
            
            # Track HVAC state over time
            current_hvac_mode = "auto"
            current_hvac_state = "idle"
            
            # Create a schedule for each hour
            current_date = start_date
            while current_date < end_date:
                # Find the closest weather data (use "Home" location as reference)
                weather_key = None
                for key in weather_forecast:
                    location_label, date = key
                    if location_label == "Home" and date == current_date:
                        weather_key = key
                        break
                
                if weather_key:
                    outdoor_weather = weather_forecast[weather_key]
                    outdoor_temp = outdoor_weather.temperature
                    
                    # Determine target temperature based on outdoor conditions
                    # and time of day
                    hour = current_date.hour
                    
                    # Nighttime setback (midnight to 6am)
                    if 0 <= hour < 6:
                        # Lower temperature at night
                        target_adjustment = -2.0
                    # Morning warm-up (6am to 9am)
                    elif 6 <= hour < 9:
                        target_adjustment = 1.0
                    # Daytime (9am to 6pm)
                    elif 9 <= hour < 18:
                        target_adjustment = 0.0
                    # Evening (6pm to midnight)
                    else:
                        target_adjustment = 0.5
                        
                    # Adjust for season (determine from outdoor temperature)
                    if outdoor_temp < 10:  # Cold outside
                        base_temp = preferred_temp_winter
                        current_hvac_mode = "heat" if outdoor_temp < 18 else "auto"
                    else:  # Warm outside
                        base_temp = preferred_temp_summer
                        current_hvac_mode = "cool" if outdoor_temp > 25 else "auto"
                        
                    target_temperature = round(base_temp + target_adjustment, 1)
                    
                    # Indoor temperature responds to outdoor, but is regulated by HVAC
                    # Start with a baseline based on outdoor temperature
                    indoor_temp_baseline = 21.0  # Default comfortable baseline
                    
                    # Adjust baseline based on outdoor temperature (outdoor influences indoor)
                    if outdoor_temp < -10:  # Very cold
                        indoor_temp_baseline = 18.0
                    elif outdoor_temp < 0:  # Cold
                        indoor_temp_baseline = 19.0
                    elif outdoor_temp < 10:  # Cool
                        indoor_temp_baseline = 20.0
                    elif outdoor_temp < 20:  # Mild
                        indoor_temp_baseline = 21.0
                    elif outdoor_temp < 30:  # Warm
                        indoor_temp_baseline = 23.0
                    else:  # Hot
                        indoor_temp_baseline = 25.0
                        
                    # Now adjust indoor temp based on HVAC activity
                    temp_diff = target_temperature - indoor_temp_baseline
                    
                    # Determine HVAC state based on temperature difference
                    if temp_diff > 1.5:  # Need heating
                        current_hvac_state = "heating"
                        # Heating pulls temperature toward target
                        indoor_temperature = indoor_temp_baseline + min(temp_diff, 1.0)
                    elif temp_diff < -1.5:  # Need cooling
                        current_hvac_state = "cooling"
                        # Cooling pulls temperature toward target
                        indoor_temperature = indoor_temp_baseline + max(temp_diff, -1.0)
                    else:  # Within comfort range
                        # 80% chance of staying idle if we're close enough
                        if abs(temp_diff) < 0.8 and random.random() < 0.8:
                            current_hvac_state = "idle"
                        elif current_hvac_state == "idle" and random.random() < 0.1:
                            current_hvac_state = "fan"  # Occasionally run fan
                            
                        # Temperature drifts slightly when HVAC is idle
                        drift = random.uniform(-0.3, 0.3)
                        indoor_temperature = indoor_temp_baseline + drift
                        
                    # Indoor humidity correlates with outdoor but is moderated
                    if outdoor_weather.humidity > 80:
                        indoor_humidity = random.uniform(55, 65)
                    elif outdoor_weather.humidity < 30:
                        indoor_humidity = random.uniform(30, 40)
                    else:
                        indoor_humidity = outdoor_weather.humidity * 0.7  # Moderate outdoor humidity
                
                    # Calculate air quality (higher is better, 0-100)
                    # Base on outdoor conditions
                    if outdoor_weather.condition in [WeatherCondition.CLEAR, WeatherCondition.PARTLY_CLOUDY]:
                        air_quality_base = random.randint(80, 95)
                    elif outdoor_weather.condition in [WeatherCondition.CLOUDY, WeatherCondition.WINDY]:
                        air_quality_base = random.randint(70, 85)
                    elif outdoor_weather.condition == WeatherCondition.FOG:
                        air_quality_base = random.randint(60, 75)
                    elif outdoor_weather.condition in [WeatherCondition.RAIN, WeatherCondition.SNOW]:
                        air_quality_base = random.randint(65, 80)
                    else:  # Poor air quality in storms/etc
                        air_quality_base = random.randint(50, 70)
                        
                    # Randomized occupancy based on room and time
                    if room == "Bedroom":
                        if 22 <= hour or hour < 7:  # Night
                            occupancy = random.random() < 0.9  # 90% occupied at night
                        elif 7 <= hour < 8:  # Morning routine
                            occupancy = random.random() < 0.7
                        else:
                            occupancy = random.random() < 0.2
                    elif room == "Living Room":
                        if 18 <= hour < 23:  # Evening
                            occupancy = random.random() < 0.8
                        elif 8 <= hour < 18:  # Daytime
                            occupancy = random.random() < 0.4
                        else:
                            occupancy = random.random() < 0.1
                    elif room == "Office":
                        if 9 <= hour < 17:  # Work hours
                            occupancy = random.random() < 0.8
                        else:
                            occupancy = random.random() < 0.1
                    elif room == "Kitchen":
                        if hour in [7, 8, 12, 13, 18, 19]:  # Meal times
                            occupancy = random.random() < 0.8
                        else:
                            occupancy = random.random() < 0.2
                    else:
                        occupancy = random.random() < 0.3
                        
                    # Create climate data
                    climate_data = IndoorClimateData(
                        timestamp=current_date,
                        location={"room": room},
                        temperature=round(indoor_temperature, 1),
                        humidity=round(indoor_humidity, 1),
                        hvac_mode=current_hvac_mode,
                        hvac_state=current_hvac_state,
                        target_temperature=target_temperature,
                        device_id=device_id,
                        device_name=device_name,
                        occupancy_detected=occupancy,
                        air_quality=air_quality_base
                    )
                    
                    # Store climate data
                    key = (room, current_date)
                    indoor_climate_data[key] = climate_data
                
                # Advance time by 1 hour
                current_date += timedelta(hours=1)
            
        return indoor_climate_data
    
    def create_weather_data_model(self, weather_data: WeatherData) -> IndalekoActivityDataModel:
        """
        Create a structured activity data model for weather data.
        
        Args:
            weather_data: WeatherData object with observation details
            
        Returns:
            IndalekoActivityDataModel ready for database insertion
        """
        # Create base record
        timestamp = weather_data.timestamp
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
            
        record = IndalekoRecordDataModel(
            SourceIdentifier=IndalekoSourceIdentifierDataModel(
                Identifier=self.weather_source_data["Identifier"],
                Version=self.weather_source_data["Version"],
                Description=self.weather_source_data["Description"]
            ),
            Timestamp=timestamp,
            Data="",  # Will be filled by encoder
            Attributes={}
        )
        
        # Create semantic attributes
        semantic_attributes = []
        for attr_id, field_name in self.weather_semantic_attributes.items():
            if hasattr(weather_data, field_name):
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=attr_id,
                            Version="1",
                            Description=field_name
                        ),
                        Data=getattr(weather_data, field_name)
                    )
                )
        
        # Create the activity data model
        activity_data = IndalekoActivityDataModel(
            Record=record,
            Timestamp=timestamp,
            SemanticAttributes=semantic_attributes
        )
        
        # Encode the weather data into the record
        activity_data.Record.Data = json.dumps(weather_data.to_dict())
        
        return activity_data
    
    def create_climate_data_model(self, climate_data: IndoorClimateData) -> IndalekoActivityDataModel:
        """
        Create a structured activity data model for indoor climate data.
        
        Args:
            climate_data: IndoorClimateData object with observation details
            
        Returns:
            IndalekoActivityDataModel ready for database insertion
        """
        # Create base record
        timestamp = climate_data.timestamp
        if not timestamp.tzinfo:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
            
        record = IndalekoRecordDataModel(
            SourceIdentifier=IndalekoSourceIdentifierDataModel(
                Identifier=self.climate_source_data["Identifier"],
                Version=self.climate_source_data["Version"],
                Description=self.climate_source_data["Description"]
            ),
            Timestamp=timestamp,
            Data="",  # Will be filled by encoder
            Attributes={}
        )
        
        # Create semantic attributes
        semantic_attributes = []
        for attr_id, field_name in self.climate_semantic_attributes.items():
            if hasattr(climate_data, field_name) and getattr(climate_data, field_name) is not None:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=attr_id,
                            Version="1",
                            Description=field_name
                        ),
                        Data=getattr(climate_data, field_name)
                    )
                )
        
        # Create the activity data model
        activity_data = IndalekoActivityDataModel(
            Record=record,
            Timestamp=timestamp,
            SemanticAttributes=semantic_attributes
        )
        
        # Encode the climate data into the record
        activity_data.Record.Data = json.dumps(climate_data.to_dict())
        
        return activity_data
    
    def prepare_for_database(self, activity_data: IndalekoActivityDataModel) -> Dict[str, Any]:
        """
        Convert an activity data model to a dictionary ready for database insertion.
        
        Args:
            activity_data: The activity data model to convert
            
        Returns:
            Dictionary formatted for ArangoDB insertion
        """
        # Convert to dictionary for database insertion
        return json.loads(activity_data.model_dump_json(exclude_none=True, exclude_unset=True))
    
    def generate_weather_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        locations: Optional[List[Dict[str, Any]]] = None,
        count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate weather data for a time period and locations.
        
        Args:
            start_date: Start date for the weather data (defaults to 7 days ago)
            end_date: End date for the weather data (defaults to now)
            locations: List of location dictionaries with lat/lon/label (defaults to "Home")
            count: If provided, generate exactly this many weather records
            
        Returns:
            List of formatted weather data records ready for database insertion
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now(timezone.utc)
        if locations is None:
            locations = [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "label": "Home"
                }
            ]
            
        # Generate weather forecast
        weather_forecast = self._generate_weather_forecast(start_date, end_date, locations)
        
        # Convert to activity data models
        db_records = []
        for key, weather_data in weather_forecast.items():
            activity_data = self.create_weather_data_model(weather_data)
            db_record = self.prepare_for_database(activity_data)
            db_records.append(db_record)
            
        # If count specified, sample that many records
        if count is not None and count < len(db_records):
            db_records = random.sample(db_records, count)
            
        return db_records
    
    def generate_indoor_climate_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        weather_data: Optional[List[Dict[str, Any]]] = None,
        count: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate indoor climate data that correlates with weather data.
        
        Args:
            start_date: Start date for the data (defaults to 7 days ago)
            end_date: End date for the data (defaults to now)
            weather_data: Optional weather data to correlate with
            count: If provided, generate exactly this many climate records
            
        Returns:
            List of formatted climate data records ready for database insertion
        """
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(days=7)
        if end_date is None:
            end_date = datetime.now(timezone.utc)
            
        # If weather data provided, convert to WeatherData objects
        weather_forecast = {}
        if weather_data:
            for record in weather_data:
                # Extract data from JSON string in Record.Data
                if "Record" in record and "Data" in record["Record"]:
                    data_str = record["Record"]["Data"]
                    if data_str:
                        try:
                            data_dict = json.loads(data_str)
                            timestamp = datetime.fromisoformat(data_dict["timestamp"])
                            location_label = data_dict["location"]["label"]
                            
                            weather = WeatherData(
                                timestamp=timestamp,
                                location=data_dict["location"],
                                condition=data_dict["condition"],
                                temperature=data_dict["temperature"],
                                humidity=data_dict["humidity"],
                                precipitation=data_dict["precipitation"],
                                wind_speed=data_dict["wind_speed"]
                            )
                            
                            key = (location_label, timestamp)
                            weather_forecast[key] = weather
                        except (json.JSONDecodeError, KeyError):
                            continue
        
        # If no weather data provided or conversion failed, generate simple forecast
        if not weather_forecast:
            locations = [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "label": "Home"
                }
            ]
            weather_forecast = self._generate_weather_forecast(start_date, end_date, locations)
        
        # Generate indoor climate data
        indoor_climate_data = self._generate_indoor_climate_data(
            start_date=start_date,
            end_date=end_date,
            weather_forecast=weather_forecast
        )
        
        # Convert to activity data models
        db_records = []
        for key, climate_data in indoor_climate_data.items():
            activity_data = self.create_climate_data_model(climate_data)
            db_record = self.prepare_for_database(activity_data)
            db_records.append(db_record)
            
        # If count specified, sample that many records
        if count is not None and count < len(db_records):
            db_records = random.sample(db_records, count)
            
        return db_records
    
    def insert_weather_data_into_database(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert generated weather data into the ArangoDB database.
        
        Args:
            records: List of formatted weather activity records
            
        Returns:
            Number of records successfully inserted
        """
        try:
            # Get database connection
            db_config = IndalekoDBConfig()
            db = db_config.db
            
            # Get or create the temperature activity collection
            collection_name = IndalekoDBCollections.Indaleko_TempActivityData_Collection
            collection = db.collection(collection_name)
            
            # Insert records in batches
            batch_size = 100
            successful_inserts = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                result = collection.insert_many(batch)
                successful_inserts += len(result)
                
            return successful_inserts
            
        except Exception as e:
            print(f"Error inserting weather data: {str(e)}")
            return 0
    
    def insert_climate_data_into_database(self, records: List[Dict[str, Any]]) -> int:
        """
        Insert generated indoor climate data into the ArangoDB database.
        
        Args:
            records: List of formatted climate activity records
            
        Returns:
            Number of records successfully inserted
        """
        try:
            # Get database connection
            db_config = IndalekoDBConfig()
            db = db_config.db
            
            # Get or create the temperature activity collection
            collection_name = IndalekoDBCollections.Indaleko_TempActivityData_Collection
            collection = db.collection(collection_name)
            
            # Insert records in batches
            batch_size = 100
            successful_inserts = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i+batch_size]
                result = collection.insert_many(batch)
                successful_inserts += len(result)
                
            return successful_inserts
            
        except Exception as e:
            print(f"Error inserting climate data: {str(e)}")
            return 0


class EnvironmentalMetadataGeneratorTool:
    """Tool for generating synthetic environmental metadata."""
    
    def __init__(self):
        """Initialize the environmental metadata generator tool."""
        self.generator = EnvironmentalMetadataGenerator()
    
    def generate_environmental_data(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        locations: Optional[List[Dict[str, Any]]] = None,
        count_weather: Optional[int] = None,
        count_climate: Optional[int] = None,
        insert_to_db: bool = False
    ) -> Dict[str, Any]:
        """
        Generate synthetic environmental data with weather and indoor climate information.
        
        Args:
            start_date: Start date for the data (defaults to 7 days ago)
            end_date: End date for the data (defaults to now)
            locations: List of location dictionaries with lat/lon/label (defaults to "Home")
            count_weather: If provided, generate exactly this many weather records
            count_climate: If provided, generate exactly this many climate records
            insert_to_db: Whether to insert the generated data into the database
            
        Returns:
            Dictionary containing generated data and summary statistics
        """
        # Generate weather data
        weather_records = self.generator.generate_weather_data(
            start_date=start_date,
            end_date=end_date,
            locations=locations,
            count=count_weather
        )
        
        # Generate climate data separately to avoid parsing issues
        # Just generate specific number of climate records if requested
        if count_climate and count_climate > 0:
            # Generate indoor climate data using default weather patterns
            # This is more reliable than trying to parse the weather records
            climate_records = []
            
            # Calculate time interval to space records appropriately
            if start_date and end_date:
                time_range = (end_date - start_date).total_seconds()
                interval = time_range / count_climate
                
                for i in range(count_climate):
                    # Create a timestamp for this record
                    timestamp = start_date + timedelta(seconds=i * interval)
                    
                    # Create a simple indoor climate record
                    room = random.choice(self.generator.indoor_locations)
                    climate_data = IndoorClimateData(
                        timestamp=timestamp,
                        location={"room": room["room"]},
                        temperature=random.uniform(19.0, 24.0),  # Comfortable indoor temp
                        humidity=random.uniform(35.0, 60.0),     # Standard indoor humidity
                        hvac_mode=random.choice(self.generator.hvac_modes),
                        hvac_state=random.choice(self.generator.hvac_states),
                        target_temperature=random.uniform(20.0, 23.0),
                        device_id=room["device_id"],
                        device_name=room["device_name"],
                        occupancy_detected=random.choice([True, False]),
                        air_quality=random.randint(70, 95)
                    )
                    
                    # Create the activity data model and convert to database format
                    activity_data = self.generator.create_climate_data_model(climate_data)
                    db_record = self.generator.prepare_for_database(activity_data)
                    
                    climate_records.append(db_record)
            else:
                # If no dates provided, just generate empty climate records
                climate_records = []
        else:
            # No climate records requested
            climate_records = []
        
        # Insert into database if requested
        weather_db_inserts = 0
        climate_db_inserts = 0
        if insert_to_db:
            if weather_records:
                weather_db_inserts = self.generator.insert_weather_data_into_database(weather_records)
            if climate_records:
                climate_db_inserts = self.generator.insert_climate_data_into_database(climate_records)
        
        # Compute summary statistics
        weather_conditions = {}
        indoor_hvac_modes = {}
        location_counts = {}
        hourly_distribution = {hour: 0 for hour in range(24)}
        indoor_rooms = {}
        
        # Process weather records
        for record in weather_records:
            # Extract timestamp for hourly distribution
            if "Timestamp" in record:
                timestamp = datetime.fromisoformat(record["Timestamp"])
                hour = timestamp.hour
                hourly_distribution[hour] += 1
            
            # Extract condition from Data field
            if "Record" in record and "Data" in record["Record"]:
                data_str = record["Record"]["Data"]
                if data_str:
                    try:
                        data_dict = json.loads(data_str)
                        condition = data_dict.get("condition")
                        if condition:
                            weather_conditions[condition] = weather_conditions.get(condition, 0) + 1
                        
                        location = data_dict.get("location", {}).get("label")
                        if location:
                            location_counts[location] = location_counts.get(location, 0) + 1
                    except json.JSONDecodeError:
                        pass
                        
        # Process climate records
        for record in climate_records:
            # Extract timestamp for hourly distribution
            if "Timestamp" in record:
                timestamp = datetime.fromisoformat(record["Timestamp"])
                hour = timestamp.hour
                hourly_distribution[hour] += 1
                
            # Extract HVAC mode and room from Data field
            if "Record" in record and "Data" in record["Record"]:
                data_str = record["Record"]["Data"]
                if data_str:
                    try:
                        data_dict = json.loads(data_str)
                        hvac_mode = data_dict.get("hvac_mode")
                        if hvac_mode:
                            indoor_hvac_modes[hvac_mode] = indoor_hvac_modes.get(hvac_mode, 0) + 1
                            
                        room = data_dict.get("location", {}).get("room")
                        if room:
                            indoor_rooms[room] = indoor_rooms.get(room, 0) + 1
                    except json.JSONDecodeError:
                        pass
        
        # Prepare top conditions and rooms
        top_conditions = sorted(weather_conditions.items(), key=lambda x: x[1], reverse=True)[:5]
        top_rooms = sorted(indoor_rooms.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "total_weather_records": len(weather_records),
            "total_climate_records": len(climate_records),
            "weather_db_inserts": weather_db_inserts,
            "climate_db_inserts": climate_db_inserts,
            "date_range": {
                "start": str(start_date),
                "end": str(end_date)
            },
            "top_weather_conditions": top_conditions,
            "location_distribution": location_counts,
            "indoor_room_distribution": indoor_rooms,
            "indoor_hvac_modes": indoor_hvac_modes,
            "hourly_distribution": hourly_distribution,
            "sample_weather_record": weather_records[0] if weather_records else None,
            "sample_climate_record": climate_records[0] if climate_records else None
        }


def main():
    """Test the EnvironmentalMetadataGenerator directly."""
    generator_tool = EnvironmentalMetadataGeneratorTool()
    
    # Generate a small batch of environmental data
    start_date = datetime.now(timezone.utc) - timedelta(days=3)
    end_date = datetime.now(timezone.utc)
    
    result = generator_tool.generate_environmental_data(
        start_date=start_date,
        end_date=end_date,
        count_weather=24,  # One per hour for a day
        count_climate=24,  # One per hour for a day
        insert_to_db=False
    )
    
    print(f"Generated {result['total_weather_records']} weather records and {result['total_climate_records']} climate records")
    print(f"Top weather conditions: {result['top_weather_conditions']}")
    print(f"Indoor room distribution: {result['indoor_room_distribution']}")
    print(f"Indoor HVAC modes: {result['indoor_hvac_modes']}")
    
    if result['sample_weather_record']:
        print("\nSample weather record:")
        record = result['sample_weather_record']
        print(f"Timestamp: {record.get('Timestamp')}")
        if "Record" in record and "Data" in record["Record"]:
            data_str = record["Record"]["Data"]
            if data_str:
                data = json.loads(data_str)
                print(f"Condition: {data.get('condition')}")
                print(f"Temperature: {data.get('temperature')}°C")
                print(f"Humidity: {data.get('humidity')}%")
                print(f"Wind Speed: {data.get('wind_speed')} km/h")


if __name__ == "__main__":
    main()