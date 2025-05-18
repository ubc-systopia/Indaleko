"""Location activity data models for ablation testing."""

from pydantic import BaseModel

from ..utils.semantic_attributes import SemanticAttributeRegistry
from .activity import ActivityData, ActivityType


class LocationCoordinates(BaseModel):
    """Model for geographic coordinates."""

    latitude: float
    longitude: float
    accuracy_meters: float | None = None

    def __str__(self) -> str:
        """String representation of coordinates."""
        return f"{self.latitude},{self.longitude}"


class LocationActivity(ActivityData):
    """Model for location activity."""

    location_name: str
    coordinates: LocationCoordinates | None = None
    location_type: str  # e.g., "home", "work", "coffee shop", etc.
    device_name: str | None = None
    wifi_ssid: str | None = None
    source: str  # e.g., "wifi", "gps", "ip", etc.

    def __init__(self, **data):
        """Initialize a location activity with proper activity type and semantic attributes."""
        # Set the activity type to LOCATION
        data["activity_type"] = ActivityType.LOCATION

        # Set the source if not provided
        if "source" not in data:
            data["source"] = "ablation_synthetic_generator"

        # Initialize semantic attributes if not provided
        if "semantic_attributes" not in data:
            data["semantic_attributes"] = {}

        # Call the parent constructor
        super().__init__(**data)

        # Add semantic attributes
        self.add_semantic_attributes()

    def add_semantic_attributes(self):
        """Add location-specific semantic attributes."""
        attrs = SemanticAttributeRegistry()

        # Add location name
        self.semantic_attributes[SemanticAttributeRegistry.LOCATION_NAME] = attrs.create_attribute(
            SemanticAttributeRegistry.LOCATION_NAME,
            self.location_name,
        )

        # Add coordinates if available
        if self.coordinates:
            self.semantic_attributes[SemanticAttributeRegistry.LOCATION_COORDINATES] = attrs.create_attribute(
                SemanticAttributeRegistry.LOCATION_COORDINATES,
                str(self.coordinates),
            )

        # Add location type
        self.semantic_attributes[SemanticAttributeRegistry.LOCATION_TYPE] = attrs.create_attribute(
            SemanticAttributeRegistry.LOCATION_TYPE,
            self.location_type,
        )

        # Add device name if available
        if self.device_name:
            self.semantic_attributes[SemanticAttributeRegistry.LOCATION_DEVICE] = attrs.create_attribute(
                SemanticAttributeRegistry.LOCATION_DEVICE,
                self.device_name,
            )

        # Add WiFi SSID if available
        if self.wifi_ssid:
            self.semantic_attributes[SemanticAttributeRegistry.LOCATION_WIFI_SSID] = attrs.create_attribute(
                SemanticAttributeRegistry.LOCATION_WIFI_SSID,
                self.wifi_ssid,
            )

        # Add source
        self.semantic_attributes[SemanticAttributeRegistry.LOCATION_SOURCE] = attrs.create_attribute(
            SemanticAttributeRegistry.LOCATION_SOURCE,
            self.source,
        )
