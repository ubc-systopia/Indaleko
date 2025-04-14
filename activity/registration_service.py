"""
Registration service for Indaleko activity data providers.

This module extends the generic registration service for activity data providers.

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
from activity.registration import IndalekoActivityDataRegistration
# pylint: enable=wrong-import-position


class IndalekoActivityRegistrationService(IndalekoRegistrationService):
    """
    Registration service for Indaleko activity data providers.
    
    This service manages the registration of activity data providers,
    which collect and record user and system activities.
    """
    
    # Service details
    service_uuid_str = "5ef4125d-4e46-4e35-bea5-f23a9fcb3f63"
    collection_name = Indaleko.Indaleko_ActivityDataProvider_Collection
    collection_prefix = IndalekoActivityDataRegistration.provider_prefix
    service_name = "IndalekoActivityDataProviderRegistrationService"
    service_description = "Indaleko Activity Data Provider Registration Service"
    service_version = "1.0.0"
    service_type = IndalekoServiceManager.service_type_activity_data_registrar
    
    def __init__(self):
        """Initialize the activity registration service."""
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
        Process registration data for activity providers.
        
        Args:
            kwargs: Registration parameters
            
        Returns:
            Processed registration data
        """
        # Required fields for activity providers
        assert "Identifier" in kwargs, "Identifier must be provided"
        assert "Name" in kwargs, "Name must be provided"
        assert "Description" in kwargs, "Description must be provided"
        assert "Version" in kwargs, "Version must be provided"
        assert "Record" in kwargs, "Record must be provided"
        assert isinstance(kwargs["Record"], IndalekoRecordDataModel), "Record must be an IndalekoRecordDataModel"
        
        # Optional activity-specific fields with defaults
        kwargs.setdefault("DataProviderType", "Activity")
        kwargs.setdefault("DataProviderSubType", "Generic")
        kwargs.setdefault("DataFormat", "JSON")
        kwargs.setdefault("DataFormatVersion", "1.0")
        kwargs.setdefault("DataAccess", "Read")
        kwargs.setdefault("SourceIdentifiers", [])
        kwargs.setdefault("SchemaIdentifiers", [])
        kwargs.setdefault("Tags", [])
        
        # Process through IndalekoActivityDataRegistration
        activity_registration = IndalekoActivityDataRegistration(
            registration_data=kwargs
        )
        
        # Use the model_dump_json method to process the data
        registration_data = activity_registration.model_dump_json()
        
        return registration_data
    
    def register_activity_provider(self, **kwargs) -> Tuple[dict, IndalekoCollection]:
        """
        Register an activity data provider.
        
        Args:
            **kwargs: Provider configuration
            
        Returns:
            Tuple of (registration_data, collection)
        """
        return self.register_provider(**kwargs)
    
    @staticmethod
    def get_activity_providers_by_type(provider_type: str) -> list:
        """
        Get activity providers of a specific type.
        
        Args:
            provider_type: The type of provider to find
            
        Returns:
            List of matching providers
        """
        service = IndalekoActivityRegistrationService()
        providers = service.get_provider_list()
        
        matching_providers = []
        for provider in providers:
            if "DataProviderSubType" in provider and provider["DataProviderSubType"] == provider_type:
                matching_providers.append(provider)
        
        return matching_providers


def main():
    """Test the activity registration service."""
    service = IndalekoActivityRegistrationService()
    print(f"Initialized {service.__class__.__name__}")
    print(f"Service UUID: {service.service_uuid_str}")
    print(f"Collection name: {service.collection_name}")
    print(f"Provider count: {len(service.get_provider_list())}")


if __name__ == "__main__":
    main()