# Entity Mapping in NTFS Recorder

## Critical Implementation Notes

The NTFS Hot Tier Recorder implements a crucial mapping between file system entities and stable UUIDs. This document captures important implementation details and lessons learned.

## Entity Identification and Lookup Process

### Key Identifiers

Entities (files and directories) in Windows NTFS are identified by a combination of:

1. **File Reference Number (FRN)** - Stored as "LocalIdentifier" in the Objects collection
   - This is the file's unique identifier within a volume
   - Also called "inode" in some systems (like Unix/Linux)

2. **Volume GUID** - Stored as "Volume" field
   - This uniquely identifies the physical storage device
   - Example: `b8c4ce1b-3581-4dce-88a6-6c05dad92f61`

3. **Machine ID** (optional but recommended)
   - For multi-machine environments, helps disambiguate volumes with identical GUIDs
   - Can be fetched from machine configuration

### Correct Entity Lookup Pattern

When updating entity metadata, the correct lookup flow is:

1. Query for entities using the FRN + Volume GUID pair
   ```sql
   FOR doc IN Objects
   FILTER doc.LocalIdentifier == "844424930132032" AND doc.Volume == "b8c4ce1b-3581-4dce-88a6-6c05dad92f61"
   LIMIT 1
   RETURN doc
   ```

2. Use the returned document's `_key` (which is the entity UUID) for updates
   ```sql
   UPDATE "1e66edbd-fcdd-493e-b196-175c234b841e" WITH { ... } IN Objects
   ```

### Common Mistakes and Errors

One common pattern that leads to errors is:

1. Generating a random UUID for an entity
2. Later attempting to look up the entity directly by this UUID
3. Since UUIDs are random, this lookup will fail unless the UUID was persisted

This causes error messages like:
```
Entity X does not exist in collection, skipping update
```

### Example Entity Document

```json
{
  "_key": "1e66edbd-fcdd-493e-b196-175c234b841e",
  "Label": "$Recycle.Bin",
  "LocalPath": "c:\\",
  "LocalIdentifier": "844424930132032",
  "Volume": "b8c4ce1b-3581-4dce-88a6-6c05dad92f61",
  "URI": "\\\\?\\Volume{b8c4ce1b-3581-4dce-88a6-6c05dad92f61}\\$Recycle.Bin",
  "WindowsFileAttributes": "FILE_ATTRIBUTE_HIDDEN | FILE_ATTRIBUTE_SYSTEM | FILE_ATTRIBUTE_DIRECTORY"
}
```

## Best Practices for Entity Operations

1. **Always lookup by FRN + Volume**: When working with file system entities, always query by FRN and Volume GUID first, not by UUID directly.

2. **Consistent schema**: Ensure entities have consistent field names - use "LocalIdentifier" for FRN, not "file_reference_number".

3. **Entity creation first**: Consider implementing a pattern where entities are created first before activity recording attempts to update them.

4. **Error handling**: Implement robust error handling that logs detailed diagnostic information when entity lookup fails, including the actual and expected document structure.

5. **Two-phase lookup**: For robustness, consider implementing a two-phase lookup:
   - First try by FRN + Volume
   - If not found, try by file path + Volume as fallback
   - Create the entity if neither lookup succeeds

## Implementation Note

In `_update_entity_metadata`, we should modify the code to query for entities by FRN + Volume rather than expecting the UUID to already exist. This would avoid the "entity does not exist" errors when processing activities.
