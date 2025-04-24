"""initializtion logic for the activity context system"""

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
from activity.characteristics import ActivityDataCharacteristics  # noqa: E402
from activity.collectors.base import CollectorBase  # noqa: E402

# pylint: enable=wrong-import-position

collector_dir = os.path.join(init_path, "collectors")
collectors = [
    x
    for x in os.listdir(collector_dir)
    if os.path.isdir(os.path.join(collector_dir, x)) and not x.startswith("_")
]
recorder_dir = os.path.join(init_path, "recorders")
recorders = [
    x
    for x in os.listdir(recorder_dir)
    if os.path.isdir(os.path.join(recorder_dir, x)) and not x.startswith("_")
]
# ic(collectors)

__version__ = "0.1.0"

__all__ = ["CollectorBase", "ActivityDataCharacteristics"]
