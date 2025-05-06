"""
Enhanced location metadata generator for Indaleko.

This module provides comprehensive location metadata generation capabilities,
including realistic locations, place categorization, and contextual attributes.
"""

import os
import sys
import random
import datetime
import uuid
from typing import Dict, List, Any, Tuple, Optional
import math

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import tool interface
from tools.data_generator_enhanced.agents.data_gen.core.tools import Tool

# Create mock SemanticAttributeRegistry for testing purposes
class SemanticAttributeRegistry:
    """Mock registry for semantic attributes."""
    
    # Common domains for attributes
    DOMAIN_STORAGE = "storage"
    DOMAIN_ACTIVITY = "activity"
    DOMAIN_SEMANTIC = "semantic"
    DOMAIN_RELATIONSHIP = "relationship"
    DOMAIN_MACHINE = "machine"
    
    @classmethod
    def get_attribute_id(cls, domain: str, name: str) -> str:
        """Get an attribute ID for a registered attribute."""
        return f"{domain}_{name}_id"
    
    @classmethod
    def get_attribute_name(cls, attribute_id: str) -> str:
        """Get the human-readable name for an attribute ID."""
        return attribute_id.replace("_id", "")

# Create mock data models for testing purposes
class IndalekoBaseModel:
    """Mock base model for testing."""
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

class IndalekoSemanticAttributeDataModel(IndalekoBaseModel):
    """Mock semantic attribute data model for testing."""
    pass

class IndalekoUUIDDataModel(IndalekoBaseModel):
    """Mock UUID data model for testing."""
    pass

class IndalekoLocationDataModel(IndalekoBaseModel):
    """Mock location data model for testing."""
    pass


class LocationProfile:
    """Class representing a realistic user location profile.
    
    This defines common locations, movement patterns, and typical schedules.
    """
    
    def __init__(self, user_id: str, seed: Optional[int] = None):
        """Initialize location profile.
        
        Args:
            user_id: User identifier
            seed: Random seed for consistent generation
        """
        self.user_id = user_id
        self.random = random.Random(seed if seed is not None else user_id)
        
        # Generate home and work locations
        self.home_location = self._generate_location()
        self.work_location = self._generate_location(
            min_distance=5.0,  # At least 5km from home
            max_distance=30.0  # At most 30km from home
        )
        
        # Generate frequently visited places
        self.frequent_places = {
            "coffee_shop": self._generate_location(max_distance=2.0, base=self.work_location),
            "gym": self._generate_location(max_distance=5.0, base=self.home_location),
            "grocery_store": self._generate_location(max_distance=3.0, base=self.home_location),
            "restaurant": self._generate_location(max_distance=10.0),
            "park": self._generate_location(max_distance=7.0),
            "shopping_mall": self._generate_location(max_distance=15.0)
        }
        
        # Define daily schedule (24-hour format)
        self.weekday_schedule = {
            # Time range: (location, activity)
            (0, 7): ("home", "sleeping"),
            (7, 9): ("home", "morning_routine"),
            (9, 12): ("work", "working"),
            (12, 13): ("coffee_shop", "lunch"),
            (13, 17): ("work", "working"),
            (17, 18): ("commuting", "traveling"),
            (18, 19): ("grocery_store", "shopping"),
            (19, 22): ("home", "evening_activities"),
            (22, 24): ("home", "sleeping")
        }
        
        self.weekend_schedule = {
            (0, 8): ("home", "sleeping"),
            (8, 10): ("home", "morning_routine"),
            (10, 12): ("grocery_store", "shopping"),
            (12, 14): ("restaurant", "dining"),
            (14, 17): ("park", "recreation"),
            (17, 19): ("shopping_mall", "shopping"),
            (19, 24): ("home", "relaxing")
        }
        
        # Travel history (trips away from home area)
        self.travel_history = []
        
        # Generate some random trips
        num_trips = self.random.randint(1, 5)
        now = datetime.datetime.now()
        for _ in range(num_trips):
            # Random trip in the past year
            days_ago = self.random.randint(7, 365)
            trip_start = now - datetime.timedelta(days=days_ago)
            trip_duration = self.random.randint(1, 10)  # 1-10 days
            trip_end = trip_start + datetime.timedelta(days=trip_duration)
            
            # Generate destination far from home
            destination = self._generate_location(min_distance=100.0, max_distance=5000.0)
            destination_name = self._get_random_city()
            
            self.travel_history.append({
                "start_date": trip_start,
                "end_date": trip_end,
                "destination": destination,
                "destination_name": destination_name,
                "purpose": self.random.choice(["business", "vacation", "family", "conference"])
            })
            
    def _generate_location(self, 
                          min_distance: float = 0.0, 
                          max_distance: float = 0.0, 
                          base: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Generate a random geo location.
        
        Args:
            min_distance: Minimum distance from base in km
            max_distance: Maximum distance from base in km
            base: Base location to generate from
            
        Returns:
            Dict with latitude and longitude
        """
        # Default to San Francisco if no base provided
        if base is None:
            base = {"latitude": 37.7749, "longitude": -122.4194}
            
        if max_distance <= 0:
            # Just return the base with small random variation
            return {
                "latitude": base["latitude"] + self.random.uniform(-0.01, 0.01),
                "longitude": base["longitude"] + self.random.uniform(-0.01, 0.01)
            }
            
        # Generate random distance within range
        distance = self.random.uniform(min_distance, max_distance)
        
        # Convert to degrees (approximate)
        lat_km = 111.0  # 1 degree latitude = ~111 km
        lon_km = 111.0 * math.cos(math.radians(base["latitude"]))  # Longitude degrees vary by latitude
        
        # Generate random direction
        angle = self.random.uniform(0, 2 * math.pi)
        
        # Calculate new position
        lat_offset = distance * math.cos(angle) / lat_km
        lon_offset = distance * math.sin(angle) / lon_km
        
        return {
            "latitude": base["latitude"] + lat_offset,
            "longitude": base["longitude"] + lon_offset
        }
    
    def get_location_for_time(self, 
                             timestamp: datetime.datetime) -> Tuple[Dict[str, float], str, str]:
        """Get the most likely location for a given time.
        
        Args:
            timestamp: Datetime to get location for
            
        Returns:
            Tuple of (coordinates, location_name, activity)
        """
        # Check if on a trip
        for trip in self.travel_history:
            if trip["start_date"] <= timestamp <= trip["end_date"]:
                return (
                    trip["destination"],
                    trip["destination_name"],
                    trip["purpose"]
                )
        
        # Regular schedule based on weekday/weekend
        is_weekend = timestamp.weekday() >= 5  # Saturday or Sunday
        schedule = self.weekend_schedule if is_weekend else self.weekday_schedule
        
        # Get current hour
        hour = timestamp.hour
        
        # Find matching schedule entry
        for (start_hour, end_hour), (location_type, activity) in schedule.items():
            if start_hour <= hour < end_hour:
                if location_type == "commuting":
                    # Generate an in-between location
                    progress = (hour - start_hour) / (end_hour - start_hour)
                    lat = self.home_location["latitude"] + progress * (self.work_location["latitude"] - self.home_location["latitude"])
                    lon = self.home_location["longitude"] + progress * (self.work_location["longitude"] - self.home_location["longitude"])
                    return (
                        {"latitude": lat, "longitude": lon},
                        "commuting",
                        activity
                    )
                elif location_type == "home":
                    return (self.home_location, "home", activity)
                elif location_type == "work":
                    return (self.work_location, "work", activity)
                else:
                    # Get location from frequent places
                    return (
                        self.frequent_places.get(location_type, self.home_location),
                        location_type,
                        activity
                    )
        
        # Default to home if no match
        return (self.home_location, "home", "other")
    
    def _get_random_city(self) -> str:
        """Get a random city name."""
        cities = [
            "New York", "London", "Tokyo", "Paris", "Hong Kong", 
            "Singapore", "Los Angeles", "Chicago", "Toronto", "Sydney",
            "Berlin", "Madrid", "Rome", "Amsterdam", "Barcelona",
            "San Francisco", "Seattle", "Boston", "Austin", "Denver"
        ]
        return self.random.choice(cities)


class LocationGeneratorTool(Tool):
    """Tool to generate realistic location metadata."""
    
    def __init__(self):
        """Initialize the location generator tool."""
        super().__init__(name="location_generator", description="Generates realistic location metadata")
        
        # Initialize data models
        self.SemanticAttributeDataModel = IndalekoSemanticAttributeDataModel
        self.LocationDataModel = IndalekoLocationDataModel
        self.UUIDModel = IndalekoUUIDDataModel
        
        # Cache of user location profiles
        self.user_profiles = {}
        
        # Location types and their detection accuracies
        self.location_types = {
            "gps": {"accuracy": (3, 10), "altitude": True, "speed": True},
            "wifi": {"accuracy": (15, 50), "altitude": False, "speed": False},
            "cell": {"accuracy": (100, 1000), "altitude": False, "speed": True},
            "ip": {"accuracy": (1000, 10000), "altitude": False, "speed": False},
            "bluetooth": {"accuracy": (1, 5), "altitude": False, "speed": False}
        }
        
        # POI (points of interest) categories
        self.poi_categories = [
            "restaurant", "coffee_shop", "shopping", "grocery", "gym",
            "park", "library", "school", "university", "hospital",
            "airport", "train_station", "bus_stop", "hotel", "museum",
            "theater", "cinema", "gas_station", "parking", "bank"
        ]
        
        # Weather conditions
        self.weather_conditions = [
            "sunny", "partly_cloudy", "cloudy", "rainy", "stormy",
            "foggy", "snowy", "windy", "hot", "cold"
        ]
    
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the location generator tool.
        
        Args:
            params: Parameters for execution
                count: Number of location records to generate
                criteria: Criteria for generation
                    user_id: User identifier
                    start_time: Start time for location records
                    end_time: End time for location records
                    location_types: List of location types to include
                    include_weather: Whether to include weather data
                    include_poi: Whether to include POI data
                    
        Returns:
            Dictionary with generated records
        """
        count = params.get("count", 1)
        criteria = params.get("criteria", {})
        
        user_id = criteria.get("user_id", str(uuid.uuid4()))
        start_time = criteria.get("start_time", datetime.datetime.now() - datetime.timedelta(days=7))
        end_time = criteria.get("end_time", datetime.datetime.now())
        location_types = criteria.get("location_types", list(self.location_types.keys()))
        include_weather = criteria.get("include_weather", True)
        include_poi = criteria.get("include_poi", True)
        
        # Generate location records
        records = []
        for _ in range(count):
            record = self._create_location_record_model(
                user_id=user_id,
                timestamp=self._random_time(start_time, end_time),
                location_type=random.choice(location_types),
                include_weather=include_weather,
                include_poi=include_poi
            )
            records.append(record)
        
        return {
            "records": records
        }
    
    def _create_location_record_model(self,
                                    user_id: str,
                                    timestamp: datetime.datetime,
                                    location_type: str,
                                    include_weather: bool = True,
                                    include_poi: bool = True) -> Dict[str, Any]:
        """Create a location record model.
        
        Args:
            user_id: User identifier
            timestamp: Timestamp for the location record
            location_type: Type of location detection
            include_weather: Whether to include weather data
            include_poi: Whether to include POI data
            
        Returns:
            Location record model
        """
        # Get user profile (create if necessary)
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = LocationProfile(user_id)
        profile = self.user_profiles[user_id]
        
        # Get location for this time
        coordinates, place_type, activity = profile.get_location_for_time(timestamp)
        
        # Add some randomness to the coordinates based on location type accuracy
        accuracy_range = self.location_types[location_type]["accuracy"]
        accuracy_meters = random.uniform(accuracy_range[0], accuracy_range[1])
        
        # Convert accuracy to rough lat/lon offsets
        lat_offset = random.uniform(-accuracy_meters/111000, accuracy_meters/111000)
        lon_offset = random.uniform(-accuracy_meters/111000, accuracy_meters/111000)
        
        # Apply the offsets
        detected_lat = coordinates["latitude"] + lat_offset
        detected_lon = coordinates["longitude"] + lon_offset
        
        # Create record ID
        record_id = str(uuid.uuid4())
        
        # Basic record structure
        record = {
            "Id": record_id,
            "UserId": user_id,
            "Timestamp": timestamp.isoformat(),
            "LocationType": location_type,
            "Latitude": detected_lat,
            "Longitude": detected_lon,
            "Accuracy": accuracy_meters,
            "PlaceType": place_type,
            "Activity": activity
        }
        
        # Add optional altitude if supported by location type
        if self.location_types[location_type]["altitude"]:
            record["Altitude"] = random.uniform(0, 500)  # Meters above sea level
            record["AltitudeAccuracy"] = random.uniform(1, 50)  # Meters
        
        # Add optional speed if supported by location type
        if self.location_types[location_type]["speed"]:
            if activity == "commuting":
                record["Speed"] = random.uniform(30, 120)  # km/h
            elif activity == "traveling":
                record["Speed"] = random.uniform(50, 900)  # km/h (could be flying)
            else:
                record["Speed"] = random.uniform(0, 5)  # km/h (walking)
            
            record["SpeedAccuracy"] = random.uniform(1, 5)  # km/h
        
        # Add weather data if requested
        if include_weather:
            record["Weather"] = self._generate_weather_data(timestamp, coordinates)
        
        # Add POI data if requested
        if include_poi:
            record["POI"] = self._generate_poi_data(coordinates, place_type)
        
        # Generate semantic attributes
        semantic_attributes = self._generate_semantic_attributes(
            record_id=record_id,
            user_id=user_id,
            location_type=location_type,
            coordinates=coordinates,
            detected_coordinates={"latitude": detected_lat, "longitude": detected_lon},
            accuracy=accuracy_meters,
            place_type=place_type,
            activity=activity,
            timestamp=timestamp,
            weather=record.get("Weather"),
            poi=record.get("POI")
        )
        
        # Add semantic attributes to record
        record["SemanticAttributes"] = semantic_attributes
        
        return record
    
    def _generate_semantic_attributes(self,
                                    record_id: str,
                                    user_id: str,
                                    location_type: str,
                                    coordinates: Dict[str, float],
                                    detected_coordinates: Dict[str, float],
                                    accuracy: float,
                                    place_type: str,
                                    activity: str,
                                    timestamp: datetime.datetime,
                                    weather: Optional[Dict[str, Any]] = None,
                                    poi: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate semantic attributes for a location record.
        
        Args:
            record_id: Record identifier
            user_id: User identifier
            location_type: Type of location detection
            coordinates: Actual coordinates
            detected_coordinates: Detected coordinates (with accuracy error)
            accuracy: Accuracy in meters
            place_type: Type of place (home, work, etc.)
            activity: Activity at the location
            timestamp: Timestamp for the location record
            weather: Weather data (optional)
            poi: POI data (optional)
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # Add location type attribute
        location_type_attr = self.SemanticAttributeDataModel(
            Identifier=SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_TYPE"),
            Value=location_type
        )
        semantic_attributes.append(location_type_attr)
        
        # Add latitude and longitude attributes
        lat_attr = self.SemanticAttributeDataModel(
            Identifier=SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_LATITUDE"),
            Value=detected_coordinates["latitude"]
        )
        semantic_attributes.append(lat_attr)
        
        lon_attr = self.SemanticAttributeDataModel(
            Identifier=SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_LONGITUDE"),
            Value=detected_coordinates["longitude"]
        )
        semantic_attributes.append(lon_attr)
        
        # Add accuracy attribute
        accuracy_attr = self.SemanticAttributeDataModel(
            Identifier=SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_ACCURACY"),
            Value=accuracy
        )
        semantic_attributes.append(accuracy_attr)
        
        # Add place type attribute
        place_type_attr = self.SemanticAttributeDataModel(
            Identifier=SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_PLACE_TYPE"),
            Value=place_type
        )
        semantic_attributes.append(place_type_attr)
        
        # Add activity attribute
        activity_attr = self.SemanticAttributeDataModel(
            Identifier=SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_ACTIVITY"),
            Value=activity
        )
        semantic_attributes.append(activity_attr)
        
        # Add weather attributes if available
        if weather:
            weather_condition_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_WEATHER_CONDITION"),
                Value=weather["condition"]
            )
            semantic_attributes.append(weather_condition_attr)
            
            weather_temp_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_WEATHER_TEMPERATURE"),
                Value=weather["temperature"]
            )
            semantic_attributes.append(weather_temp_attr)
        
        # Add POI attributes if available
        if poi:
            poi_name_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_POI_NAME"),
                Value=poi["name"]
            )
            semantic_attributes.append(poi_name_attr)
            
            poi_category_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "LOCATION_POI_CATEGORY"),
                Value=poi["category"]
            )
            semantic_attributes.append(poi_category_attr)
        
        return semantic_attributes
    
    def _generate_weather_data(self, 
                             timestamp: datetime.datetime, 
                             coordinates: Dict[str, float]) -> Dict[str, Any]:
        """Generate weather data for a location.
        
        Args:
            timestamp: Timestamp for the weather data
            coordinates: Location coordinates
            
        Returns:
            Weather data dictionary
        """
        # Determine season (very rough approximation)
        month = timestamp.month
        if 3 <= month <= 5:  # Spring
            season = "spring"
            temp_base = 15  # Celsius
        elif 6 <= month <= 8:  # Summer
            season = "summer"
            temp_base = 25
        elif 9 <= month <= 11:  # Fall
            season = "fall"
            temp_base = 15
        else:  # Winter
            season = "winter"
            temp_base = 5
        
        # Adjust temperature based on latitude (colder away from equator)
        lat_factor = abs(coordinates["latitude"]) / 90.0  # 0 at equator, 1 at poles
        temp_base -= lat_factor * 20  # Up to 20 degrees colder at poles
        
        # Add daily variation
        hour = timestamp.hour
        if 6 <= hour <= 18:  # Daytime is warmer
            temp_base += 5 * math.sin(math.pi * (hour - 6) / 12)
        else:  # Nighttime is cooler
            temp_base -= 5
        
        # Add some randomness
        temperature = temp_base + random.uniform(-5, 5)
        
        # Determine weather condition (biased by season)
        season_conditions = {
            "spring": ["sunny", "partly_cloudy", "rainy", "cloudy"],
            "summer": ["sunny", "hot", "partly_cloudy", "stormy"],
            "fall": ["cloudy", "rainy", "partly_cloudy", "foggy"],
            "winter": ["cloudy", "snowy", "cold", "partly_cloudy"]
        }
        
        condition = random.choice(season_conditions[season])
        
        return {
            "temperature": round(temperature, 1),
            "condition": condition,
            "humidity": random.randint(30, 90),
            "wind_speed": random.uniform(0, 30),
            "season": season
        }
    
    def _generate_poi_data(self, 
                          coordinates: Dict[str, float], 
                          place_type: str) -> Dict[str, Any]:
        """Generate POI data for a location.
        
        Args:
            coordinates: Location coordinates
            place_type: Type of place (home, work, etc.)
            
        Returns:
            POI data dictionary
        """
        # Map place type to likely POI category
        place_to_poi = {
            "home": "residential",
            "work": "office",
            "coffee_shop": "coffee_shop",
            "restaurant": "restaurant",
            "grocery_store": "grocery",
            "gym": "gym",
            "park": "park",
            "shopping_mall": "shopping"
        }
        
        # Get category based on place type or random
        category = place_to_poi.get(place_type, random.choice(self.poi_categories))
        
        # Generate a plausible POI name based on category
        name = self._generate_poi_name(category)
        
        return {
            "name": name,
            "category": category,
            "distance": random.uniform(0, 50),  # Distance in meters
            "address": self._generate_address(coordinates)
        }
    
    def _generate_poi_name(self, category: str) -> str:
        """Generate a plausible POI name based on category.
        
        Args:
            category: POI category
            
        Returns:
            POI name
        """
        category_names = {
            "restaurant": ["Joe's Diner", "The Italian Place", "Sushi Spot", "Taco Temple", "Burger Palace"],
            "coffee_shop": ["JavaCup", "Bean Scene", "Espresso Express", "Coffee Culture", "Morning Brew"],
            "shopping": ["Fashion Central", "The Mall", "Boutique Boulevard", "Retail Row", "Shopping Haven"],
            "grocery": ["SuperMart", "Fresh Foods", "Organic Market", "Value Grocery", "Family Foods"],
            "gym": ["Fitness First", "Power Gym", "Iron Works", "Flex Fitness", "Wellness Center"],
            "park": ["Green Park", "City Gardens", "Memorial Park", "Riverside Park", "Nature Reserve"],
            "library": ["Central Library", "Community Books", "Knowledge Center", "Reading Room", "Public Library"],
            "office": ["Business Center", "Corporate Plaza", "Tech Campus", "Office Park", "Professional Building"],
            "residential": ["Home", "Residence", "Apartment", "House", "Condo"]
        }
        
        names = category_names.get(category, ["Unknown Place"])
        return random.choice(names)
    
    def _generate_address(self, coordinates: Dict[str, float]) -> str:
        """Generate a plausible address for coordinates.
        
        Args:
            coordinates: Location coordinates
            
        Returns:
            Address string
        """
        # Very simplified address generation
        streets = ["Main St", "Oak Ave", "Park Rd", "Maple Dr", "Washington Blvd", 
                  "Cedar Ln", "Lake St", "River Rd", "Highland Ave", "College St"]
        
        cities = ["Springfield", "Rivertown", "Lakeside", "Hillview", "Newport", 
                 "Fairview", "Oakdale", "Cedar Rapids", "Maplewood", "Franklin"]
        
        state_codes = ["CA", "NY", "TX", "FL", "IL", "PA", "OH", "GA", "NC", "MI"]
        
        return f"{random.randint(100, 9999)} {random.choice(streets)}, {random.choice(cities)}, {random.choice(state_codes)}"
    
    def _random_time(self, start_time: datetime.datetime, end_time: datetime.datetime) -> datetime.datetime:
        """Generate a random time between start and end.
        
        Args:
            start_time: Start time
            end_time: End time
            
        Returns:
            Random datetime
        """
        delta = end_time - start_time
        delta_seconds = delta.total_seconds()
        random_seconds = random.uniform(0, delta_seconds)
        return start_time + datetime.timedelta(seconds=random_seconds)


# Add register method to the SemanticAttributeRegistry class
@classmethod
def register_attribute(cls, domain: str, name: str, attribute_id: Optional[str] = None) -> str:
    """Mock method to register an attribute."""
    return cls.get_attribute_id(domain, name)

# Add the method to the class
setattr(SemanticAttributeRegistry, 'register_attribute', register_attribute)


if __name__ == "__main__":
    # Simple test
    location_generator = LocationGeneratorTool()
    result = location_generator.execute({
        "count": 5,
        "criteria": {
            "user_id": "test_user",
            "start_time": datetime.datetime.now() - datetime.timedelta(days=7),
            "end_time": datetime.datetime.now(),
            "location_types": ["gps", "wifi"],
            "include_weather": True,
            "include_poi": True
        }
    })
    
    import json
    
    # Custom JSON encoder for datetime and other complex types
    class CustomEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime.datetime):
                return obj.isoformat()
            return super().default(obj)
    
    # Print the first record
    print(json.dumps(result["records"][0], indent=2, cls=CustomEncoder))