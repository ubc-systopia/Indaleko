"""initializtion logic for the activity context system"""

import importlib
import os
import sys

# from icecream import ic

init_path = os.path.dirname(os.path.abspath(__file__))

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# from perf_collector import IndalekoPerformanceDataCollector
# from perf_recorder import IndalekoPerformanceDataRecorder
# from perf_mixin import IndalekoPerformanceMixin
# pylint: enable=wrong-import-position


# ic(collectors)

__version__ = "0.1.0"

__all__ = [
    #    'IndalekoPerformanceDataCollector',
    #    'IndalekoPerformanceDataRecorder',
    #    'IndalekoPerformanceMixin',
]
