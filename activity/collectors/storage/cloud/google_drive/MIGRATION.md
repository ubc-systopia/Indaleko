# Google Drive Collector Migration

This document outlines the restructuring of the Google Drive collector to follow a more consistent organizational pattern.

## Changes Made

1. Created a dedicated `google_drive` directory structure:
   - `/activity/collectors/storage/cloud/google_drive/`
   - `/activity/collectors/storage/cloud/google_drive/data_models/`
   - `/activity/collectors/storage/cloud/google_drive/examples/`

2. Renamed files for consistency:
   - `gdrive_activity_collector.py` → `google_drive_collector.py`
   - `gdrive_activity_model.py` → `google_drive_activity_model.py`
   - `gdrive_example.py` → `google_drive_example.py`
   - `test_gdrive_collector.py` → `test_google_drive_collector.py`

3. Updated imports in all files to reflect new structure:
   - Updated Google Drive collector imports
   - Updated data model imports
   - Kept OAuth utils at cloud level as shared functionality

4. Created proper __init__.py files:
   - Main `google_drive/__init__.py` with key exports
   - Data models `data_models/__init__.py` with model exports
   - Examples `examples/__init__.py`

5. Created comprehensive documentation:
   - Added a detailed README.md
   - Created this MIGRATION.md to document changes

6. Updated recorder structure:
   - Moved recorder to `/activity/recorders/storage/cloud/google_drive/`
   - Updated imports in recorder
   - Created `__init__.py` for the recorder directory

## Testing

To test the new structure, you can run:

```bash
# Test organizational structure
python -m activity.collectors.storage.cloud.google_drive.examples.test_organization

# Run the example script
python -m activity.collectors.storage.cloud.google_drive.examples.google_drive_example --test-oauth
```

## Original Files

The original files still exist in their old locations:
- `/activity/collectors/storage/cloud/gdrive_activity_collector.py`
- `/activity/collectors/storage/cloud/data_models/gdrive_activity_model.py`
- `/activity/collectors/storage/cloud/examples/gdrive_example.py`
- `/activity/collectors/storage/cloud/test_gdrive_collector.py`

Once the new structure is confirmed working, these files can be removed.

## Next Steps

1. Test the new structure thoroughly
2. Update any references to the old structure in other code
3. Remove the original files once everything is confirmed working
4. Apply similar restructuring to other collectors (Dropbox, etc.)