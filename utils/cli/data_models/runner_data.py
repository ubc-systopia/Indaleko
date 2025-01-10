'''
This module provides the data model for the CLI runner.

Indaleko Windows Local Recorder
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
'''
import argparse
import logging
import os
from pathlib import Path
import sys

from typing import Type, Union, TypeVar, Any, Callable
from abc import ABC, abstractmethod

from icecream import ic
from pydantic import BaseModel

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)


# pylint: disable=wrong-import-position
# pylint: enable=wrong-import-position

class IndalekoCLIRunnerData(BaseModel):
    '''This class provides a common CLI runner'''
    GetPreParser : Union[Callable[..., Union[argparse.ArgumentParser, None]], None] = None
    SetupLogging : Callable[..., None]
    LoadConfiguration : Callable[..., bool]
    AddParameters : Union[Callable[..., argparse.ArgumentParser], None] = None
    PerformanceConfiguration : Callable[..., bool]
    Run: Callable[..., None]
    PerformanceRecording: Callable[..., None]
    Cleanup: Callable[..., None]
