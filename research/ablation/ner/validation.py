"""Validation utilities for named entities."""

import logging
import re

from ..error import ErrorSeverity, ValidationError
from ..models.named_entity import (
    EntityRelation,
    EntityRelationType,
    EntityType,
    NamedEntity,
)

logger = logging.getLogger(__name__)


def validate_entity_name(name: str) -> ValidationError | None:
    """Validate an entity name.

    Args:
        name: The name to validate.

    Returns:
        Optional[ValidationError]: An error if the name is invalid, None otherwise.
    """
    if not name:
        return ValidationError(
            message="Entity name cannot be empty",
            field_name="name",
            severity=ErrorSeverity.ERROR,
        )

    if len(name.strip()) == 0:
        return ValidationError(
            message="Entity name cannot be whitespace only",
            field_name="name",
            severity=ErrorSeverity.ERROR,
        )

    if len(name) > 100:
        return ValidationError(
            message="Entity name is too long (max 100 characters)",
            field_name="name",
            severity=ErrorSeverity.ERROR,
        )

    return None


def validate_entity_alias(alias: str) -> ValidationError | None:
    """Validate an entity alias.

    Args:
        alias: The alias to validate.

    Returns:
        Optional[ValidationError]: An error if the alias is invalid, None otherwise.
    """
    if not alias:
        return ValidationError(
            message="Entity alias cannot be empty",
            field_name="alias.name",
            severity=ErrorSeverity.ERROR,
        )

    if len(alias.strip()) == 0:
        return ValidationError(
            message="Entity alias cannot be whitespace only",
            field_name="alias.name",
            severity=ErrorSeverity.ERROR,
        )

    if len(alias) > 50:
        return ValidationError(
            message="Entity alias is too long (max 50 characters)",
            field_name="alias.name",
            severity=ErrorSeverity.ERROR,
        )

    return None


def validate_entity_type(entity_type: str) -> ValidationError | None:
    """Validate an entity type.

    Args:
        entity_type: The entity type to validate.

    Returns:
        Optional[ValidationError]: An error if the entity type is invalid, None otherwise.
    """
    try:
        # Try to convert the string to an EntityType enum
        EntityType(entity_type)
        return None
    except ValueError:
        return ValidationError(
            message=f"Invalid entity type: {entity_type}",
            field_name="entity_type",
            expected_type=EntityType,
            actual_value=entity_type,
            severity=ErrorSeverity.ERROR,
        )


def validate_relation_type(relation_type: str) -> ValidationError | None:
    """Validate a relation type.

    Args:
        relation_type: The relation type to validate.

    Returns:
        Optional[ValidationError]: An error if the relation type is invalid, None otherwise.
    """
    try:
        # Try to convert the string to an EntityRelationType enum
        EntityRelationType(relation_type)
        return None
    except ValueError:
        return ValidationError(
            message=f"Invalid relation type: {relation_type}",
            field_name="relation_type",
            expected_type=EntityRelationType,
            actual_value=relation_type,
            severity=ErrorSeverity.ERROR,
        )


def validate_property_key(key: str) -> ValidationError | None:
    """Validate a property key.

    Args:
        key: The property key to validate.

    Returns:
        Optional[ValidationError]: An error if the key is invalid, None otherwise.
    """
    if not key:
        return ValidationError(
            message="Property key cannot be empty",
            field_name="property_key",
            severity=ErrorSeverity.ERROR,
        )

    if len(key.strip()) == 0:
        return ValidationError(
            message="Property key cannot be whitespace only",
            field_name="property_key",
            severity=ErrorSeverity.ERROR,
        )

    if len(key) > 50:
        return ValidationError(
            message="Property key is too long (max 50 characters)",
            field_name="property_key",
            severity=ErrorSeverity.ERROR,
        )

    # Check for valid characters
    if not re.match(r"^[a-zA-Z0-9_.-]+$", key):
        return ValidationError(
            message="Property key can only contain letters, numbers, underscores, hyphens, and periods",
            field_name="property_key",
            severity=ErrorSeverity.ERROR,
        )

    return None


def validate_property_value(value: str) -> ValidationError | None:
    """Validate a property value.

    Args:
        value: The property value to validate.

    Returns:
        Optional[ValidationError]: An error if the value is invalid, None otherwise.
    """
    if not isinstance(value, str):
        return ValidationError(
            message="Property value must be a string",
            field_name="property_value",
            expected_type=str,
            actual_value=value,
            severity=ErrorSeverity.ERROR,
        )

    if len(value) > 1000:
        return ValidationError(
            message="Property value is too long (max 1000 characters)",
            field_name="property_value",
            severity=ErrorSeverity.ERROR,
        )

    return None


def validate_properties(properties: dict[str, str]) -> list[ValidationError]:
    """Validate a dictionary of properties.

    Args:
        properties: The properties to validate.

    Returns:
        List[ValidationError]: A list of validation errors.
    """
    errors = []

    for key, value in properties.items():
        key_error = validate_property_key(key)
        if key_error:
            errors.append(key_error)

        value_error = validate_property_value(value)
        if value_error:
            errors.append(value_error)

    return errors


def validate_named_entity(entity: dict | NamedEntity) -> list[ValidationError]:
    """Validate a named entity.

    Args:
        entity: The entity to validate.

    Returns:
        List[ValidationError]: A list of validation errors.
    """
    errors = []

    # Convert dict to NamedEntity if needed
    if isinstance(entity, dict):
        try:
            entity = NamedEntity(**entity)
        except Exception as e:
            errors.append(
                ValidationError(
                    message=f"Failed to parse entity data: {e}",
                    severity=ErrorSeverity.ERROR,
                ),
            )
            return errors

    # Validate entity name
    name_error = validate_entity_name(entity.name)
    if name_error:
        errors.append(name_error)

    # Validate entity type
    if not isinstance(entity.entity_type, EntityType):
        try:
            # Try to convert string to EntityType
            EntityType(entity.entity_type)  # type: ignore
        except (ValueError, TypeError):
            errors.append(
                ValidationError(
                    message=f"Invalid entity type: {entity.entity_type}",
                    field_name="entity_type",
                    expected_type=EntityType,
                    actual_value=entity.entity_type,
                    severity=ErrorSeverity.ERROR,
                ),
            )

    # Validate aliases
    for i, alias in enumerate(entity.aliases):
        alias_error = validate_entity_alias(alias.name)
        if alias_error:
            alias_error.field_name = f"aliases[{i}].name"
            errors.append(alias_error)

    # Validate properties
    property_errors = validate_properties(entity.properties)
    errors.extend(property_errors)

    return errors


def validate_entity_relation(relation: dict | EntityRelation) -> list[ValidationError]:
    """Validate an entity relation.

    Args:
        relation: The relation to validate.

    Returns:
        List[ValidationError]: A list of validation errors.
    """
    errors = []

    # Convert dict to EntityRelation if needed
    if isinstance(relation, dict):
        try:
            relation = EntityRelation(**relation)
        except Exception as e:
            errors.append(
                ValidationError(
                    message=f"Failed to parse relation data: {e}",
                    severity=ErrorSeverity.ERROR,
                ),
            )
            return errors

    # Validate relation type
    if not isinstance(relation.relation_type, EntityRelationType):
        try:
            # Try to convert string to EntityRelationType
            EntityRelationType(relation.relation_type)  # type: ignore
        except (ValueError, TypeError):
            errors.append(
                ValidationError(
                    message=f"Invalid relation type: {relation.relation_type}",
                    field_name="relation_type",
                    expected_type=EntityRelationType,
                    actual_value=relation.relation_type,
                    severity=ErrorSeverity.ERROR,
                ),
            )

    # Validate properties
    property_errors = validate_properties(relation.properties)
    errors.extend(property_errors)

    return errors


def validate_entities_for_relation(
    source_entity: NamedEntity | None,
    target_entity: NamedEntity | None,
) -> list[ValidationError]:
    """Validate that entities exist for a relation.

    Args:
        source_entity: The source entity.
        target_entity: The target entity.

    Returns:
        List[ValidationError]: A list of validation errors.
    """
    errors = []

    if source_entity is None:
        errors.append(
            ValidationError(
                message="Source entity does not exist",
                field_name="source_entity_id",
                severity=ErrorSeverity.ERROR,
            ),
        )

    if target_entity is None:
        errors.append(
            ValidationError(
                message="Target entity does not exist",
                field_name="target_entity_id",
                severity=ErrorSeverity.ERROR,
            ),
        )

    return errors
