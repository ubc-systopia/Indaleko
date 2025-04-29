"""
This module provides timestamp management for Indaleko.

Indaleko Windows Local Indexer
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

import datetime
import os
import sys

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
import utils.data_validation

# pylint: enable=wrong-import-position


def validate_iso_timestamp(source: str) -> bool:
    """Given a string, ensure it is a valid ISO timestamp."""
    return utils.data_validation.validate_iso_timestamp(source)


def generate_iso_timestamp(ts: datetime = None) -> str:
    """Given a timestamp, convert it to an ISO timestamp."""
    if ts is None:
        ts = datetime.datetime.now(datetime.UTC)
    assert isinstance(ts, datetime.datetime), f"ts must be a datetime, not {type(ts)}"
    return ts.isoformat()


def extract_iso_timestamp_from_file_timestamp(file_timestamp: str) -> str:
    """Given a file timestamp, convert it to an ISO timestamp."""
    ts = file_timestamp.replace("_", "-").replace("#", ":")
    ts_check = datetime.datetime.fromisoformat(ts)
    if ts_check is None:
        raise ValueError("timestamp is not valid")
    return ts


def generate_iso_timestamp_for_file(ts: str = None) -> str:
    """Create an ISO timestamp for the current time."""
    if ts is None:
        ts = datetime.datetime.now(datetime.UTC).isoformat()
    ts_check = extract_iso_timestamp_from_file_timestamp(ts)
    if ts_check != ts:  # validate that the timestamp is reversible
        raise ValueError(f"timestamp mismatch {ts} != {ts_check}")
    return f"-ts={ts.replace(':', '#').replace('-', '_')}"
