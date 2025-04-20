"""
Fire Circle implementation for Indaleko.

This package implements the Fire Circle, a collaborative space where
multiple AI entities can engage in non-hierarchical dialogue, build
collective understanding, and produce joint insights.

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

# Version information
__version__ = "0.1.0"
__author__ = "Tony Mason and contributors"
__email__ = "noreply@indaleko.io"

# Import submodules to make them available
from firecircle.protocol import (
    Message, MessageType, CircleRequest, CircleResponse,
    CircleOrchestrator, TurnTakingPolicy
)

from firecircle.entities import (
    Entity, EntityCapability, EntityRegistry
)

from firecircle.memory import (
    CircleContext, ContextVariable, MemoryStore
)

# Setup version variable to make it available in module
VERSION = __version__