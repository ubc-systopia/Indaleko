"""
Data model for thesis-focused query execution results.

This model creates a flattened structure optimized for statistical analysis
and thesis presentation, with one record per query variant execution.
"""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import json

from pydantic import BaseModel, Field

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))


class ThesisQueryResult(BaseModel):
    """Single query variant execution result optimized for thesis analysis."""
    
    # Execution identification
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this specific variant was executed"
    )
    run_id: str = Field(description="Identifier for the overall test run")
    sequence_number: int = Field(description="Which iteration this is (1-based)")
    query_id: str = Field(description="Query identifier (e.g., 'q1', 'q2')")
    variant: str = Field(description="Query variant: 'with_limits', 'no_limit', or 'count'")
    
    # Performance metrics
    execution_time: float = Field(description="Query execution time in seconds")
    result_count: int = Field(description="Number of results returned")
    count_value: int | None = Field(
        default=None, 
        description="For count queries, the actual count value"
    )
    
    # Cache and system state
    cache_state: str = Field(
        default="unknown",
        description="Cache state: 'cold' (first run), 'warm' (2-3), or 'hot' (4+)"
    )
    
    # Query details
    query_text: str = Field(description="Natural language query")
    aql_query: str = Field(description="The AQL query executed")
    bind_variables: dict[str, object] = Field(description="Bind variables used in the query")
    
    # Error tracking
    error: str | None = Field(default=None, description="Error message if query failed")
    
    # Optional extended data
    database_size: int | None = Field(
        default=None,
        description="Number of documents in primary collection at execution time"
    )
    
    def to_jsonl_record(self) -> str:
        """Convert to JSONL record with consistent formatting."""
        # Use model_dump to get dict, then ensure consistent datetime format
        data = self.model_dump()
        if isinstance(data['timestamp'], datetime):
            data['timestamp'] = data['timestamp'].isoformat()
        return json.dumps(data, ensure_ascii=False) + "\n"
    
    @classmethod
    def from_jsonl_record(cls, line: str) -> "ThesisQueryResult":
        """Create from a JSONL record."""
        return cls.model_validate_json(line.strip())
    
    
    @staticmethod
    def determine_cache_state(sequence_number: int) -> str:
        """
        Determine cache state based on sequence number.
        
        In the warm cache pattern, all queries in round 1 are "cold",
        rounds 2-3 are "warm", and rounds 4+ are "hot".
        """
        if sequence_number == 1:
            return "cold"
        elif sequence_number <= 3:
            return "warm"
        else:
            return "hot"