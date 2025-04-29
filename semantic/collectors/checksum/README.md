# Multi-Checksum Generator for Indaleko

This semantic collector computes and stores multiple checksums for files, enhancing Indaleko's ability to verify file integrity, detect duplicates, and provide security verification.

## Features

- Computes five different checksum types in a single efficient pass:
  - **MD5**: Fast but collision-prone hash (32 characters)
  - **SHA1**: Widely used but no longer cryptographically secure (40 characters)
  - **SHA256**: Strong cryptographic hash (64 characters)
  - **SHA512**: Very strong cryptographic hash with higher security margin (128 characters)
  - **Dropbox Content Hash**: Special hash used by Dropbox for content addressing (64 characters)

- Performance optimizations:
  - Memory-mapped I/O for large files
  - Chunked processing to minimize memory usage
  - Single-pass calculation of all hash types
  - Threshold-based approach for optimal performance with both small and large files

## Usage

```python
from semantic.collectors.checksum.checksum import IndalekoSemanticChecksums, compute_checksums

# Basic usage - compute checksums for a file
checksums = compute_checksums("/path/to/file.txt")
print(f"MD5: {checksums['MD5']}")
print(f"SHA1: {checksums['SHA1']}")
print(f"SHA256: {checksums['SHA256']}")
print(f"SHA512: {checksums['SHA512']}")
print(f"Dropbox: {checksums['Dropbox']}")

# Advanced usage - create semantic record in Indaleko
collector = IndalekoSemanticChecksums()
object_id = "467de59f-fe7f-4cdd-b5b8-0256e090ed04"  # UUID of the file object
checksum_record = collector.get_checksums_for_file("/path/to/file.txt", object_id)
```

## Integration with Indaleko

The Multi-Checksum Generator integrates with the Indaleko semantic collection framework:

1. **Semantic Attributes**: Each checksum type is stored as a distinct semantic attribute with its own UUID
2. **Data Model**: `SemanticChecksumDataModel` extends the base semantic data model with checksum-specific fields
3. **Collector Interface**: Implements the standard `SemanticCollector` interface for consistent integration

## Implementation Details

- The Dropbox Content Hash is a special hash algorithm used by Dropbox for content-based deduplication:
  1. Split the file into 4MB blocks
  2. Compute SHA256 hash for each block
  3. Concatenate all block hashes
  4. Compute a final SHA256 hash of the concatenated hashes

- For optimal performance, the implementation uses:
  - Direct read for small files (< 16MB)
  - Memory-mapped chunked processing for large files (≥ 16MB)
  - 4MB chunk size for optimal processing of large files

## Testing

Run the included test file to verify functionality:

```bash
python -m semantic.collectors.checksum.test_checksum_collector
```

Or run the unit tests directly:

```bash
python -m semantic.collectors.checksum.checksum
```
