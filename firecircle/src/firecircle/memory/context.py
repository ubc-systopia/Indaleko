"""
Fire Circle Context Management.

This module provides context management for the Fire Circle implementation,
allowing shared context variables across the circle.

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

import enum
import uuid
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set, Union, TypeVar

from pydantic import BaseModel, Field, validator


class AccessLevel(str, enum.Enum):
    """Access levels for context variables."""
    
    PUBLIC = "public"        # Accessible to all entities
    PROTECTED = "protected"  # Accessible to specific entities
    PRIVATE = "private"      # Accessible only to the creating entity


T = TypeVar('T')


class ContextVariable(BaseModel):
    """
    A shared context variable within the Fire Circle.
    
    Context variables allow entities to share information with
    each other and maintain state across interactions.
    """
    
    key: str = Field(
        ...,
        description="The name/key of this variable"
    )
    
    value: Any = Field(
        ...,
        description="The value of this variable"
    )
    
    access_level: AccessLevel = Field(
        default=AccessLevel.PUBLIC,
        description="Who can access this variable"
    )
    
    created_by: str = Field(
        ...,
        description="Entity ID that created this variable"
    )
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this variable was created"
    )
    
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this variable was last updated"
    )
    
    allowed_entities: List[str] = Field(
        default_factory=list,
        description="Entity IDs allowed to access this variable (for PROTECTED level)"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about this variable"
    )
    
    @validator('updated_at')
    def updated_at_must_be_valid(cls, v, values):
        """Ensure updated_at is not earlier than created_at."""
        if 'created_at' in values and v < values['created_at']:
            return values['created_at']
        return v


class CircleContext:
    """
    Manages shared context within a Fire Circle.
    
    The CircleContext provides a structured way for entities in
    the circle to share and access contextual information.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize the circle context.
        
        Args:
            logger: Optional logger for context events
        """
        self.variables: Dict[str, ContextVariable] = {}
        self.logger = logger or logging.getLogger(__name__)
    
    def set_variable(
        self,
        key: str,
        value: Any,
        entity_id: str,
        access_level: AccessLevel = AccessLevel.PUBLIC,
        allowed_entities: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ContextVariable:
        """
        Set a context variable.
        
        Args:
            key: The variable name/key
            value: The variable value
            entity_id: ID of the entity setting the variable
            access_level: Who can access this variable
            allowed_entities: Entity IDs allowed to access (for PROTECTED level)
            metadata: Additional metadata about this variable
            
        Returns:
            The created or updated context variable
        """
        # Check if variable already exists
        if key in self.variables:
            # Update existing variable
            variable = self.variables[key]
            variable.value = value
            variable.updated_at = datetime.now(timezone.utc)
            
            # Only update access settings if set by original creator
            if entity_id == variable.created_by:
                variable.access_level = access_level
                if allowed_entities is not None:
                    variable.allowed_entities = allowed_entities
            
            # Update metadata if provided
            if metadata:
                variable.metadata.update(metadata)
                
            self.logger.info(f"Updated variable: {key}")
        else:
            # Create new variable
            variable = ContextVariable(
                key=key,
                value=value,
                access_level=access_level,
                created_by=entity_id,
                allowed_entities=allowed_entities or [],
                metadata=metadata or {},
            )
            self.variables[key] = variable
            self.logger.info(f"Created variable: {key}")
        
        return variable
    
    def get_variable(
        self, key: str, entity_id: str, default: Optional[T] = None
    ) -> Union[Any, Optional[T]]:
        """
        Get a context variable.
        
        Args:
            key: The variable name/key
            entity_id: ID of the entity requesting the variable
            default: Default value if variable not found or not accessible
            
        Returns:
            The variable value, or default if not found/accessible
        """
        # Check if variable exists
        if key not in self.variables:
            return default
        
        variable = self.variables[key]
        
        # Check access permissions
        if variable.access_level == AccessLevel.PUBLIC:
            # Public variables accessible to all
            return variable.value
        
        elif variable.access_level == AccessLevel.PROTECTED:
            # Protected variables accessible to creator and allowed entities
            if entity_id == variable.created_by or entity_id in variable.allowed_entities:
                return variable.value
            else:
                self.logger.warning(
                    f"Entity {entity_id} attempted to access protected variable {key}"
                )
                return default
        
        elif variable.access_level == AccessLevel.PRIVATE:
            # Private variables accessible only to creator
            if entity_id == variable.created_by:
                return variable.value
            else:
                self.logger.warning(
                    f"Entity {entity_id} attempted to access private variable {key}"
                )
                return default
        
        # Should never get here
        return default
    
    def delete_variable(self, key: str, entity_id: str) -> bool:
        """
        Delete a context variable.
        
        Args:
            key: The variable name/key
            entity_id: ID of the entity attempting to delete
            
        Returns:
            True if deleted, False otherwise
        """
        # Check if variable exists
        if key not in self.variables:
            return False
        
        variable = self.variables[key]
        
        # Only creator can delete
        if entity_id != variable.created_by:
            self.logger.warning(
                f"Entity {entity_id} attempted to delete variable {key} created by {variable.created_by}"
            )
            return False
        
        # Delete the variable
        del self.variables[key]
        self.logger.info(f"Deleted variable: {key}")
        return True
    
    def get_all_accessible_variables(self, entity_id: str) -> Dict[str, Any]:
        """
        Get all variables accessible to an entity.
        
        Args:
            entity_id: ID of the entity requesting variables
            
        Returns:
            Dictionary mapping variable keys to values
        """
        result = {}
        
        for key, variable in self.variables.items():
            # Public variables
            if variable.access_level == AccessLevel.PUBLIC:
                result[key] = variable.value
            
            # Protected variables
            elif variable.access_level == AccessLevel.PROTECTED:
                if entity_id == variable.created_by or entity_id in variable.allowed_entities:
                    result[key] = variable.value
            
            # Private variables
            elif variable.access_level == AccessLevel.PRIVATE:
                if entity_id == variable.created_by:
                    result[key] = variable.value
        
        return result
    
    def get_variable_metadata(self, key: str, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a variable.
        
        Args:
            key: The variable name/key
            entity_id: ID of the entity requesting metadata
            
        Returns:
            Variable metadata dict if accessible, None otherwise
        """
        # Check if variable exists
        if key not in self.variables:
            return None
        
        variable = self.variables[key]
        
        # Check access permissions (same as get_variable)
        if variable.access_level == AccessLevel.PUBLIC:
            return variable.metadata
        
        elif variable.access_level == AccessLevel.PROTECTED:
            if entity_id == variable.created_by or entity_id in variable.allowed_entities:
                return variable.metadata
        
        elif variable.access_level == AccessLevel.PRIVATE:
            if entity_id == variable.created_by:
                return variable.metadata
        
        return None
    
    def update_variable_metadata(
        self, key: str, entity_id: str, metadata: Dict[str, Any]
    ) -> bool:
        """
        Update metadata for a variable.
        
        Args:
            key: The variable name/key
            entity_id: ID of the entity updating metadata
            metadata: New metadata to add/update
            
        Returns:
            True if updated, False otherwise
        """
        # Check if variable exists
        if key not in self.variables:
            return False
        
        variable = self.variables[key]
        
        # Only creator can update metadata
        if entity_id != variable.created_by:
            self.logger.warning(
                f"Entity {entity_id} attempted to update metadata for variable {key}"
            )
            return False
        
        # Update metadata
        variable.metadata.update(metadata)
        self.logger.info(f"Updated metadata for variable: {key}")
        return True
    
    def serialize(self) -> str:
        """
        Serialize context to JSON string.
        
        Returns:
            JSON string representation of the context
        """
        # Convert to dictionary representation
        serializable = {
            key: {
                "key": var.key,
                "value": _make_serializable(var.value),
                "access_level": var.access_level,
                "created_by": var.created_by,
                "created_at": var.created_at.isoformat(),
                "updated_at": var.updated_at.isoformat(),
                "allowed_entities": var.allowed_entities,
                "metadata": _make_serializable(var.metadata)
            }
            for key, var in self.variables.items()
        }
        
        return json.dumps(serializable, indent=2)
    
    @classmethod
    def deserialize(cls, serialized: str) -> 'CircleContext':
        """
        Deserialize context from JSON string.
        
        Args:
            serialized: JSON string representation of the context
            
        Returns:
            Deserialized CircleContext
        """
        context = cls()
        data = json.loads(serialized)
        
        for key, var_data in data.items():
            # Deserialize the variable
            variable = ContextVariable(
                key=var_data["key"],
                value=var_data["value"],
                access_level=var_data["access_level"],
                created_by=var_data["created_by"],
                created_at=datetime.fromisoformat(var_data["created_at"]),
                updated_at=datetime.fromisoformat(var_data["updated_at"]),
                allowed_entities=var_data["allowed_entities"],
                metadata=var_data["metadata"]
            )
            
            context.variables[key] = variable
        
        return context


def _make_serializable(value: Any) -> Any:
    """
    Convert a value to a JSON-serializable form.
    
    Args:
        value: The value to convert
        
    Returns:
        JSON-serializable representation of the value
    """
    if isinstance(value, (str, int, float, bool, type(None))):
        return value
    elif isinstance(value, (list, tuple)):
        return [_make_serializable(item) for item in value]
    elif isinstance(value, dict):
        return {str(k): _make_serializable(v) for k, v in value.items()}
    elif isinstance(value, datetime):
        return value.isoformat()
    elif isinstance(value, uuid.UUID):
        return str(value)
    elif hasattr(value, "to_dict") and callable(getattr(value, "to_dict")):
        return value.to_dict()
    else:
        return str(value)