# Indaleko Registration Services

## Overview

Indaleko uses a unified registration system for data providers of different types (activity, semantic, storage, etc.). This system enables:

1. Discovery of available data providers
2. Dynamic collection management
3. Metadata enrichment
4. Runtime capability detection

The architecture consists of:

- A base `IndalekoRegistrationService` class that provides common functionality
- Specialized subclasses for each provider type:
  - `IndalekoActivityRegistrationService`
  - `IndalekoSemanticRegistrationService`
  - (potential future extensions)

## Registration Service Base Class

The base registration service provides:

- Provider registration
- Provider lookup (by identifier or name)
- Collection creation and management
- Provider listing
- Provider deactivation

```python
from utils.registration_service import IndalekoRegistrationService

# Create a specialized registration service
class MySpecializedRegistrationService(IndalekoRegistrationService):
    # Configure service details
    service_uuid_str = "00000000-0000-0000-0000-000000000000"
    collection_name = "MyProviders"
    collection_prefix = "MyProviderData_"
    service_name = "MySpecializedRegistrationService"
    service_description = "My specialized registration service"
    service_version = "1.0.0"
    service_type = "my_provider_registrar"

    def __init__(self):
        super().__init__(
            service_uuid=self.service_uuid_str,
            service_name=self.service_name,
            service_description=self.service_description,
            service_version=self.service_version,
            service_type=self.service_type,
            collection_name=self.collection_name,
            collection_prefix=self.collection_prefix
        )

    def _process_registration_data(self, kwargs):
        # Process and validate provider-specific data
        # ...
        return kwargs
```

## Activity Registration Service

The activity registration service manages providers that collect user and system activities:

- Calendar events
- File activities
- Location data
- Collaboration events
- And more

```python
from activity.registration_service import IndalekoActivityRegistrationService

# Register an activity provider
service = IndalekoActivityRegistrationService()
service.register_activity_provider(
    Identifier="12345678-1234-5678-1234-567812345678",
    Name="My Activity Provider",
    Description="Collects custom activity data",
    Version="1.0.0",
    Record=record_data_model,
    DataProviderType="Activity",
    DataProviderSubType="Custom",
    Tags=["custom", "activity"]
)

# Find providers by type
calendar_providers = service.get_activity_providers_by_type("Calendar")
```

## Semantic Registration Service

The semantic registration service manages providers that extract metadata from files:

- MIME type detection
- Checksum calculation
- EXIF data extraction
- Content analysis
- And more

```python
from semantic.registration_service import IndalekoSemanticRegistrationService

# Register a semantic extractor
service = IndalekoSemanticRegistrationService()
service.register_semantic_extractor(
    Identifier="12345678-1234-5678-1234-567812345678",
    Name="My Semantic Extractor",
    Description="Extracts custom metadata",
    Version="1.0.0",
    Record=record_data_model,
    SupportedMimeTypes=["image/jpeg", "image/png"],
    ResourceIntensity="medium",
    ProcessingPriority=75,
    ExtractedAttributes=["custom:attribute1", "custom:attribute2"]
)

# Find extractors for a MIME type
jpeg_extractors = service.find_extractors_for_mime_type("image/jpeg")

# Get all supported MIME types
mime_types = service.get_supported_mime_types()
```

## Benefits of the Registration System

### 1. Discovery and Extensibility

The registration system enables dynamic discovery of data providers at runtime. This means:

- New providers can be added without code changes
- The system can adapt to available providers
- Plugins and extensions can be developed independently

### 2. Metadata Enrichment

The registration system stores rich metadata about each provider:

- Capabilities and limitations
- Supported data types
- Resource requirements
- Semantic attributes provided

This metadata can be used to make intelligent decisions about which provider to use for a given task.

### 3. Privacy Enhancement

The registration system creates a layer of abstraction between semantic meaning and data storage:

- Provider collections are identified by UUIDs, not semantic names
- The mapping between UUIDs and semantic meaning is only available to authorized components
- External systems see only opaque identifiers, not meaningful labels

### 4. Resource Management

For semantic extractors, the registration system enables intelligent resource management:

- Resource-intensive extractors can be prioritized based on system load
- Extractors can be selected based on the specific file type
- Processing can be scheduled during idle times

## Architecture Evolution

The registration system is designed to evolve over time:

1. **Current state**: Separate registration for different provider types
2. **Future direction**: Potential consolidation into a single registration system
3. **Privacy direction**: Progressive separation of semantic meaning from storage representation

As the system evolves, the registration services provide a stable API while allowing for internal changes to the registration mechanism.

## Security and Privacy Considerations

The registration system supports several security and privacy features:

- **Provider verification**: Providers must register with the system before contributing data
- **Collection isolation**: Each provider has its own collection, limiting the impact of a compromised provider
- **Semantic abstraction**: The meaning of data is separated from its storage representation
- **Activity tracking**: Provider registrations create an audit trail of data sources

In future versions, the system could be extended to support:

- **Encrypted metadata**: Registration data could be encrypted with user-controlled keys
- **Multi-level access**: Different levels of semantic understanding based on access privileges
- **Contextual access**: Access to semantic mappings only in specific contexts
