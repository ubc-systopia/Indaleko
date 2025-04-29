"""
Knowledge Base Updating module for Indaleko Archivist.

This module provides functionality for updating the knowledge base
based on query patterns, user feedback, and system observations.

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

from .continuous_learning import ContinuousLearningSystem
from .data_models import (
    FeedbackRecordDataModel,
    FeedbackType,
    KnowledgePatternDataModel,
    KnowledgePatternType,
    LearningEventDataModel,
    LearningEventType,
)
from .knowledge_manager import KnowledgeBaseManager
