#!/usr/bin/env python
"""
Test script for NTFS Activity Context Integration.

This script tests the integration between NTFS storage activity
and the Indaleko Activity Context system.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import argparse
import logging
import os
import sys
import time
import uuid
from datetime import UTC, datetime

# Set up environment
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from activity.collectors.storage.data_models.storage_activity_data_model import (
    NtfsStorageActivityData,
    StorageActivityType,
)
from activity.context.service import IndalekoActivityContextService
from activity.recorders.storage.ntfs.activity_context_integration import (
    NtfsActivityContextIntegration,
)
from activity.recorders.storage.ntfs.ntfs_recorder import NtfsStorageActivityRecorder

# pylint: enable=wrong-import-position


def create_mock_activity(file_name: str, activity_type: str) -> NtfsStorageActivityData:
    """Create a mock NTFS storage activity."""
    return NtfsStorageActivityData(
        activity_id=uuid.uuid4(),
        activity_type=activity_type,
        file_name=file_name,
        file_path=f"C:\\Test\\{file_name}",
        volume_name="C:",
        timestamp=datetime.now(UTC),
        process_name="test_process",
        process_id=1234,
        file_reference_number=str(int(time.time())),
        parent_file_reference_number="0",
        reason_flags=1,
        usn=12345,
        provider_id=str(uuid.uuid4()),
    )


def test_integration_directly():
    """Test activity context integration directly."""
    logging.info("Testing NtfsActivityContextIntegration directly")

    # Create integration
    integration = NtfsActivityContextIntegration(debug=True)

    # Check if context is available
    if not integration.is_context_available():
        logging.warning("Activity context service is not available")
        return

    # Get activity handle
    handle = integration.get_activity_handle()
    logging.info(f"Activity handle: {handle}")

    # Create test activities
    activities = [
        create_mock_activity("test1.docx", StorageActivityType.CREATE),
        create_mock_activity("test2.xlsx", StorageActivityType.MODIFY),
        create_mock_activity("test3.pptx", StorageActivityType.RENAME),
    ]

    # Associate with context
    for i, activity in enumerate(activities):
        enhanced = integration.associate_with_activity_context(activity)
        logging.info(
            f"Enhanced activity {i+1}: {enhanced.get('activity_context_handle') if isinstance(enhanced, dict) else 'No handle'}",
        )

    # Test batch update
    updates = integration.batch_update_context(activities)
    logging.info(f"Batch updates: {updates}")

    # Write context to database
    service = IndalekoActivityContextService()
    result = service.write_activity_context_to_database()
    logging.info(f"Write to database: {result}")

    # Retrieve latest context
    context_data = IndalekoActivityContextService.get_latest_db_update_dict()
    if context_data:
        logging.info(f"Retrieved context with handle: {context_data.get('Handle')}")
        cursors = context_data.get("Cursors", [])
        logging.info(f"Context has {len(cursors)} cursors")
        for cursor in cursors:
            if cursor.get("Provider") == str(
                NtfsActivityContextIntegration.NTFS_CONTEXT_PROVIDER_ID,
            ):
                logging.info(f"Found NTFS cursor: {cursor}")
    else:
        logging.warning("No context data found in database")


def test_integration_with_recorder(use_hot_tier: bool = False):
    """Test activity context integration with NTFS recorder."""
    logging.info(f"Testing with {'hot tier' if use_hot_tier else 'standard'} recorder")

    # Create recorder
    if use_hot_tier:
        # Import hot tier recorder dynamically to avoid load-time dependency
        from activity.recorders.storage.ntfs.tiered.hot.recorder import (
            NtfsHotTierRecorder,
        )

        recorder = NtfsHotTierRecorder(debug=True)
    else:
        recorder = NtfsStorageActivityRecorder(debug=True)

    # Create test activities
    activities = [
        create_mock_activity("recorder_test1.docx", StorageActivityType.CREATE),
        create_mock_activity("recorder_test2.xlsx", StorageActivityType.MODIFY),
        create_mock_activity("recorder_test3.pptx", StorageActivityType.RENAME),
    ]

    # Store activities
    activity_ids = recorder.store_activities(activities)
    logging.info(f"Stored {len(activity_ids)} activities")

    # Verify context integration
    service = IndalekoActivityContextService()
    context_data = IndalekoActivityContextService.get_latest_db_update_dict()
    if context_data:
        logging.info(f"Retrieved context with handle: {context_data.get('Handle')}")
        cursors = context_data.get("Cursors", [])
        logging.info(f"Context has {len(cursors)} cursors")
        ntfs_cursors = [
            cursor
            for cursor in cursors
            if cursor.get("Provider") == str(NtfsActivityContextIntegration.NTFS_CONTEXT_PROVIDER_ID)
        ]
        logging.info(f"Found {len(ntfs_cursors)} NTFS cursors")
    else:
        logging.warning("No context data found in database")


def main():
    """Main function for testing NTFS Activity Context Integration."""
    parser = argparse.ArgumentParser(
        description="Test NTFS Activity Context Integration",
    )
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Test integration directly",
    )
    parser.add_argument(
        "--recorder",
        action="store_true",
        help="Test with standard recorder",
    )
    parser.add_argument(
        "--hot-tier",
        action="store_true",
        help="Test with hot tier recorder",
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Print banner
    print("=" * 70)
    print("NTFS Activity Context Integration Test")
    print("=" * 70)

    # Run tests
    if args.all or args.direct:
        print("\nTesting direct integration...")
        test_integration_directly()

    if args.all or args.recorder:
        print("\nTesting with standard recorder...")
        test_integration_with_recorder(use_hot_tier=False)

    if args.all or args.hot_tier:
        print("\nTesting with hot tier recorder...")
        test_integration_with_recorder(use_hot_tier=True)

    # Summary
    print("\nAll tests completed")


if __name__ == "__main__":
    main()
