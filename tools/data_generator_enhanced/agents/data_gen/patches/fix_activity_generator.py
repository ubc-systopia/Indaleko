"""
Patch to add semantic attributes to the ActivityGeneratorTool class.

This patch updates the ActivityGeneratorTool class to generate semantic attributes
for activity objects, similar to what was done for the FileMetadataGeneratorTool.
"""

import os
import sys
import random
from typing import Dict, List, Any, Tuple

# Update path for imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Import semantic attributes registry
from tools.data_generator_enhanced.agents.data_gen.core.semantic_attributes import SemanticAttributeRegistry


def patch_activity_generator_tool():
    """
    This patch function adds a _generate_semantic_attributes method to the
    ActivityGeneratorTool class, which is responsible for generating semantic
    attributes for activity objects.

    The method should be placed within the ActivityGeneratorTool class and
    used in the _create_activity_record_model method to generate and add 
    semantic attributes to the activity model.
    """
    patch_code = """
    def _generate_semantic_attributes(self, 
                                     activity_type: str, 
                                     domain: str, 
                                     provider_type: str,
                                     obj_id: str = None,
                                     path: str = None,
                                     name: str = None,
                                     user: str = None,
                                     app: str = None,
                                     device: str = None,
                                     platform: str = None
                                    ) -> List[Any]:
        \"\"\"Generate semantic attributes for an activity record.
        
        Args:
            activity_type: Type of activity (CREATE, READ, MODIFY, DELETE, etc.)
            domain: Domain of the activity (storage, collaboration, etc.)
            provider_type: Type of provider (ntfs, gdrive, etc.)
            obj_id: Target object identifier
            path: Target file path
            name: Target file name
            user: User who performed the activity
            app: Application used
            device: Device used
            platform: Operating system platform
            
        Returns:
            List of semantic attribute models
        \"\"\"
        semantic_attributes = []
        
        # Add activity type attribute
        activity_type_attr = self.SemanticAttributeDataModel(
            Identifier=SemanticAttributeRegistry.get_attribute_id(
                SemanticAttributeRegistry.DOMAIN_ACTIVITY, "ACTIVITY_TYPE"),
            Value=activity_type
        )
        semantic_attributes.append(activity_type_attr)
        
        # Add object ID attribute if available
        if obj_id:
            object_id_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "OBJECT_ID"),
                Value=obj_id
            )
            semantic_attributes.append(object_id_attr)
        
        # Add path and name attributes if available
        if path:
            path_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_PATH"),
                Value=path
            )
            semantic_attributes.append(path_attr)
            
        if name:
            name_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_NAME"),
                Value=name
            )
            semantic_attributes.append(name_attr)
        
        # Add user attribute if available
        if user:
            user_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_USER"),
                Value=user
            )
            semantic_attributes.append(user_attr)
        
        # Add application attribute if available
        if app:
            app_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_APPLICATION"),
                Value=app
            )
            semantic_attributes.append(app_attr)
        
        # Add device attribute if available
        if device:
            device_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_DEVICE"),
                Value=device
            )
            semantic_attributes.append(device_attr)
        
        # Add platform attribute if available
        if platform:
            platform_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "DATA_PLATFORM"),
                Value=platform
            )
            semantic_attributes.append(platform_attr)
            
        # Add domain-specific attributes
        if domain == "storage":
            # Add storage-specific attributes based on activity type
            if activity_type == "CREATE":
                storage_attr = self.SemanticAttributeDataModel(
                    Identifier=SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_CREATE"),
                    Value=True
                )
                semantic_attributes.append(storage_attr)
            elif activity_type == "MODIFY":
                storage_attr = self.SemanticAttributeDataModel(
                    Identifier=SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_MODIFY"),
                    Value=True
                )
                semantic_attributes.append(storage_attr)
            elif activity_type == "READ":
                storage_attr = self.SemanticAttributeDataModel(
                    Identifier=SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_READ"),
                    Value=True
                )
                semantic_attributes.append(storage_attr)
            elif activity_type == "DELETE":
                storage_attr = self.SemanticAttributeDataModel(
                    Identifier=SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_ACTIVITY, "STORAGE_DELETE"),
                    Value=True
                )
                semantic_attributes.append(storage_attr)
                
        elif domain == "collaboration":
            # Add collaboration-specific attributes
            collab_attr = self.SemanticAttributeDataModel(
                Identifier=SemanticAttributeRegistry.get_attribute_id(
                    SemanticAttributeRegistry.DOMAIN_ACTIVITY, "COLLABORATION_TYPE"),
                Value=provider_type
            )
            semantic_attributes.append(collab_attr)
            
            # Add random participants if it's an event or meeting
            if provider_type in ["calendar", "meeting"]:
                participants = ["user1@example.com", "user2@example.com", "user3@example.com"]
                participant_attr = self.SemanticAttributeDataModel(
                    Identifier=SemanticAttributeRegistry.get_attribute_id(
                        SemanticAttributeRegistry.DOMAIN_ACTIVITY, "COLLABORATION_PARTICIPANTS"),
                    Value=participants
                )
                semantic_attributes.append(participant_attr)
                
        return semantic_attributes
    """
    
    usage_code = """
    # In the _create_activity_record_model method, replace:
    semantic_attributes = []
    
    # With:
    activity_type = self._get_random_activity_type() if not activity_type else activity_type
    domain = self._get_random_domain() if not domain else domain
    provider_type = self._get_random_provider(domain) if not provider_type else provider_type
    
    # Get related object properties if available
    obj_id = storage_object.get("Id") if storage_object else None
    path = storage_object.get("LocalPath") if storage_object else None
    name = storage_object.get("Label") if storage_object else None
    
    # Generate random user, app, device, platform if not provided
    user = user or self._get_random_user()
    app = app or self._get_random_application()
    device = device or self._get_random_device()
    platform = platform or self._get_random_platform()
    
    # Generate semantic attributes
    semantic_attributes = self._generate_semantic_attributes(
        activity_type=activity_type,
        domain=domain,
        provider_type=provider_type,
        obj_id=obj_id,
        path=path,
        name=name,
        user=user,
        app=app,
        device=device,
        platform=platform
    )
    """
    
    # Additional helper methods that may be needed
    helper_methods = """
    def _get_random_user(self) -> str:
        \"\"\"Get a random user name.\"\"\"
        users = ["alice", "bob", "charlie", "dave", "eve", "frank", "grace", "heidi"]
        return random.choice(users)
        
    def _get_random_application(self) -> str:
        \"\"\"Get a random application name.\"\"\"
        apps = ["Microsoft Word", "Adobe Reader", "Microsoft Excel", 
               "Google Chrome", "Firefox", "Visual Studio Code", 
               "Outlook", "Spotify", "VLC Media Player"]
        return random.choice(apps)
        
    def _get_random_device(self) -> str:
        \"\"\"Get a random device name.\"\"\"
        devices = ["Desktop-PC", "Laptop-01", "Workstation-02", 
                  "Mobile-Phone", "Tablet-1", "DevBox-432"]
        return random.choice(devices)
        
    def _get_random_platform(self) -> str:
        \"\"\"Get a random platform name.\"\"\"
        platforms = ["Windows", "macOS", "Linux", "iOS", "Android"]
        return random.choice(platforms)
    """
    
    return {
        "patch_code": patch_code,
        "usage_code": usage_code,
        "helper_methods": helper_methods
    }


if __name__ == "__main__":
    patch = patch_activity_generator_tool()
    print("=== Patch Code for ActivityGeneratorTool ===")
    print(patch["patch_code"])
    print("\n=== Usage in _create_activity_record_model ===")
    print(patch["usage_code"])
    print("\n=== Helper Methods ===")
    print(patch["helper_methods"])