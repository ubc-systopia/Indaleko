# CLAUDE.md - Indaleko Development Guidelines

## Commands
- Run all tests: `pytest tests/`
- Run single test: `pytest tests/path/to/test.py::test_function_name -v`
- Lint code: `flake8` or `pylint`
- Format code: `black .`
- Build package: `python -m build`
- Test query tools: `python query/tools/test_tools.py --query "Your query here" --debug`
- Test EXPLAIN: `python query/test_explain.py --query "Your query here" --debug`

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

## Query Tooling Framework and Assistant Integration
Indaleko uses a modular tooling framework for query processing, with OpenAI Assistant API integration:

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

### Using the CLI with EXPLAIN
The query CLI supports the `--show-plan` flag to display execution plans:
```bash
python query/cli.py --query "Show me documents about Indaleko" --show-plan
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