#!/bin/bash
# Script to remove the old NTFS activity implementation
# while preserving README files for reference

# Create backup directories
mkdir -p backup/ntfs_activity/collectors
mkdir -p backup/ntfs_activity/recorders

# Copy README files to backup
cp /mnt/c/Users/TonyMason/source/repos/indaleko/activity/collectors/ntfs_activity/README.md backup/ntfs_activity/collectors/
cp /mnt/c/Users/TonyMason/source/repos/indaleko/activity/recorders/ntfs_activity/README.md backup/ntfs_activity/recorders/

# Create a simple README explaining what happened
cat > backup/ntfs_activity/README.md << 'EOF'
# Old NTFS Activity Implementation

This directory contains backup information from the old NTFS activity implementation
that was replaced by the new standardized storage activity collector/recorder pattern.

The new implementation can be found in:
- `/activity/collectors/storage/ntfs/` - Collector
- `/activity/recorders/storage/ntfs/` - Recorder

The old implementation was removed on $(date) to avoid confusion, but README files
have been preserved here for reference.

If you need to recover the complete implementation, you can find it in git history.
EOF

# Remove the old implementation
rm -rf /mnt/c/Users/TonyMason/source/repos/indaleko/activity/collectors/ntfs_activity
rm -rf /mnt/c/Users/TonyMason/source/repos/indaleko/activity/recorders/ntfs_activity

echo "Old NTFS activity implementation removed."
echo "README files have been backed up to backup/ntfs_activity/"
echo "You can use git to restore the implementation if needed."
