"""
This module provides a performance monitoring framework for semantic extractors.

DESIGN NOTE:
This implementation currently uses a custom machine identification mechanism 
rather than Indaleko's relationship model. In the future, it should be updated 
to use the proper device-file relationship (UUID: f3dde8a2-cff5-41b9-bd00-0f41330895e1)
as defined in storage/i_relationship.py. 

IMPORTANT: Storage recorders should be adding this relationship between devices and files.
This is critical because semantic extractors should ONLY run on the machine where the 
data is physically stored. The device-file relationship is necessary to enforce this
constraint and ensure efficient extraction without unnecessary network transfers.

The current approach was chosen because these relationships were not consistently
available in the existing data files.

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

import os
import sys
import time
import uuid
import logging
import functools
import psutil
import platform
import socket
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Callable, Union, List, Tuple

# Import path setup
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from perf.perf_recorder import IndalekoPerformanceDataRecorder
from data_models.i_perf import IndalekoPerformanceDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from utils.singleton import IndalekoSingleton as Singleton
from constants import IndalekoConstants

# pylint: enable=wrong-import-position

def get_machine_id() -> uuid.UUID:
    """
    Get the UUID that identifies the current machine.
    
    FUTURE IMPROVEMENT:
    In the future, this function should be replaced with a mechanism that
    leverages Indaleko's existing device-file relationships (relationship UUID: 
    f3dde8a2-cff5-41b9-bd00-0f41330895e1). This would provide better integration
    with the rest of the Indaleko data model and ensure consistent machine 
    identification across the system.
    
    Current implementation tries several strategies to identify the machine:
    1. Load from config file if available
    2. Generate based on hardware info (platform-specific)
    3. Generate based on hostname and basic system info
    
    Returns:
        uuid.UUID: A UUID that uniquely identifies this machine
    """
    # First try to load from config file
    config_dir = IndalekoConstants.default_config_dir
    machine_id_file = os.path.join(config_dir, "machine_id.txt")
    
    if os.path.exists(machine_id_file):
        try:
            with open(machine_id_file, 'r') as f:
                machine_id_str = f.read().strip()
                return uuid.UUID(machine_id_str)
        except Exception as e:
            logging.warning(f"Error reading machine ID from file: {e}")
    
    # Platform-specific ID generation
    if platform.system() == "Windows":
        try:
            # Try to get Windows machine GUID from registry
            import winreg
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Microsoft\Cryptography") as key:
                machine_guid = winreg.QueryValueEx(key, "MachineGuid")[0]
                return uuid.UUID(machine_guid)
        except Exception as e:
            logging.warning(f"Could not get Windows MachineGuid: {e}")
    
    elif platform.system() == "Darwin":  # macOS
        try:
            # Try to get Hardware UUID on macOS
            import subprocess
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True, text=True, check=True
            )
            for line in result.stdout.splitlines():
                if "Hardware UUID" in line:
                    hw_uuid = line.split(":", 1)[1].strip()
                    return uuid.UUID(hw_uuid)
        except Exception as e:
            logging.warning(f"Could not get macOS Hardware UUID: {e}")
    
    elif platform.system() == "Linux":
        try:
            # Try to use machine-id on Linux
            with open("/etc/machine-id", "r") as f:
                machine_id = f.read().strip()
                # machine-id is 32 hex chars, but UUID needs 32 + 4 hyphens
                if len(machine_id) == 32:
                    machine_id = (
                        machine_id[:8] + "-" + machine_id[8:12] + "-" + 
                        machine_id[12:16] + "-" + machine_id[16:20] + "-" + 
                        machine_id[20:]
                    )
                return uuid.UUID(machine_id)
        except Exception as e:
            logging.warning(f"Could not get Linux machine-id: {e}")
    
    # Fallback: Generate a stable ID based on hostname and system info
    hostname = socket.gethostname()
    cpu_info = platform.processor()
    system_info = platform.system() + platform.release()
    
    # Create a stable UUID based on system information
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # DNS namespace
    name = f"{hostname}:{cpu_info}:{system_info}"
    
    machine_id = uuid.uuid5(namespace, name)
    
    # Store in config file for future use
    try:
        os.makedirs(config_dir, exist_ok=True)
        with open(machine_id_file, 'w') as f:
            f.write(str(machine_id))
    except Exception as e:
        logging.warning(f"Could not save machine ID to file: {e}")
    
    return machine_id


class SemanticExtractorPerformance(metaclass=Singleton):
    """
    Performance monitoring framework for semantic extractors.
    
    This class provides monitoring capabilities for semantic metadata extraction
    operations, tracking metrics such as extraction time, resource usage, and throughput.
    It leverages Indaleko's existing performance monitoring infrastructure.
    
    This is implemented as a singleton to ensure consistent access across
    different parts of the application.
    """

    def __init__(self, **kwargs):
        """Initialize the performance monitor."""
        self._provider_id = kwargs.get(
            "provider_id", uuid.UUID("f7a5b3e9-1c2d-4e8f-a9b0-c5d3e1f2a8d4")
        )
        self._description = "Semantic Extractor Performance Monitor"
        self._enabled = kwargs.get("enabled", True)
        self._perf_recorder = IndalekoPerformanceDataRecorder()
        self._record_to_db = kwargs.get("record_to_db", True)
        self._record_to_file = kwargs.get("record_to_file", False)
        self._perf_file_name = kwargs.get("perf_file_name", None)
        
        if self._record_to_file and not self._perf_file_name:
            self._perf_file_name = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "..",
                "data",
                "semantic_extractor_perf.jsonl"
            )
        
        # Automatically detect machine configuration ID if not provided
        self._machine_config_id = None
        if "machine_config_id" in kwargs:
            self._machine_config_id = kwargs["machine_config_id"]
        else:
            # Auto-detect machine ID
            try:
                self._machine_config_id = get_machine_id()
                logging.info(f"Auto-detected machine ID: {self._machine_config_id}")
            except Exception as e:
                logging.warning(f"Could not auto-detect machine ID: {e}")
        
        # Statistics dictionary
        self._stats = {
            "total_files": 0,
            "total_bytes": 0,
            "total_processing_time": 0.0,
            "extractor_stats": {},
            "machine_id": str(self._machine_config_id) if self._machine_config_id else None,
            "platform": platform.system(),
            "hostname": socket.gethostname(),
        }
        
        # File type statistics
        self._file_type_stats = {}
        
        logging.info(f"Semantic Extractor Performance Monitor initialized on {platform.system()} host {socket.gethostname()}")

    def is_enabled(self) -> bool:
        """Check if performance monitoring is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable performance monitoring."""
        self._enabled = True

    def disable(self) -> None:
        """Disable performance monitoring."""
        self._enabled = False
    
    def reset_stats(self) -> None:
        """Reset all accumulated statistics."""
        self._stats = {
            "total_files": 0,
            "total_bytes": 0,
            "total_processing_time": 0.0,
            "extractor_stats": {},
        }
        self._file_type_stats = {}
    
    def get_stats(self) -> Dict[str, Any]:
        """Get accumulated statistics."""
        # Calculate derived metrics
        stats = self._stats.copy()
        
        # Calculate average processing time per file
        if stats["total_files"] > 0:
            stats["avg_processing_time"] = stats["total_processing_time"] / stats["total_files"]
            stats["bytes_per_second"] = stats["total_bytes"] / stats["total_processing_time"] if stats["total_processing_time"] > 0 else 0
            stats["files_per_second"] = stats["total_files"] / stats["total_processing_time"] if stats["total_processing_time"] > 0 else 0
        
        # Add file type statistics
        stats["file_type_stats"] = self._file_type_stats
        
        return stats
    
    def start_monitoring(self, extractor_name: str, file_path: Optional[str] = None, 
                          file_size: Optional[int] = None, 
                          mime_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Start monitoring a semantic extraction process.
        
        Args:
            extractor_name: Name of the extractor being monitored
            file_path: Path to the file being processed (optional)
            file_size: Size of the file in bytes (optional)
            mime_type: MIME type of the file (optional)
            
        Returns:
            Dict containing the monitoring context
        """
        if not self._enabled:
            return {"enabled": False}
        
        # Get file size if path is provided but size isn't
        if file_path and file_size is None:
            try:
                file_size = os.path.getsize(file_path)
            except (OSError, FileNotFoundError) as e:
                logging.warning(f"Error getting file size for {file_path}: {e}")
                file_size = 0
        
        # Initialize extractor stats if needed
        if extractor_name not in self._stats["extractor_stats"]:
            self._stats["extractor_stats"][extractor_name] = {
                "files_processed": 0,
                "bytes_processed": 0,
                "total_time": 0.0,
                "success_count": 0,
                "error_count": 0,
            }
        
        # Track MIME type statistics if provided
        if mime_type:
            if mime_type not in self._file_type_stats:
                self._file_type_stats[mime_type] = {
                    "count": 0,
                    "total_bytes": 0,
                    "total_time": 0.0,
                }
        
        # Create monitoring context
        context = {
            "enabled": True,
            "start_time": time.time(),
            "extractor_name": extractor_name,
            "file_path": file_path,
            "file_size": file_size,
            "mime_type": mime_type,
            "process": psutil.Process(),
            "start_cpu_times": psutil.Process().cpu_times(),
            "start_io_counters": psutil.Process().io_counters() if hasattr(psutil.Process(), 'io_counters') else None,
            "start_memory_info": psutil.Process().memory_info(),
        }
        
        return context
    
    def stop_monitoring(self, context: Dict[str, Any], success: bool = True, 
                        additional_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Stop monitoring a semantic extraction process and record metrics.
        
        Args:
            context: Monitoring context from start_monitoring
            success: Whether the extraction was successful
            additional_data: Additional data to include in the performance record
            
        Returns:
            Dict containing performance metrics
        """
        if not context.get("enabled", False):
            return {}
        
        # Calculate elapsed time
        end_time = time.time()
        elapsed_time = end_time - context["start_time"]
        
        # Get extractor information
        extractor_name = context["extractor_name"]
        file_path = context.get("file_path")
        file_size = context.get("file_size", 0)
        mime_type = context.get("mime_type")
        
        # Get resource usage
        process = context["process"]
        end_cpu_times = process.cpu_times()
        user_cpu_time = end_cpu_times.user - context["start_cpu_times"].user
        system_cpu_time = end_cpu_times.system - context["start_cpu_times"].system
        
        # Get I/O counters if available
        io_stats = {}
        if context["start_io_counters"] and hasattr(process, 'io_counters'):
            end_io_counters = process.io_counters()
            io_stats = {
                "read_count": end_io_counters.read_count - context["start_io_counters"].read_count,
                "write_count": end_io_counters.write_count - context["start_io_counters"].write_count,
                "read_bytes": end_io_counters.read_bytes - context["start_io_counters"].read_bytes,
                "write_bytes": end_io_counters.write_bytes - context["start_io_counters"].write_bytes,
            }
        
        # Get memory usage
        end_memory_info = process.memory_info()
        memory_stats = {
            "rss_delta": end_memory_info.rss - context["start_memory_info"].rss,
            "vms_delta": end_memory_info.vms - context["start_memory_info"].vms,
            "peak_rss": end_memory_info.rss,
            "peak_vms": end_memory_info.vms,
        }
        
        # Update statistics
        self._stats["total_files"] += 1
        self._stats["total_bytes"] += file_size if file_size else 0
        self._stats["total_processing_time"] += elapsed_time
        
        extractor_stats = self._stats["extractor_stats"][extractor_name]
        extractor_stats["files_processed"] += 1
        extractor_stats["bytes_processed"] += file_size if file_size else 0
        extractor_stats["total_time"] += elapsed_time
        if success:
            extractor_stats["success_count"] += 1
        else:
            extractor_stats["error_count"] += 1
        
        # Update file type statistics
        if mime_type:
            if mime_type not in self._file_type_stats:
                self._file_type_stats[mime_type] = {
                    "count": 0,
                    "total_bytes": 0,
                    "total_time": 0.0,
                }
            
            mime_stats = self._file_type_stats[mime_type]
            mime_stats["count"] += 1
            mime_stats["total_bytes"] += file_size if file_size else 0
            mime_stats["total_time"] += elapsed_time
        
        # Create metrics dictionary
        metrics = {
            "extractor_name": extractor_name,
            "file_path": file_path,
            "file_size": file_size,
            "mime_type": mime_type,
            "elapsed_time": elapsed_time,
            "success": success,
            "user_cpu_time": user_cpu_time,
            "system_cpu_time": system_cpu_time,
            "io_stats": io_stats,
            "memory_stats": memory_stats,
            "timestamp": datetime.now(timezone.utc),
        }
        
        # Add additional data if provided
        if additional_data:
            metrics["additional_data"] = additional_data
        
        # Record performance data
        self._record_performance_data(metrics)
        
        return metrics
    
    def _record_performance_data(self, metrics: Dict[str, Any]) -> None:
        """
        Record performance data using Indaleko's performance infrastructure.
        
        Args:
            metrics: Performance metrics to record
        """
        # Create source identifier
        source_identifier = IndalekoSourceIdentifierDataModel(
            Identifier=str(self._provider_id),
            Version="1.0"
        )
        
        # Create record
        record = IndalekoRecordDataModel(
            SourceIdentifier=source_identifier,
            Timestamp=metrics["timestamp"],
            Attributes={
                "ExtractorName": metrics["extractor_name"],
                "FilePath": metrics.get("file_path", ""),
                "FileSize": metrics.get("file_size", 0),
                "MimeType": metrics.get("mime_type", ""),
                "Success": metrics["success"],
            },
            Data=""
        )
        
        # Create performance data model
        perf_data = IndalekoPerformanceDataModel(
            Record=record,
            MachineConfigurationId=self._machine_config_id,
            StartTimestamp=metrics["timestamp"],
            EndTimestamp=metrics["timestamp"],
            ElapsedTime=metrics["elapsed_time"],
            UserCPUTime=metrics["user_cpu_time"],
            SystemCPUTime=metrics["system_cpu_time"],
            ActivityStats={
                "IO": metrics["io_stats"],
                "Memory": metrics["memory_stats"],
                "AdditionalData": metrics.get("additional_data", {})
            }
        )
        
        # Record to database if enabled
        if self._record_to_db:
            try:
                self._perf_recorder.add_data_to_db(perf_data)
            except Exception as e:
                logging.error(f"Error recording performance data to database: {e}")
        
        # Record to file if enabled
        if self._record_to_file and self._perf_file_name:
            try:
                self._perf_recorder.add_data_to_file(self._perf_file_name, perf_data)
            except Exception as e:
                logging.error(f"Error recording performance data to file: {e}")


def monitor_semantic_extraction(func: Optional[Callable] = None, 
                               extractor_name: Optional[str] = None):
    """
    Decorator for monitoring semantic extraction functions.
    
    This decorator can be used with or without arguments. When used without arguments,
    it will use the function name as the extractor name.
    
    Args:
        func: The function to decorate (when used as @monitor_semantic_extraction)
        extractor_name: Name to use for the extractor (when used as @monitor_semantic_extraction("name"))
        
    Returns:
        Decorated function
    """
    def decorator_monitor(func):
        @functools.wraps(func)
        def wrapper_monitor(*args, **kwargs):
            # Get or create monitor instance
            monitor = SemanticExtractorPerformance()
            
            if not monitor.is_enabled():
                return func(*args, **kwargs)
            
            # Determine extractor name
            func_extractor_name = extractor_name or func.__qualname__
            
            # Extract file_path from args or kwargs
            file_path = None
            file_size = None
            mime_type = None
            
            # Try to find file path in args or kwargs
            for arg in args:
                if isinstance(arg, str) and os.path.exists(arg):
                    file_path = arg
                    break
            
            if not file_path and 'file_path' in kwargs:
                file_path = kwargs['file_path']
                
            if 'file_size' in kwargs:
                file_size = kwargs['file_size']
                
            if 'mime_type' in kwargs:
                mime_type = kwargs['mime_type']
            
            # Start monitoring
            context = monitor.start_monitoring(
                func_extractor_name, 
                file_path=file_path,
                file_size=file_size,
                mime_type=mime_type
            )
            
            # Call the function
            success = True
            result = None
            try:
                result = func(*args, **kwargs)
                
                # Try to extract mime_type from result if not already set
                if not mime_type and isinstance(result, dict):
                    mime_type = result.get('mime_type')
                    if mime_type and context.get('enabled', False):
                        context['mime_type'] = mime_type
                
                return result
            except Exception as e:
                success = False
                raise e
            finally:
                # Stop monitoring and record metrics
                if context.get('enabled', False):
                    additional_data = {}
                    if isinstance(result, dict):
                        # Extract relevant data from result if it's a dictionary
                        for key in ['confidence', 'encoding', 'category']:
                            if key in result:
                                additional_data[key] = result[key]
                                
                    monitor.stop_monitoring(context, success=success, additional_data=additional_data)
        
        return wrapper_monitor
    
    # Handle usage without arguments: @monitor_semantic_extraction
    if func is not None:
        return decorator_monitor(func)
    
    # Handle usage with arguments: @monitor_semantic_extraction("name")
    return decorator_monitor


# Example usage
if __name__ == "__main__":
    # Enable logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create monitor instance
    monitor = SemanticExtractorPerformance(record_to_file=True)
    
    # Define a test function using the decorator
    @monitor_semantic_extraction(extractor_name="TestMimeDetector")
    def test_mime_detection(file_path: str):
        """Test function for MIME detection."""
        time.sleep(0.5)  # Simulate processing
        return {
            "mime_type": "text/plain",
            "confidence": 0.95,
            "encoding": "utf-8"
        }
    
    # Create a test file
    test_file = "test_sample.txt"
    with open(test_file, "w") as f:
        f.write("This is a test file for monitoring semantic extraction performance.")
    
    # Run the test function
    result = test_mime_detection(test_file)
    print(f"MIME detection result: {result}")
    
    # Get performance statistics
    stats = monitor.get_stats()
    print(f"Performance stats: {stats}")
    
    # Clean up
    os.remove(test_file)