"""Exemplar data model."""

import os
import sys

from pathlib import Path

from pydantic import BaseModel

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from data_models.named_entity import IndalekoNamedEntityDataModel

# pylint: enable=wrong-import-position


class ExemplarQuery(BaseModel):
    """Data model for exemplar queries."""
    query: str
    aql_query: str | None = None
    aql_count_query: str | None = None
    named_entities: list[IndalekoNamedEntityDataModel] | None = None
    bind_variables: dict[str, str] | None = None
