"""
This module is used to do various basic data validation operations for Indaleko

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

import datetime
import ipaddress
import os
import socket
import sys
import uuid

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position


@staticmethod
def validate_ip_address(ip: str) -> bool:
    """Given a string, verify that it is in fact a valid IP address."""
    if not isinstance(ip, str):
        print(f"ip is not a string it is a {type(ip)}")
        return False
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        print("ip is not valid")
        return False


@staticmethod
def validate_hostname(hostname: str) -> bool:
    """Given a string, verify that it is in fact a valid hostname."""
    if not isinstance(hostname, str):
        print(f"hostname is not a string it is a {type(hostname)}")
        return False
    try:
        socket.gethostbyname(hostname)
        return True
    except OSError:
        print("hostname is not valid")
        return False


@staticmethod
def validate_uuid_string(uuid_string: str) -> bool:
    """Given a string, verify that it is in fact a valid uuid."""
    if not isinstance(uuid_string, str):
        print(f"uuid is not a string it is a {type(uuid_string)}")
        return False
    try:
        uuid.UUID(uuid_string)
        return True
    except ValueError:
        print("uuid is not valid")
        return False


@staticmethod
def validate_iso_timestamp(source: str) -> bool:
    """Given a string, ensure it is a valid ISO timestamp."""
    valid = True
    if not isinstance(source, str):
        valid = False
    else:
        try:
            datetime.datetime.fromisoformat(source)
        except ValueError:
            valid = False
    return valid
