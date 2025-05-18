# Checksum Generator Tool

The Checksum Generator Tool creates file checksums for testing and evaluation in Indaleko. It generates multiple types of checksums (MD5, SHA1, SHA256, SHA512, Dropbox) with realistic properties and support for simulating duplicate files.

## Features

- **Multiple Checksum Types**: Generates MD5, SHA1, SHA256, SHA512, and Dropbox checksums for files
- **Duplication Support**: Creates simulated file duplicates with identical checksums
- **Deterministic Generation**: Produces consistent checksums based on file properties
- **Rich Semantic Attributes**: Generates all required semantic attributes for effective querying
- **Database Integration**: Fully compatible with ArangoDB schema for persistent storage
- **Realistic Patterns**: Creates checksums that match actual file types and sizes

## Usage

### Basic Usage

```python
from tools.data_generator_enhanced.agents.data_gen.tools.checksum_generator import ChecksumGeneratorTool

# Initialize the generator
generator = ChecksumGeneratorTool()

# Create test files
test_files = [
    {
        "path": "/files/document1.docx",
        "name": "document1.docx",
        "size": 25000,
        "created": "2023-01-01T00:00:00Z",
        "modified": "2023-01-02T00:00:00Z",
        "object_id": "123e4567-e89b-12d3-a456-426614174000"
    },
    {
        "path": "/files/image1.jpg",
        "name": "image1.jpg",
        "size": 500000,
        "created": "2023-01-01T00:00:00Z",
        "modified": "2023-01-02T00:00:00Z",
        "object_id": "223e4567-e89b-12d3-a456-426614174001"
    }
]

# Generate checksums
result = generator.execute({
    "files": test_files
})

# Access the generated checksums
checksums = result["checksums"]
```

### Controlling Duplication

```python
# Set up duplicate groups (file indices to make duplicates)
duplicate_groups = [[0, 2]]  # Make files 0 and 2 duplicates

result = generator.execute({
    "files": test_files,
    "duplicate_groups": duplicate_groups,
    "duplication_rate": 0.2  # 20% chance of creating duplicates naturally
})
```

## Data Model

Each generated checksum record includes:

- **Checksums**:
  - `MD5`: 32-character MD5 hash (fast but collision-prone)
  - `SHA1`: 40-character SHA1 hash (widely used but no longer cryptographically secure)
  - `SHA256`: 64-character SHA256 hash (strong cryptographic hash)
  - `SHA512`: 128-character SHA512 hash (very strong cryptographic hash)
  - `Dropbox`: 64-character Dropbox content hash (special hash used by Dropbox)

- **Duplication Information**:
  - `is_duplicate`: Whether this file is a duplicate of another
  - `duplicate_of`: Path to the original file (if a duplicate)

- **Semantic Attributes**:
  - Standard semantic attributes for each checksum type

## Semantic Attributes

Each checksum record is enriched with semantic attributes for querying:

- `MD5_CHECKSUM`: MD5 checksum value
- `SHA1_CHECKSUM`: SHA1 checksum value
- `SHA256_CHECKSUM`: SHA256 checksum value
- `SHA512_CHECKSUM`: SHA512 checksum value
- `DROPBOX_CHECKSUM`: Dropbox checksum value

## Query Examples

The generated checksums support rich querying capabilities:

```aql
// Find files by MD5
FOR doc IN FileChecksums
    FILTER doc.MD5 == "d41d8cd98f00b204e9800998ecf8427e"
    RETURN doc

// Find all duplicates
FOR doc IN FileChecksums
    FILTER doc.is_duplicate == true
    RETURN doc

// Find by semantic attribute
FOR doc IN FileChecksums
    FOR attr IN doc.SemanticAttributes
        FILTER attr.Identifier.Label == "SHA256 Checksum"
        AND attr.Value == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        RETURN doc
```

## Integration with Other Tools

The Checksum Generator integrates well with other Indaleko data generators:

- **CloudStorageActivityGeneratorTool**: Checksums enhance cloud storage activity metadata
- **LocationGeneratorTool**: Files with identical checksums can be linked to different locations
- **EXIFGeneratorTool**: EXIF metadata can be linked to files with specific checksums

## Duplication Scenarios

The tool supports creating several types of duplication:

1. **Exact Duplicates**: Files with identical content (same checksums)
2. **Planned Duplicates**: Files explicitly set to be duplicates via duplicate_groups
3. **Random Duplicates**: Files randomly selected to be duplicates based on duplication_rate

## Running Tests

To test the Checksum Generator:

### Linux/macOS
```bash
./run_checksum_tests.sh
```

### Windows
```batch
run_checksum_tests.bat
```

The tests verify:
1. Basic checksum generation with all required fields
2. Duplication detection and control
3. Database integration with ArangoDB
4. Query capability for various checksum types
5. Semantic attribute generation and usage