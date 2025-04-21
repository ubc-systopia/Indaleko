# Storage Activity Collection Restructuring Plan

## Current Issues
The current organizational structure for storage activity collectors is inconsistent:
- Google Drive example is under `activity/collectors/storage/cloud/examples/`
- Dropbox example is under a different path
- There's no clear separation between cloud and local storage providers
- The organization doesn't follow a consistent pattern

## Proposed Structure
We propose reorganizing the storage activity collectors with the following structure:

```
activity/collectors/storage/
├── cloud/                    # All cloud storage providers
│   ├── dropbox/              # Dropbox specific code
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── data_models/      # Data models specific to Dropbox
│   │   ├── dropbox_collector.py
│   │   └── examples/         # Dropbox examples
│   │
│   ├── google_drive/         # Google Drive specific code
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── data_models/      # Data models specific to Google Drive
│   │   ├── google_drive_collector.py
│   │   └── examples/         # Google Drive examples
│   │
│   ├── onedrive/             # OneDrive specific code (future)
│   │   ├── README.md
│   │   ├── __init__.py
│   │   ├── data_models/
│   │   └── onedrive_collector.py
│   │
│   ├── __init__.py           # Common cloud storage functionality
│   ├── data_models/          # Shared data models for cloud storage
│   └── oauth_utils.py        # Shared OAuth utilities
│
├── local/                    # All local storage providers
│   ├── windows/              # Windows-specific collectors
│   │   ├── ntfs/             # NTFS specific code
│   │   │   ├── README.md
│   │   │   ├── __init__.py
│   │   │   ├── data_models/
│   │   │   └── ntfs_collector.py
│   │   ├── __init__.py
│   │   └── collector.py      # General Windows collector
│   │
│   ├── mac/                  # macOS specific collectors (future)
│   │   ├── __init__.py
│   │   └── collector.py
│   │
│   ├── linux/                # Linux specific collectors (future)
│   │   ├── __init__.py
│   │   └── collector.py
│   │
│   └── __init__.py           # Common local storage functionality
│
├── __init__.py               # Common functionality for all storage collectors
├── base.py                   # Base classes for storage collectors
└── data_models/              # Common data models for all storage activities
```

## File Movement Plan

### 1. Google Drive Files
- Move `gdrive_activity_collector.py` → `google_drive/google_drive_collector.py`
- Move cloud-specific data models to `google_drive/data_models/`
- Move example to `google_drive/examples/google_drive_example.py`
- Create a proper README.md in the google_drive directory

### 2. Dropbox Files
- Move files to match the new structure
- Reorganize examples to be in `dropbox/examples/`

### 3. OAuth Utilities
- Keep `oauth_utils.py` at the cloud level as it's shared across cloud providers
- Update imports in all files to reflect the new structure

### 4. NTFS Files
- Ensure they follow the `local/windows/ntfs` structure
- Update any examples to be in the appropriate example folders

## Implementation Steps

1. Create the new directory structure
2. Move files to their new locations
3. Update imports in all affected files
4. Update any path references in documentation
5. Update examples to use the new structure
6. Test that everything works with the new structure

## Benefits

- Consistent organization makes the codebase easier to navigate
- Clear separation between cloud and local providers
- Easier to add new providers in the future (e.g., Box, iCloud)
- Better isolation of provider-specific code and dependencies
- Examples are consistently located relative to their collectors