"""
This implements a semantic extractor for EXIF metadata from image files.

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

# standard imports
import os
import sys
import re
import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple

# third-party imports
import exifread
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS

# Set up path for Indaleko imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Indaleko imports
from semantic.collectors.semantic_collector import SemanticCollector
from semantic.characteristics import SemanticDataCharacteristics
import semantic.recorders.exif.characteristics as ExifCharacteristics
from semantic.collectors.exif.data_model import (
    ExifDataModel, ExifCameraData, ExifCaptureSettings, ExifGpsData, ExifImageInfo
)
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel


class ExifCollector(SemanticCollector):
    """
    Semantic collector for EXIF metadata extraction from image files.
    
    This collector extracts metadata from images including:
    - Camera information (make, model, lens)
    - Capture settings (exposure, aperture, ISO)
    - GPS data (location, altitude)
    - Image information (dimensions, software used, copyright)
    """

    def __init__(self, **kwargs):
        """Initialize the EXIF metadata collector"""
        self._name = "EXIF Metadata Collector"
        self._provider_id = uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6")
        self._exif_data = None
        self._cache = {}  # Cache EXIF data by file path
        
        for key, values in kwargs.items():
            setattr(self, key, values)
            
    def get_collector_characteristics(self) -> List[SemanticDataCharacteristics]:
        """Get the characteristics of the collector"""
        return [
            SemanticDataCharacteristics.SEMANTIC_DATA_CONTENTS,
            ExifCharacteristics.SEMANTIC_EXIF_DATA,
            # Camera information
            ExifCharacteristics.SEMANTIC_EXIF_CAMERA_MAKE,
            ExifCharacteristics.SEMANTIC_EXIF_CAMERA_MODEL,
            ExifCharacteristics.SEMANTIC_EXIF_CAMERA_SERIAL,
            ExifCharacteristics.SEMANTIC_EXIF_LENS_MAKE,
            ExifCharacteristics.SEMANTIC_EXIF_LENS_MODEL,
            ExifCharacteristics.SEMANTIC_EXIF_LENS_SERIAL,
            # Capture settings
            ExifCharacteristics.SEMANTIC_EXIF_DATETIME_ORIGINAL,
            ExifCharacteristics.SEMANTIC_EXIF_DATETIME_DIGITIZED,
            ExifCharacteristics.SEMANTIC_EXIF_EXPOSURE_TIME,
            ExifCharacteristics.SEMANTIC_EXIF_FNUMBER,
            ExifCharacteristics.SEMANTIC_EXIF_ISO,
            ExifCharacteristics.SEMANTIC_EXIF_FOCAL_LENGTH,
            ExifCharacteristics.SEMANTIC_EXIF_EXPOSURE_BIAS,
            ExifCharacteristics.SEMANTIC_EXIF_METERING_MODE,
            ExifCharacteristics.SEMANTIC_EXIF_FLASH,
            # GPS data
            ExifCharacteristics.SEMANTIC_EXIF_GPS_LATITUDE,
            ExifCharacteristics.SEMANTIC_EXIF_GPS_LONGITUDE,
            ExifCharacteristics.SEMANTIC_EXIF_GPS_ALTITUDE,
            ExifCharacteristics.SEMANTIC_EXIF_GPS_TIMESTAMP,
            ExifCharacteristics.SEMANTIC_EXIF_GPS_MAPDATUM,
            # Image information
            ExifCharacteristics.SEMANTIC_EXIF_IMAGE_WIDTH,
            ExifCharacteristics.SEMANTIC_EXIF_IMAGE_HEIGHT,
            ExifCharacteristics.SEMANTIC_EXIF_BITS_PER_SAMPLE,
            ExifCharacteristics.SEMANTIC_EXIF_COMPRESSION,
            ExifCharacteristics.SEMANTIC_EXIF_PHOTOMETRIC_INTERPRETATION,
            ExifCharacteristics.SEMANTIC_EXIF_ORIENTATION,
            ExifCharacteristics.SEMANTIC_EXIF_SAMPLES_PER_PIXEL,
            ExifCharacteristics.SEMANTIC_EXIF_PLANAR_CONFIGURATION,
            ExifCharacteristics.SEMANTIC_EXIF_SOFTWARE,
            ExifCharacteristics.SEMANTIC_EXIF_ARTIST,
            ExifCharacteristics.SEMANTIC_EXIF_COPYRIGHT,
            ExifCharacteristics.SEMANTIC_EXIF_USER_COMMENT,
        ]
        
    def get_collector_name(self) -> str:
        """Get the name of the collector"""
        return self._name
        
    def get_collector_id(self) -> uuid.UUID:
        """Get the ID of the collector"""
        return self._provider_id
        
    def retrieve_data(self, data_id: str) -> Dict:
        """Retrieve the data for the collector"""
        if not self._exif_data:
            logging.warning("No EXIF data has been collected yet")
            return {}
        return self._exif_data.model_dump()
        
    def get_collector_description(self) -> str:
        """Get the description of the collector"""
        return """This collector extracts EXIF metadata from image files, providing information about:
        - Camera equipment (make, model, lens)
        - Capture settings (exposure, aperture, ISO)
        - GPS location data (when available)
        - Image information (dimensions, software used, copyright)"""
        
    def get_json_schema(self) -> dict:
        """Get the JSON schema for the collector"""
        return ExifDataModel.model_json_schema()
        
    def extract_exif_data(self, file_path: str) -> Dict[str, Any]:
        """
        Extract raw EXIF data from an image file using exifread.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dict[str, Any]: Dictionary of EXIF tags
        """
        # Check for supported image file types
        if not self.is_supported_image(file_path):
            logging.warning(f"Unsupported image file: {file_path}")
            return {}
            
        # Check if data is already cached
        if file_path in self._cache:
            return self._cache[file_path]
            
        try:
            # Extract using exifread for comprehensive EXIF data
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f, details=True)
                
            # Extract additional data using Pillow
            pil_exif = {}
            try:
                with Image.open(file_path) as img:
                    pil_exif["ImageWidth"] = img.width
                    pil_exif["ImageHeight"] = img.height
                    
                    # Get standard EXIF data from Pillow
                    if hasattr(img, '_getexif') and img._getexif():
                        exif = {
                            TAGS.get(tag, tag): value
                            for tag, value in img._getexif().items()
                            if tag in TAGS
                        }
                        pil_exif.update(exif)
            except Exception as e:
                logging.warning(f"Error extracting additional EXIF data with Pillow: {e}")
                
            # Convert exifread tags to a more usable format
            exif_data = {}
            for tag, value in tags.items():
                # Convert exifread.classes.IfdTag to string or appropriate type
                if hasattr(value, 'values'):
                    exif_data[tag] = value.values
                else:
                    exif_data[tag] = str(value)
                    
            # Merge with Pillow EXIF data
            exif_data.update(pil_exif)
            
            # Cache the result
            self._cache[file_path] = exif_data
            
            return exif_data
            
        except Exception as e:
            logging.error(f"Error extracting EXIF data from {file_path}: {e}")
            return {}
            
    def is_supported_image(self, file_path: str) -> bool:
        """
        Check if the file is a supported image format.
        
        Args:
            file_path: Path to the file
            
        Returns:
            bool: True if the file is a supported image format
        """
        supported_extensions = ['.jpg', '.jpeg', '.tif', '.tiff', '.png', '.heic', '.heif', '.nef', '.cr2', '.dng']
        _, ext = os.path.splitext(file_path.lower())
        return ext in supported_extensions
            
    def parse_datetime(self, date_str: str) -> Optional[datetime]:
        """
        Parse EXIF date string to Python datetime.
        
        Args:
            date_str: EXIF date string (e.g. '2023:07:15 14:22:36')
            
        Returns:
            Optional[datetime]: Parsed datetime or None if parsing fails
        """
        if not date_str:
            return None
            
        # EXIF dates are typically in the format 'YYYY:MM:DD HH:MM:SS'
        try:
            # Replace colons in the date part with dashes for better parsing
            normalized = re.sub(r'^(\d{4}):(\d{2}):(\d{2})', r'\1-\2-\3', str(date_str))
            return datetime.fromisoformat(normalized)
        except (ValueError, TypeError) as e:
            logging.warning(f"Failed to parse date '{date_str}': {e}")
            return None
            
    def extract_gps_data(self, exif_data: Dict[str, Any]) -> Optional[ExifGpsData]:
        """
        Extract and format GPS data from EXIF tags.
        
        Args:
            exif_data: Raw EXIF data dictionary
            
        Returns:
            Optional[ExifGpsData]: Structured GPS data or None if not available
        """
        gps_latitude = gps_longitude = gps_altitude = None
        gps_timestamp = None
        map_datum = None
        
        # Extract GPS data from EXIF
        try:
            if 'GPS GPSLatitude' in exif_data and 'GPS GPSLatitudeRef' in exif_data:
                lat = self._convert_to_decimal_degrees(exif_data['GPS GPSLatitude'], exif_data['GPS GPSLatitudeRef'])
                gps_latitude = lat
                
            if 'GPS GPSLongitude' in exif_data and 'GPS GPSLongitudeRef' in exif_data:
                lon = self._convert_to_decimal_degrees(exif_data['GPS GPSLongitude'], exif_data['GPS GPSLongitudeRef'])
                gps_longitude = lon
                
            if 'GPS GPSAltitude' in exif_data and 'GPS GPSAltitudeRef' in exif_data:
                alt_ref = exif_data['GPS GPSAltitudeRef']
                altitude = float(str(exif_data['GPS GPSAltitude']).split('/')[0])
                if alt_ref == '1':  # Below sea level
                    altitude = -altitude
                gps_altitude = altitude
                
            if ('GPS GPSTimeStamp' in exif_data and 
                'GPS GPSDateStamp' in exif_data):
                time_str = str(exif_data['GPS GPSTimeStamp'])
                date_str = str(exif_data['GPS GPSDateStamp'])
                gps_timestamp = self.parse_datetime(f"{date_str} {time_str}")
                
            if 'GPS GPSMapDatum' in exif_data:
                map_datum = str(exif_data['GPS GPSMapDatum'])
                
            # Only return a GPS model if we have at least latitude and longitude
            if gps_latitude is not None and gps_longitude is not None:
                return ExifGpsData(
                    latitude=gps_latitude,
                    longitude=gps_longitude,
                    altitude=gps_altitude,
                    timestamp=gps_timestamp,
                    map_datum=map_datum
                )
                
        except Exception as e:
            logging.warning(f"Error processing GPS data: {e}")
            
        return None
            
    def _convert_to_decimal_degrees(self, dms_values, ref) -> float:
        """
        Convert degrees/minutes/seconds to decimal degrees.
        
        Args:
            dms_values: Degrees, minutes, seconds values
            ref: Direction reference (N, S, E, W)
            
        Returns:
            float: Decimal degrees
        """
        # Parse the values based on different formats
        if isinstance(dms_values, str):
            # Try to parse from string like "[59, 12, 33.48]"
            match = re.search(r'\[(\d+),\s*(\d+),\s*([\d.]+)\]', dms_values)
            if match:
                degrees, minutes, seconds = map(float, match.groups())
            else:
                # Just return 0 if we can't parse it
                return 0.0
        elif hasattr(dms_values, '__iter__') and not isinstance(dms_values, str):
            # If it's an iterable like a list or tuple
            values = list(dms_values)
            if len(values) == 3:
                degrees, minutes, seconds = values
                # Handle fraction values
                if hasattr(degrees, 'numerator') and hasattr(degrees, 'denominator'):
                    degrees = degrees.numerator / degrees.denominator
                if hasattr(minutes, 'numerator') and hasattr(minutes, 'denominator'):
                    minutes = minutes.numerator / minutes.denominator
                if hasattr(seconds, 'numerator') and hasattr(seconds, 'denominator'):
                    seconds = seconds.numerator / seconds.denominator
            else:
                return 0.0
        else:
            # Just return 0 if we can't parse it
            return 0.0
            
        # Convert to decimal degrees
        decimal_degrees = float(degrees) + float(minutes) / 60 + float(seconds) / 3600
        
        # Apply direction
        ref = str(ref).upper()
        if ref in ['S', 'W']:
            decimal_degrees = -decimal_degrees
            
        return decimal_degrees
            
    def extract_camera_data(self, exif_data: Dict[str, Any]) -> Optional[ExifCameraData]:
        """
        Extract camera equipment information from EXIF data.
        
        Args:
            exif_data: Raw EXIF data dictionary
            
        Returns:
            Optional[ExifCameraData]: Camera information or None if not available
        """
        make = model = serial_number = None
        lens_make = lens_model = lens_serial = None
        
        if 'Image Make' in exif_data:
            make = str(exif_data['Image Make']).strip()
        elif 'Make' in exif_data:
            make = str(exif_data['Make']).strip()
            
        if 'Image Model' in exif_data:
            model = str(exif_data['Image Model']).strip()
        elif 'Model' in exif_data:
            model = str(exif_data['Model']).strip()
            
        if 'EXIF BodySerialNumber' in exif_data:
            serial_number = str(exif_data['EXIF BodySerialNumber']).strip()
            
        if 'EXIF LensMake' in exif_data:
            lens_make = str(exif_data['EXIF LensMake']).strip()
            
        if 'EXIF LensModel' in exif_data:
            lens_model = str(exif_data['EXIF LensModel']).strip()
        elif 'Lens Model' in exif_data:
            lens_model = str(exif_data['Lens Model']).strip()
            
        if 'EXIF LensSerialNumber' in exif_data:
            lens_serial = str(exif_data['EXIF LensSerialNumber']).strip()
            
        # Only return a camera model if we have at least make or model
        if make or model:
            return ExifCameraData(
                make=make,
                model=model,
                serial_number=serial_number,
                lens_make=lens_make,
                lens_model=lens_model,
                lens_serial_number=lens_serial
            )
            
        return None
            
    def extract_capture_settings(self, exif_data: Dict[str, Any]) -> Optional[ExifCaptureSettings]:
        """
        Extract capture settings from EXIF data.
        
        Args:
            exif_data: Raw EXIF data dictionary
            
        Returns:
            Optional[ExifCaptureSettings]: Capture settings or None if not available
        """
        datetime_original = datetime_digitized = None
        exposure_time = f_number = iso = None
        focal_length = exposure_bias = None
        metering_mode = flash = None
        
        # Extract date/time information
        if 'EXIF DateTimeOriginal' in exif_data:
            datetime_original = self.parse_datetime(str(exif_data['EXIF DateTimeOriginal']))
            
        if 'EXIF DateTimeDigitized' in exif_data:
            datetime_digitized = self.parse_datetime(str(exif_data['EXIF DateTimeDigitized']))
            
        # Extract exposure information
        if 'EXIF ExposureTime' in exif_data:
            exposure_str = str(exif_data['EXIF ExposureTime'])
            # Handle fraction format like "1/125"
            if '/' in exposure_str:
                num, denom = exposure_str.split('/')
                exposure_time = float(num) / float(denom)
            else:
                try:
                    exposure_time = float(exposure_str)
                except ValueError:
                    exposure_time = None
                    
        if 'EXIF FNumber' in exif_data:
            fnumber_str = str(exif_data['EXIF FNumber'])
            # Handle fraction format like "4/1"
            if '/' in fnumber_str:
                num, denom = fnumber_str.split('/')
                f_number = float(num) / float(denom)
            else:
                try:
                    f_number = float(fnumber_str)
                except ValueError:
                    f_number = None
                    
        if 'EXIF ISOSpeedRatings' in exif_data:
            iso_str = str(exif_data['EXIF ISOSpeedRatings'])
            try:
                iso = int(iso_str)
            except ValueError:
                iso = None
                
        if 'EXIF FocalLength' in exif_data:
            focal_str = str(exif_data['EXIF FocalLength'])
            # Handle fraction format like "50/1"
            if '/' in focal_str:
                num, denom = focal_str.split('/')
                focal_length = float(num) / float(denom)
            else:
                try:
                    focal_length = float(focal_str)
                except ValueError:
                    focal_length = None
                    
        if 'EXIF ExposureBiasValue' in exif_data:
            bias_str = str(exif_data['EXIF ExposureBiasValue'])
            # Handle fraction format like "0/1"
            if '/' in bias_str:
                num, denom = bias_str.split('/')
                exposure_bias = float(num) / float(denom)
            else:
                try:
                    exposure_bias = float(bias_str)
                except ValueError:
                    exposure_bias = None
                    
        if 'EXIF MeteringMode' in exif_data:
            # Map metering mode codes to readable values
            metering_codes = {
                '0': 'Unknown',
                '1': 'Average',
                '2': 'Center-weighted average',
                '3': 'Spot',
                '4': 'Multi-spot',
                '5': 'Pattern',
                '6': 'Partial',
                '255': 'Other'
            }
            metering_str = str(exif_data['EXIF MeteringMode'])
            metering_mode = metering_codes.get(metering_str, metering_str)
            
        if 'EXIF Flash' in exif_data:
            # Map flash codes to readable values
            flash_codes = {
                '0': 'No Flash',
                '1': 'Flash',
                '5': 'Flash, no strobe return',
                '7': 'Flash, strobe return',
                '9': 'Compulsory Flash',
                '13': 'Compulsory Flash, no strobe return',
                '15': 'Compulsory Flash, strobe return',
                '16': 'No Flash, compulsory',
                '24': 'No Flash, auto',
                '25': 'Flash, auto',
                '29': 'Flash, auto, no strobe return',
                '31': 'Flash, auto, strobe return',
                '32': 'No Flash function',
                '65': 'Flash, red-eye',
                '69': 'Flash, red-eye, no strobe return',
                '71': 'Flash, red-eye, strobe return',
                '73': 'Compulsory Flash, red-eye',
                '77': 'Compulsory Flash, red-eye, no strobe return',
                '79': 'Compulsory Flash, red-eye, strobe return',
                '89': 'Flash, auto, red-eye',
                '93': 'Flash, auto, red-eye, no strobe return',
                '95': 'Flash, auto, red-eye, strobe return'
            }
            flash_str = str(exif_data['EXIF Flash'])
            flash = flash_codes.get(flash_str, flash_str)
            
        # Only return a capture settings model if we have at least one setting
        if (datetime_original or exposure_time or f_number or 
            iso or focal_length):
            return ExifCaptureSettings(
                datetime_original=datetime_original,
                datetime_digitized=datetime_digitized,
                exposure_time=exposure_time,
                f_number=f_number,
                iso=iso,
                focal_length=focal_length,
                exposure_bias=exposure_bias,
                metering_mode=metering_mode,
                flash=flash
            )
            
        return None
            
    def extract_image_info(self, exif_data: Dict[str, Any]) -> Optional[ExifImageInfo]:
        """
        Extract image information from EXIF data.
        
        Args:
            exif_data: Raw EXIF data dictionary
            
        Returns:
            Optional[ExifImageInfo]: Image information or None if not available
        """
        width = height = bits_per_sample = None
        compression = photometric_interpretation = None
        orientation = samples_per_pixel = None
        planar_configuration = software = None
        artist = copyright_info = user_comment = None
        
        # Extract image dimensions
        if 'ImageWidth' in exif_data:
            try:
                width = int(exif_data['ImageWidth'])
            except (ValueError, TypeError):
                width = None
                
        if 'ImageHeight' in exif_data:
            try:
                height = int(exif_data['ImageHeight'])
            except (ValueError, TypeError):
                height = None
                
        # Extract technical image information
        if 'EXIF BitsPerSample' in exif_data:
            bits_str = str(exif_data['EXIF BitsPerSample'])
            try:
                # Could be a list like "[8, 8, 8]" for RGB
                if bits_str.startswith('['):
                    bits_per_sample = int(bits_str.strip('[]').split(',')[0])
                else:
                    bits_per_sample = int(bits_str)
            except (ValueError, IndexError):
                bits_per_sample = None
                
        if 'EXIF Compression' in exif_data:
            compression_codes = {
                '1': 'Uncompressed',
                '2': 'CCITT 1D',
                '3': 'T4/Group 3 Fax',
                '4': 'T6/Group 4 Fax',
                '5': 'LZW',
                '6': 'JPEG (old style)',
                '7': 'JPEG',
                '8': 'Adobe Deflate',
                '9': 'JBIG B&W',
                '10': 'JBIG Color',
                '32773': 'PackBits',
                '32946': 'Deflate',
                '34712': 'JPEG 2000',
            }
            compression_str = str(exif_data['EXIF Compression'])
            compression = compression_codes.get(compression_str, compression_str)
            
        if 'EXIF PhotometricInterpretation' in exif_data:
            interpretation_codes = {
                '0': 'WhiteIsZero',
                '1': 'BlackIsZero',
                '2': 'RGB',
                '3': 'RGB Palette',
                '4': 'Transparency Mask',
                '5': 'CMYK',
                '6': 'YCbCr',
                '8': 'CIELab',
                '9': 'ICCLab',
                '10': 'ITULab',
                '32844': 'Color Filter Array',
                '32845': 'Pixar LogL',
                '32846': 'Pixar LogLuv',
                '34892': 'Linear Raw'
            }
            interp_str = str(exif_data['EXIF PhotometricInterpretation'])
            photometric_interpretation = interpretation_codes.get(interp_str, interp_str)
            
        if 'EXIF Orientation' in exif_data:
            orientation_codes = {
                '1': 'Normal',
                '2': 'Mirrored horizontally',
                '3': 'Rotated 180°',
                '4': 'Mirrored vertically',
                '5': 'Mirrored horizontally and rotated 270° CW',
                '6': 'Rotated 90° CW',
                '7': 'Mirrored horizontally and rotated 90° CW',
                '8': 'Rotated 270° CW'
            }
            orientation_str = str(exif_data['EXIF Orientation'])
            orientation = orientation_codes.get(orientation_str, orientation_str)
            
        if 'EXIF SamplesPerPixel' in exif_data:
            try:
                samples_per_pixel = int(str(exif_data['EXIF SamplesPerPixel']))
            except ValueError:
                samples_per_pixel = None
                
        if 'EXIF PlanarConfiguration' in exif_data:
            planar_codes = {
                '1': 'Chunky format',
                '2': 'Planar format'
            }
            planar_str = str(exif_data['EXIF PlanarConfiguration'])
            planar_configuration = planar_codes.get(planar_str, planar_str)
            
        # Extract metadata information
        if 'EXIF Software' in exif_data:
            software = str(exif_data['EXIF Software']).strip()
        elif 'Software' in exif_data:
            software = str(exif_data['Software']).strip()
            
        if 'EXIF Artist' in exif_data:
            artist = str(exif_data['EXIF Artist']).strip()
        elif 'Image Artist' in exif_data:
            artist = str(exif_data['Image Artist']).strip()
        elif 'Artist' in exif_data:
            artist = str(exif_data['Artist']).strip()
            
        if 'EXIF Copyright' in exif_data:
            copyright_info = str(exif_data['EXIF Copyright']).strip()
        elif 'Image Copyright' in exif_data:
            copyright_info = str(exif_data['Image Copyright']).strip()
        elif 'Copyright' in exif_data:
            copyright_info = str(exif_data['Copyright']).strip()
            
        if 'EXIF UserComment' in exif_data:
            user_comment = str(exif_data['EXIF UserComment']).strip()
            
        # Only return an image info model if we have at least width/height
        if width is not None and height is not None:
            return ExifImageInfo(
                width=width,
                height=height,
                bits_per_sample=bits_per_sample,
                compression=compression,
                photometric_interpretation=photometric_interpretation,
                orientation=orientation,
                samples_per_pixel=samples_per_pixel,
                planar_configuration=planar_configuration,
                software=software,
                artist=artist,
                copyright=copyright_info,
                user_comment=user_comment
            )
            
        return None
            
    def process_exif_data(self, exif_data: Dict[str, Any]) -> ExifDataModel:
        """
        Process raw EXIF data into structured ExifDataModel.
        
        Args:
            exif_data: Raw EXIF data dictionary
            
        Returns:
            ExifDataModel: Structured EXIF data model
        """
        # Extract structured data components
        camera = self.extract_camera_data(exif_data)
        capture_settings = self.extract_capture_settings(exif_data)
        gps = self.extract_gps_data(exif_data)
        image_info = self.extract_image_info(exif_data)
        
        # Create record and semantic attributes
        record = IndalekoRecordDataModel(
            SourceIdentifier={
                "Identifier": str(self._provider_id),
                "Version": "1.0",
            },
            Timestamp=datetime.now().isoformat(),
            Attributes={},
            Data=""
        )
        
        # Create semantic attributes for relevant EXIF data
        semantic_attributes = []
        
        # Add camera information attributes if available
        if camera:
            if camera.make:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_CAMERA_MAKE,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_CAMERA_MAKE
                        ),
                        Value=camera.make
                    )
                )
                
            if camera.model:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_CAMERA_MODEL,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_CAMERA_MODEL
                        ),
                        Value=camera.model
                    )
                )
                
            if camera.lens_model:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_LENS_MODEL,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_LENS_MODEL
                        ),
                        Value=camera.lens_model
                    )
                )
                
        # Add GPS attributes if available
        if gps and gps.latitude is not None and gps.longitude is not None:
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=ExifCharacteristics.SEMANTIC_EXIF_GPS_LATITUDE,
                        Label=ExifCharacteristics.SEMANTIC_EXIF_GPS_LATITUDE
                    ),
                    Value=str(gps.latitude)
                )
            )
            
            semantic_attributes.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=ExifCharacteristics.SEMANTIC_EXIF_GPS_LONGITUDE,
                        Label=ExifCharacteristics.SEMANTIC_EXIF_GPS_LONGITUDE
                    ),
                    Value=str(gps.longitude)
                )
            )
            
        # Add capture settings attributes if available
        if capture_settings:
            if capture_settings.datetime_original:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_DATETIME_ORIGINAL,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_DATETIME_ORIGINAL
                        ),
                        Value=capture_settings.datetime_original.isoformat()
                    )
                )
                
            if capture_settings.iso:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_ISO,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_ISO
                        ),
                        Value=str(capture_settings.iso)
                    )
                )
                
        # Add image information attributes if available
        if image_info:
            if image_info.width and image_info.height:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_IMAGE_WIDTH,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_IMAGE_WIDTH
                        ),
                        Value=str(image_info.width)
                    )
                )
                
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_IMAGE_HEIGHT,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_IMAGE_HEIGHT
                        ),
                        Value=str(image_info.height)
                    )
                )
                
            if image_info.software:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_SOFTWARE,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_SOFTWARE
                        ),
                        Value=image_info.software
                    )
                )
                
            if image_info.artist:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_ARTIST,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_ARTIST
                        ),
                        Value=image_info.artist
                    )
                )
                
            if image_info.copyright:
                semantic_attributes.append(
                    IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=ExifCharacteristics.SEMANTIC_EXIF_COPYRIGHT,
                            Label=ExifCharacteristics.SEMANTIC_EXIF_COPYRIGHT
                        ),
                        Value=image_info.copyright
                    )
                )
                
        # Create the full ExifDataModel
        exif_model = ExifDataModel(
            Record=record,
            Timestamp=datetime.now(),
            ObjectIdentifier=uuid.uuid4(),  # This would be replaced with actual object ID
            RelatedObjects=[uuid.uuid4()],  # This would be replaced with actual object ID
            SemanticAttributes=semantic_attributes,
            exif_data_id=uuid.uuid4(),
            raw_exif=exif_data,
            camera=camera,
            capture_settings=capture_settings,
            gps=gps,
            image_info=image_info
        )
        
        return exif_model
        
    def extract_exif_from_file(self, file_path: str, object_id: uuid.UUID) -> Optional[ExifDataModel]:
        """
        Extract EXIF data from a file and create an ExifDataModel.
        
        Args:
            file_path: Path to the image file
            object_id: UUID of the file object in Indaleko
            
        Returns:
            Optional[ExifDataModel]: Structured EXIF data or None if extraction fails
        """
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            return None
            
        if not self.is_supported_image(file_path):
            logging.info(f"Not a supported image file: {file_path}")
            return None
            
        # Extract raw EXIF data
        raw_exif = self.extract_exif_data(file_path)
        if not raw_exif:
            logging.info(f"No EXIF data found in file: {file_path}")
            return None
            
        # Process the EXIF data
        exif_model = self.process_exif_data(raw_exif)
        
        # Update with the correct object ID
        exif_model.ObjectIdentifier = object_id
        exif_model.RelatedObjects = [object_id]
        
        # Store for later retrieval
        self._exif_data = exif_model
        
        return exif_model
        

# Unit tests
import unittest

class TestExifCollector(unittest.TestCase):
    """Test the ExifCollector class."""
    
    def setUp(self):
        """Set up the test environment."""
        self.collector = ExifCollector()
        
    def test_init(self):
        """Test initialization."""
        self.assertEqual(self.collector.get_collector_name(), "EXIF Metadata Collector")
        self.assertEqual(self.collector.get_collector_id(), uuid.UUID("3fa85f64-5717-4562-b3fc-2c963f66afa6"))
        
    def test_is_supported_image(self):
        """Test supported image detection."""
        self.assertTrue(self.collector.is_supported_image("test.jpg"))
        self.assertTrue(self.collector.is_supported_image("test.jpeg"))
        self.assertTrue(self.collector.is_supported_image("test.tif"))
        self.assertTrue(self.collector.is_supported_image("test.png"))
        self.assertFalse(self.collector.is_supported_image("test.txt"))
        self.assertFalse(self.collector.is_supported_image("test.pdf"))
        
    def test_parse_datetime(self):
        """Test EXIF datetime parsing."""
        dt = self.collector.parse_datetime("2023:07:15 14:22:36")
        self.assertEqual(dt.year, 2023)
        self.assertEqual(dt.month, 7)
        self.assertEqual(dt.day, 15)
        self.assertEqual(dt.hour, 14)
        self.assertEqual(dt.minute, 22)
        self.assertEqual(dt.second, 36)
        
        # Test invalid datetime
        self.assertIsNone(self.collector.parse_datetime("Invalid date"))
        
    def test_convert_to_decimal_degrees(self):
        """Test conversion of DMS to decimal degrees."""
        # Test with North latitude
        lat = self.collector._convert_to_decimal_degrees([10, 20, 30], "N")
        self.assertAlmostEqual(lat, 10 + 20/60 + 30/3600)
        
        # Test with South latitude
        lat = self.collector._convert_to_decimal_degrees([10, 20, 30], "S")
        self.assertAlmostEqual(lat, -(10 + 20/60 + 30/3600))
        
        # Test with East longitude
        lon = self.collector._convert_to_decimal_degrees([10, 20, 30], "E")
        self.assertAlmostEqual(lon, 10 + 20/60 + 30/3600)
        
        # Test with West longitude
        lon = self.collector._convert_to_decimal_degrees([10, 20, 30], "W")
        self.assertAlmostEqual(lon, -(10 + 20/60 + 30/3600))
        

if __name__ == "__main__":
    unittest.main()