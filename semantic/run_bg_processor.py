#!/usr/bin/env python3
"""
Windows service wrapper for Indaleko's semantic background processor.

This script can be:
1. Run directly to start the background processor
2. Installed as a Windows service using NSSM
3. Added to Task Scheduler for periodic execution

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
import atexit
import logging
import os
import signal
import subprocess
import sys


# Ensure INDALEKO_ROOT is set
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# Configure logging to file
log_dir = os.path.join(os.environ["INDALEKO_ROOT"], "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "indaleko_bg_service.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
)
logger = logging.getLogger("IndalekoBgService")


class BackgroundProcessorService:
    """Service wrapper for the background processor."""

    def __init__(self, config_path=None, python_exe=None) -> None:
        """Initialize the service."""
        self.config_path = config_path
        self.python_exe = python_exe or sys.executable
        self.process = None
        self.stopping = False

        # Register cleanup handlers
        atexit.register(self.cleanup)
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def _handle_signal(self, signum, frame) -> None:
        """Handle termination signals."""
        logger.info(f"Received signal {signum}, stopping service...")
        self.stop()

    def start(self) -> None:
        """Start the background processor."""
        logger.info("Starting Indaleko background processor service")

        try:
            # Build command
            cmd = [self.python_exe, "-m", "semantic.background_processor"]

            if self.config_path:
                cmd.extend(["--config", self.config_path])

            # Add default stats file in the logs directory
            stats_file = os.path.join(log_dir, "bg_processor_stats.json")
            cmd.extend(["--stats-file", stats_file])

            logger.info(f"Running command: {' '.join(cmd)}")

            # Start the process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
            )

            # Log process output
            logger.info(f"Background processor started with PID {self.process.pid}")

            # Monitor the process output
            while self.process.poll() is None and not self.stopping:
                line = self.process.stdout.readline()
                if line:
                    logger.info(f"BG: {line.strip()}")

            # Check if process exited
            if self.process.poll() is not None:
                logger.info(
                    f"Background processor exited with code {self.process.returncode}",
                )

        except Exception as e:
            logger.error(f"Error starting background processor: {e}", exc_info=True)

    def stop(self) -> None:
        """Stop the background processor."""
        self.stopping = True

        if self.process and self.process.poll() is None:
            logger.info("Stopping background processor...")

            try:
                # Send termination signal
                self.process.terminate()

                # Wait for process to exit
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning("Process did not terminate gracefully, forcing...")
                    self.process.kill()

            except Exception as e:
                logger.exception(f"Error stopping background processor: {e}")

        logger.info("Background processor service stopped")

    def cleanup(self) -> None:
        """Cleanup resources on exit."""
        self.stop()


def main() -> None:
    """Main function for the service wrapper."""
    parser = argparse.ArgumentParser(
        description="Indaleko Background Processor Service",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "bg_processor_config.json"),
        help="Path to configuration file",
    )
    parser.add_argument(
        "--python",
        type=str,
        default=None,
        help="Path to Python executable (defaults to current Python)",
    )
    parser.add_argument(
        "--install-service",
        action="store_true",
        help="Install as a Windows service (requires NSSM utility)",
    )
    parser.add_argument(
        "--uninstall-service",
        action="store_true",
        help="Uninstall the Windows service (requires NSSM utility)",
    )
    parser.add_argument(
        "--service-name",
        type=str,
        default="IndalekoBackgroundProcessor",
        help="Service name when installing/uninstalling",
    )
    parser.add_argument(
        "--install-task",
        action="store_true",
        help="Install as a Windows scheduled task",
    )
    parser.add_argument(
        "--uninstall-task",
        action="store_true",
        help="Uninstall the Windows scheduled task",
    )
    parser.add_argument(
        "--task-name",
        type=str,
        default="IndalekoBackgroundProcessor",
        help="Task name when installing/uninstalling",
    )

    args = parser.parse_args()

    # Handle service installation
    if args.install_service:
        install_windows_service(args.service_name, args.config, args.python)
        return

    # Handle service uninstallation
    if args.uninstall_service:
        uninstall_windows_service(args.service_name)
        return

    # Handle task installation
    if args.install_task:
        install_scheduled_task(args.task_name, args.config, args.python)
        return

    # Handle task uninstallation
    if args.uninstall_task:
        uninstall_scheduled_task(args.task_name)
        return

    # Run the service
    service = BackgroundProcessorService(args.config, args.python)
    service.start()


def install_windows_service(service_name, config_path, python_exe) -> None:
    """Install as a Windows service using NSSM."""
    try:
        import shutil

        nssm_path = shutil.which("nssm.exe")
        if not nssm_path:
            logger.error(
                "NSSM utility not found in PATH. Please install NSSM to install as a service.",
            )
            logger.error("Download from http://nssm.cc/download")
            return

        # Get absolute paths
        script_path = os.path.abspath(__file__)
        config_path = os.path.abspath(config_path)
        python_exe = python_exe or sys.executable

        # Build installation command
        cmd = [
            nssm_path,
            "install",
            service_name,
            python_exe,
            script_path,
            "--config",
            config_path,
        ]

        logger.info(f"Installing service: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        # Configure service details
        subprocess.run(
            [
                nssm_path,
                "set",
                service_name,
                "DisplayName",
                "Indaleko Background Processor",
            ],
            check=True,
        )
        subprocess.run(
            [
                nssm_path,
                "set",
                service_name,
                "Description",
                "Performs background semantic data extraction for Indaleko",
            ],
            check=True,
        )
        subprocess.run(
            [nssm_path, "set", service_name, "Start", "SERVICE_DELAYED_AUTO_START"],
            check=True,
        )

        logger.info(f"Service '{service_name}' installed successfully")
        logger.info("To start the service, run: nssm start " + service_name)

    except Exception as e:
        logger.exception(f"Error installing service: {e}")


def uninstall_windows_service(service_name) -> None:
    """Uninstall a Windows service using NSSM."""
    try:
        import shutil

        nssm_path = shutil.which("nssm.exe")
        if not nssm_path:
            logger.error(
                "NSSM utility not found in PATH. Please install NSSM to uninstall the service.",
            )
            return

        # Stop the service first
        subprocess.run([nssm_path, "stop", service_name], check=False)

        # Remove the service
        cmd = [nssm_path, "remove", service_name, "confirm"]
        logger.info(f"Uninstalling service: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        logger.info(f"Service '{service_name}' uninstalled successfully")

    except Exception as e:
        logger.exception(f"Error uninstalling service: {e}")


def install_scheduled_task(task_name, config_path, python_exe) -> None:
    """Install as a Windows scheduled task."""
    try:
        # Get absolute paths
        script_path = os.path.abspath(__file__)
        config_path = os.path.abspath(config_path)
        python_exe = python_exe or sys.executable

        # Build the task command

        # Create XML for the task
        xml_content = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.4" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Indaleko Background Semantic Processor</Description>
    <URI>\\{task_name}</URI>
  </RegistrationInfo>
  <Triggers>
    <LogonTrigger>
      <Enabled>true</Enabled>
      <Delay>PT1M</Delay>
    </LogonTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>false</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <DisallowStartOnRemoteAppSession>false</DisallowStartOnRemoteAppSession>
    <UseUnifiedSchedulingEngine>true</UseUnifiedSchedulingEngine>
    <WakeToRun>false</WakeToRun>
    <ExecutionTimeLimit>PT0S</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{script_path}" --config "{config_path}"</Arguments>
      <WorkingDirectory>{os.path.dirname(script_path)}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>
"""

        # Save XML to temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as temp:
            temp_path = temp.name
            temp.write(xml_content.encode("utf-16"))

        try:
            # Create the task
            cmd = ["schtasks", "/create", "/tn", task_name, "/xml", temp_path, "/f"]
            logger.info(f"Installing scheduled task: {' '.join(cmd)}")
            subprocess.run(cmd, check=True)

            logger.info(f"Scheduled task '{task_name}' installed successfully")
            logger.info("To run the task now: schtasks /run /tn " + task_name)

        finally:
            # Clean up temp file
            os.unlink(temp_path)

    except Exception as e:
        logger.exception(f"Error installing scheduled task: {e}")


def uninstall_scheduled_task(task_name) -> None:
    """Uninstall a Windows scheduled task."""
    try:
        # Remove the task
        cmd = ["schtasks", "/delete", "/tn", task_name, "/f"]
        logger.info(f"Uninstalling scheduled task: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)

        logger.info(f"Scheduled task '{task_name}' uninstalled successfully")

    except Exception as e:
        logger.exception(f"Error uninstalling scheduled task: {e}")


if __name__ == "__main__":
    main()
