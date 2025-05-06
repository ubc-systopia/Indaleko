# ActivityGeneratorTool Semantic Attributes Fix

This document describes the issues with semantic attribute generation in the ActivityGeneratorTool class and provides implementation details for the fix.

## Issue Description

Similar to the previously fixed FileMetadataGeneratorTool, the ActivityGeneratorTool initializes the `semantic_attributes` list as empty but never populates it with actual attributes. This prevents database queries from finding activities based on semantic attributes, which is crucial for the functionality of the data generator and its testing capabilities.

## Solution Approach

The fix consists of:

1. Adding a `_generate_semantic_attributes` method to ActivityGeneratorTool
2. Updating the `_create_activity_record_model` method to use this new method
3. Adding helper methods for generating random values if needed
4. Creating unit tests to verify the semantic attribute generation

## Implementation Details

### 1. _generate_semantic_attributes Method

This method generates semantic attributes for an activity record based on various properties:

```python
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
    """Generate semantic attributes for an activity record."""
    semantic_attributes = []
    
    # Add activity type attribute
    activity_type_attr = self.SemanticAttributeDataModel(
        Identifier=SemanticAttributeRegistry.get_attribute_id(
            SemanticAttributeRegistry.DOMAIN_ACTIVITY, "ACTIVITY_TYPE"),
        Value=activity_type
    )
    semantic_attributes.append(activity_type_attr)
    
    # Add more attributes based on parameters...
    
    return semantic_attributes
```

### 2. Updating _create_activity_record_model

Replace the empty semantic attributes initialization:

```python
semantic_attributes = []
```

With:

```python
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
```

### 3. Helper Methods

Add these helper methods to generate random values:

```python
def _get_random_user(self) -> str:
    """Get a random user name."""
    users = ["alice", "bob", "charlie", "dave", "eve", "frank", "grace", "heidi"]
    return random.choice(users)
    
def _get_random_application(self) -> str:
    """Get a random application name."""
    apps = ["Microsoft Word", "Adobe Reader", "Microsoft Excel", 
           "Google Chrome", "Firefox", "Visual Studio Code", 
           "Outlook", "Spotify", "VLC Media Player"]
    return random.choice(apps)
    
def _get_random_device(self) -> str:
    """Get a random device name."""
    devices = ["Desktop-PC", "Laptop-01", "Workstation-02", 
              "Mobile-Phone", "Tablet-1", "DevBox-432"]
    return random.choice(devices)
    
def _get_random_platform(self) -> str:
    """Get a random platform name."""
    platforms = ["Windows", "macOS", "Linux", "iOS", "Android"]
    return random.choice(platforms)
```

## Testing

Two types of tests have been created:

1. **Unit Tests**: Test the semantic attribute generation in isolation
   - File: `testing/test_activity_semantic_attributes.py`
   - Tests attribute structure, expected values, and specific domain attributes

2. **Database Integration Tests**: Test the complete flow
   - File: `testing/test_db_integration.py`
   - Tests that attributes are properly stored and can be queried in the database

## How to Apply the Fix

1. Add the `_generate_semantic_attributes` method to the ActivityGeneratorTool class
2. Update the `_create_activity_record_model` method to populate semantic attributes
3. Add helper methods for random value generation if they don't already exist
4. Run tests to verify the fix:
   - On Linux/macOS: `./tools/data_generator_enhanced/run_activity_tests.sh`
   - On Windows: `tools\data_generator_enhanced\run_activity_tests.bat`

## Expected Outcomes

After applying this fix:

1. Activity objects will have proper semantic attributes
2. Database queries targeting activity semantic attributes will work
3. All integration tests will pass with 100% success rate
4. The data generator will produce more realistic and queryable test data

## Related Files

- **Patch File**: `patches/fix_activity_generator.py`
- **Unit Tests**: `testing/test_activity_semantic_attributes.py`
- **Integration Tests**: `testing/test_db_integration.py`
- **Test Scripts**: `run_activity_tests.sh` and `run_activity_tests.bat`
- **Documentation**: `ACTIVITY_GENERATOR_FIX.md` (this file)

## Next Steps

After fixing the ActivityGeneratorTool:

1. Apply similar fixes to other generator tools if needed
2. Enhance the test suite to cover more complex query patterns
3. Update the data generator documentation to reflect these changes