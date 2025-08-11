"""
Initialization for knowledge base updating data models.

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

from knowledge_base.data_models.feedback_record import FeedbackRecordDataModel, FeedbackType
from knowledge_base.data_models.knowledge_pattern import (
    KnowledgePatternDataModel,
    KnowledgePatternType,
)
from knowledge_base.data_models.learning_event import LearningEventDataModel, LearningEventType
