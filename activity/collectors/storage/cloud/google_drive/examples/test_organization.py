# \!/usr/bin/env python3
"""
Google Drive organization test.

This script tests the new organizational structure for Google Drive collectors.
"""

import os
import sys


# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


def main():
    """Main entry point."""

    try:
        # Import Google Drive collector
        # Import data models
        from activity.collectors.storage.cloud.google_drive.data_models import (
            GDriveActivityData,
            GDriveActivityType,
        )
        from activity.collectors.storage.cloud.google_drive.google_drive_collector import (
            GoogleDriveActivityCollector,
        )

        # Import OAuth utils
        from activity.collectors.storage.cloud.oauth_utils import GoogleOAuthManager


        return 0
    except ImportError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
