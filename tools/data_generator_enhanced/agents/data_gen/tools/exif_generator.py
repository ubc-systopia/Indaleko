"""
Enhanced EXIF metadata generator for Indaleko.

This module provides comprehensive EXIF metadata generation capabilities,
including camera information, GPS data, and image attributes.
"""

import os
import sys
import random
import datetime
import uuid
from typing import Dict, List, Any, Tuple, Optional, Union
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
# Import real registry
from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry
# Import data models and database
from data_models.base import IndalekoBaseModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from semantic.collectors.exif.data_model import ExifDataModel, ExifCameraData, ExifCaptureSettings, ExifGpsData, ExifImageInfo


class EXIFGeneratorTool(Tool):
    """Tool to generate realistic EXIF metadata."""
    
    def __init__(self):
        """Initialize the EXIF generator tool."""
        super().__init__(name="exif_generator", description="Generates realistic EXIF metadata")
        
        # Initialize database connection
        self.db_config = IndalekoDBConfig()
        self.db_config.setup_database(self.db_config.config["database"]["database"])
        
        # Initialize camera profiles
        self.camera_profiles = {
            # Mobile phones
            "iphone": {
                "make": "Apple",
                "models": ["iPhone 13 Pro", "iPhone 14", "iPhone 15 Pro Max", "iPhone SE", "iPhone 12 Mini"],
                "software": "iOS",
                "lens_make": "Apple",
                "lens_models": ["Ultra Wide", "Wide", "Telephoto"],
                "megapixels": (12, 48),
                "iso_range": (32, 3200),
                "max_aperture": (1.8, 2.8),
                "flash": True
            },
            "samsung": {
                "make": "Samsung",
                "models": ["Galaxy S23 Ultra", "Galaxy S22", "Galaxy Note 20", "Galaxy Z Fold 5", "Galaxy A54"],
                "software": "One UI",
                "lens_make": "Samsung",
                "lens_models": ["Ultra Wide", "Wide Angle", "Telephoto"],
                "megapixels": (12, 200),
                "iso_range": (50, 3200),
                "max_aperture": (1.5, 2.4),
                "flash": True
            },
            "google": {
                "make": "Google",
                "models": ["Pixel 7 Pro", "Pixel 6", "Pixel 8", "Pixel 7a", "Pixel Fold"],
                "software": "Android",
                "lens_make": "Google",
                "lens_models": ["Main Camera", "Ultra Wide", "Telephoto"],
                "megapixels": (12, 50),
                "iso_range": (64, 1600),
                "max_aperture": (1.9, 2.8),
                "flash": True
            },
            # DSLR cameras
            "canon": {
                "make": "Canon",
                "models": ["EOS 5D Mark IV", "EOS R5", "EOS 90D", "EOS 6D Mark II", "EOS R6"],
                "software": "Digital Photo Professional",
                "lens_make": "Canon",
                "lens_models": ["EF 24-70mm f/2.8L II USM", "RF 70-200mm f/2.8L IS USM", "EF 50mm f/1.4 USM", "EF 100mm f/2.8L Macro IS USM", "RF 15-35mm f/2.8L IS USM"],
                "megapixels": (20, 45),
                "iso_range": (100, 51200),
                "max_aperture": (1.2, 4.0),
                "flash": True
            },
            "nikon": {
                "make": "Nikon",
                "models": ["Z9", "D850", "Z7 II", "D750", "Z6"],
                "software": "Capture NX-D",
                "lens_make": "Nikon",
                "lens_models": ["NIKKOR Z 24-70mm f/2.8 S", "AF-S NIKKOR 70-200mm f/2.8E FL ED VR", "NIKKOR Z 50mm f/1.8 S", "AF-S NIKKOR 14-24mm f/2.8G ED", "NIKKOR Z 85mm f/1.8 S"],
                "megapixels": (24, 45.7),
                "iso_range": (64, 25600),
                "max_aperture": (1.4, 4.0),
                "flash": True
            },
            "sony": {
                "make": "Sony",
                "models": ["Alpha A7 IV", "Alpha A1", "Alpha A6600", "Alpha A7R V", "Alpha A9 III"],
                "software": "Imaging Edge",
                "lens_make": "Sony",
                "lens_models": ["FE 24-70mm F2.8 GM II", "FE 70-200mm F2.8 GM OSS II", "FE 50mm F1.2 GM", "FE 16-35mm F2.8 GM", "FE 85mm F1.4 GM"],
                "megapixels": (24, 61),
                "iso_range": (50, 204800),
                "max_aperture": (1.2, 4.0),
                "flash": True
            },
            # Mirrorless cameras
            "fujifilm": {
                "make": "Fujifilm",
                "models": ["X-T5", "X-Pro3", "X-H2S", "X-E4", "X-S20"],
                "software": "Capture One Fujifilm",
                "lens_make": "Fujinon",
                "lens_models": ["XF 16-55mm F2.8 R LM WR", "XF 50-140mm F2.8 R LM OIS WR", "XF 56mm F1.2 R WR", "XF 23mm F1.4 R LM WR", "XF 18mm F1.4 R LM WR"],
                "megapixels": (26, 40),
                "iso_range": (160, 12800),
                "max_aperture": (1.0, 4.0),
                "flash": True
            },
            # Compact cameras
            "panasonic": {
                "make": "Panasonic",
                "models": ["LUMIX LX100 II", "LUMIX ZS200", "LUMIX FZ1000 II", "LUMIX GH6", "LUMIX S5 II"],
                "software": "LUMIX Webcam Software",
                "lens_make": "Leica",
                "lens_models": ["LEICA DC VARIO-SUMMILUX", "LEICA DG VARIO-ELMARIT", "LEICA DG SUMMILUX"],
                "megapixels": (17, 24),
                "iso_range": (200, 25600),
                "max_aperture": (1.7, 4.0),
                "flash": True
            },
            # Drones
            "dji": {
                "make": "DJI",
                "models": ["Mavic 3", "Air 2S", "Mini 3 Pro", "Phantom 4 Pro V2.0", "Inspire 2"],
                "software": "DJI Fly",
                "lens_make": "Hasselblad",
                "lens_models": ["L2D-20c", "1-inch CMOS Sensor", "1/1.3-inch CMOS Sensor"],
                "megapixels": (12, 20),
                "iso_range": (100, 6400),
                "max_aperture": (2.8, 4.0),
                "flash": False
            }
        }
        
        # Initialize common EXIF characteristics
        self.scene_types = ["standard", "landscape", "portrait", "night", "sports", "macro", "indoor", "beach", "snow", "sunset", "food", "text"]
        self.exposure_programs = ["manual", "normal", "aperture_priority", "shutter_priority", "creative", "action", "portrait", "landscape"]
        self.metering_modes = ["average", "center_weighted", "spot", "multi_spot", "pattern", "partial"]
        self.white_balance = ["auto", "daylight", "cloudy", "shade", "tungsten", "fluorescent", "flash", "custom"]
        self.light_sources = ["daylight", "fluorescent", "tungsten", "flash", "fine_weather", "cloudy_weather", "shade", "daylight_fluorescent", 
                            "day_white_fluorescent", "cool_white_fluorescent", "white_fluorescent", "standard_light_a", "standard_light_b", 
                            "standard_light_c", "d55", "d65", "d75", "d50", "iso_studio_tungsten"]
        self.orientations = ["horizontal", "mirror_horizontal", "rotate_180", "mirror_vertical", "mirror_horizontal_rotate_270", 
                            "rotate_90", "mirror_horizontal_rotate_90", "rotate_270"]
        
        # Register EXIF semantic attributes if needed
        self._register_exif_attributes()
        
    def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EXIF generator tool.
        
        Args:
            params: Parameters for execution
                count: Number of EXIF records to generate
                criteria: Criteria for generation
                    user_id: User identifier
                    storage_ids: List of storage object IDs to attach EXIF data to
                    camera_types: List of camera types to include
                    time_range: Dict with 'start' and 'end' timestamps
                    location_coordinates: Optional Dict with 'latitude' and 'longitude'
                    
        Returns:
            Dictionary with generated records
        """
        count = params.get("count", 1)
        criteria = params.get("criteria", {})
        
        user_id = criteria.get("user_id", str(uuid.uuid4()))
        storage_ids = criteria.get("storage_ids", [])
        camera_types = criteria.get("camera_types", list(self.camera_profiles.keys()))
        start_time = criteria.get("time_range", {}).get("start", (datetime.datetime.now() - datetime.timedelta(days=365)).timestamp())
        end_time = criteria.get("time_range", {}).get("end", datetime.datetime.now().timestamp())
        coordinates = criteria.get("location_coordinates", None)
        
        # If no storage IDs provided, fetch some image files from database
        if not storage_ids:
            self.logger.info("No storage IDs provided, fetching from database")
            storage_ids = self._fetch_image_storage_ids(count)
            
        if not storage_ids:
            self.logger.warning("No storage IDs available. Cannot generate EXIF metadata.")
            return {"records": []}
        
        # Generate EXIF records for each storage ID (up to count)
        storage_ids = storage_ids[:count]
        records = []
        
        for storage_id in storage_ids:
            # Skip if EXIF data already exists
            if self._exif_exists(storage_id):
                self.logger.debug(f"EXIF metadata already exists for {storage_id}")
                continue
            
            # Generate EXIF data
            timestamp = self._random_timestamp(start_time, end_time)
            camera_type = random.choice(camera_types)
            
            # Generate GPS data if coordinates provided
            gps_data = None
            if coordinates:
                gps_data = self._generate_gps_data(coordinates, timestamp)
            else:
                # 40% chance to include GPS data
                if random.random() < 0.4:
                    gps_data = self._generate_random_gps_data(timestamp)
            
            # Create EXIF record
            record = self._create_exif_record(
                storage_id=storage_id,
                user_id=user_id,
                camera_type=camera_type,
                timestamp=timestamp,
                gps_data=gps_data
            )
            
            if record:
                records.append(record)
                # Store in database
                self._store_exif_record(record)
        
        return {
            "records": records
        }
    
    def _register_exif_attributes(self):
        """Register EXIF semantic attributes."""
        # Main EXIF domain
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_DATA", 
            "3fa85f64-5717-4562-b3fc-2c963f66afa6"
        )
        
        # Camera attributes
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_CAMERA_MAKE", 
            "a21e78f1-4751-4d0d-b45e-73fe204c44cb"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_CAMERA_MODEL", 
            "6ad1a25f-8e98-4c9e-a70a-e3bd13afed1c"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_CAMERA_SERIAL", 
            "e6c3dbb6-ddfa-4a2a-b6a1-fc3f3e47dc51"
        )
        
        # Lens attributes
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_LENS_MAKE", 
            "b9fa3ce6-32ee-4a1c-a760-e0db7da9d9a2"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_LENS_MODEL", 
            "c2f0dda8-0c36-4ce3-8e65-afe1dbd34dd2"
        )
        
        # Capture settings
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_DATETIME", 
            "41ce62a8-8db5-43e4-ba8a-a3c1b832b28d"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_EXPOSURE", 
            "1f16c85e-3e10-4a95-a34a-9c5db2b1fb7b"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_APERTURE", 
            "0d0682d0-8c9a-4fa0-9c64-b428e6b067c1"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_ISO", 
            "9b4d3df8-6365-49a7-a24b-0e7b5f92d1a5"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_FOCAL_LENGTH", 
            "ae8ba1d6-6ce2-4bc4-a159-974e5d291102"
        )
        
        # GPS attributes
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_GPS_LATITUDE", 
            "43285899-cc75-4418-a4ff-46beef787836"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_GPS_LONGITUDE", 
            "7a4e43aa-7cda-4fc1-99f5-fc3d26876ad7"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_GPS_ALTITUDE", 
            "b14a53ca-29cd-4e0a-9bf3-4cbf41efaed2"
        )
        
        # Image attributes
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_WIDTH", 
            "55107084-9943-44a5-bc43-193acca0cc9c"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_HEIGHT", 
            "e3eefb4b-c056-49e7-a957-1d449a07b74f"
        )
        SemanticAttributeRegistry.register_attribute(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, 
            "EXIF_ORIENTATION", 
            "78de6832-8253-450d-842a-89ee0f7935f5"
        )
        
    def _fetch_image_storage_ids(self, count: int) -> List[str]:
        """Fetch storage IDs for image files.
        
        Args:
            count: Number of image storage IDs to fetch
            
        Returns:
            List of storage IDs
        """
        # Query for image files (based on common image extensions)
        query = """
        FOR doc IN @@collection
        FILTER doc.IsDirectory == false || doc.IsDirectory == null
        FILTER 
            doc.Name LIKE "%.jpg" OR 
            doc.Name LIKE "%.jpeg" OR 
            doc.Name LIKE "%.png" OR 
            doc.Name LIKE "%.gif" OR 
            doc.Name LIKE "%.bmp" OR 
            doc.Name LIKE "%.tiff" OR 
            doc.Name LIKE "%.heic" OR
            doc.Name LIKE "%.raw" OR
            doc.Name LIKE "%.nef" OR
            doc.Name LIKE "%.cr2" OR
            doc.Name LIKE "%.arw"
        SORT RAND()
        LIMIT @count
        RETURN doc._key
        """
        
        try:
            cursor = self.db_config.db.aql.execute(
                query,
                bind_vars={
                    "@collection": IndalekoDBCollections.Indaleko_Object_Collection,
                    "count": count
                }
            )
            storage_ids = [doc for doc in cursor]
            self.logger.info(f"Fetched {len(storage_ids)} image storage IDs")
            return storage_ids
        except Exception as e:
            self.logger.error(f"Error fetching image storage IDs: {e}")
            return []
    
    def _exif_exists(self, storage_id: str) -> bool:
        """Check if EXIF data already exists for a storage ID.
        
        Args:
            storage_id: Storage ID to check
            
        Returns:
            True if EXIF data exists, False otherwise
        """
        query = """
        FOR doc IN @@collection
        FILTER doc.Object == @storage_id
        LIMIT 1
        RETURN doc
        """
        
        try:
            cursor = self.db_config.db.aql.execute(
                query,
                bind_vars={
                    "@collection": IndalekoDBCollections.Indaleko_SemanticData_Collection,
                    "storage_id": storage_id
                }
            )
            return any(cursor)
        except Exception as e:
            self.logger.error(f"Error checking if EXIF exists: {e}")
            return False
    
    def _random_timestamp(self, start_time: float, end_time: float) -> float:
        """Generate a random timestamp between start and end times.
        
        Args:
            start_time: Start timestamp
            end_time: End timestamp
            
        Returns:
            Random timestamp
        """
        return random.uniform(start_time, end_time)
    
    def _create_exif_record(self, 
                          storage_id: str, 
                          user_id: str, 
                          camera_type: str, 
                          timestamp: float,
                          gps_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an EXIF record.
        
        Args:
            storage_id: Storage ID to attach EXIF data to
            user_id: User ID associated with the record
            camera_type: Type of camera
            timestamp: Timestamp for the EXIF data
            gps_data: Optional GPS data
            
        Returns:
            EXIF record dictionary
        """
        try:
            # Get camera profile
            camera_profile = self.camera_profiles.get(camera_type, self.camera_profiles["canon"])
            
            # Generate camera data
            camera_make = camera_profile["make"]
            camera_model = random.choice(camera_profile["models"])
            camera_serial = f"{camera_type.upper()}-{random.randint(10000000, 99999999)}"
            
            # Generate lens data
            lens_make = camera_profile["lens_make"]
            lens_model = random.choice(camera_profile["lens_models"])
            
            # Generate capture settings
            scene_type = random.choice(self.scene_types)
            iso = random.randint(camera_profile["iso_range"][0], camera_profile["iso_range"][1])
            
            # Aperture as f-stop (f/1.8, f/2.8, etc.)
            aperture = round(random.uniform(camera_profile["max_aperture"][0], camera_profile["max_aperture"][1]), 1)
            
            # Shutter speed (1/250, 1/125, etc. for action, longer for night)
            if scene_type in ["sports", "action"]:
                shutter_denominator = random.choice([1000, 500, 250, 125])
                exposure_time = f"1/{shutter_denominator}"
            elif scene_type in ["night", "sunset"]:
                exposure_options = [f"1/{d}" for d in [60, 30, 15, 8]] + ["1", "2", "4"]
                exposure_time = random.choice(exposure_options)
            else:
                shutter_denominator = random.choice([125, 100, 60, 30])
                exposure_time = f"1/{shutter_denominator}"
            
            # Focal length (mm)
            if lens_model and "mm" in lens_model:
                # Extract from lens model (e.g., "24-70mm" -> random between 24 and 70)
                focal_range = lens_model.split("mm")[0].split("-")
                if len(focal_range) == 2:
                    try:
                        min_focal = int(focal_range[0].split()[-1])
                        max_focal = int(focal_range[1])
                        focal_length = random.randint(min_focal, max_focal)
                    except (ValueError, IndexError):
                        focal_length = random.randint(24, 200)
                else:
                    focal_length = random.randint(24, 200)
            else:
                # Default focal length range
                focal_length = random.randint(24, 200)
            
            # Flash used?
            flash_used = camera_profile["flash"] and random.random() < 0.3
            
            # Image dimensions (based on megapixels)
            megapixels = random.uniform(camera_profile["megapixels"][0], camera_profile["megapixels"][1])
            
            # Approximate width and height based on megapixels and 3:2 aspect ratio
            # sqrt(megapixels * aspect_ratio) = width, height = width / aspect_ratio
            aspect_ratio = 3/2
            width = int(math.sqrt(megapixels * 1_000_000 * aspect_ratio))
            height = int(width / aspect_ratio)
            
            # Round to common resolutions
            width = round(width / 16) * 16
            height = round(height / 16) * 16
            
            # Color space
            color_space = random.choice(["sRGB", "Adobe RGB", "ProPhoto RGB"])
            
            # Exposure program
            exposure_program = random.choice(self.exposure_programs)
            
            # Metering mode
            metering_mode = random.choice(self.metering_modes)
            
            # White balance
            white_balance = random.choice(self.white_balance)
            
            # Orientation
            orientation = random.choice(self.orientations)
            
            # Create the EXIF record
            camera_data = {
                "make": camera_make,
                "model": camera_model,
                "serial_number": camera_serial,
                "lens_make": lens_make,
                "lens_model": lens_model,
                "software": camera_profile["software"]
            }
            
            capture_settings = {
                "date_time": timestamp,
                "exposure_time": exposure_time,
                "aperture": f"f/{aperture}",
                "iso": iso,
                "focal_length": f"{focal_length}mm",
                "flash": flash_used,
                "scene_type": scene_type,
                "exposure_program": exposure_program,
                "metering_mode": metering_mode,
                "white_balance": white_balance
            }
            
            image_info = {
                "width": width,
                "height": height,
                "bit_depth": 24,
                "color_space": color_space,
                "orientation": orientation,
                "software": camera_profile["software"],
                "artist": user_id
            }
            
            # Create core EXIF record
            exif_record = {
                "_key": str(uuid.uuid4()),
                "Object": storage_id,
                "UserId": user_id,
                "Timestamp": timestamp,
                "CameraData": camera_data,
                "CaptureSettings": capture_settings,
                "ImageInfo": image_info,
                "MIMEType": "image/jpeg"  # Default to JPEG
            }
            
            # Add GPS data if provided
            if gps_data:
                exif_record["GpsData"] = gps_data
            
            # Generate semantic attributes
            semantic_attributes = self._generate_semantic_attributes(
                storage_id=storage_id,
                camera_data=camera_data,
                capture_settings=capture_settings,
                image_info=image_info,
                gps_data=gps_data
            )
            
            # Add semantic attributes to record
            exif_record["SemanticAttributes"] = semantic_attributes
            
            return exif_record
        
        except Exception as e:
            self.logger.error(f"Error creating EXIF record: {e}")
            return None
    
    def _generate_semantic_attributes(self,
                                    storage_id: str,
                                    camera_data: Dict[str, Any],
                                    capture_settings: Dict[str, Any],
                                    image_info: Dict[str, Any],
                                    gps_data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate semantic attributes for EXIF data.
        
        Args:
            storage_id: Storage ID of the object
            camera_data: Camera data dictionary
            capture_settings: Capture settings dictionary
            image_info: Image information dictionary
            gps_data: Optional GPS data dictionary
            
        Returns:
            List of semantic attributes
        """
        semantic_attributes = []
        
        # Main EXIF attribute
        semantic_attributes.append(
            IndalekoSemanticAttributeDataModel(
                Identifier=IndalekoUUIDDataModel(
                    Identifier=SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_DATA"),
                    Label="EXIF_DATA"
                ),
                Value=True
            ).model_dump()
        )
        
        # Camera make
        if camera_data.get("make"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_CAMERA_MAKE"),
                        Label="EXIF_CAMERA_MAKE"
                    ),
                    Value=camera_data["make"]
                ).model_dump()
            )
        
        # Camera model
        if camera_data.get("model"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_CAMERA_MODEL"),
                        Label="EXIF_CAMERA_MODEL"
                    ),
                    Value=camera_data["model"]
                ).model_dump()
            )
        
        # Camera serial
        if camera_data.get("serial_number"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_CAMERA_SERIAL"),
                        Label="EXIF_CAMERA_SERIAL"
                    ),
                    Value=camera_data["serial_number"]
                ).model_dump()
            )
        
        # Lens make
        if camera_data.get("lens_make"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_LENS_MAKE"),
                        Label="EXIF_LENS_MAKE"
                    ),
                    Value=camera_data["lens_make"]
                ).model_dump()
            )
        
        # Lens model
        if camera_data.get("lens_model"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_LENS_MODEL"),
                        Label="EXIF_LENS_MODEL"
                    ),
                    Value=camera_data["lens_model"]
                ).model_dump()
            )
        
        # Capture date/time
        if capture_settings.get("date_time"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_DATETIME"),
                        Label="EXIF_DATETIME"
                    ),
                    Value=capture_settings["date_time"]
                ).model_dump()
            )
        
        # Exposure time
        if capture_settings.get("exposure_time"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_EXPOSURE"),
                        Label="EXIF_EXPOSURE"
                    ),
                    Value=capture_settings["exposure_time"]
                ).model_dump()
            )
        
        # Aperture
        if capture_settings.get("aperture"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_APERTURE"),
                        Label="EXIF_APERTURE"
                    ),
                    Value=capture_settings["aperture"]
                ).model_dump()
            )
        
        # ISO
        if capture_settings.get("iso"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_ISO"),
                        Label="EXIF_ISO"
                    ),
                    Value=capture_settings["iso"]
                ).model_dump()
            )
        
        # Focal length
        if capture_settings.get("focal_length"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_FOCAL_LENGTH"),
                        Label="EXIF_FOCAL_LENGTH"
                    ),
                    Value=capture_settings["focal_length"]
                ).model_dump()
            )
        
        # Image width
        if image_info.get("width"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_WIDTH"),
                        Label="EXIF_WIDTH"
                    ),
                    Value=image_info["width"]
                ).model_dump()
            )
        
        # Image height
        if image_info.get("height"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_HEIGHT"),
                        Label="EXIF_HEIGHT"
                    ),
                    Value=image_info["height"]
                ).model_dump()
            )
        
        # Image orientation
        if image_info.get("orientation"):
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=SemanticAttributeRegistry.get_attribute_id(
                            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_ORIENTATION"),
                        Label="EXIF_ORIENTATION"
                    ),
                    Value=image_info["orientation"]
                ).model_dump()
            )
        
        # GPS data
        if gps_data:
            if gps_data.get("latitude"):
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=SemanticAttributeRegistry.get_attribute_id(
                                SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_GPS_LATITUDE"),
                            Label="EXIF_GPS_LATITUDE"
                        ),
                        Value=gps_data["latitude"]
                    ).model_dump()
                )
            
            if gps_data.get("longitude"):
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=SemanticAttributeRegistry.get_attribute_id(
                                SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_GPS_LONGITUDE"),
                            Label="EXIF_GPS_LONGITUDE"
                        ),
                        Value=gps_data["longitude"]
                    ).model_dump()
                )
            
            if gps_data.get("altitude"):
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=SemanticAttributeRegistry.get_attribute_id(
                                SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_GPS_ALTITUDE"),
                            Label="EXIF_GPS_ALTITUDE"
                        ),
                        Value=gps_data["altitude"]
                    ).model_dump()
                )
        
        return semantic_attributes
    
    def _store_exif_record(self, record: Dict[str, Any]) -> bool:
        """Store an EXIF record in the database.
        
        Args:
            record: EXIF record to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Make sure the SemanticData collection exists
            if not self.db_config.db.has_collection(IndalekoDBCollections.Indaleko_SemanticData_Collection):
                self.logger.info(f"Creating SemanticData collection")
                self.db_config.db.create_collection(IndalekoDBCollections.Indaleko_SemanticData_Collection)
            
            # Get the collection
            collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_SemanticData_Collection)
            
            # Insert the record
            collection.insert(record)
            
            return True
        except Exception as e:
            self.logger.error(f"Error storing EXIF record: {e}")
            return False
    
    def _generate_gps_data(self, coordinates: Dict[str, float], timestamp: float) -> Dict[str, Any]:
        """Generate GPS data based on provided coordinates.
        
        Args:
            coordinates: Base coordinates dictionary
            timestamp: Timestamp
            
        Returns:
            GPS data dictionary
        """
        # Add some small randomness to coordinates
        latitude = coordinates["latitude"] + random.uniform(-0.001, 0.001)
        longitude = coordinates["longitude"] + random.uniform(-0.001, 0.001)
        
        # Generate random altitude (0-1000m)
        altitude = random.uniform(0, 1000)
        
        # Format timestamp
        datetime_obj = datetime.datetime.fromtimestamp(timestamp)
        date_str = datetime_obj.strftime("%Y:%m:%d")
        time_str = datetime_obj.strftime("%H:%M:%S")
        
        return {
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude,
            "date": date_str,
            "time": time_str
        }
    
    def _generate_random_gps_data(self, timestamp: float) -> Dict[str, Any]:
        """Generate random GPS data.
        
        Args:
            timestamp: Timestamp
            
        Returns:
            GPS data dictionary
        """
        # Generate random coordinates within realistic ranges
        latitude = random.uniform(-85, 85)
        longitude = random.uniform(-180, 180)
        
        return self._generate_gps_data({"latitude": latitude, "longitude": longitude}, timestamp)


if __name__ == "__main__":
    # Simple test
    import logging
    logging.basicConfig(level=logging.INFO)
    
    exif_generator = EXIFGeneratorTool()
    result = exif_generator.execute({
        "count": 5,
        "criteria": {
            "user_id": "test_user",
            "camera_types": ["canon", "nikon", "iphone"],
            "time_range": {
                "start": (datetime.datetime.now() - datetime.timedelta(days=30)).timestamp(),
                "end": datetime.datetime.now().timestamp()
            },
            "location_coordinates": {
                "latitude": 37.7749,
                "longitude": -122.4194
            }
        }
    })
    
    # Print the results
    logging.info(f"Generated {len(result['records'])} EXIF records")
    
    if result["records"]:
        # Print sample record (without semantic attributes)
        sample = result["records"][0].copy()
        if "SemanticAttributes" in sample:
            sample["SemanticAttributes"] = f"[{len(sample['SemanticAttributes'])} attributes]"
        
        import json
        print(json.dumps(sample, indent=2))