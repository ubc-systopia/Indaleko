"""
Base class for exemplar queries following Ayni principles.

This foundation stone represents the shared wisdom between human and AI,
creating patterns that will serve future builders of this cathedral.
"""

import os
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Self, TextIO

from icecream import ic

# Path setup - common to all
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from data_models.named_entity import IndalekoNamedEntityDataModel
from db.db_collections import IndalekoDBCollections
from db.utils.query_performance import TimedAQLExecute
from exemplar.exemplar_data_model import ExemplarQuery, ExemplarAQLQuery
from exemplar.ner_documents import ExemplarNamedEntity
from exemplar.thesis_results_model import ThesisQueryResult
# pylint: enable=wrong-import-position


class ExemplarQueryBase(ABC):
    """
    Base class for exemplar queries that honors the principle of Ayni.

    This base class provides the common structure while respecting the unique
    characteristics of each query. It offers what is shared and receives what
    is specific, creating a balanced exchange.
    """

    DEFAULT_LIMIT = 50

    def __init__(self: Self, *, limit: int | str = DEFAULT_LIMIT) -> None:
        """Initialize the exemplar query with common setup."""
        self._limit = int(limit) if isinstance(limit, str) else limit

        # Each child provides these through abstract methods
        self._query = self._get_user_query()
        self._base_aql = self._get_base_aql()

        # Common query construction pattern
        self._aql_query_limit= self._get_aql_query_limit()
        self._aql_query_no_limit = self._get_aql_query_no_limit()
        self._aql_count_query = self._get_aql_count_query()

        # Initialize bind variables
        self._base_bind_variables = self._get_base_bind_variables()
        self._limit_bind_variables = self._base_bind_variables.copy()
        self._limit_bind_variables["limit"] = self._limit
        self._no_limit_bind_variables = self._base_bind_variables

        # Named entities - optional, defaults to empty
        self._named_entities = self._get_named_entities()
        self._create_named_entities()

        # Create the exemplar query
        self._exemplar_query = self._create_exemplar_query()

    def _get_aql_query_limit(self: Self) -> str:
        """Return the AQL query with limit."""
        return f"""
            {self._base_aql}
            LIMIT @limit
            RETURN doc
        """

    def _get_aql_query_no_limit(self: Self) -> str:
        return self._base_aql + """
            RETURN {
                "ObjectIdentifier": doc.ObjectIdentifier,
                "Path": doc.Path,
                "Label": doc.Label,
            }
       """

    def _get_aql_count_query(self: Self) -> str:
        return f"""
            RETURN LENGTH(
            {self._base_aql}
            RETURN 1
        )
        """

    def _create_named_entities(self: Self) -> None:
        """Create named entities if provided."""
        if self._named_entities:
            for entity in self._named_entities:
                existing_entity = ExemplarNamedEntity.lookup_entity_in_db(entity["name"])
                if existing_entity is None:
                    ic(f"Creating named entity: {entity}")
                    new_entity = IndalekoNamedEntityDataModel(**entity)
                    ExemplarNamedEntity.add_entity_to_db(new_entity)

    @abstractmethod
    def _get_user_query(self: Self) -> str:
        """Return the natural language query string."""
        pass

    @abstractmethod
    def _get_base_aql(self: Self) -> str:
        """Return the base AQL query without LIMIT or RETURN."""
        pass

    @abstractmethod
    def _get_base_bind_variables(self: Self) -> dict[str, object]:
        """Return the base bind variables including @collection."""
        pass

    def _get_named_entities(self: Self) -> list:
        """Return named entities. Override if query uses entities."""
        return []

    def _get_collection(self: Self) -> str:
        """Return the collection to query. Override if not using text view."""
        return IndalekoDBCollections.Indaleko_Objects_Text_View

    def _create_exemplar_query(self: Self) -> ExemplarQuery:
        """Create the ExemplarQuery object with all variants."""
        return ExemplarQuery(
            user_query=self._query,
            aql_queries={
                "with_limits": ExemplarAQLQuery(
                    aql_query=self._aql_query_limit,
                    bind_variables=self._limit_bind_variables,
                ),
                "no_limit": ExemplarAQLQuery(
                    aql_query=self._aql_query_no_limit,
                    bind_variables=self._no_limit_bind_variables,
                ),
                "count": ExemplarAQLQuery(
                    aql_query=self._aql_count_query,
                    bind_variables=self._no_limit_bind_variables,
                ),
            }
        )

    def get_exemplar_query(self: Self) -> ExemplarQuery | None:
        """Get the exemplar query."""
        if self._exemplar_query is None:
            ic("Exemplar query is None.")
            return None
        return self._exemplar_query

    def execute(
        self: Self, 
        output_file: TextIO | Path | None = None,
        run_id: str | None = None,
        sequence_number: int | None = None
    ) -> dict[str, object]:
        """
        Execute all query variants and return results.
        This embodies the common execution pattern.
        
        Args:
            output_file: Optional file handle or Path to write structured results to JSONL
            run_id: Identifier for this test run
            sequence_number: Which iteration this is (1-based)
        """
        exemplar_query = self.get_exemplar_query()
        if exemplar_query is None:
            ic("Exemplar query is None.")
            return {}

        result = {}
        
        # Extract query ID from class name (ExemplarQuery1 -> q1)
        query_id = self.__class__.__name__.lower().replace("exemplarquery", "q")

        for key, value in exemplar_query.aql_queries.items(): # type: ignore
            try:
                ic(f"Executing query variant: {key}")
                result[key] = TimedAQLExecute(
                    description=f"{exemplar_query.user_query} - {key}",
                    query=value.aql_query,
                    bind_vars=value.bind_variables,
                )
            except ConnectionAbortedError as error:
                ic(f"Connection aborted while executing {key} "
                   f"query {value.aql_query} "
                   f"(bind_vars={value.bind_variables}): {error}")
                
                # Write error result if output requested
                if output_file:
                    error_result = ThesisQueryResult(
                        run_id=run_id or "unknown",
                        sequence_number=sequence_number or 1,
                        query_id=query_id,
                        variant=key,
                        execution_time=0.0,
                        result_count=0,
                        count_value=None,
                        cache_state=ThesisQueryResult.determine_cache_state(sequence_number or 1),
                        query_text=self._query,
                        aql_query=value.aql_query,
                        bind_variables=value.bind_variables,
                        error=str(error),
                    )
                    self._write_thesis_results(error_result, output_file)
                continue

        # Display results - the common pattern
        for key, timed_query in result.items():
            data = timed_query.get_data()
            ic(f"Query: {data['description']} (type {key})")
            results_cursor = list(timed_query.get_cursor())
            ic(f"Number of results: {len(results_cursor)}")
            
            # For count queries, extract the actual count value
            count_value = None
            if key == "count" and len(results_cursor) == 1:
                count_value = results_cursor[0]
                ic(f"Result: {count_value}")
            elif len(results_cursor) == 1:
                ic(f"Result: {results_cursor[0]}")
                
            query_time = data.get("query_time")
            if query_time is not None:
                ic(f"Query time: {query_time} seconds")
            
            # Write results if output requested
            if output_file and query_time is not None:
                query_variant = exemplar_query.aql_queries[key]
                
                thesis_result = ThesisQueryResult(
                    run_id=run_id or "unknown",
                    sequence_number=sequence_number or 1,
                    query_id=query_id,
                    variant=key,
                    execution_time=query_time,
                    result_count=len(results_cursor),
                    count_value=count_value,
                    cache_state=ThesisQueryResult.determine_cache_state(sequence_number or 1),
                    query_text=self._query,
                    aql_query=query_variant.aql_query,
                    bind_variables=query_variant.bind_variables,
                    error=None,
                )
                self._write_thesis_results(thesis_result, output_file)
        
        return result
    
    def _write_thesis_results(
        self: Self, 
        result: ThesisQueryResult, 
        output_file: TextIO | Path
    ) -> None:
        """Write thesis-format results to file."""
        if isinstance(output_file, Path):
            # Append to file
            with open(output_file, "a", encoding="utf-8") as f:
                f.write(result.to_jsonl_record())
        else:
            # Write to provided file handle
            output_file.write(result.to_jsonl_record())
            output_file.flush()  # Ensure it's written


def exemplar_main(
    query_class: type[ExemplarQueryBase], 
    output_file: TextIO | Path | None = None,
    run_id: str | None = None,
    sequence_number: int | None = None
) -> None:
    """
    Common main function for all exemplar queries.
    This represents the shared execution wisdom.
    
    Args:
        query_class: The query class to instantiate and execute
        output_file: Optional file handle or Path to write structured results to JSONL
        run_id: Identifier for this test run
        sequence_number: Which iteration this is (1-based)
    """
    query_instance = query_class()
    query_instance.execute(
        output_file=output_file,
        run_id=run_id,
        sequence_number=sequence_number
    )
