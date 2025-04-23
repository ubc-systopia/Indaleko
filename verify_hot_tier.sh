#!/bin/bash
# Root wrapper script for Hot Tier Recorder verification
# This script calls the verify_hot_tier.sh script in the appropriate directory

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Call the actual verification script
"$SCRIPT_DIR/activity/recorders/storage/ntfs/tiered/hot/verify_hot_tier.sh" "$@"
