from pydantic import BaseModel, Field, ConfigDict
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


class LLMQueryResponse(BaseModel):
    aql_query: str = Field(..., title='AQL Query')
    rationale: str = Field(..., title='Rationale')
    alternatives_considered: list[dict[str, str]] = Field(..., title='Alternatives Considered')
    index_warnings: list[dict[str, str]] = Field(..., title='Index Warnings')

    model_config = ConfigDict(
        json_schema_extra={
            'requred': [
                'aql_query',
                'rationale',
                'alternatives_considered',
                'index_warnings'
            ]
        }
    )
