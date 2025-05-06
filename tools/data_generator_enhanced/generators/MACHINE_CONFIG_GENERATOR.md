# Machine Configuration Generator

The Machine Configuration Generator creates realistic device hardware and software profiles for testing Indaleko's cross-device search capabilities. It supports a variety of device types including desktop computers, laptops, and mobile devices.

## Core Features

- Generates realistic machine configuration metadata for multiple device types
- Creates configurations for Windows, macOS, Linux, iOS, and Android devices
- Directly integrates with the ArangoDB database 
- Supports generating truth records for testing specific device criteria
- Produces unique machine identifiers for relationship tracking

## Device Types

The generator supports three main device categories:

### 1. Desktop Computers

Desktop configurations include powerful workstations with:
- High-core-count CPUs (Intel Core i7/i9, AMD Ryzen 9, Apple M1 Ultra)
- Windows, macOS, and Linux operating systems
- Realistic hardware specifications matching actual devices

### 2. Laptop Computers

Laptop configurations represent portable devices with:
- Mobile-optimized CPUs (Intel Core mobile series, AMD Ryzen mobile, Apple M-series)
- Windows, macOS, and Linux operating systems
- Balanced performance characteristics

### 3. Mobile Devices

Mobile device configurations include:
- Smartphones (iPhone, Android phones)
- Tablets (iPad, Android tablets)
- ARM-based processors with appropriate core counts
- iOS, iPadOS, and Android operating systems

## Implementation Details

The machine configuration generator:

1. Creates realistic device templates for each device category
2. Generates unique machine identifiers (UUIDs) for each device
3. Creates proper hardware and software configurations
4. Assigns realistic hostnames based on device type
5. Sets appropriate timestamps for when the configuration was captured
6. Inserts records into the MachineConfig collection with direct database integration

## Database Schema

Machine configurations are stored in the `MachineConfig` collection with the following structure:

- **_key**: UUID for the machine
- **MachineUUID**: UUID string matching the _key value
- **Hardware**: CPU architecture, processor version, core count, thread count
- **Software**: OS type, OS version, hostname, architecture
- **Record**: Metadata and timestamps
- **Captured**: When the configuration was captured
- **DeviceType**: Desktop, laptop, or mobile (for filtering)

## Usage

### Basic Usage

```python
from tools.data_generator_enhanced.generators.machine_config import MachineConfigGeneratorImpl
from db.db_config import IndalekoDBConfig

# Initialize database connection
db_config = IndalekoDBConfig()

# Create machine configuration generator
machine_generator = MachineConfigGeneratorImpl({}, db_config, seed=42)

# Generate machine configuration records
machine_records = machine_generator.generate(10)  # Generate 10 records
```

### Generating Truth Records

For testing specific device queries, you can create truth records with known characteristics:

```python
# Generate specific mobile device records for testing
truth_criteria = {
    "machine_criteria": {
        "device_type": "mobile",
        "os": "iOS",
        "version": "16.5.1",
        "days_ago": 5  # Configuration captured 5 days ago
    }
}

# Generate truth records
truth_machine_records = machine_generator.generate_truth(2, truth_criteria)
```

## Integration with Test Data Generation

The machine configuration generator integrates with the enhanced data generator pipeline:

1. Device configurations are generated for multiple device types
2. These can be linked to storage objects through relationships
3. This enables testing queries like "show me files I edited on my phone last week"

## Customization

To add new device templates:

1. Extend the `_initialize_device_templates` method with new configurations
2. Add the templates to the appropriate category list (desktop, laptop, mobile)
3. Ensure each template has the required hardware and software components

## Practical Applications

The machine configuration generator enables testing various real-world search scenarios:

- Finding files that were edited on a specific device type
- Locating documents accessed across multiple devices
- Tracking content creation and consumption patterns across devices
- Testing device-specific search filters and facets
