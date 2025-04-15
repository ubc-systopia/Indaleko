from typing import Dict, Any
import random
import uuid
from datetime import datetime
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from activity.data_model.activity import IndalekoActivityDataModel
from activity.collectors.location.data_models.windows_gps_location_data_model import (
    WindowsGPSLocationDataModel,
)
from activity.collectors.location.data_models.windows_gps_satellite_data import (
    WindowsGPSLocationSatelliteDataModel,
)
from data_generator.scripts.metadata.activity_metadata import ActivityMetadata


class GeoActivityData(ActivityMetadata):
    DEFAULT_MIN_ALT = -10
    DEFAULT_MAX_ALT = 1000
    DEFAULT_MIN_LAT = -90
    DEFAULT_MAX_LAT = 90
    DEFAULT_MIN_LONG = -180
    DEFAULT_MAX_LONG = 180

    def __init__(self, selected_AC_md):
        super().__init__(selected_AC_md)
        self.saved_geo_loc = None

    def generate_metadata(
        self,
        record_kwargs: IndalekoRecordDataModel,
        timestamps: Dict[str, datetime],
        is_truth_file: bool,
        truth_like: bool,
        truthlike_attributes: list[str],
    ) -> Any:
        is_truth_file = self._define_truth_attribute(
            "geo_location", is_truth_file, truth_like, truthlike_attributes
        )
        return self._generate_geo_metadata(record_kwargs, timestamps, is_truth_file)

    def _generate_geo_metadata(
        self,
        record_kwargs: IndalekoRecordDataModel,
        timestamps: Dict[str, datetime],
        is_truth_file: bool,
    ) -> IndalekoActivityDataModel:
        """
        Creates the geographical semantic data
        """
        geo_timestamp = self._generate_ac_timestamp(
            is_truth_file, timestamps, "geo_location"
        )
        activity_geo_loc = self._generate_geo_context(is_truth_file)
        activity_geo_md = self._generate_WindowsGPSLocation(
            activity_geo_loc, geo_timestamp
        )

        UUID_longitude = uuid.uuid4()
        UUID_latitude = uuid.uuid4()
        UUID_accuracy = uuid.uuid4()

        longitude = IndalekoUUIDDataModel(Identifier=UUID_longitude, Label="Longitude")
        latitude = IndalekoUUIDDataModel(Identifier=UUID_latitude, Label="Latitude")
        accuracy = IndalekoUUIDDataModel(Identifier=UUID_accuracy, Label="Accuracy")

        semantic_attributes = [
            IndalekoSemanticAttributeDataModel(
                Identifier=longitude, Value=activity_geo_md.longitude
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=latitude, Value=activity_geo_md.latitude
            ),
            IndalekoSemanticAttributeDataModel(
                Identifier=accuracy, Value=activity_geo_md.accuracy
            ),
        ]

        # timestamp is set to when the activity data is collected
        geo_activity_context = IndalekoActivityDataModel(
            Record=record_kwargs,
            Timestamp=geo_timestamp,
            SemanticAttributes=semantic_attributes,
        )

        # longitude_data_provider = ActivityDataModel(Provider = uuid.uuid4(), ProviderReference=UUID_longitude)
        # latitude_data_provider = ActivityDataModel(Provider = uuid.uuid4(), ProviderReference=UUID_latitude)
        # accuracy_data_provider = ActivityDataModel(Provider = uuid.uuid4(), ProviderReference=UUID_accuracy)
        # geo_activity_service = IndalekoActivityContextDataModel(Handle=uuid.uuid4(), Timestamp=geo_timestamp, Cursors=[longitude_data_provider, latitude_data_provider,accuracy_data_provider])
        return geo_activity_context

    def _generate_geo_context(self, is_truth_file: bool = True) -> Dict[str, Any]:
        """
        Generates a geographical activity context based on the location given:
        self.selected_md["geo_location"] = {'location': str, 'command': str}
        """
        location_dict = {}
        delta = 5

        if "geo_location" in self.selected_md:
            geo_location = self.selected_md["geo_location"]["location"]
            geo_command = self.selected_md["geo_location"]["command"]
            # run only once to initialize the saved location
            if not self.saved_geo_loc:
                self.saved_geo_loc = self._save_location(geo_location, geo_command)
            if geo_command == "at":
                if is_truth_file:
                    # geo location generator that given a city, generates longitude and latitude
                    latitude = self.saved_geo_loc["latitude"]
                    longitude = self.saved_geo_loc["longitude"]
                    altitude = self.saved_geo_loc["altitude"]

                else:
                    truth_latitude = self.saved_geo_loc["latitude"]
                    truth_longitude = self.saved_geo_loc["longitude"]
                    truth_altitude = self.saved_geo_loc["altitude"]

                    max_lat = min(
                        GeoActivityData.DEFAULT_MAX_LAT, truth_latitude + delta
                    )
                    min_lat = max(
                        GeoActivityData.DEFAULT_MIN_LAT, truth_latitude - delta
                    )
                    max_long = min(
                        GeoActivityData.DEFAULT_MAX_LONG, truth_longitude + delta
                    )
                    min_long = max(
                        GeoActivityData.DEFAULT_MIN_LONG, truth_longitude - delta
                    )
                    min_alt = max(
                        GeoActivityData.DEFAULT_MIN_ALT, truth_altitude - delta
                    )
                    max_alt = min(
                        GeoActivityData.DEFAULT_MAX_ALT, truth_altitude + delta
                    )

                    latitude = self._check_return_value_within_range(
                        GeoActivityData.DEFAULT_MIN_LAT,
                        GeoActivityData.DEFAULT_MAX_LAT,
                        min_lat,
                        max_lat,
                        random.uniform,
                    )

                    longitude = self._check_return_value_within_range(
                        GeoActivityData.DEFAULT_MIN_LONG,
                        GeoActivityData.DEFAULT_MAX_LONG,
                        min_long,
                        max_long,
                        random.uniform,
                    )

                    altitude = self._check_return_value_within_range(
                        GeoActivityData.DEFAULT_MIN_ALT,
                        GeoActivityData.DEFAULT_MAX_ALT,
                        min_alt,
                        max_alt,
                        random.uniform,
                    )

            elif geo_command == "within":
                north_bound = self.saved_geo_loc["latitude"][0]
                south_bound = self.saved_geo_loc["latitude"][1]
                east_bound = self.saved_geo_loc["longitude"][0]
                west_bound = self.saved_geo_loc["longitude"][1]
                altitude = self.saved_geo_loc["altitude"]

                if is_truth_file:
                    latitude = random.uniform(north_bound, south_bound)
                    longitude = random.uniform(east_bound, west_bound)

                else:
                    max_lat = min(GeoActivityData.DEFAULT_MAX_LAT, north_bound + delta)
                    min_lat = max(GeoActivityData.DEFAULT_MIN_LAT, south_bound - delta)
                    max_long = min(GeoActivityData.DEFAULT_MAX_LONG, east_bound + delta)
                    min_long = max(GeoActivityData.DEFAULT_MIN_LONG, west_bound - delta)
                    min_alt = max(GeoActivityData.DEFAULT_MIN_ALT, altitude - delta)
                    max_alt = min(GeoActivityData.DEFAULT_MAX_ALT, altitude + delta)

                    latitude = self._self._check_return_value_within_range(
                        GeoActivityData.DEFAULT_MIN_LAT,
                        GeoActivityData.DEFAULT_MAX_LAT,
                        min_lat,
                        max_lat,
                        random.uniform,
                    )

                    longitude = self._check_return_value_within_range(
                        GeoActivityData.DEFAULT_MIN_LONG,
                        GeoActivityData.DEFAULT_MAX_LONG,
                        min_long,
                        max_long,
                        random.uniform,
                    )

                    altitude = self._check_return_value_within_range(
                        GeoActivityData.DEFAULT_MIN_ALT,
                        GeoActivityData.DEFAULT_MAX_ALT,
                        min_alt,
                        max_alt,
                        random.uniform,
                    )

        else:
            latitude = random.uniform(
                GeoActivityData.DEFAULT_MIN_LAT, GeoActivityData.DEFAULT_MAX_LAT
            )
            longitude = random.uniform(
                GeoActivityData.DEFAULT_MIN_LONG, GeoActivityData.DEFAULT_MAX_LONG
            )
            altitude = random.uniform(
                GeoActivityData.DEFAULT_MIN_ALT, GeoActivityData.DEFAULT_MAX_ALT
            )

        location_dict["latitude"] = latitude
        location_dict["longitude"] = longitude
        location_dict["altitude"] = altitude
        return location_dict

    # helper for _generate_geo_context()
    def _save_location(self, geo_location: str, geo_command: str) -> Dict[str, float]:
        """
        Saves the geographical location specified in the selected_md_attributes; run once
        """
        geo_py = Nominatim(user_agent="Geo Location Metadata Generator")
        location = geo_py.geocode(geo_location, timeout=1000)

        latitude = location.latitude
        longitude = location.longitude
        altitude = location.altitude

        # save a list of longitude and latitude values if command is within
        if geo_command == "within":
            kilometer_range = self.selected_md["geo_location"]["km"]
            north_bound = (
                geodesic(kilometers=kilometer_range)
                .destination((latitude, longitude), bearing=0)
                .latitude
            )
            south_bound = (
                geodesic(kilometers=kilometer_range)
                .destination((latitude, longitude), bearing=180)
                .latitude
            )
            east_bound = (
                geodesic(kilometers=kilometer_range)
                .destination((latitude, longitude), bearing=90)
                .longitude
            )
            west_bound = (
                geodesic(kilometers=kilometer_range)
                .destination((latitude, longitude), bearing=270)
                .longitude
            )
            latitude = [south_bound, north_bound]
            longitude = [west_bound, east_bound]

        return {"latitude": latitude, "longitude": longitude, "altitude": altitude}

    def _generate_WindowsGPSLocation(
        self, geo_activity_context: Dict[str, float], timestamp: datetime
    ) -> Dict[str, Any]:
        """
        Generate the Windows GPS location in the form of a dictionary
        """
        latitude = geo_activity_context["latitude"]
        longitude = geo_activity_context["longitude"]
        altitude = geo_activity_context["altitude"]

        windowsGPS_satellite_location = WindowsGPSLocationSatelliteDataModel(
            geometric_dilution_of_precision=random.uniform(1, 10),
            horizontal_dilution_of_precision=random.uniform(1, 10),
            position_dilution_of_precision=random.uniform(1, 10),
            time_dilution_of_precision=random.uniform(1, 10),
            vertical_dilution_of_precision=random.uniform(1, 10),
        )

        no_windowsGPS_satellite_location = WindowsGPSLocationSatelliteDataModel(
            geometric_dilution_of_precision=None,
            horizontal_dilution_of_precision=None,
            position_dilution_of_precision=None,
            time_dilution_of_precision=None,
            vertical_dilution_of_precision=None,
        )

        GPS_location_dict = WindowsGPSLocationDataModel(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            accuracy=random.uniform(1, 10),
            altitude_accuracy=random.uniform(0, 10),
            heading=random.randint(0, 360),
            speed=random.uniform(0, 20),
            source="GPS",
            timestamp=timestamp,
            is_remote_source=False,
            point=f"POINT({longitude} {latitude})",
            position_source="GPS",
            position_source_timestamp=timestamp,
            satellite_data=random.choice(
                [windowsGPS_satellite_location, no_windowsGPS_satellite_location]
            ),
            civic_address=None,
            venue_data=None,
        )

        return GPS_location_dict
