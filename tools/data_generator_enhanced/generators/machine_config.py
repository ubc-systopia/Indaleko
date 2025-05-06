#!/usr/bin/env python3
"""
Machine Configuration generator.

This module provides implementation for generating realistic machine 
configuration records for various device types (desktop, laptop, mobile).
"""

import hashlib
import json
import logging
import os
import random
import string
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set, Tuple, Union, cast

from data_models.base import IndalekoBaseModel
from data_models.machine_config import IndalekoMachineConfigDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from db.db_collections import IndalekoDBCollections
from db.db_config import IndalekoDBConfig
from platforms.data_models.hardware import Hardware
from platforms.data_models.software import Software
from pydantic import Field

from tools.data_generator_enhanced.generators.base import BaseGenerator
from tools.data_generator_enhanced.utils.statistical import Distribution


class MachineConfigGenerator(BaseGenerator):
    """Base class for machine configuration generators."""
    
    def __init__(self, config: Dict[str, Any], seed: Optional[int] = None):
        """Initialize the machine config generator.
        
        Args:
            config: Configuration dictionary for the generator
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)


class MachineConfigGeneratorImpl(MachineConfigGenerator):
    """Generator for machine configuration metadata with direct database integration."""
    
    def __init__(self, config: Dict[str, Any], db_config: Optional[IndalekoDBConfig] = None, seed: Optional[int] = None):
        """Initialize the machine configuration generator.
        
        Args:
            config: Configuration dictionary for the generator
            db_config: Database configuration for direct insertion
            seed: Optional random seed for reproducible generation
        """
        super().__init__(config, seed)
        
        # Set random seed if provided
        if seed is not None:
            random.seed(seed)
        
        # Initialize database connection
        self.db_config = db_config or IndalekoDBConfig()
        self.db_config.setup_database(self.db_config.config["database"]["database"])
        
        # Make sure the machine config collection exists
        self._ensure_collections_exist()
        
        # Initialize device templates
        self._initialize_device_templates()
        
        # Truth generator tracks
        self.truth_list = []
    
    def _ensure_collections_exist(self):
        """Ensure required collections exist in the database."""
        try:
            if not self.db_config.db.has_collection(IndalekoDBCollections.Indaleko_MachineConfig_Collection):
                self.logger.info(f"Creating MachineConfig collection")
                self.db_config.db.create_collection(IndalekoDBCollections.Indaleko_MachineConfig_Collection)
        except Exception as e:
            self.logger.error(f"Error ensuring collections exist: {e}")
            raise
    
    def _initialize_device_templates(self):
        """Initialize device templates for different device types."""
        # Desktop computers
        self.desktop_templates = [
            {
                "hardware": {
                    "CPU": "x86_64",
                    "Version": "Intel Core i7-12700K",
                    "Cores": 12,
                    "Threads": 20
                },
                "software": {
                    "OS": "Windows",
                    "Version": "11 Pro",
                    "Architecture": "x64",
                    "Hostname": "DESKTOP-"
                }
            },
            {
                "hardware": {
                    "CPU": "x86_64",
                    "Version": "AMD Ryzen 9 5950X",
                    "Cores": 16,
                    "Threads": 32
                },
                "software": {
                    "OS": "Windows",
                    "Version": "10 Enterprise",
                    "Architecture": "x64",
                    "Hostname": "DESKTOP-"
                }
            },
            {
                "hardware": {
                    "CPU": "x86_64",
                    "Version": "Intel Core i9-13900K",
                    "Cores": 24,
                    "Threads": 32
                },
                "software": {
                    "OS": "Linux",
                    "Version": "Ubuntu 22.04 LTS",
                    "Architecture": "x64",
                    "Hostname": "ubuntu-ws-"
                }
            },
            {
                "hardware": {
                    "CPU": "arm64",
                    "Version": "Apple M1 Ultra",
                    "Cores": 20,
                    "Threads": 20
                },
                "software": {
                    "OS": "macOS",
                    "Version": "Ventura 13.5",
                    "Architecture": "arm64",
                    "Hostname": "Mac-Studio-"
                }
            }
        ]
        
        # Laptop computers
        self.laptop_templates = [
            {
                "hardware": {
                    "CPU": "x86_64",
                    "Version": "Intel Core i7-1165G7",
                    "Cores": 4,
                    "Threads": 8
                },
                "software": {
                    "OS": "Windows",
                    "Version": "11 Home",
                    "Architecture": "x64",
                    "Hostname": "LAPTOP-"
                }
            },
            {
                "hardware": {
                    "CPU": "x86_64",
                    "Version": "AMD Ryzen 7 5800U",
                    "Cores": 8,
                    "Threads": 16
                },
                "software": {
                    "OS": "Windows",
                    "Version": "10 Pro",
                    "Architecture": "x64",
                    "Hostname": "LAPTOP-"
                }
            },
            {
                "hardware": {
                    "CPU": "arm64",
                    "Version": "Apple M2 Pro",
                    "Cores": 10,
                    "Threads": 10
                },
                "software": {
                    "OS": "macOS",
                    "Version": "Ventura 13.4",
                    "Architecture": "arm64",
                    "Hostname": "MacBook-Pro-"
                }
            },
            {
                "hardware": {
                    "CPU": "x86_64",
                    "Version": "Intel Core i5-1135G7",
                    "Cores": 4,
                    "Threads": 8
                },
                "software": {
                    "OS": "Linux",
                    "Version": "Fedora 38",
                    "Architecture": "x64",
                    "Hostname": "fedora-"
                }
            }
        ]
        
        # Mobile devices (smartphones and tablets)
        self.mobile_templates = [
            {
                "hardware": {
                    "CPU": "arm64",
                    "Version": "Apple A16 Bionic",
                    "Cores": 6,
                    "Threads": 6
                },
                "software": {
                    "OS": "iOS",
                    "Version": "16.5.1",
                    "Architecture": "arm64",
                    "Hostname": "iPhone-"
                }
            },
            {
                "hardware": {
                    "CPU": "arm64",
                    "Version": "Apple M2",
                    "Cores": 8,
                    "Threads": 8
                },
                "software": {
                    "OS": "iPadOS",
                    "Version": "16.5",
                    "Architecture": "arm64",
                    "Hostname": "iPad-"
                }
            },
            {
                "hardware": {
                    "CPU": "arm64",
                    "Version": "Qualcomm Snapdragon 8 Gen 2",
                    "Cores": 8,
                    "Threads": 8
                },
                "software": {
                    "OS": "Android",
                    "Version": "13",
                    "Architecture": "arm64",
                    "Hostname": "Galaxy-S23-"
                }
            },
            {
                "hardware": {
                    "CPU": "arm64",
                    "Version": "Google Tensor G2",
                    "Cores": 8,
                    "Threads": 8
                },
                "software": {
                    "OS": "Android",
                    "Version": "13",
                    "Architecture": "arm64",
                    "Hostname": "Pixel-7-"
                }
            }
        ]
    
    def generate(self, count: int) -> List[Dict[str, Any]]:
        """Generate the specified number of machine configuration records.
        
        Args:
            count: Number of records to generate
            
        Returns:
            List of generated machine configuration records
        """
        self.logger.info(f"Generating {count} machine configuration records")
        
        # Calculate distribution of device types (40% desktop, 40% laptop, 20% mobile)
        desktop_count = int(count * 0.4)
        laptop_count = int(count * 0.4)
        mobile_count = count - desktop_count - laptop_count
        
        # Generate records for each device type
        desktop_records = self._generate_device_records("desktop", desktop_count)
        laptop_records = self._generate_device_records("laptop", laptop_count)
        mobile_records = self._generate_device_records("mobile", mobile_count)
        
        # Combine all records
        machine_config_records = desktop_records + laptop_records + mobile_records
        
        # Insert records into database
        self._insert_machine_config_records(machine_config_records)
        
        return machine_config_records
    
    def _generate_device_records(self, device_type: str, count: int) -> List[Dict[str, Any]]:
        """Generate machine configuration records for a specific device type.
        
        Args:
            device_type: Type of device (desktop, laptop, mobile)
            count: Number of records to generate
            
        Returns:
            List of generated machine configuration records
        """
        records = []
        
        # Select the appropriate template list
        if device_type == "desktop":
            templates = self.desktop_templates
        elif device_type == "laptop":
            templates = self.laptop_templates
        elif device_type == "mobile":
            templates = self.mobile_templates
        else:
            raise ValueError(f"Unknown device type: {device_type}")
        
        for _ in range(count):
            # Choose a random template
            template = random.choice(templates)
            
            # Generate a hostname with a random suffix
            hostname_suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            hostname = template["software"]["Hostname"] + hostname_suffix
            
            # Create unique machine UUID
            machine_uuid = str(uuid.uuid4())
            
            # Create hardware config
            hardware = Hardware(
                CPU=template["hardware"]["CPU"],
                Version=template["hardware"]["Version"],
                Cores=template["hardware"]["Cores"],
                Threads=template["hardware"]["Threads"]
            )
            
            # Create software config
            software = Software(
                OS=template["software"]["OS"],
                Version=template["software"]["Version"],
                Hostname=hostname,
                Architecture=template["software"]["Architecture"]
            )
            
            # Create source identifier
            source_identifier = IndalekoSourceIdentifierDataModel(
                Identifier=str(uuid.uuid4()),
                Version="1.0",
                Description=f"Generated {device_type} configuration"
            )
            
            # Create timestamp for when the configuration was captured
            # Random timestamp within the last 30 days
            days_ago = random.randint(0, 30)
            timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
            captured = IndalekoTimestampDataModel(
                Timestamp=timestamp.isoformat()
            )
            
            # Create record
            record = IndalekoRecordDataModel(
                SourceIdentifier=source_identifier.dict(),
                Timestamp=timestamp.isoformat()
            )
            
            # Create machine config record
            machine_config = IndalekoMachineConfigDataModel(
                Record=record.dict(),
                Captured=captured.dict(),
                Hardware=hardware.dict(),
                Software=software.dict(),
                MachineUUID=machine_uuid
            )
            
            # Create document with _key for the database
            document = machine_config.dict()
            document["_key"] = machine_uuid
            
            # Add device type as an additional field for filtering
            document["DeviceType"] = device_type
            
            records.append(document)
        
        return records
    
    def _insert_machine_config_records(self, records: List[Dict[str, Any]]) -> None:
        """Insert machine configuration records into the database.
        
        Args:
            records: List of machine configuration records to insert
        """
        if not records:
            self.logger.info("No machine configuration records to insert")
            return
        
        try:
            collection = self.db_config.db.collection(IndalekoDBCollections.Indaleko_MachineConfig_Collection)
            self.logger.info(f"Inserting {len(records)} machine configuration records into database")
            
            # Insert records one by one for better error handling
            success_count = 0
            for record in records:
                try:
                    # Check if record already exists
                    if collection.has(record["_key"]):
                        self.logger.debug(f"Machine configuration record {record['_key']} already exists, skipping")
                        continue
                    
                    # Insert the record
                    collection.insert(record)
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"Error inserting machine configuration record {record.get('_key')}: {e}")
            
            self.logger.info(f"Successfully inserted {success_count} machine configuration records")
        except Exception as e:
            self.logger.error(f"Error inserting machine configuration records: {e}")
            raise
    
    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth machine configuration records based on specific criteria.
        
        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy
            
        Returns:
            List of generated truth machine configuration records
        """
        self.logger.info(f"Generating {count} truth machine configuration records")
        
        # Extract criteria for machine configuration generation
        machine_criteria = criteria.get("machine_criteria", {})
        device_type = machine_criteria.get("device_type", "mobile")  # Default to mobile for truth records
        os_type = machine_criteria.get("os", "iOS")  # Default to iOS for truth records
        
        records = []
        
        # Select the appropriate template list
        if device_type == "desktop":
            templates = [t for t in self.desktop_templates if t["software"]["OS"] == os_type]
            if not templates:
                templates = self.desktop_templates
        elif device_type == "laptop":
            templates = [t for t in self.laptop_templates if t["software"]["OS"] == os_type]
            if not templates:
                templates = self.laptop_templates
        elif device_type == "mobile":
            templates = [t for t in self.mobile_templates if t["software"]["OS"] == os_type]
            if not templates:
                templates = self.mobile_templates
        else:
            raise ValueError(f"Unknown device type: {device_type}")
        
        for i in range(count):
            # Choose a template matching the criteria
            template = random.choice(templates)
            
            # Generate a hostname with a deterministic suffix for truth records
            hostname_suffix = f"TRUTH{i:03d}"
            hostname = template["software"]["Hostname"] + hostname_suffix
            
            # Create unique machine UUID
            machine_uuid = str(uuid.uuid4())
            
            # Create hardware config
            hardware = Hardware(
                CPU=template["hardware"]["CPU"],
                Version=template["hardware"]["Version"],
                Cores=template["hardware"]["Cores"],
                Threads=template["hardware"]["Threads"]
            )
            
            # Create software config - use criteria values if provided
            software = Software(
                OS=machine_criteria.get("os", template["software"]["OS"]),
                Version=machine_criteria.get("version", template["software"]["Version"]),
                Hostname=hostname,
                Architecture=template["software"]["Architecture"]
            )
            
            # Create source identifier
            source_identifier = IndalekoSourceIdentifierDataModel(
                Identifier=str(uuid.uuid4()),
                Version="1.0",
                Description=f"Truth {device_type} configuration for testing"
            )
            
            # Create timestamp for when the configuration was captured
            # Use a specific timestamp for truth records for deterministic queries
            days_ago = machine_criteria.get("days_ago", 7)
            timestamp = datetime.now(timezone.utc) - timedelta(days=days_ago)
            captured = IndalekoTimestampDataModel(
                Timestamp=timestamp.isoformat()
            )
            
            # Create record
            record = IndalekoRecordDataModel(
                SourceIdentifier=source_identifier.dict(),
                Timestamp=timestamp.isoformat()
            )
            
            # Create machine config record
            machine_config = IndalekoMachineConfigDataModel(
                Record=record.dict(),
                Captured=captured.dict(),
                Hardware=hardware.dict(),
                Software=software.dict(),
                MachineUUID=machine_uuid
            )
            
            # Create document with _key for the database
            document = machine_config.dict()
            document["_key"] = machine_uuid
            
            # Add device type as an additional field for filtering
            document["DeviceType"] = device_type
            
            # Add truth-specific fields
            document["TruthRecord"] = True
            document["TruthCriteria"] = machine_criteria
            
            records.append(document)
            
            # Add to truth list
            self.truth_list.append(machine_uuid)
        
        # Insert truth records into database
        self._insert_machine_config_records(records)
        
        return records
