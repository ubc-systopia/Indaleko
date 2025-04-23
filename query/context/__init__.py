"""
Query Context Integration module for Indaleko.

This module provides functionality to integrate queries with the Indaleko Activity
Context system, allowing query relationships to be tracked, analyzed, and utilized
to improve search experiences.

Project Indaleko
Copyright (C) 2025 Tony Mason

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

# Import key components for easier access
from query.context.activity_provider import QueryActivityProvider
from query.context.navigation import QueryNavigator
from query.context.relationship import QueryRelationshipDetector
from query.context.visualization import QueryPathVisualizer
