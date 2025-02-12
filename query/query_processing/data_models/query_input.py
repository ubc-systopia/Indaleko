from pydantic import BaseModel
from typing import Any


class QueryFilter(BaseModel):
    field: str
    operation: str  # E.g., "=", ">", "<", "IN"
    value: str


class StructuredQuery(BaseModel):
    original_query: str
    intent: str  # "search", "filter", etc.
    entities: dict[str, str]  # Extracted entities
    filters: list[QueryFilter]
    db_schema: dict[str, Any]  # Schema reference
