"""
Registration service for Indaleko semantic data providers.

This module extends the generic registration service for semantic data extractors.

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

import os
import sys
import uuid
from typing import Dict, Any, Union, Tuple

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from Indaleko import Indaleko
from db.collection import IndalekoCollection
from utils.registration_service import IndalekoRegistrationService
from data_models.record import IndalekoRecordDataModel
# pylint: enable=wrong-import-position


class IndalekoSemanticRegistrationService(IndalekoRegistrationService):
    """
    Registration service for Indaleko semantic data providers.
    
    This service manages the registration of semantic data extractors,
    which provide metadata about files such as MIME types, checksums,
    EXIF data, etc.
    """
    
    # Service details
    service_uuid_str = "7a8b9c0d-1e2f-3a4b-5c6d-7e8f9a0b1c2d"
    collection_name = "SemanticDataProviders"
    collection_prefix = "SemanticProviderData_"
    service_name = "IndalekoSemanticDataProviderRegistrationService"
    service_description = "Indaleko Semantic Data Provider Registration Service"
    service_version = "1.0.0"
    service_type = "semantic_data_registrar"
    
    def __init__(self):
        """Initialize the semantic registration service."""
        super().__init__(
            service_uuid=self.service_uuid_str,
            service_name=self.service_name,
            service_description=self.service_description,
            service_version=self.service_version,
            service_type=self.service_type,
            collection_name=self.collection_name,
            collection_prefix=self.collection_prefix
        )
    
    def _process_registration_data(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process registration data for semantic extractors.
        
        Args:
            kwargs: Registration parameters
            
        Returns:
            Processed registration data
        """
        # Required fields for semantic extractors
        assert "Name" in kwargs, "Name must be provided"
        assert "Description" in kwargs, "Description must be provided"
        assert "Version" in kwargs, "Version must be provided"
        assert "Record" in kwargs, "Record must be provided"
        assert isinstance(kwargs["Record"], IndalekoRecordDataModel), "Record must be an IndalekoRecordDataModel"
        
        # Optional semantic-specific fields with defaults
        kwargs.setdefault("SupportedMimeTypes", [])
        kwargs.setdefault("ResourceIntensity", "low")  # low, medium, high
        kwargs.setdefault("ExtractedAttributes", [])
        kwargs.setdefault("ProcessingPriority", 50)  # 0-100, higher is more important
        
        # Additional validation
        assert kwargs["ResourceIntensity"] in ["low", "medium", "high"], "ResourceIntensity must be low, medium, or high"
        assert 0 <= kwargs["ProcessingPriority"] <= 100, "ProcessingPriority must be between 0 and 100"
        
        return kwargs
    
    def register_semantic_extractor(self, **kwargs) -> Tuple[dict, IndalekoCollection]:
        """
        Register a semantic data extractor.
        
        Args:
            **kwargs: Extractor configuration
            
        Returns:
            Tuple of (registration_data, collection)
        """
        return self.register_provider(**kwargs)
    
    @staticmethod
    def get_supported_mime_types() -> list:
        """
        Get a list of MIME types supported by registered extractors.
        
        Returns:
            List of supported MIME types
        """
        service = IndalekoSemanticRegistrationService()
        providers = service.get_provider_list()
        
        mime_types = set()
        for provider in providers:
            if "SupportedMimeTypes" in provider:
                mime_types.update(provider["SupportedMimeTypes"])
        
        return list(mime_types)
    
    @staticmethod
    def find_extractors_for_mime_type(mime_type: str) -> list:
        """
        Find extractors that support a given MIME type.
        
        Args:
            mime_type: MIME type to search for
            
        Returns:
            List of extractor data
        """
        service = IndalekoSemanticRegistrationService()
        providers = service.get_provider_list()
        
        matching_extractors = []
        for provider in providers:
            if "SupportedMimeTypes" in provider:
                if mime_type in provider["SupportedMimeTypes"] or "*/*" in provider["SupportedMimeTypes"]:
                    matching_extractors.append(provider)
        
        # Sort by processing priority (highest first)
        matching_extractors.sort(
            key=lambda x: x.get("ProcessingPriority", 50),
            reverse=True
        )
        
        return matching_extractors


def main():
    """Test the semantic registration service."""
    service = IndalekoSemanticRegistrationService()
    print(f"Initialized {service.__class__.__name__}")
    print(f"Service UUID: {service.service_uuid_str}")
    print(f"Collection name: {service.collection_name}")
    print(f"Provider count: {len(service.get_provider_list())}")


if __name__ == "__main__":
    main()