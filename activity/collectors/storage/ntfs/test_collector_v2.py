"""
This module is a test wrapper for the NTFS activity data collector.

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
import inspect
import os
import sys
import time
import uuid

from datetime import datetime
from pathlib import Path

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
from activity.collectors.base import BaseActivityCollector
from activity.collectors.data_model import IndalekoActivityCollectorDataModel
from platforms.machine_config import IndalekoMachineConfig
from platforms.windows.machine_config import IndalekoWindowsMachineConfig
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel
from utils.cli.runner import IndalekoCLIRunner


# pylint: enable=wrong-import-position


class TestCollectorV2(BaseActivityCollector):
    """This is a test wrapper for the NTFS activity data collector."""

    collector_data = IndalekoActivityCollectorDataModel(
        PlatformName="Windows",
        ServiceRegistrationName="NTFS Test Collection V2",
        ServiceFileName="activity_collector",
        ServiceUUID=uuid.UUID("c53c339a-edba-4328-bfdf-0504ac9c0b35"),
        ServiceVersion="1.0",
        ServiceDescription="NTFS Test Activity Collector V2",
    )

    @classmethod
    def get_collector_service_registration_name(cls):
        """Get the collector service registration name."""
        return cls.collector_data.ServiceRegistrationName

    @classmethod
    def get_collector_service_file_name(cls):
        """Get the collector service file name."""
        return cls.collector_data.ServiceFileName

    @classmethod
    def get_collector_cli_handler_mixin(cls):
        """Get the collector CLI handler mixin."""
        return cls.cli_handler_mixin

    def __init__(self, **kwargs):
        """This is the constructor for the test collector."""
        for key, value in self.collector_data:
            if key not in kwargs:
                kwargs[key] = value
        if "platform" not in kwargs:
            kwargs["platform"] = "Windows"
        if "collector_data" not in kwargs:
            kwargs["collector_data"] = TestCollectorV2.collector_data

        # Import our actual NTFS collector implementation
        from activity.collectors.storage.ntfs.ntfs_collector_v2 import (
            NtfsStorageActivityCollectorV2,
        )

        # Create the NTFS collector that will do the actual work
        ntfs_collector_args = {}

        # Pass along relevant parameters
        if "volumes" in kwargs:
            ntfs_collector_args["volumes"] = kwargs["volumes"]
        if "path" in kwargs:
            # Extract drive letter from path if needed
            path = kwargs["path"]
            if path and len(path) >= 2 and path[1] == ":":
                ntfs_collector_args["volumes"] = [path[0] + ":"]

        ntfs_collector_args["auto_start"] = False  # We'll start it manually
        ntfs_collector_args["debug"] = kwargs.get("debug", False)

        try:
            # Add some extra parameters that might be needed
            if "timestamp" in kwargs and "timestamp" not in ntfs_collector_args:
                ntfs_collector_args["timestamp"] = kwargs["timestamp"]
            if "output_path" in kwargs and "output_path" not in ntfs_collector_args:
                ntfs_collector_args["output_path"] = kwargs["output_path"]
            if "machine_config" in kwargs and "machine_config" not in ntfs_collector_args:
                ntfs_collector_args["machine_config"] = kwargs["machine_config"]
            if "configdir" in kwargs and "config_dir" not in ntfs_collector_args:
                ntfs_collector_args["config_dir"] = kwargs["configdir"]

            # Add provider_id from our collector data
            ntfs_collector_args["provider_id"] = self.collector_data.ServiceUUID

            # Try to create the collector
            self.ntfs_collector = NtfsStorageActivityCollectorV2(**ntfs_collector_args)
        except Exception as e:
            print(f"Warning: Failed to create NTFS collector: {e}")
            import traceback

            traceback.print_exc()
            self.ntfs_collector = None

        # Save some parameters for later use
        self.drive = kwargs.get("drive", "C:")

        super().__init__(**kwargs)
        if not hasattr(self, "storage") and "storage" in kwargs:
            self.storage = kwargs["storage"]

    def collect_data(self):
        """Collect storage activity data using the NTFS collector."""
        if hasattr(self, "ntfs_collector") and self.ntfs_collector:
            # Check for admin rights - accessing USN journal typically requires this
            try:
                import ctypes

                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
                if not is_admin:
                    print("\n*** WARNING: Not running as administrator. ***")
                    print("*** USN Journal access typically requires admin rights. ***")
                    print(
                        "*** Consider running this script as administrator for best results. ***\n",
                    )
            except Exception:
                # Ignore if we can't check admin status
                pass

            # Start monitoring
            try:
                self.ntfs_collector.start_monitoring()
                print("Successfully started NTFS monitoring")
            except Exception as e:
                print(f"Error starting monitoring: {e}")
                import traceback

                traceback.print_exc()

            # Create some test files to generate activity
            try:
                # Get the drive from our parameters
                drive = "C:"
                if hasattr(self, "drive"):
                    drive = self.drive

                # Create a test directory if it doesn't exist
                test_dir = os.path.join(drive, "Indaleko_Test")
                os.makedirs(test_dir, exist_ok=True)

                # Create a few test files
                timestamp = int(time.time())
                for i in range(3):
                    test_file = os.path.join(test_dir, f"test_file_{timestamp}_{i}.txt")
                    with open(test_file, "w", encoding="utf-8") as f:
                        f.write(f"Test file created at {datetime.now()}\n")
                        f.write(f"This is test file {i+1} of 3\n")
                        f.flush()

                    # Read the file to generate read activity
                    with open(test_file, encoding="utf-8") as f:
                        _ = f.read()

                    # Modify the file to generate write activity
                    with open(test_file, "a", encoding="utf-8") as f:
                        f.write(f"Modified at {datetime.now()}\n")
                        f.flush()

                print(f"Created test files in {test_dir}")

                # Create and rename a file
                orig_name = os.path.join(test_dir, f"rename_test_{timestamp}.txt")
                with open(orig_name, "w", encoding="utf-8") as f:
                    f.write(f"Test file for renaming, created at {datetime.now()}\n")
                    f.flush()

                new_name = os.path.join(test_dir, f"renamed_{timestamp}.txt")
                os.rename(orig_name, new_name)
                print(f"Created and renamed file: {orig_name} -> {new_name}")

            except Exception as e:
                print(f"Error creating test files: {e}")
                import traceback

                traceback.print_exc()

            # Collect data from the NTFS collector
            try:
                self.ntfs_collector.collect_data()
                print("Successfully collected NTFS data")
            except Exception as e:
                print(f"Error collecting data: {e}")
                import traceback

                traceback.print_exc()
        else:
            print("Warning: NTFS collector not available")

    def get_activities(self):
        """Get the collected activities."""
        if hasattr(self, "ntfs_collector") and self.ntfs_collector:
            activities = self.ntfs_collector.get_activities()
            print(
                f"TestCollectorV2.get_activities(): Got {len(activities)} activities from ntfs_collector",
            )
            return activities
        else:
            print("TestCollectorV2.get_activities(): No ntfs_collector available")
        return []

    def stop_monitoring(self):
        """Stop monitoring for file system events."""
        if hasattr(self, "ntfs_collector") and self.ntfs_collector:
            self.ntfs_collector.stop_monitoring()

    class collector_mixin(IndalekoBaseCLI.default_handler_mixin):
        """This is the CLI handler mixin for the NTFS activity collector."""

        @staticmethod
        def get_pre_parser() -> argparse.ArgumentParser | None:
            """This method is used to get the pre-parser"""
            parser = argparse.ArgumentParser(add_help=False)
            default_drive = "C:"
            parser.add_argument(
                "--drive",
                help=f"Drive to monitor (default={default_drive})",
                type=str,
                default=default_drive,
            )
            # Add the path parameter for compatibility with the storage collector pattern
            parser.add_argument(
                "--path",
                help="Path to monitor (default is based on drive)",
                type=str,
            )
            return parser

        @staticmethod
        def load_machine_config(keys: dict[str, str]) -> IndalekoMachineConfig:
            """Load the machine configuration"""
            ic(keys)
            if keys.get("debug"):
                ic(f"load_machine_config: {keys}")
            if "machine_config_file" not in keys:
                raise ValueError(
                    f"{inspect.currentframe().f_code.co_name}: " "machine_config_file must be specified",
                )
            offline = keys.get("offline", False)
            platform_class = keys["class"]  # must exist
            return platform_class.load_config_from_file(
                config_file=str(keys["machine_config_file"]),
                offline=offline,
            )

    cli_handler_mixin = collector_mixin

    @staticmethod
    def local_run(keys: dict[str, str]) -> dict | None:
        """Run the test"""
        args = keys["args"]  # must be here
        cli = keys["cli"]  # must be here
        config_data = cli.get_config_data()
        debug = hasattr(args, "debug") and args.debug
        if debug:
            ic(config_data)
        machine_config_class = keys["parameters"]["MachineConfigClass"]
        collector_class = keys["parameters"]["CollectorClass"]

        # Determine the path to use
        path = None
        drive = "C:"

        if hasattr(args, "path") and args.path:
            path = args.path
            # Try to extract drive letter from path
            if path and len(path) >= 2 and path[1] == ":":
                drive = path[0] + ":"
        elif hasattr(args, "drive") and args.drive:
            drive = args.drive
            # Convert drive to a full path
            if drive.endswith(":"):
                path = f"{drive}\\"
            else:
                drive = f"{drive}:"
                path = f"{drive}\\"

        if debug:
            ic(f"Using path: {path}")
            ic(f"Using drive: {drive}")

        kwargs = {
            "machine_config": cli.handler_mixin.load_machine_config(
                {
                    "machine_config_file": str(
                        Path(args.configdir) / args.machine_config,
                    ),
                    "offline": args.offline,
                    "class": machine_config_class,
                },
            ),
            "timestamp": config_data["Timestamp"],
            "path": path,
            "drive": drive,
            "offline": args.offline,
            "volumes": [drive],
            "output_path": (
                os.path.join(args.datadir, config_data["OutputFile"]) if "OutputFile" in config_data else None
            ),
            "configdir": args.configdir,  # Pass the config directory for state persistence
        }
        collector = collector_class(**kwargs)
        ic(collector)

        # Actually collect some data
        try:
            # Start collecting data
            collector.collect_data()

            # Let it run for a bit longer to gather events
            print("\nWaiting for events to be collected (this may take 15 seconds)...")
            for i in range(15):
                time.sleep(1)
                print(".", end="", flush=True)

                # Create a new file every 5 seconds to generate more activity
                if i % 5 == 0:
                    try:
                        test_dir = os.path.join(drive, "Indaleko_Test")
                        if os.path.exists(test_dir):
                            test_file = os.path.join(
                                test_dir,
                                f"extra_test_{int(time.time())}.txt",
                            )
                            with open(test_file, "w") as f:
                                f.write(
                                    f"Extra test file created at {datetime.now()}\n",
                                )
                            print(f"\nCreated extra test file: {test_file}")
                    except Exception as e:
                        print(f"\nError creating extra test file: {e}")

            print("\nFinished waiting. Checking for collected activities...")

            # Get the activities
            activities = collector.get_activities()
            print(f"Collector reports {len(activities)} activities collected")
            print(f"Collector object: {collector}")

            # If activities is empty but the collector has internal activities, use those
            if len(activities) == 0 and hasattr(collector, "ntfs_collector"):
                print("Checking internal NTFS collector directly...")
                if collector.ntfs_collector:
                    direct_activities = collector.ntfs_collector.get_activities()
                    print(
                        f"Internal NTFS collector has {len(direct_activities)} activities",
                    )
                    activities = direct_activities

            # Print out what we found
            if debug or True:  # Always show activities for now
                print(f"\nCollected {len(activities)} activities:")
                for i, activity in enumerate(activities[:10], 1):  # Show first 10
                    print(
                        f"{i}. {activity.file_name} - {activity.activity_type} - {activity.timestamp}",
                    )

                if len(activities) > 10:
                    print(f"... and {len(activities) - 10} more")

            # Stop monitoring
            collector.stop_monitoring()

            return {"activities": activities}

        except Exception as e:
            import traceback

            print(f"Error collecting data: {e}")
            traceback.print_exc()
            return None

    @staticmethod
    def local_collector_runner(
        collector_class: "TestCollectorV2",
        machine_config_class: IndalekoMachineConfig,
    ) -> None:
        """This is the CLI handler for local storage collectors."""
        IndalekoCLIRunner(
            cli_data=IndalekoBaseCliDataModel(
                RegistrationServiceName=collector_class.get_collector_service_registration_name(),
                FileServiceName=collector_class.get_collector_service_file_name(),
            ),
            handler_mixin=collector_class.get_collector_cli_handler_mixin(),
            features=IndalekoBaseCLI.cli_features(input=False),
            Run=TestCollectorV2.local_run,
            RunParameters={
                "CollectorClass": collector_class,
                "MachineConfigClass": machine_config_class,
            },
        ).run()


def main():
    """The CLI handler for the NTFS activity collector test."""
    TestCollectorV2.local_collector_runner(
        TestCollectorV2,
        IndalekoWindowsMachineConfig,
    )


if __name__ == "__main__":
    main()
