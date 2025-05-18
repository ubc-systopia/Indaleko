"""
Unit tests for the EXIFGeneratorTool.

This module contains tests for the enhanced EXIF metadata generator.
"""

import os
import sys
import unittest
import datetime
import uuid
from typing import Dict, List, Any

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import EXIF generator tool
from tools.data_generator_enhanced.agents.data_gen.tools.exif_generator import (
    EXIFGeneratorTool
)
from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry


class TestEXIFGeneratorTool(unittest.TestCase):
    """Test case for EXIFGeneratorTool."""

    def setUp(self):
        """Set up test case."""
        self.exif_generator = EXIFGeneratorTool()
        self.user_id = "test_user"
        self.start_time = (datetime.datetime.now() - datetime.timedelta(days=30)).timestamp()
        self.end_time = datetime.datetime.now().timestamp()

        # Create test storage record
        self.storage_id = str(uuid.uuid4())

    def test_exif_generator_creation(self):
        """Test that EXIFGeneratorTool can be instantiated."""
        self.assertIsNotNone(self.exif_generator)
        self.assertEqual(self.exif_generator.name, "exif_generator")
        self.assertIsNotNone(self.exif_generator.camera_profiles)
        self.assertIsNotNone(self.exif_generator.scene_types)
        self.assertIsNotNone(self.exif_generator.exposure_programs)

    def test_camera_profiles(self):
        """Test camera profiles are properly configured."""
        # Check some camera profiles exist
        self.assertIn("canon", self.exif_generator.camera_profiles)
        self.assertIn("nikon", self.exif_generator.camera_profiles)
        self.assertIn("sony", self.exif_generator.camera_profiles)
        self.assertIn("iphone", self.exif_generator.camera_profiles)

        # Check profile structure
        canon_profile = self.exif_generator.camera_profiles["canon"]
        self.assertIn("make", canon_profile)
        self.assertIn("models", canon_profile)
        self.assertIn("software", canon_profile)
        self.assertIn("lens_make", canon_profile)
        self.assertIn("lens_models", canon_profile)
        self.assertIn("megapixels", canon_profile)
        self.assertIn("iso_range", canon_profile)

    def test_generate_exif_data(self):
        """Test generating EXIF data."""
        # Generate EXIF data with explicit storage ID
        result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="canon",
            timestamp=self.end_time
        )

        # Check record structure
        self.assertIsNotNone(result)
        self.assertEqual(result["Object"], self.storage_id)
        self.assertEqual(result["UserId"], self.user_id)
        self.assertEqual(result["Timestamp"], self.end_time)

        # Check sections
        self.assertIn("CameraData", result)
        self.assertIn("CaptureSettings", result)
        self.assertIn("ImageInfo", result)

        # Check camera data
        camera_data = result["CameraData"]
        self.assertEqual(camera_data["make"], "Canon")
        self.assertIn("model", camera_data)
        self.assertIn("serial_number", camera_data)

        # Check capture settings
        capture_settings = result["CaptureSettings"]
        self.assertEqual(capture_settings["date_time"], self.end_time)
        self.assertIn("exposure_time", capture_settings)
        self.assertIn("aperture", capture_settings)
        self.assertIn("iso", capture_settings)
        self.assertIn("focal_length", capture_settings)

        # Check image info
        image_info = result["ImageInfo"]
        self.assertIn("width", image_info)
        self.assertIn("height", image_info)
        self.assertIn("bit_depth", image_info)
        self.assertIn("color_space", image_info)
        self.assertIn("orientation", image_info)

    def test_generate_with_gps(self):
        """Test generating EXIF data with GPS information."""
        coords = {"latitude": 37.7749, "longitude": -122.4194}

        # Generate EXIF data with GPS
        result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="iphone",
            timestamp=self.end_time,
            gps_data=self.exif_generator._generate_gps_data(coords, self.end_time)
        )

        # Check GPS data
        self.assertIn("GpsData", result)
        gps_data = result["GpsData"]

        self.assertIn("latitude", gps_data)
        self.assertIn("longitude", gps_data)
        self.assertIn("altitude", gps_data)
        self.assertIn("date", gps_data)
        self.assertIn("time", gps_data)

        # Check coordinates are close to original
        self.assertAlmostEqual(gps_data["latitude"], coords["latitude"], delta=0.01)
        self.assertAlmostEqual(gps_data["longitude"], coords["longitude"], delta=0.01)

    def test_semantic_attributes(self):
        """Test semantic attributes generation."""
        # Generate EXIF data
        result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="canon",
            timestamp=self.end_time,
            gps_data=self.exif_generator._generate_random_gps_data(self.end_time)
        )

        # Check semantic attributes
        self.assertIn("SemanticAttributes", result)
        semantic_attributes = result["SemanticAttributes"]

        self.assertIsInstance(semantic_attributes, list)
        self.assertGreater(len(semantic_attributes), 0)

        # Check for required attributes
        attribute_ids = [attr["Identifier"]["Identifier"] for attr in semantic_attributes]

        # Check main EXIF data attribute
        exif_data_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_DATA")
        self.assertIn(exif_data_id, attribute_ids)

        # Check camera attributes
        camera_make_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_CAMERA_MAKE")
        self.assertIn(camera_make_id, attribute_ids)

        camera_model_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_CAMERA_MODEL")
        self.assertIn(camera_model_id, attribute_ids)

        # Check at least one GPS attribute
        gps_lat_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_GPS_LATITUDE")
        self.assertIn(gps_lat_id, attribute_ids)

        # Check at least one image attribute
        width_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_WIDTH")
        self.assertIn(width_id, attribute_ids)

    def test_different_camera_types(self):
        """Test different camera types produce different data."""
        # Generate data for different camera types
        canon_result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="canon",
            timestamp=self.end_time
        )

        iphone_result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="iphone",
            timestamp=self.end_time
        )

        # Verify different makes
        self.assertEqual(canon_result["CameraData"]["make"], "Canon")
        self.assertEqual(iphone_result["CameraData"]["make"], "Apple")

        # Verify different model patterns
        self.assertIn("EOS", canon_result["CameraData"]["model"])
        self.assertIn("iPhone", iphone_result["CameraData"]["model"])

        # Verify different software
        self.assertNotEqual(
            canon_result["CameraData"]["software"],
            iphone_result["CameraData"]["software"]
        )

    def test_temporal_consistency(self):
        """Test EXIF timestamps match the provided timestamp."""
        timestamp = datetime.datetime.now().timestamp()

        # Generate EXIF data with specific timestamp
        result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="canon",
            timestamp=timestamp
        )

        # Check timestamp in capture settings
        self.assertEqual(result["CaptureSettings"]["date_time"], timestamp)
        self.assertEqual(result["Timestamp"], timestamp)

        # Check timestamp in semantic attributes
        datetime_attr = next((attr for attr in result["SemanticAttributes"]
                             if attr["Identifier"]["Label"] == "EXIF_DATETIME"), None)

        self.assertIsNotNone(datetime_attr)
        self.assertEqual(datetime_attr["Value"], timestamp)


if __name__ == "__main__":
    unittest.main()"""
Unit tests for the EXIFGeneratorTool.

This module contains tests for the enhanced EXIF metadata generator.
"""

import os
import sys
import unittest
import datetime
import uuid
from typing import Dict, List, Any

# Setup path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import EXIF generator tool
from tools.data_generator_enhanced.agents.data_gen.tools.exif_generator import (
    EXIFGeneratorTool
)
from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry


class TestEXIFGeneratorTool(unittest.TestCase):
    """Test case for EXIFGeneratorTool."""

    def setUp(self):
        """Set up test case."""
        self.exif_generator = EXIFGeneratorTool()
        self.user_id = "test_user"
        self.start_time = (datetime.datetime.now() - datetime.timedelta(days=30)).timestamp()
        self.end_time = datetime.datetime.now().timestamp()

        # Create test storage record
        self.storage_id = str(uuid.uuid4())

    def test_exif_generator_creation(self):
        """Test that EXIFGeneratorTool can be instantiated."""
        self.assertIsNotNone(self.exif_generator)
        self.assertEqual(self.exif_generator.name, "exif_generator")
        self.assertIsNotNone(self.exif_generator.camera_profiles)
        self.assertIsNotNone(self.exif_generator.scene_types)
        self.assertIsNotNone(self.exif_generator.exposure_programs)

    def test_camera_profiles(self):
        """Test camera profiles are properly configured."""
        # Check some camera profiles exist
        self.assertIn("canon", self.exif_generator.camera_profiles)
        self.assertIn("nikon", self.exif_generator.camera_profiles)
        self.assertIn("sony", self.exif_generator.camera_profiles)
        self.assertIn("iphone", self.exif_generator.camera_profiles)

        # Check profile structure
        canon_profile = self.exif_generator.camera_profiles["canon"]
        self.assertIn("make", canon_profile)
        self.assertIn("models", canon_profile)
        self.assertIn("software", canon_profile)
        self.assertIn("lens_make", canon_profile)
        self.assertIn("lens_models", canon_profile)
        self.assertIn("megapixels", canon_profile)
        self.assertIn("iso_range", canon_profile)

    def test_generate_exif_data(self):
        """Test generating EXIF data."""
        # Generate EXIF data with explicit storage ID
        result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="canon",
            timestamp=self.end_time
        )

        # Check record structure
        self.assertIsNotNone(result)
        self.assertEqual(result["Object"], self.storage_id)
        self.assertEqual(result["UserId"], self.user_id)
        self.assertEqual(result["Timestamp"], self.end_time)

        # Check sections
        self.assertIn("CameraData", result)
        self.assertIn("CaptureSettings", result)
        self.assertIn("ImageInfo", result)

        # Check camera data
        camera_data = result["CameraData"]
        self.assertEqual(camera_data["make"], "Canon")
        self.assertIn("model", camera_data)
        self.assertIn("serial_number", camera_data)

        # Check capture settings
        capture_settings = result["CaptureSettings"]
        self.assertEqual(capture_settings["date_time"], self.end_time)
        self.assertIn("exposure_time", capture_settings)
        self.assertIn("aperture", capture_settings)
        self.assertIn("iso", capture_settings)
        self.assertIn("focal_length", capture_settings)

        # Check image info
        image_info = result["ImageInfo"]
        self.assertIn("width", image_info)
        self.assertIn("height", image_info)
        self.assertIn("bit_depth", image_info)
        self.assertIn("color_space", image_info)
        self.assertIn("orientation", image_info)

    def test_generate_with_gps(self):
        """Test generating EXIF data with GPS information."""
        coords = {"latitude": 37.7749, "longitude": -122.4194}

        # Generate EXIF data with GPS
        result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="iphone",
            timestamp=self.end_time,
            gps_data=self.exif_generator._generate_gps_data(coords, self.end_time)
        )

        # Check GPS data
        self.assertIn("GpsData", result)
        gps_data = result["GpsData"]

        self.assertIn("latitude", gps_data)
        self.assertIn("longitude", gps_data)
        self.assertIn("altitude", gps_data)
        self.assertIn("date", gps_data)
        self.assertIn("time", gps_data)

        # Check coordinates are close to original
        self.assertAlmostEqual(gps_data["latitude"], coords["latitude"], delta=0.01)
        self.assertAlmostEqual(gps_data["longitude"], coords["longitude"], delta=0.01)

    def test_semantic_attributes(self):
        """Test semantic attributes generation."""
        # Generate EXIF data
        result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="canon",
            timestamp=self.end_time,
            gps_data=self.exif_generator._generate_random_gps_data(self.end_time)
        )

        # Check semantic attributes
        self.assertIn("SemanticAttributes", result)
        semantic_attributes = result["SemanticAttributes"]

        self.assertIsInstance(semantic_attributes, list)
        self.assertGreater(len(semantic_attributes), 0)

        # Check for required attributes
        attribute_ids = [attr["Identifier"]["Identifier"] for attr in semantic_attributes]

        # Check main EXIF data attribute
        exif_data_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_DATA")
        self.assertIn(exif_data_id, attribute_ids)

        # Check camera attributes
        camera_make_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_CAMERA_MAKE")
        self.assertIn(camera_make_id, attribute_ids)

        camera_model_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_CAMERA_MODEL")
        self.assertIn(camera_model_id, attribute_ids)

        # Check at least one GPS attribute
        gps_lat_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_GPS_LATITUDE")
        self.assertIn(gps_lat_id, attribute_ids)

        # Check at least one image attribute
        width_id = SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_SEMANTIC, "EXIF_WIDTH")
        self.assertIn(width_id, attribute_ids)

    def test_different_camera_types(self):
        """Test different camera types produce different data."""
        # Generate data for different camera types
        canon_result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="canon",
            timestamp=self.end_time
        )

        iphone_result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="iphone",
            timestamp=self.end_time
        )

        # Verify different makes
        self.assertEqual(canon_result["CameraData"]["make"], "Canon")
        self.assertEqual(iphone_result["CameraData"]["make"], "Apple")

        # Verify different model patterns
        self.assertIn("EOS", canon_result["CameraData"]["model"])
        self.assertIn("iPhone", iphone_result["CameraData"]["model"])

        # Verify different software
        self.assertNotEqual(
            canon_result["CameraData"]["software"],
            iphone_result["CameraData"]["software"]
        )

    def test_temporal_consistency(self):
        """Test EXIF timestamps match the provided timestamp."""
        timestamp = datetime.datetime.now().timestamp()

        # Generate EXIF data with specific timestamp
        result = self.exif_generator._create_exif_record(
            storage_id=self.storage_id,
            user_id=self.user_id,
            camera_type="canon",
            timestamp=timestamp
        )

        # Check timestamp in capture settings
        self.assertEqual(result["CaptureSettings"]["date_time"], timestamp)
        self.assertEqual(result["Timestamp"], timestamp)

        # Check timestamp in semantic attributes
        datetime_attr = next((attr for attr in result["SemanticAttributes"]
                             if attr["Identifier"]["Label"] == "EXIF_DATETIME"), None)

        self.assertIsNotNone(datetime_attr)
        self.assertEqual(datetime_attr["Value"], timestamp)


if __name__ == "__main__":
    unittest.main()
