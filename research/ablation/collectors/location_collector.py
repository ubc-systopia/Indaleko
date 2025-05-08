"""Location activity collector for ablation testing."""

import random
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from ..base import ISyntheticCollector
from ..models.location_activity import LocationActivity, LocationCoordinates
from ..ner.entity_manager import NamedEntityManager
from ..utils.uuid_utils import generate_deterministic_uuid


class LocationActivityCollector(ISyntheticCollector):
    """Synthetic collector for location activity."""

    def __init__(self, entity_manager: NamedEntityManager | None = None, seed_value: int | None = None):
        """Initialize the location activity collector.

        Args:
            entity_manager: Optional entity manager for consistent entity identifiers.
                           If not provided, a new one will be created.
            seed_value: Optional seed for random number generation to ensure reproducibility.
        """
        self.entity_manager = entity_manager or NamedEntityManager()
        if seed_value is not None:
            self.seed(seed_value)

        # Sample location data
        self.locations = [
            "Home",
            "Work",
            "Coffee Shop",
            "Library",
            "Gym",
            "Restaurant",
            "Park",
            "Shopping Mall",
            "Airport",
            "Train Station",
        ]

        # Map each location to a realistic latitude/longitude
        self.coordinates_by_location = {
            "Home": (37.7749, -122.4194, 10),  # San Francisco with 10m accuracy
            "Work": (37.7833, -122.4167, 5),  # San Francisco downtown with 5m accuracy
            "Coffee Shop": (37.7691, -122.4227, 15),  # Mission District with 15m accuracy
            "Library": (37.7785, -122.4156, 8),  # San Francisco Public Library with 8m accuracy
            "Gym": (37.7830, -122.4100, 12),  # SOMA district with 12m accuracy
            "Restaurant": (37.7770, -122.4240, 20),  # Hayes Valley with 20m accuracy
            "Park": (37.7694, -122.4862, 30),  # Golden Gate Park with 30m accuracy
            "Shopping Mall": (37.7841, -122.4076, 15),  # Westfield SF with 15m accuracy
            "Airport": (37.6213, -122.3790, 25),  # SFO with 25m accuracy
            "Train Station": (37.7793, -122.3933, 10),  # Caltrain with 10m accuracy
        }

        # Map each location to a specific type
        self.location_types = {
            "Home": "residential",
            "Work": "commercial",
            "Coffee Shop": "commercial",
            "Library": "educational",
            "Gym": "recreational",
            "Restaurant": "commercial",
            "Park": "recreational",
            "Shopping Mall": "commercial",
            "Airport": "transportation",
            "Train Station": "transportation",
        }

        # List of potential WiFi networks
        self.wifi_networks = {
            "Home": ["Home_WiFi", "HomeNetwork_5G", "Family_Net"],
            "Work": ["CompanyWiFi", "Office_Net", "Guest_WiFi", "Corp_Secure"],
            "Coffee Shop": ["CoffeeShop_Free", "CafeWiFi", "BaristaNet"],
            "Library": ["Library_Public", "LibraryGuest", "BookLovers_WiFi"],
            "Gym": ["Gym_FreeWiFi", "FitnessCenter", "WorkoutNet"],
            "Restaurant": ["Restaurant_Guest", "DiningWiFi", "FoodLovers"],
            "Park": ["Park_PublicWiFi", "CityParks", "OutdoorNet"],
            "Shopping Mall": ["Mall_FreeWiFi", "Shopping_Net", "RetailWiFi"],
            "Airport": ["Airport_Free", "FlightWiFi", "AirportSecure"],
            "Train Station": ["Station_Public", "TrainWiFi", "CommuterNet"],
        }

        # List of potential devices
        self.devices = ["iPhone", "Android", "Laptop", "Tablet", "Smartwatch"]

        # Location sources
        self.sources = ["gps", "wifi", "cell", "ip", "bluetooth"]

    def seed(self, seed_value: int) -> None:
        """Set the random seed for deterministic data generation.

        Args:
            seed_value: The seed value to use.
        """
        random.seed(seed_value)

    def collect(self) -> dict:
        """Generate synthetic location activity data.

        Returns:
            Dict: The generated location activity data.
        """
        # Select a random location
        location_name = random.choice(self.locations)

        # Get coordinates for the location
        lat, lon, accuracy = self.coordinates_by_location[location_name]

        # Add some randomness to the coordinates to make them more realistic
        lat += random.uniform(-0.001, 0.001)
        lon += random.uniform(-0.001, 0.001)
        accuracy += random.uniform(-2, 2)

        coordinates = LocationCoordinates(
            latitude=lat, longitude=lon, accuracy_meters=max(1.0, accuracy),  # Ensure accuracy is at least 1 meter
        )

        # Get the location type
        location_type = self.location_types[location_name]

        # Select a random device
        device_name = random.choice(self.devices)

        # Select a WiFi network appropriate for the location
        wifi_ssid = random.choice(self.wifi_networks[location_name]) if random.random() > 0.2 else None

        # Select a random source with appropriate probabilities
        source_weights = {"gps": 0.4, "wifi": 0.3, "cell": 0.2, "ip": 0.05, "bluetooth": 0.05}
        source = random.choices(population=list(source_weights.keys()), weights=list(source_weights.values()), k=1)[0]

        # Create a location activity
        activity = LocationActivity(
            location_name=location_name,
            coordinates=coordinates,
            location_type=location_type,
            device_name=device_name,
            wifi_ssid=wifi_ssid,
            source=source,
            # Add a created_at timestamp within the last 24 hours
            created_at=datetime.now(UTC) - timedelta(hours=random.randint(0, 24)),
        )

        # Register entities with the entity manager
        self.entity_manager.register_entity("location", location_name)
        self.entity_manager.register_entity("device", device_name)

        # Return the activity as a dictionary
        return activity.dict()

    def generate_batch(self, count: int) -> list[dict[str, Any]]:
        """Generate a batch of synthetic location activity data.

        Args:
            count: Number of activity records to generate.

        Returns:
            List[Dict]: List of generated location activity data.
        """
        return [self.collect() for _ in range(count)]

    def generate_truth_data(self, query: str) -> set[UUID]:
        """Generate truth data for a location-related query.

        This method identifies which location activities should match the query.

        Args:
            query: The natural language query to generate truth data for.

        Returns:
            Set[UUID]: The set of UUIDs that should match the query.
        """
        # Generate matching data with the exact same IDs to ensure consistency
        matching_data = self.generate_matching_data(query, count=10)
        matching_entities = set()
        
        # Extract IDs from the generated matching data
        for data in matching_data:
            if "id" in data:
                if isinstance(data["id"], UUID):
                    matching_entities.add(data["id"])
                else:
                    matching_entities.add(UUID(data["id"]) if isinstance(data["id"], str) else data["id"])
        
        # If there's no query terms that match anything, create at least 5 matching entities
        # This ensures we have data to measure recall against
        if not matching_entities:
            for i in range(5):
                matching_entities.add(generate_deterministic_uuid(f"location_activity:generic:{query}:{i}"))
        
        return matching_entities

    def generate_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate location activity data that should match a specific query.

        Args:
            query: The natural language query to generate matching data for.
            count: Number of matching records to generate.

        Returns:
            List[Dict]: List of generated location activity data that should match the query.
        """
        matching_data = []
        query_lower = query.lower()

        # Extract key terms from the query
        locations_in_query = [loc for loc in self.locations if loc.lower() in query_lower]
        types_in_query = [loc_type for loc_type in set(self.location_types.values()) if loc_type.lower() in query_lower]
        devices_in_query = [device for device in self.devices if device.lower() in query_lower]
        sources_in_query = [source for source in self.sources if source.lower() in query_lower]

        for i in range(count):
            # Start with a base activity that we'll modify to match the query
            base_activity = self.collect()
            activity_dict = base_activity.copy()

            # Make the activity match the query based on extracted terms
            if locations_in_query:
                location_name = random.choice(locations_in_query)
                activity_dict["location_name"] = location_name

                # Update coordinates to match the location
                lat, lon, accuracy = self.coordinates_by_location[location_name]
                # Add small random variation
                lat += random.uniform(-0.0005, 0.0005)
                lon += random.uniform(-0.0005, 0.0005)
                activity_dict["coordinates"] = {"latitude": lat, "longitude": lon, "accuracy_meters": accuracy}

                # Update location type to match
                activity_dict["location_type"] = self.location_types[location_name]

                # Assign an appropriate WiFi network
                if random.random() > 0.3:  # 70% chance to have WiFi
                    activity_dict["wifi_ssid"] = random.choice(self.wifi_networks[location_name])

                # Generate a deterministic UUID for this location activity
                activity_dict["id"] = generate_deterministic_uuid(f"location_activity:{location_name}:{i}")

            # If query mentions location types, ensure we match
            elif types_in_query:
                loc_type = random.choice(types_in_query)
                matching_locations = [loc for loc, type_ in self.location_types.items() if type_ == loc_type]
                if matching_locations:
                    location_name = random.choice(matching_locations)
                    activity_dict["location_name"] = location_name
                    activity_dict["location_type"] = loc_type

                    # Update coordinates
                    lat, lon, accuracy = self.coordinates_by_location[location_name]
                    activity_dict["coordinates"] = {
                        "latitude": lat + random.uniform(-0.0005, 0.0005),
                        "longitude": lon + random.uniform(-0.0005, 0.0005),
                        "accuracy_meters": accuracy,
                    }
                    
                    # Generate a deterministic UUID for this location type activity
                    activity_dict["id"] = generate_deterministic_uuid(f"location_activity:{loc_type}:{i}")

            # If query mentions devices, ensure we match
            if devices_in_query:
                device_name = random.choice(devices_in_query)
                activity_dict["device_name"] = device_name
                
                # Update ID to include device if no location was matched
                if "id" not in activity_dict:
                    activity_dict["id"] = generate_deterministic_uuid(f"location_activity:{device_name}:{i}")

            # If query mentions sources, ensure we match
            if sources_in_query:
                source = random.choice(sources_in_query)
                activity_dict["source"] = source
                
                # Update ID to include source if no other entity was matched
                if "id" not in activity_dict:
                    activity_dict["id"] = generate_deterministic_uuid(f"location_activity:{source}:{i}")
                    
            # Ensure every activity has an ID
            if "id" not in activity_dict:
                # Fallback UUID if no specific entity was matched
                activity_dict["id"] = generate_deterministic_uuid(f"location_activity:generic:{i}")

            matching_data.append(activity_dict)

        return matching_data

    def generate_non_matching_data(self, query: str, count: int = 1) -> list[dict[str, Any]]:
        """Generate location activity data that should NOT match a specific query.

        Args:
            query: The natural language query to generate non-matching data for.
            count: Number of non-matching records to generate.

        Returns:
            List[Dict]: List of generated location activity data that should NOT match the query.
        """
        non_matching_data = []
        query_lower = query.lower()

        # Extract key terms from the query
        locations_in_query = [loc for loc in self.locations if loc.lower() in query_lower]
        types_in_query = [loc_type for loc_type in set(self.location_types.values()) if loc_type.lower() in query_lower]
        devices_in_query = [device for device in self.devices if device.lower() in query_lower]
        sources_in_query = [source for source in self.sources if source.lower() in query_lower]

        for _ in range(count):
            # Generate a base activity
            base_activity = self.collect()
            activity_dict = base_activity.copy()

            # Ensure location doesn't match query
            if locations_in_query:
                excluded_locations = [loc for loc in self.locations if loc not in locations_in_query]
                if excluded_locations:
                    location_name = random.choice(excluded_locations)
                    activity_dict["location_name"] = location_name

                    # Update coordinates
                    lat, lon, accuracy = self.coordinates_by_location[location_name]
                    activity_dict["coordinates"] = {
                        "latitude": lat + random.uniform(-0.0005, 0.0005),
                        "longitude": lon + random.uniform(-0.0005, 0.0005),
                        "accuracy_meters": accuracy,
                    }

                    activity_dict["location_type"] = self.location_types[location_name]

            # Ensure location type doesn't match query
            if types_in_query:
                excluded_types = [t for t in set(self.location_types.values()) if t not in types_in_query]
                if excluded_types:
                    loc_type = random.choice(excluded_types)
                    matching_locations = [loc for loc, type_ in self.location_types.items() if type_ == loc_type]
                    if matching_locations:
                        location_name = random.choice(matching_locations)
                        activity_dict["location_name"] = location_name
                        activity_dict["location_type"] = loc_type

                        # Update coordinates
                        lat, lon, accuracy = self.coordinates_by_location[location_name]
                        activity_dict["coordinates"] = {
                            "latitude": lat + random.uniform(-0.0005, 0.0005),
                            "longitude": lon + random.uniform(-0.0005, 0.0005),
                            "accuracy_meters": accuracy,
                        }

            # Ensure device doesn't match query
            if devices_in_query:
                excluded_devices = [d for d in self.devices if d not in devices_in_query]
                if excluded_devices:
                    activity_dict["device_name"] = random.choice(excluded_devices)

            # Ensure source doesn't match query
            if sources_in_query:
                excluded_sources = [s for s in self.sources if s not in sources_in_query]
                if excluded_sources:
                    activity_dict["source"] = random.choice(excluded_sources)

            # Set created_at to a time outside the typical query window (much older)
            activity_dict["created_at"] = (datetime.now(UTC) - timedelta(days=random.randint(30, 180))).isoformat()

            non_matching_data.append(activity_dict)

        return non_matching_data
