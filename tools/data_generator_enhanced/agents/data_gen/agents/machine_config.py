"""
Machine configuration generator agent.

This module provides an agent for generating realistic machine
configuration metadata for the Indaleko system, supporting
cross-device testing scenarios.
"""

import json
import logging
import random
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from db.db_collections import IndalekoDBCollections
from data_models.machine_config import IndalekoMachineConfigDataModel

from ..core.llm import LLMProvider
from ..core.tools import ToolRegistry
from .base import DomainAgent


class MachineConfigGeneratorAgent(DomainAgent):
    """Agent for generating machine configuration metadata."""

    def __init__(self, llm_provider: LLMProvider, tool_registry: ToolRegistry, config: Optional[Dict[str, Any]] = None):
        """Initialize the machine configuration generator agent.

        Args:
            llm_provider: LLM provider instance
            tool_registry: Tool registry instance
            config: Optional agent configuration
        """
        super().__init__(llm_provider, tool_registry, config)
        self.collection_name = IndalekoDBCollections.Indaleko_MachineConfig_Collection
        self.logger = logging.getLogger(self.__class__.__name__)

        # Device types and their proportions
        self.device_types = {
            "desktop": 0.3,
            "laptop": 0.4,
            "mobile": 0.2,
            "tablet": 0.1
        }

        # Operating systems by device type
        self.os_by_device = {
            "desktop": {
                "Windows": 0.65,
                "macOS": 0.25,
                "Linux": 0.1
            },
            "laptop": {
                "Windows": 0.60,
                "macOS": 0.35,
                "Linux": 0.05
            },
            "mobile": {
                "iOS": 0.45,
                "Android": 0.55
            },
            "tablet": {
                "iPadOS": 0.4,
                "Android": 0.5,
                "Windows": 0.1
            }
        }

        # CPU models by device type and OS
        self.cpu_models = {
            "desktop": {
                "Windows": ["Intel Core i9-13900K", "Intel Core i7-13700K", "Intel Core i5-13600K",
                           "AMD Ryzen 9 7950X", "AMD Ryzen 7 7700X", "AMD Ryzen 5 7600X"],
                "macOS": ["Apple M1 Ultra", "Apple M1 Max", "Apple M2 Max", "Apple M2 Pro", "Intel Core i9"],
                "Linux": ["Intel Core i7-13700K", "AMD Ryzen 9 7950X", "AMD Ryzen 7 7700X", "Intel Xeon E-2388G"]
            },
            "laptop": {
                "Windows": ["Intel Core i7-1370P", "Intel Core i5-1340P", "AMD Ryzen 9 7940HS", "AMD Ryzen 7 7840U"],
                "macOS": ["Apple M2 Pro", "Apple M2", "Apple M1 Pro", "Apple M1"],
                "Linux": ["Intel Core i7-1370P", "AMD Ryzen 7 7840U"]
            },
            "mobile": {
                "iOS": ["Apple A16 Bionic", "Apple A15 Bionic", "Apple A14 Bionic"],
                "Android": ["Qualcomm Snapdragon 8 Gen 2", "MediaTek Dimensity 9200", "Google Tensor G2", "Samsung Exynos 2300"]
            },
            "tablet": {
                "iPadOS": ["Apple M2", "Apple M1", "Apple A15 Bionic"],
                "Android": ["Qualcomm Snapdragon 8 Gen 2", "MediaTek Dimensity 9200"],
                "Windows": ["Intel Core i7-1370P", "Intel Core i5-1340P"]
            }
        }

        # GPU models by device type and OS
        self.gpu_models = {
            "desktop": {
                "Windows": ["NVIDIA GeForce RTX 4090", "NVIDIA GeForce RTX 4080", "AMD Radeon RX 7900 XTX",
                           "NVIDIA GeForce RTX 4070 Ti", "AMD Radeon RX 7900 XT", "Intel Arc A770"],
                "macOS": ["Apple M1 Ultra GPU", "Apple M1 Max GPU", "Apple M2 Max GPU", "AMD Radeon Pro"],
                "Linux": ["NVIDIA GeForce RTX 4080", "AMD Radeon RX 7900 XTX", "Intel Arc A770"]
            },
            "laptop": {
                "Windows": ["NVIDIA GeForce RTX 4080 Mobile", "NVIDIA GeForce RTX 4070 Mobile", "AMD Radeon RX 6800M", "Intel Iris Xe Graphics"],
                "macOS": ["Apple M2 Pro GPU", "Apple M2 GPU", "Apple M1 Pro GPU", "Apple M1 GPU"],
                "Linux": ["NVIDIA GeForce RTX 4060 Mobile", "AMD Radeon RX 6700M", "Intel Iris Xe Graphics"]
            },
            "mobile": {
                "iOS": ["Apple GPU (Integrated)", "Apple A16 GPU"],
                "Android": ["Adreno 740", "Adreno 730", "Mali-G715", "Mali-G710"]
            },
            "tablet": {
                "iPadOS": ["Apple M2 GPU", "Apple M1 GPU", "Apple GPU (Integrated)"],
                "Android": ["Adreno 740", "Adreno 730", "Mali-G715"],
                "Windows": ["Intel Iris Xe Graphics", "NVIDIA GeForce RTX 3050 Mobile"]
            }
        }

        # RAM configurations (in GB) by device type
        self.ram_configs = {
            "desktop": [16, 32, 64, 128],
            "laptop": [8, 16, 32, 64],
            "mobile": [4, 6, 8, 12],
            "tablet": [4, 6, 8, 16]
        }

        # Storage configurations (in GB) by device type
        self.storage_configs = {
            "desktop": [512, 1024, 2048, 4096],
            "laptop": [256, 512, 1024, 2048],
            "mobile": [64, 128, 256, 512],
            "tablet": [64, 128, 256, 512]
        }

        # Device models by type and OS
        self.device_models = {
            "desktop": {
                "Windows": ["Dell XPS Desktop", "HP Omen", "Alienware Aurora", "Lenovo Legion Tower", "Custom Build"],
                "macOS": ["Mac Studio", "Mac Pro", "iMac", "Mac mini"],
                "Linux": ["System76 Thelio", "Dell XPS Desktop", "Custom Build"]
            },
            "laptop": {
                "Windows": ["Dell XPS 15", "HP Spectre x360", "Lenovo ThinkPad X1 Carbon", "Microsoft Surface Laptop", "ASUS ROG Zephyrus"],
                "macOS": ["MacBook Pro 16\"", "MacBook Pro 14\"", "MacBook Air M2", "MacBook Air M1"],
                "Linux": ["System76 Lemur Pro", "Dell XPS 13 Developer Edition", "Lenovo ThinkPad X1 Carbon"]
            },
            "mobile": {
                "iOS": ["iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15", "iPhone 14 Pro", "iPhone 14"],
                "Android": ["Samsung Galaxy S23 Ultra", "Google Pixel 7 Pro", "OnePlus 11", "Xiaomi 13 Pro", "Samsung Galaxy Z Fold 4"]
            },
            "tablet": {
                "iPadOS": ["iPad Pro 12.9\"", "iPad Pro 11\"", "iPad Air", "iPad mini"],
                "Android": ["Samsung Galaxy Tab S8 Ultra", "Samsung Galaxy Tab S8+", "Google Pixel Tablet"],
                "Windows": ["Microsoft Surface Pro 9", "Dell Latitude 7320 Detachable"]
            }
        }

        # Software/applications by OS
        self.software_by_os = {
            "Windows": [
                {"name": "Microsoft Office 365", "version": "16.0.16130", "type": "productivity"},
                {"name": "Adobe Creative Cloud", "version": "5.10.0.726", "type": "creative"},
                {"name": "Google Chrome", "version": "112.0.5615.138", "type": "browser"},
                {"name": "Mozilla Firefox", "version": "113.0", "type": "browser"},
                {"name": "Microsoft Edge", "version": "113.0.1774.42", "type": "browser"},
                {"name": "Visual Studio Code", "version": "1.78.0", "type": "development"},
                {"name": "Visual Studio", "version": "17.6", "type": "development"},
                {"name": "Slack", "version": "4.33.73", "type": "communication"},
                {"name": "Discord", "version": "1.0.9013", "type": "communication"},
                {"name": "Spotify", "version": "1.2.9.743", "type": "media"},
                {"name": "VLC Media Player", "version": "3.0.18", "type": "media"},
                {"name": "Steam", "version": "1.0.0.76", "type": "gaming"}
            ],
            "macOS": [
                {"name": "Microsoft Office 365", "version": "16.0.16130", "type": "productivity"},
                {"name": "Adobe Creative Cloud", "version": "5.10.0.726", "type": "creative"},
                {"name": "Final Cut Pro", "version": "10.6.5", "type": "creative"},
                {"name": "Safari", "version": "16.4", "type": "browser"},
                {"name": "Google Chrome", "version": "112.0.5615.138", "type": "browser"},
                {"name": "Visual Studio Code", "version": "1.78.0", "type": "development"},
                {"name": "Xcode", "version": "14.3", "type": "development"},
                {"name": "Slack", "version": "4.33.73", "type": "communication"},
                {"name": "Spotify", "version": "1.2.8.460", "type": "media"},
                {"name": "Apple Music", "version": "1.2.5", "type": "media"}
            ],
            "Linux": [
                {"name": "LibreOffice", "version": "7.5.2", "type": "productivity"},
                {"name": "GIMP", "version": "2.10.34", "type": "creative"},
                {"name": "Mozilla Firefox", "version": "113.0", "type": "browser"},
                {"name": "Google Chrome", "version": "112.0.5615.138", "type": "browser"},
                {"name": "Visual Studio Code", "version": "1.78.0", "type": "development"},
                {"name": "Slack", "version": "4.33.73", "type": "communication"},
                {"name": "Spotify", "version": "1.2.9.743", "type": "media"},
                {"name": "VLC Media Player", "version": "3.0.18", "type": "media"}
            ],
            "iOS": [
                {"name": "Safari", "version": "16.4", "type": "browser"},
                {"name": "Mail", "version": "16.4", "type": "communication"},
                {"name": "Photos", "version": "16.4", "type": "media"},
                {"name": "Apple Music", "version": "4.2", "type": "media"},
                {"name": "Spotify", "version": "8.8.12", "type": "media"},
                {"name": "Microsoft Outlook", "version": "4.2343.0", "type": "communication"},
                {"name": "Microsoft Word", "version": "2.71", "type": "productivity"},
                {"name": "Adobe Photoshop Express", "version": "22.20.0", "type": "creative"}
            ],
            "Android": [
                {"name": "Chrome", "version": "112.0.5615.136", "type": "browser"},
                {"name": "Gmail", "version": "2023.04.30.550775944", "type": "communication"},
                {"name": "Google Photos", "version": "6.44.0.517019044", "type": "media"},
                {"name": "Spotify", "version": "8.8.12.520", "type": "media"},
                {"name": "YouTube", "version": "18.17.38", "type": "media"},
                {"name": "Microsoft Outlook", "version": "4.2340.2", "type": "communication"},
                {"name": "Microsoft Word", "version": "16.0.16509.20182", "type": "productivity"},
                {"name": "Adobe Photoshop Express", "version": "8.12.1", "type": "creative"}
            ],
            "iPadOS": [
                {"name": "Safari", "version": "16.4", "type": "browser"},
                {"name": "Mail", "version": "16.4", "type": "communication"},
                {"name": "Photos", "version": "16.4", "type": "media"},
                {"name": "Apple Music", "version": "4.2", "type": "media"},
                {"name": "Procreate", "version": "5.3.3", "type": "creative"},
                {"name": "Microsoft Office", "version": "2.71", "type": "productivity"},
                {"name": "Adobe Photoshop", "version": "3.8.0", "type": "creative"},
                {"name": "GoodNotes 5", "version": "5.9.43", "type": "productivity"}
            ]
        }

    def generate(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate machine configuration records.

        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation

        Returns:
            List of generated records
        """
        self.logger.info(f"Generating {count} machine configuration records")

        # Use direct generation for small counts or when specified
        if count <= 20 or (criteria and criteria.get("direct_generation", False)):
            return self._direct_generation(count, criteria)

        # Use LLM-powered generation for larger counts or complex criteria
        instruction = f"Generate {count} realistic machine configuration records"
        if criteria:
            instruction += f" matching these criteria: {json.dumps(criteria)}"

        input_data = {
            "count": count,
            "criteria": criteria or {},
            "config": self.config,
            "collection_name": self.collection_name
        }

        # Generate in batches to avoid overwhelming the LLM
        results = []
        batch_size = min(count, 10)
        remaining = count

        while remaining > 0:
            current_batch = min(batch_size, remaining)
            self.logger.info(f"Generating batch of {current_batch} machine configuration records")

            # Update input data for this batch
            batch_input = input_data.copy()
            batch_input["count"] = current_batch

            # Run the agent
            response = self.run(instruction, batch_input)

            # Extract the generated records
            if "actions" in response:
                for action in response["actions"]:
                    if action["tool"] == "database_insert" or action["tool"] == "database_bulk_insert":
                        # If records were inserted directly, we need to query them
                        tool = self.tools.get_tool("database_query")
                        if tool:
                            query_result = tool.execute({
                                "query": f"FOR doc IN {self.collection_name} SORT RAND() LIMIT {current_batch} RETURN doc"
                            })
                            results.extend(query_result)

            remaining -= current_batch

        return results

    def _direct_generation(self, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate machine configuration records directly without LLM.

        Args:
            count: Number of records to generate
            criteria: Optional criteria for generation

        Returns:
            List of generated records
        """
        self.logger.info(f"Direct generation of {count} machine configuration records")

        # Try to use the model-based MachineConfigGeneratorTool
        tool = self.tools.get_tool("machine_config_generator")
        if tool:
            self.logger.info("Using model-based machine config generator tool")
            result = tool.execute({
                "count": count,
                "criteria": criteria or {}
            })

            configs = result.get("records", [])

            # Transform the records into the format expected by the database
            transformed_records = [self._transform_to_db_format(record) for record in configs]

            # Store the records if needed
            if self.config.get("store_directly", False):
                bulk_tool = self.tools.get_tool("database_bulk_insert")
                if bulk_tool:
                    bulk_tool.execute({
                        "collection": self.collection_name,
                        "documents": transformed_records
                    })

            return transformed_records

        # Fall back to legacy generation if tool is not available
        self.logger.warning("Machine config generator tool not available, using legacy generation")

        # Apply device distribution from criteria, if provided
        device_distribution = criteria.get("device_distribution", self.device_types)

        # Calculate counts for each device type
        device_counts = self._calculate_device_counts(count, device_distribution)

        # Generate each type of device
        configs = []

        for device_type, device_count in device_counts.items():
            device_configs = self._generate_device_records(device_type, device_count, criteria)
            configs.extend(device_configs)

        # Store the records if needed
        if self.config.get("store_directly", False):
            bulk_tool = self.tools.get_tool("database_bulk_insert")
            if bulk_tool:
                bulk_tool.execute({
                    "collection": self.collection_name,
                    "documents": configs
                })

        return configs

    def _calculate_device_counts(self, total_count: int, device_distribution: Dict[str, float]) -> Dict[str, int]:
        """Calculate the number of devices of each type to generate.

        Args:
            total_count: Total number of devices to generate
            device_distribution: Distribution of device types

        Returns:
            Dictionary of device type to count
        """
        # Calculate raw counts
        raw_counts = {device: total_count * weight for device, weight in device_distribution.items()}

        # Round counts
        rounded_counts = {device: int(count) for device, count in raw_counts.items()}

        # Distribute any remaining devices due to rounding
        total_rounded = sum(rounded_counts.values())
        remaining = total_count - total_rounded

        if remaining > 0:
            # Sort devices by fractional part of raw count, descending
            devices_by_fraction = sorted(
                device_distribution.keys(),
                key=lambda d: raw_counts[d] - rounded_counts[d],
                reverse=True
            )

            # Distribute remaining count
            for i in range(remaining):
                device = devices_by_fraction[i % len(devices_by_fraction)]
                rounded_counts[device] += 1

        return rounded_counts

    def _generate_device_records(self, device_type: str, count: int, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate machine configuration records for a specific device type.

        Args:
            device_type: Type of device
            count: Number of records to generate
            criteria: Optional criteria for generation

        Returns:
            List of generated records
        """
        # Apply OS distribution from criteria, if provided
        os_distribution = criteria.get(f"{device_type}_os_distribution", self.os_by_device[device_type])

        # Calculate counts for each OS
        os_counts = self._calculate_device_counts(count, os_distribution)

        # Generate configurations for each OS
        configs = []

        for os_name, os_count in os_counts.items():
            for _ in range(os_count):
                config = self._generate_single_device(device_type, os_name, criteria)
                configs.append(config)

        return configs

    def _generate_single_device(self, device_type: str, os_name: str, criteria: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a single machine configuration record.

        Args:
            device_type: Type of device
            os_name: Operating system
            criteria: Optional criteria for generation

        Returns:
            Machine configuration record
        """
        # Generate a machine ID
        machine_id = criteria.get("machine_id", str(uuid.uuid4()))

        # Generate hardware configuration
        cpu_model = random.choice(self.cpu_models[device_type][os_name])
        gpu_model = random.choice(self.gpu_models[device_type][os_name])
        ram_gb = random.choice(self.ram_configs[device_type])
        storage_gb = random.choice(self.storage_configs[device_type])
        model = random.choice(self.device_models[device_type][os_name])

        # Generate software configuration
        os_version = self._generate_os_version(os_name)
        installed_software = self._generate_installed_software(os_name, criteria)

        # Set hostname and username
        hostname = criteria.get("hostname", f"{model.split(' ')[0].lower()}-{random.randint(100, 999)}")
        username = criteria.get("username", f"user{random.randint(100, 999)}")

        # Generate timestamps
        timestamp = datetime.now(timezone.utc).isoformat()

        # Create the configuration record
        config = {
            "MachineID": machine_id,
            "DeviceType": device_type,
            "Hostname": hostname,
            "Username": username,
            "LastUpdated": timestamp,
            "Hardware": {
                "Model": model,
                "CPU": cpu_model,
                "GPU": gpu_model,
                "RAM": ram_gb * 1024 * 1024 * 1024,  # Convert GB to bytes
                "Storage": storage_gb * 1024 * 1024 * 1024  # Convert GB to bytes
            },
            "Software": {
                "OS": os_name,
                "OSVersion": os_version,
                "InstalledSoftware": installed_software
            }
        }

        # Add network information for non-mobile devices
        if device_type in ["desktop", "laptop"]:
            config["Network"] = {
                "IPAddress": self._generate_ip_address(),
                "MACAddress": self._generate_mac_address(),
                "Hostname": hostname
            }

        # Add mobile-specific information
        if device_type in ["mobile", "tablet"]:
            config["Mobile"] = {
                "PhoneNumber": self._generate_phone_number() if device_type == "mobile" else None,
                "IMEI": self._generate_imei() if device_type == "mobile" else None,
                "Carrier": random.choice(["Verizon", "AT&T", "T-Mobile", "Sprint", "Vodafone"]) if device_type == "mobile" else None
            }

        return config

    def _generate_os_version(self, os_name: str) -> str:
        """Generate OS version based on OS name.

        Args:
            os_name: Operating system name

        Returns:
            OS version string
        """
        if os_name == "Windows":
            return random.choice(["10.0.19044", "10.0.22621", "11.0.22621"])
        elif os_name == "macOS":
            return random.choice(["13.3.1", "13.2", "12.6.3", "11.7.6"])
        elif os_name == "Linux":
            return random.choice(["5.15.0-71-generic", "6.2.0-26-generic", "5.19.0-45-generic"])
        elif os_name == "iOS" or os_name == "iPadOS":
            return random.choice(["16.4.1", "16.3.1", "16.0", "15.7.5"])
        elif os_name == "Android":
            return random.choice(["13", "12", "11", "10"])
        else:
            return "1.0"

    def _generate_installed_software(self, os_name: str, criteria: Optional[Dict[str, Any]] = None) -> List[Dict[str, str]]:
        """Generate installed software based on OS.

        Args:
            os_name: Operating system name
            criteria: Optional criteria for generation

        Returns:
            List of installed software
        """
        # Get the list of possible software for this OS
        possible_software = self.software_by_os.get(os_name, [])

        # If criteria specifies required software, make sure to include it
        required_software = criteria.get("required_software", []) if criteria else []

        # Determine how many software items to include
        software_count = random.randint(3, min(10, len(possible_software)))

        # Select random software
        selected_software = random.sample(possible_software, software_count)

        # Make sure required software is included
        for req_sw in required_software:
            if isinstance(req_sw, dict) and "name" in req_sw:
                # Check if required software is already in the list
                if not any(sw["name"] == req_sw["name"] for sw in selected_software):
                    selected_software.append(req_sw)
            elif isinstance(req_sw, str):
                # Check if required software name is already in the list
                if not any(sw["name"] == req_sw for sw in selected_software):
                    # Find the software in possible_software
                    matching_sw = next((sw for sw in possible_software if sw["name"] == req_sw), None)
                    if matching_sw:
                        selected_software.append(matching_sw)

        return selected_software

    def _generate_ip_address(self) -> str:
        """Generate a random IP address.

        Returns:
            IP address string
        """
        # Generate private IP addresses most of the time
        if random.random() < 0.8:
            # 192.168.0.0/16, 172.16.0.0/12, or 10.0.0.0/8
            first_octet = random.choice([192, 172, 10])
            if first_octet == 192:
                return f"192.168.{random.randint(0, 255)}.{random.randint(1, 254)}"
            elif first_octet == 172:
                return f"172.{random.randint(16, 31)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            else:  # 10
                return f"10.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        else:
            # Public IP address
            return f"{random.randint(1, 223)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"

    def _generate_mac_address(self) -> str:
        """Generate a random MAC address.

        Returns:
            MAC address string
        """
        return ":".join([f"{random.randint(0, 255):02x}" for _ in range(6)])

    def _generate_phone_number(self) -> str:
        """Generate a random phone number.

        Returns:
            Phone number string
        """
        return f"+1{random.randint(200, 999)}{random.randint(100, 999)}{random.randint(1000, 9999)}"

    def _generate_imei(self) -> str:
        """Generate a random IMEI number.

        Returns:
            IMEI string
        """
        # Generate a 15-digit IMEI
        return "".join([str(random.randint(0, 9)) for _ in range(15)])

    def _transform_to_db_format(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a generated record to the database format.

        Args:
            record: Generated record from MachineConfigGeneratorTool

        Returns:
            Transformed record in database format
        """
        # Check if this is already in IndalekoMachineConfigDataModel format
        if "MachineID" in record and "Hardware" in record and "Software" in record:
            # Record is already in proper format, return as is
            self.logger.debug("Record is already in database format")
            return record

        # For other formats, convert to the expected database format
        # We'll need to extract or generate relevant fields
        machine_id = record.get("MachineID", str(uuid.uuid4()))

        # Create a basic structure if we need to handle other formats
        # This is mostly a placeholder as we expect the tool to generate properly formatted data
        db_record = {
            "MachineID": machine_id,
            "DeviceType": record.get("DeviceType", "unknown"),
            "Hostname": record.get("Hostname", f"host-{machine_id[:8]}"),
            "Username": record.get("Username", "user"),
            "LastUpdated": record.get("LastUpdated", datetime.now(timezone.utc).isoformat()),
            "Hardware": record.get("Hardware", {}),
            "Software": record.get("Software", {})
        }

        # Add network information for non-mobile devices if missing
        if "Network" not in db_record and db_record["DeviceType"] in ["desktop", "laptop"]:
            db_record["Network"] = {
                "IPAddress": self._generate_ip_address(),
                "MACAddress": self._generate_mac_address(),
                "Hostname": db_record["Hostname"]
            }

        # Add mobile-specific information if missing
        if "Mobile" not in db_record and db_record["DeviceType"] in ["mobile", "tablet"]:
            mobile_info = {
                "Carrier": random.choice(["Verizon", "AT&T", "T-Mobile", "Sprint", "Vodafone"])
            }

            if db_record["DeviceType"] == "mobile":
                mobile_info["PhoneNumber"] = self._generate_phone_number()
                mobile_info["IMEI"] = self._generate_imei()

            db_record["Mobile"] = mobile_info

        return db_record

    def generate_truth(self, count: int, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate truth machine configuration records with specific characteristics.

        Args:
            count: Number of truth records to generate
            criteria: Criteria that the truth records must satisfy

        Returns:
            List of generated truth records
        """
        self.logger.info(f"Generating {count} truth machine configuration records with criteria: {criteria}")

        # For truth records, we use direct generation but with specific overrides
        device_type = criteria.get("device_type", "laptop")
        os_name = criteria.get("os_name", "Windows")

        # Override device distribution to ensure we get the right device type
        device_distribution = {device_type: 1.0}
        os_distribution = {os_name: 1.0}

        # Create criteria with overrides
        truth_criteria = criteria.copy()
        truth_criteria["device_distribution"] = device_distribution
        truth_criteria[f"{device_type}_os_distribution"] = os_distribution

        # Generate records
        configs = self._direct_generation(count, truth_criteria)

        # Track the truth records
        for config in configs:
            self.truth_list.append(config.get("MachineID", ""))

        # Store truth characteristics for later verification
        self.state["truth_criteria"] = criteria
        self.state["truth_count"] = count
        self.state["truth_ids"] = self.truth_list

        return configs

    def _build_context(self, instruction: str, input_data: Optional[Dict[str, Any]] = None) -> str:
        """Build the context for the LLM.

        Args:
            instruction: The instruction for the agent
            input_data: Optional input data

        Returns:
            Context string for the LLM
        """
        context = f"""
        You are a specialized agent for generating realistic machine configuration metadata for the Indaleko system.

        Your task: {instruction}

        Generate machine configuration metadata that follows these guidelines:
        1. Create realistic hardware specifications for different device types
        2. Include appropriate software configurations
        3. Generate unique identifiers and network information
        4. Ensure all records have required fields for database insertion

        Machine configuration records should include the following fields:
        - MachineID: Unique identifier for the machine
        - DeviceType: Type of device (desktop, laptop, mobile, tablet)
        - Hostname: Machine hostname
        - Username: Current user
        - LastUpdated: Timestamp of last update
        - Hardware: Hardware specifications (CPU, GPU, RAM, Storage, etc.)
        - Software: Software configuration (OS, OSVersion, InstalledSoftware)
        - Network: Network information (for non-mobile devices)
        - Mobile: Mobile-specific information (for mobile devices)

        """

        if input_data:
            context += f"Input data: {json.dumps(input_data, indent=2)}\n\n"

        # Add tips for specific criteria if provided
        if input_data and "criteria" in input_data and input_data["criteria"]:
            context += "Special instructions for the criteria:\n"

            for key, value in input_data["criteria"].items():
                if key == "device_type":
                    context += f"- All configurations should be for '{value}' devices\n"
                elif key == "os_name":
                    context += f"- All configurations should use the '{value}' operating system\n"
                elif key == "username":
                    context += f"- Use '{value}' as the username for all configurations\n"
                elif key == "required_software":
                    context += f"- Include these software applications: {', '.join(value if isinstance(value, list) else [value])}\n"
                elif not key.endswith("_distribution") and key != "direct_generation":
                    context += f"- Apply the criterion '{key}': '{value}'\n"

        # If generating truth records, add special instructions
        if input_data and input_data.get("truth", False):
            context += "\nIMPORTANT: You are generating TRUTH records. These records must EXACTLY match the criteria provided. These records will be used for testing and validation, so their properties must match the criteria precisely.\n"

        return context
