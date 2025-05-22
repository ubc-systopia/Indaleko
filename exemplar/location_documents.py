"""This handles creating the location data needed for the exemplar query set."""

import os
import sys
import time

from pathlib import Path

from geopy.geocoders import Nominatim
from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from db.db_config import IndalekoDBConfig


# pylint: enable=wrong-import-position


def get_location_name_coordinates(location_name: str) -> tuple[float, float]:
    """Get the coordinates for a given location name."""
    # This is a placeholder function. In a real implementation, you would
    # use a geocoding service to get the coordinates for the location name.
    geolocator = Nominatim(user_agent="exemplar_location_lookup")
    location = geolocator.geocode(location_name)
    if location:
        # Returns (latitude, longitude, altitude if available)
        return location.latitude, location.longitude, getattr(location, "altitude", None)
    return None, None, None

def lookup_location_in_db(location_name: str) -> dict[str, object] | None:
    db_config = IndalekoDBConfig()


def main():
    """Main function for testing functionality."""
    ic(get_location_name_coordinates("New York, NY"))
    time.sleep(1)
    ic(get_location_name_coordinates("Los Angeles, CA"))
    time.sleep(1)
    ic(get_location_name_coordinates("Cusco, Peru"))
    time.sleep(1)
    ic(get_location_name_coordinates("Nairobi, Kenya"))
    time.sleep(1)
    ic(get_location_name_coordinates("Vancouver, Canada"))

if __name__ == "__main__":
    main()
