# Query Context Integration Implementation Plan

This document outlines the implementation plan for integrating queries with the Indaleko Activity Context system, allowing query relationships to be tracked, analyzed, and utilized to improve search experiences.

## Goals

1. Treat queries as first-class activities in the Activity Context system
2. Track relationships between queries and other activities
3. Enable navigation between related queries (backtracking, pivoting)
4. Analyze query relationships to improve search experiences
5. Visualize query exploration paths

## Architecture Overview

```
query/context/
├── __init__.py
├── activity_provider.py   # QueryActivityProvider class
├── data_models/
│   ├── __init__.py
│   └── query_activity.py  # Query activity data model
├── navigation.py          # Query navigation functionality
├── relationship.py        # Query relationship analysis
├── test_query_context.py  # Unit tests
└── visualization.py       # Path visualization
```

## Phase 1: Core Components (1-2 days)

### QueryActivityProvider Component

The `QueryActivityProvider` class will be responsible for:
- Recording queries as activities in the Activity Context system
- Associating queries with the context in which they were issued
- Managing the persistence of query activity data

```python
class QueryActivityProvider:
    """Provides query activities to the Activity Context system."""

    QUERY_CONTEXT_PROVIDER_ID = uuid.UUID("a7b4c3d2-e5f6-47g8-h9i1-j2k3l4m5n6o7")

    def __init__(self, db_config=None):
        self._context_service = IndalekoActivityContextService(db_config=db_config)

    def record_query(self, query_text, results=None, execution_time=None, query_params=None):
        """Record a query as an activity and associate it with current context."""
        # Get current activity context
        current_context_handle = self._context_service.get_activity_handle()

        # Create query reference and attributes
        query_id = uuid.uuid4()
        attributes = self._build_query_attributes(
            query_text, results, execution_time, query_params, current_context_handle
        )

        # Update activity context with this query
        self._context_service.update_cursor(
            provider=self.QUERY_CONTEXT_PROVIDER_ID,
            provider_reference=query_id,
            provider_data=f"Query: {query_text[:50]}...",
            provider_attributes=attributes
        )

        # Write updated context to database
        self._context_service.write_activity_context_to_database()

        return query_id, current_context_handle

    def _build_query_attributes(self, query_text, results, execution_time, query_params, context_handle):
        """Build the attributes dictionary for the query activity."""
        attributes = {
            "query_text": query_text,
            "result_count": len(results) if results else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        if execution_time is not None:
            attributes["execution_time"] = execution_time

        if query_params is not None:
            attributes["query_params"] = json.dumps(query_params)

        if context_handle is not None:
            attributes["context_handle"] = str(context_handle)

        return attributes

    def get_query_by_id(self, query_id):
        """Retrieve a query by its ID."""
        # Implementation to fetch query data from the activity context system

    def get_recent_queries(self, limit=10):
        """Get the most recent queries."""
        # Implementation to fetch recent queries from the activity context system
```

### Query Activity Data Model

```python
class QueryActivityData(IndalekoBaseModel):
    """Data model for query activities in the activity context system."""

    query_id: uuid.UUID = Field(..., description="Unique identifier for the query")
    query_text: str = Field(..., description="The text of the query")
    execution_time: Optional[float] = Field(None, description="Query execution time in ms")
    result_count: Optional[int] = Field(None, description="Number of results returned")
    context_handle: Optional[uuid.UUID] = Field(None, description="Associated activity context")
    query_params: Optional[Dict[str, Any]] = Field(None, description="Query parameters")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Add pydantic validator to ensure timezone awareness
    @validator("timestamp")
    def ensure_timezone(cls, v):
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    class Config:
        """Configuration for the QueryActivityData model."""
        json_schema_extra = {
            "example": {
                "query_id": "00000000-0000-0000-0000-000000000000",
                "query_text": "Find documents about Indaleko",
                "execution_time": 123.45,
                "result_count": 5,
                "context_handle": "00000000-0000-0000-0000-000000000000",
                "query_params": {
                    "database": "main",
                    "limit": 10
                },
                "timestamp": "2023-04-20T15:30:45.123456Z"
            }
        }
```

## Phase 2: Integration with Query System (2-3 days)

### Hook into Query CLI

Modify `query/cli.py` and `query/assistants/assistant.py` to record queries:

```python
# In query/cli.py
# Add QueryActivityProvider initialization
from query.context.activity_provider import QueryActivityProvider

# Initialize provider
self.query_activity_provider = QueryActivityProvider()

# In execute_query method
start_time = time.time()
results = self.execute_query_internal(query_text, params)
end_time = time.time()
execution_time = (end_time - start_time) * 1000  # ms

# Record the query activity
if hasattr(self, 'query_activity_provider'):
    self.query_activity_provider.record_query(
        query_text=query_text,
        results=results,
        execution_time=execution_time,
        query_params=params
    )
```

### Assistant Integration

Modify the Assistant API implementation to record queries:

```python
# In query/assistants/assistant.py
from query.context.activity_provider import QueryActivityProvider

# In process_message method
# After executing the query tool
if tool_name == "query_executor":
    self.query_activity_provider.record_query(
        query_text=tool_input.get("query"),
        results=tool_output.get("results"),
        execution_time=tool_output.get("execution_time"),
        query_params=tool_input.get("bind_vars")
    )
```

### Query Navigation Implementation

```python
class QueryNavigator:
    """Provides navigation between related queries based on shared context."""

    def __init__(self, db_config=None):
        self._db_config = db_config
        self._context_service = IndalekoActivityContextService(db_config=db_config)

    def get_related_queries(self, query_id=None, context_handle=None, limit=10):
        """Get queries related to the specified query or context."""
        # Implementation retrieves queries sharing contexts with the specified query

        if query_id:
            # Get the context handle for this query
            query_data = self.get_query_by_id(query_id)
            if query_data and "context_handle" in query_data:
                context_handle = query_data["context_handle"]

        if not context_handle:
            return []

        # Query the database for activities with this context handle
        # This returns queries that were part of the same context

        query = """
            FOR ctx IN ActivityContext
            FILTER ctx.Handle == @context_handle
            FOR cursor IN ctx.Cursors
            FILTER cursor.Provider == @provider_id
            RETURN cursor
        """

        # Process and return the results

    def get_query_path(self, query_id):
        """Get the sequence of queries leading to the specified query."""
        # Implementation reconstructs the query exploration path

        query_data = self.get_query_by_id(query_id)
        if not query_data or "context_handle" not in query_data:
            return []

        context_handle = query_data["context_handle"]

        # Retrieve the chain of contexts that led to this one
        # This requires traversing the context graph backwards

        query = """
        FOR ctx IN ActivityContext
        FILTER ctx.Handle == @context_handle

        // Find previous contexts that this one refers to
        // This is a complex traversal based on cursor references

        RETURN ctx
        """

        # Process and return the results

    def get_exploration_branches(self, query_id):
        """Get different exploration branches from a common query point."""
        # Implementation identifies divergent query paths

        # Similar to get_query_path, but identifies branches
        # where the path diverges into multiple directions
```

## Phase 3: Relationship Analysis and Visualization (2-3 days)

### Relationship Detection

```python
class QueryRelationshipDetector:
    """Detects relationships between queries."""

    def detect_refinements(self, query1, query2):
        """Detect if query2 is a refinement of query1."""
        # Analyze query structure for added constraints

        # If query1 is "Find documents about Indaleko"
        # and query2 is "Find PDF documents about Indaleko"
        # then query2 is a refinement of query1

        # We'll need to analyze query structure, which can be done by:
        # 1. Comparing parsed query structures
        # 2. Using LLM-based classification
        # 3. Simple text pattern analysis

    def detect_broadening(self, query1, query2):
        """Detect if query2 is a broadening of query1."""
        # Analyze query structure for removed constraints

        # Similar to detect_refinements but in reverse

    def detect_pivot(self, query1, query2):
        """Detect if query2 is a pivot from query1 (related but different focus)."""
        # Analyze entity focus and context overlap

        # If query1 is "Find documents about Indaleko"
        # and query2 is "Show me the authors of Indaleko documents"
        # then query2 is a pivot from query1

        # This will likely use entity analysis to identify
        # when the focus changes while maintaining some similarity
```

### Path Visualization

```python
class QueryPathVisualizer:
    """Visualizes query paths and relationships."""

    def __init__(self):
        self.graph = None

    def generate_path_graph(self, query_id=None, context_handle=None):
        """Generate a visual graph of related queries."""
        # Creates a graph visualization using networkx
        import networkx as nx

        # Create a new graph
        self.graph = nx.DiGraph()

        # Get query path or related queries
        navigator = QueryNavigator()

        if query_id:
            path = navigator.get_query_path(query_id)

            # Add nodes and edges for the path
            for i, query in enumerate(path):
                self.graph.add_node(query["query_id"], label=query["query_text"])

                if i > 0:
                    # Connect to previous query
                    self.graph.add_edge(path[i-1]["query_id"], query["query_id"])

            # Add branches
            branches = navigator.get_exploration_branches(query_id)

            # Add nodes and edges for branches

        return self.graph

    def export_graph(self, file_path, format="png"):
        """Export the graph in the specified format."""
        # Exports the visualization
        import networkx as nx
        import matplotlib.pyplot as plt

        if not self.graph:
            raise ValueError("No graph has been generated")

        plt.figure(figsize=(12, 8))

        # Create a layout for the graph
        pos = nx.spring_layout(self.graph)

        # Draw the graph
        nx.draw(
            self.graph, pos,
            with_labels=True,
            node_color="skyblue",
            node_size=1500,
            edge_color="gray",
            arrows=True,
            font_size=8
        )

        # Save the graph
        plt.savefig(file_path, format=format)
        plt.close()

        return file_path
```

## Phase 4: Testing (1-2 days)

### Unit Tests

```python
class TestQueryActivityProvider(unittest.TestCase):
    """Tests for the QueryActivityProvider class."""

    def setUp(self):
        # Setup test environment with mock database
        self.provider = QueryActivityProvider()

    def test_record_query(self):
        # Test query recording functionality
        query_text = "Find documents about Indaleko"
        results = [{"id": 1, "name": "Doc1"}, {"id": 2, "name": "Doc2"}]

        query_id, context_handle = self.provider.record_query(query_text, results)

        self.assertIsNotNone(query_id)
        self.assertIsNotNone(context_handle)

        # Verify query was recorded in the database

    def test_context_association(self):
        # Test context association
        query_text = "Find documents about Indaleko"
        query_id, context_handle = self.provider.record_query(query_text)

        # Get query by ID
        query_data = self.provider.get_query_by_id(query_id)

        self.assertEqual(query_data["context_handle"], str(context_handle))

    def test_query_attributes(self):
        # Test query attribute handling
        query_text = "Find documents about Indaleko"
        results = [{"id": 1, "name": "Doc1"}, {"id": 2, "name": "Doc2"}]
        execution_time = 123.45
        query_params = {"limit": 10}

        query_id, _ = self.provider.record_query(
            query_text, results, execution_time, query_params
        )

        query_data = self.provider.get_query_by_id(query_id)

        self.assertEqual(query_data["query_text"], query_text)
        self.assertEqual(query_data["result_count"], 2)
        self.assertEqual(query_data["execution_time"], execution_time)
        self.assertEqual(json.loads(query_data["query_params"]), query_params)
```

### Integration Test Script

```python
def test_query_context_integration():
    """Test the full query context integration."""
    # Initialize query CLI with context integration
    cli = QueryCLI(context_integration=True)

    # Execute a sequence of related queries
    query1_id = cli.execute_query("Find documents about Indaleko")
    query2_id = cli.execute_query("Find PDF documents about Indaleko")
    query3_id = cli.execute_query("Find PDF documents about Indaleko created last week")

    # Navigate between queries
    navigator = QueryNavigator()
    related = navigator.get_related_queries(query1_id)

    # Verify query2 and query3 are related to query1
    related_ids = [q["query_id"] for q in related]
    assert query2_id in related_ids
    assert query3_id in related_ids

    # Verify relationships
    detector = QueryRelationshipDetector()
    assert detector.detect_refinements(query1_id, query2_id)
    assert detector.detect_refinements(query2_id, query3_id)

    # Get query path
    path = navigator.get_query_path(query3_id)
    path_ids = [q["query_id"] for q in path]

    # Verify path contains the sequence of queries
    assert query1_id in path_ids
    assert query2_id in path_ids
    assert query3_id in path_ids

    # Verify correct order
    assert path_ids.index(query1_id) < path_ids.index(query2_id)
    assert path_ids.index(query2_id) < path_ids.index(query3_id)

    # Test path visualization
    visualizer = QueryPathVisualizer()
    graph = visualizer.generate_path_graph(query3_id)
    visualizer.export_graph("query_path.png")

    # Verify graph structure
    assert query1_id in graph.nodes
    assert query2_id in graph.nodes
    assert query3_id in graph.nodes

    # Verify edges
    assert (query1_id, query2_id) in graph.edges
    assert (query2_id, query3_id) in graph.edges
```

## Deliverables

1. Core QueryActivityProvider component
2. Query data models
3. Integration with query system
4. Relationship detection
5. Query navigation functionality
6. Path visualization
7. Comprehensive test suite
8. CLI extension for testing and demonstration

## Verification Strategy

1. **Functional Verification**:
   - Verify queries are properly recorded in activity context
   - Confirm context associations are maintained
   - Test relationship detection accuracy
   - Validate navigation works correctly

2. **Performance Testing**:
   - Measure overhead of context recording
   - Test with large query histories
   - Verify scalability with complex relationship graphs

3. **Integration Testing**:
   - Test with both CLI and Assistant interfaces
   - Verify proper context handling across query sessions
   - Validate backtracking functionality

## Possible Extensions

1. **Query Recommendation System**:
   - Suggest related queries based on current context
   - Identify successful query patterns for recommendation
   - Implement "More like this" functionality

2. **Advanced Visualization**:
   - Interactive visualization in the Streamlit GUI
   - Filtering and exploration of query graphs
   - Highlighting successful exploration paths

3. **Exploration Status Preservation**:
   - Save and restore query exploration state
   - Allow returning to previous exploration sessions
   - Support named "bookmarks" in exploration paths

4. **Multi-User Pattern Analysis**:
   - Anonymized aggregation of exploration patterns
   - Identification of common exploration strategies
   - Learning from successful query paths

## Conclusion

The Query Context Integration will leverage the existing Activity Context system to create a more natural and intuitive search experience. By treating queries as first-class activities that both influence and are influenced by context, we enable a continuous exploration experience that mirrors how humans naturally think.

This implementation will require minimal changes to the existing architecture while adding powerful new capabilities for query relationship tracking and exploration.
