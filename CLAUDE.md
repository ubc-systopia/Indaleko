# CLAUDE.md - Indaleko Development Guidelines

## Commands
- Run all tests: `pytest tests/`
- Run single test: `pytest tests/path/to/test.py::test_function_name -v`
- Lint code: `flake8` or `pylint`
- Format code: `black .`
- Build package: `python -m build`
- Test query tools: `python query/tools/test_tools.py --query "Your query here" --debug`
- Test EXPLAIN: `python query/test_explain.py --query "Your query here" --debug`
- Test enhanced NL: `python query/test_enhanced_nl.py --query "Your query here" --debug`
- Test relationships: `python query/test_relationship_query.py --query "Show files I shared with Bob last week" --debug`
- Run CLI with enhanced NL: `python -m query.cli --enhanced-nl --context-aware --deduplicate --dynamic-facets`

## Style Guidelines
- Imports: standard library → third-party → local (with blank lines between)
- Types: Use type hints for all functions and variable declarations
- Formatting: 4 spaces, ~100 char line length, docstrings with triple quotes
- Naming: CamelCase for classes, snake_case for functions/vars, UPPER_CASE for constants
- Interfaces: Prefix with 'I' (IObject, IRelationship)
- Error handling: Specific exceptions with descriptive messages
- Documentation: All modules, classes and methods need docstrings (Args/Returns sections)
- Module organization: Copyright header, imports, constants, classes, functions, main
- Datetime fields: Always use timezone-aware datetimes for ArangoDB compatibility:
  ```python
  from datetime import datetime, timezone
  from pydantic import BaseModel, Field, validator
  
  class MyModel(BaseModel):
      # Use Field with default_factory for timezone-aware dates
      created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
      
      # Add validators to ensure datetimes have timezones
      @validator('created_at')
      def ensure_timezone(cls, v):
          if v.tzinfo is None:
              return v.replace(tzinfo=timezone.utc)
          return v
  ```

## Tools
- Models: Extend IndalekoBaseModel (not directly Pydantic's BaseModel) when data may be stored in ArangoDB
- Testing: pytest with unittest for unit tests
- Validation: Use type checking decorators and explicit assertions

### IndalekoBaseModel
For models that will be stored in ArangoDB, always extend IndalekoBaseModel instead of Pydantic's BaseModel:

```python
from data_models.base import IndalekoBaseModel

class MyArangoModel(IndalekoBaseModel):
    name: str
    value: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "example_name",
                "value": 42
            }
        }
```

IndalekoBaseModel provides several key methods:
- `serialize()`: Serializes to a dictionary, excluding unset and None values
- `deserialize()`: Class method to create model from dict or JSON string
- `get_json_example()`: Gets a JSON-compatible example from the model's Config
- `get_example()`: Returns a complete model instance based on the Config example
- `build_arangodb_doc()`: Builds a document ready for ArangoDB insertion, adding `_key`
- `get_arangodb_schema()`: Returns schema in ArangoDB's required format with:
  - `message`: Custom validation error message
  - `level`: Validation level (usually "strict")
  - `type`: Schema type ("json")
  - `rule`: The actual JSON schema

## Dependencies
- Required packages for LLM integration: 
  - openai>=1.0.0
  - tiktoken>=0.5.0
  - regex>=2023.0.0

## Query Capabilities
Indaleko features an extensive modular query system with natural language understanding, faceted search, relationship queries, and more:

### Core Tool Components
1. **BaseTool**: Abstract base class for all tools, with:
   - `definition`: Returns the tool definition
   - `execute`: Executes the tool with given inputs
   
2. **ToolRegistry**: Manages tool registration and execution:
   - `register_tool`: Registers a tool
   - `execute_tool`: Executes a tool with given inputs
   - `get_registry`: Singleton access function

### Key Query Tools
1. **NLParserTool**: Parses natural language queries to extract:
   - Intent
   - Entities
   - Relevant collections

2. **AQLTranslatorTool**: Converts structured queries to AQL:
   - Builds AQL based on intent and entities
   - Includes bind variables for parameterized queries
   - Properly formats entities for translation

3. **QueryExecutorTool**: Executes or explains AQL queries:
   - Can execute queries or just explain them
   - Returns results, execution plans, or both

### Data Flow
1. Natural language query → NLParserTool → Structured query
2. Structured query → AQLTranslatorTool → AQL query + bind variables
3. AQL query → QueryExecutorTool → Results and/or execution plan

### Entity Handling
- NLParser extracts entities and maps them to `IndalekoNamedEntityDataModel` objects
- Entities are collected in a `NamedEntityCollection` container
- AQLTranslator maps these entities to AQL query expressions

### Assistant API Implementation
Indaleko now integrates with OpenAI's Assistant API for more interactive query capabilities:

#### Components
1. **IndalekoAssistant**: Core class that manages interaction with OpenAI's Assistant API:
   - Automatically creates and manages Assistant configurations
   - Converts Indaleko tool definitions to OpenAI function formats
   - Manages conversation threads and tool execution

2. **ConversationState**: Stores conversation state including:
   - Messages (user, assistant, system)
   - Detected entities
   - Query history
   - Execution context (thread IDs, etc.)

3. **Assistant CLI**: Command-line interface for the Assistant:
   - Interactive conversation mode
   - Batch processing mode
   - Conversation saving/loading

#### Usage
To use the Assistant API implementation:

```python
# Initialize the assistant with our tools
from query.assistants.assistant import IndalekoAssistant
from query.tools.registry import get_registry
from query.tools.translation import nl_parser, aql_translator
from query.tools.database import executor

# Register tools
registry = get_registry()
registry.register_tool(nl_parser.NLParserTool)
registry.register_tool(aql_translator.AQLTranslatorTool)
registry.register_tool(executor.QueryExecutorTool)

# Create assistant
assistant = IndalekoAssistant()

# Create a conversation
conversation = assistant.create_conversation()
conversation_id = conversation.conversation_id

# Process messages
response = assistant.process_message(
    conversation_id=conversation_id,
    message_content="Show me documents about Indaleko"
)

# Display response
print(response["response"])
```

You can also use the CLI:
```bash
# Interactive mode
python query/assistants/assistant_cli.py --model gpt-4o

# Batch mode
python query/assistants/assistant_cli.py --batch queries.txt --debug
```

For testing, use the test script:
```bash
python query/assistants/test_assistant.py --model gpt-4o-mini --debug
```

## Advanced Query Features

### Enhanced Natural Language Processing
Indaleko includes advanced natural language understanding for queries:

1. **EnhancedNLParser**: Extends the base NLParser with:
   - More sophisticated intent classification
   - Entity resolution and linking
   - Constraint extraction with rich type system
   - Temporal and spatial understanding
   - Context awareness across multiple queries
   - Integration with dynamic facets

2. **EnhancedAQLTranslator**: Improved query translation with:
   - Direct handling of enhanced query understanding
   - More sophisticated constraint handling
   - Support for complex temporal and spatial queries
   - Performance optimization hints
   - Improved bind variable handling

3. **Usage**:
```python
from query.query_processing.enhanced_nl_parser import EnhancedNLParser
from query.query_processing.query_translator.enhanced_aql_translator import EnhancedAQLTranslator

# Initialize components
enhanced_parser = EnhancedNLParser(llm_connector, collections_metadata)
enhanced_translator = EnhancedAQLTranslator(collections_metadata)

# Parse query with enhanced understanding
query_understanding = enhanced_parser.parse_enhanced(
    query="Find PDF documents I modified last week",
    facet_context=facet_data,  # Optional: previous facet data for context
    include_history=True  # Optional: use query history for context
)

# Create translator input
query_data = TranslatorInput(
    Query=query_understanding,
    Connector=llm_connector,
)

# Translate to AQL with enhanced capabilities
translated_query = enhanced_translator.translate_enhanced(
    query_understanding, query_data
)
```

### Dynamic Faceted Search
Indaleko provides rich faceted search capabilities:

1. **FacetGenerator**: Analyzes search results to produce:
   - Dynamic facets based on result attributes
   - Statistical distribution analysis of values
   - Relevance ranking of potential facets
   - Conversational suggestions for refinement

2. **QueryRefiner**: Manages interactive query refinement:
   - Handles state for active refinements
   - Applies facet selections to queries
   - Provides command-based interface (!refine, !remove, etc.)
   - Maintains refinement history

3. **Usage Example**:
```python
from query.result_analysis.facet_generator import FacetGenerator
from query.result_analysis.query_refiner import QueryRefiner

# Initialize components
facet_generator = FacetGenerator(
    max_facets=5,
    min_facet_coverage=0.2,
    conversational=True
)
query_refiner = QueryRefiner()

# Generate facets from results
facets = facet_generator.generate(query_results)

# Apply a facet refinement
refined_query, new_state = query_refiner.apply_refinement(
    facet_name="file_type",
    facet_value="PDF"
)
```

### Relationship Queries
Indaleko supports relationship-based queries that focus on connections between entities:

1. **RelationshipParser**: Extracts relationship information from queries:
   - Identifies relationship types (created, modified, shared_with, etc.)
   - Extracts source and target entities
   - Determines relationship direction
   - Supports time constraints on relationships

2. **Relationship Types**:
   - User-File: created, modified, viewed, owns
   - File-File: derived_from, contains, same_folder, related_to
   - User-User: shared_with, collaborated_with, recommended_to

3. **Usage Example**:
```python
from query.query_processing.relationship_parser import RelationshipParser
from query.query_processing.data_models.relationship_query_model import RelationshipType

# Initialize parser
relationship_parser = RelationshipParser(
    llm_connector=llm_connector,
    collections_metadata=collections_metadata
)

# Parse a relationship query
relationship_query = relationship_parser.parse_relationship_query(
    "Show files I shared with Bob last week"
)

# Access the relationship information
relationship_type = relationship_query.relationship_type  # e.g., SHARED_WITH
source_entity = relationship_query.source_entity  # e.g., current user
target_entity = relationship_query.target_entity  # e.g., Bob
```

## ArangoDB Query Performance
To optimize ArangoDB queries, use the EXPLAIN functionality:

### Using EXPLAIN with AQL
```python
# Basic usage
explain_result = db.aql.explain(
    query_string,
    bind_vars={},
    options={}
)

# With all options
explain_result = db.aql.explain(
    query_string,
    bind_vars={},
    options={
        "allPlans": True,        # Return all possible execution plans
        "maxNumberOfPlans": 10,  # Maximum number of plans to return
        "optimizer": {           # Optimizer rules to include/exclude
            "rules": ["-all", "+use-indexes"]
        },
        "colors": False          # No ANSI color codes in explanation
    }
)
```

### Explanation Result Structure
```python
{
    # Main execution plan
    "plan": {
        "nodes": [...],         # Plan operation nodes
        "rules": [...],         # Optimizer rules applied
        "collections": [...],   # Collections used
        "variables": [...],     # Variables used
        "estimatedCost": 123.45 # Estimated cost of execution
    },
    
    # Only included when allPlans=True
    "plans": [
        { "nodes": [...], "rules": [...], ... },
        { ... }
    ],
    
    # Cache usage info
    "cacheable": True,
    
    # Warnings about the query
    "warnings": [],
    
    # Statistics
    "stats": {
        "rulesExecuted": 23,    # Number of rules executed
        "rulesSkipped": 3,      # Number of rules skipped
        "plansCreated": 4       # Number of plans created
    }
}
```

### Using the CLI with Advanced Features
The query CLI supports various flags for enhanced functionality:

```bash
# Show execution plan
python query/cli.py --query "Show me documents about Indaleko" --show-plan

# Use enhanced natural language understanding
python query/cli.py --enhanced-nl --query "Find PDF documents I modified last week that contain budget information"

# Enable context-aware queries that remember previous interactions
python query/cli.py --enhanced-nl --context-aware

# Use dynamic facets for interactive result exploration
python query/cli.py --dynamic-facets --interactive

# Enable deduplication with Jaro-Winkler similarity
python query/cli.py --deduplicate --similarity-threshold 0.85

# Combine multiple features
python query/cli.py --enhanced-nl --context-aware --deduplicate --dynamic-facets --conversational
```

### Programmatic EXPLAIN Usage
```python
# Using the QueryExecutorTool
executor = QueryExecutorTool()
result = executor.execute(ToolInput(
    tool_name="query_executor",
    parameters={
        "query": "FOR obj IN Objects FILTER obj.name LIKE '%Indaleko%' RETURN obj",
        "bind_vars": {},
        "explain_only": True,
        "include_plan": True,
        "all_plans": False,
        "max_plans": 5
    }
))

# With the test_explain.py script
python query/test_explain.py --query "Show me documents about Indaleko" --debug
```

### Interpreting Results
- Lower `estimatedCost` indicates a more efficient plan
- Check for full collection scans (nodes with type "EnumerateCollectionNode")
- Look for index usage (nodes with type "IndexNode")
- Examine "collections" to ensure the right ones are being queried
- Check "warnings" for potential issues
- Look for recommendations in the analysis section

### Common Issues and Fixes
- "No indexes are being used in this query" - Add appropriate indexes for frequently filtered fields
- High `estimatedCost` - Refine your query to use indexes and reduce collection scans
- "collection not found" - Check collection names, ensure using valid collections from the database