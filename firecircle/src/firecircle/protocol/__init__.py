"""
Fire Circle Protocol module.

This module defines the message protocol and orchestration mechanisms
for the Fire Circle implementation.

Project Indaleko
Copyright (C) 2024-2025 Tony Mason and contributors

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

# Import submodules to make them available
from firecircle.protocol.message import (
    CircleRequest,
    CircleResponse,
    Message,
    MessageType,
)
from firecircle.protocol.orchestrator import CircleOrchestrator, TurnTakingPolicy
