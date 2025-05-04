# LLM Connector Integration Plan for Indaleko

This document outlines the comprehensive plan for implementing multi-LLM provider support in the Indaleko query assistant functionality.

## Progress Update (June 2, 2024)

### Completed Tasks
- ✅ LLM connector factory implementation with dynamic provider loading
- ✅ Environment variable support for API keys
- ✅ Unified configuration with `llm-keys.ini`
- ✅ Support for OpenAI-compatible providers (Deepseek, Grok)
- ✅ Implementation of Anthropic (Claude) connector 
- ✅ Update Tool Base Class
- ✅ Update Tool Registry 
- ✅ Update NL Parser Tool
- ✅ Update AQL Translator Tool
- ✅ Update NL Parser Implementation
- ✅ Update AQL Translator Implementation
- ✅ Update Enhanced NL Parser Implementation
- ✅ Update Enhanced AQL Translator Implementation
- ✅ Update CLI Interface
- ✅ Update Conversation Manager

### In Progress
- Test full query flow with different connectors
- Performance Benchmarking

### Pending Tasks
- Add cost tracking and optimization

## 1. Current Architecture Analysis

The Indaleko query assistant currently relies on a sequence of tools to process natural language queries:

1. Natural language parsing (`nl_parser`)
2. Query translation (`aql_translator`)
3. Query execution (`query_executor`)

Each of these components currently creates its own LLM connection when needed, primarily hardcoded to use OpenAI.

## 2. Components Requiring Modification

### Core LLM Interaction Components

1. **Natural Language Processing Tools**
   - `query/tools/translation/nl_parser.py` - Tool wrapper for NL parser
   - `query/query_processing/nl_parser.py` - Core implementation
   - `query/query_processing/enhanced_nl_parser.py` - Extended implementation

2. **Query Translation Components**
   - `query/tools/translation/aql_translator.py` - Tool wrapper
   - `query/query_processing/query_translator/aql_translator.py` - Core implementation
   - `query/query_processing/query_translator/enhanced_aql_translator.py` - Extended implementation

3. **LLM Connectors**
   - `query/utils/llm_connector/llm_base.py` - Base interface
   - `query/utils/llm_connector/openai_connector.py` - OpenAI implementation
   - `query/utils/llm_connector/gemma_connector.py` - Gemma implementation
   - `query/utils/llm_connector/factory.py` - Factory implementation

4. **Prompt Management**
   - `query/utils/prompt_manager.py` - Manages prompts and optimizations

### Integration Points

1. **CLI Interface**
   - `query/assistants/cli.py` - Command-line interface
   - `query/assistants/conversation.py` - Conversation management

2. **Tool Registration and Execution**
   - `query/tools/registry.py` - Manages tool registration
   - `query/tools/base.py` - Base tool definitions

## 3. Implementation Plan

### Phase 1: Tool Interface Modification

1. **Update Tool Base Class**
   - Modify `query/tools/base.py` to support LLM connector injection
   - Add parameters for passing connector to tool constructor
   - Update `ToolInput` to include connector information

2. **Update Tool Registry**
   - Modify `query/tools/registry.py` to pass connector during tool execution
   - Ensure existing tools continue to work if no connector provided

3. **Refactor NL Parser Tool**
   - Update `query/tools/translation/nl_parser.py` to accept connector
   - Pass connector to underlying implementation
   - Add backward compatibility

4. **Refactor AQL Translator Tool**
   - Update `query/tools/translation/aql_translator.py` to accept connector
   - Pass connector to underlying implementation
   - Add backward compatibility

### Phase 2: Core Processing Updates

1. **Update NL Parser Implementation**
   - Modify `query/query_processing/nl_parser.py` to use provided connector
   - Remove internal connector creation
   - Ensure API compatibility

2. **Update AQL Translator Implementation**
   - Modify `query/query_processing/query_translator/aql_translator.py` to use provided connector
   - Ensure response handling works with various providers
   - Handle provider-specific schema requirements

3. **Update Enhanced Implementations**
   - Update `query/query_processing/enhanced_nl_parser.py`
   - Update `query/query_processing/query_translator/enhanced_aql_translator.py`

### Phase 3: Integration Layer

1. **Update Conversation Manager**
   - Ensure `query/assistants/conversation.py` passes connector to tools
   - Add connector type selection to initialization

2. **Update CLI Interface**
   - Add connector selection to CLI arguments in `query/assistants/cli.py`
   - Pass connector to conversation manager

3. **Connector Configuration**
   - Implement unified configuration approach
   - Support specifying model parameters for each provider

### Phase 4: Testing and Validation

1. **Unit Tests**
   - Create tests for each connector type
   - Verify compatibility with existing tools

2. **Integration Tests**
   - Test full query flow with different connectors
   - Compare output quality and performance

3. **Performance Benchmarking**
   - Measure response times for different providers
   - Compare token usage and costs

## 4. Detailed Changes Required

### Tool Base Classes (`query/tools/base.py`)

```python
class ToolInput:
    """Input for a tool execution."""
    
    def __init__(
        self,
        tool_name: str,
        parameters: dict[str, Any],
        conversation_id: str,
        invocation_id: str,
        llm_connector: Optional[IndalekoLLMBase] = None,  # Add LLM connector
    ):
        """Initialize the tool input."""
        self.tool_name = tool_name
        self.parameters = parameters
        self.conversation_id = conversation_id
        self.invocation_id = invocation_id
        self.llm_connector = llm_connector  # Store the connector
```

### Tool Registry (`query/tools/registry.py`)

```python
def execute_tool(self, tool_input: ToolInput) -> ToolOutput:
    """Execute a tool with the given input."""
    tool_name = tool_input.tool_name
    if tool_name not in self._tools:
        return ToolOutput(
            tool_name=tool_name,
            success=False,
            error=f"Tool '{tool_name}' not found",
            elapsed_time=0,
        )
    
    tool = self._tools[tool_name]
    
    # Pass LLM connector to tool
    if tool_input.llm_connector:
        tool_instance = tool(llm_connector=tool_input.llm_connector)
    else:
        tool_instance = tool()
        
    # Execute tool
    return tool_instance.execute(tool_input)
```

### NL Parser Tool (`query/tools/translation/nl_parser.py`)

```python
class NLParserTool(IndalekoToolBase):
    """Tool for parsing natural language queries."""
    
    def __init__(self, llm_connector: Optional[IndalekoLLMBase] = None):
        """Initialize the tool with an optional LLM connector."""
        super().__init__()
        self.llm_connector = llm_connector
        
    def execute(self, tool_input: ToolInput) -> ToolOutput:
        """Execute the tool."""
        start_time = time.time()
        
        try:
            # Create parser with provided connector or default
            connector = tool_input.llm_connector or self.llm_connector
            parser = NLParser(collections_metadata, llm_connector=connector)
            
            # Process query
            result = parser.parse(tool_input.parameters["query"])
            
            elapsed_time = time.time() - start_time
            return ToolOutput(
                tool_name=tool_input.tool_name,
                success=True,
                result=result,
                elapsed_time=elapsed_time,
            )
        except Exception as e:
            elapsed_time = time.time() - start_time
            return ToolOutput(
                tool_name=tool_input.tool_name,
                success=False,
                error=str(e),
                elapsed_time=elapsed_time,
            )
```

### NL Parser Implementation (`query/query_processing/nl_parser.py`)

```python
class NLParser:
    """Natural language parser for user queries."""
    
    def __init__(
        self,
        collections_metadata: IndalekoDBCollectionsMetadata,
        llm_connector: Optional[IndalekoLLMBase] = None,
    ):
        """
        Initialize the parser.
        
        Args:
            collections_metadata: DB collection metadata
            llm_connector: Optional LLM connector to use
        """
        self.collections_metadata = collections_metadata
        
        # Use provided connector or create a default one
        if llm_connector:
            self.llm_connector = llm_connector
        else:
            # Create default connector (backward compatibility)
            from query.utils.llm_connector.factory import LLMConnectorFactory
            self.llm_connector = LLMConnectorFactory.create_connector()
```

### Execute Tool in Conversation Manager (`query/assistants/conversation.py`)

```python
def execute_tool(
    self,
    conversation_id: str,
    tool_name: str,
    parameters: dict[str, Any],
) -> ToolOutput:
    """Execute a tool in the context of a conversation."""
    conversation = self.get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation not found: {conversation_id}")
    
    # Create tool input with LLM connector
    tool_input = ToolInput(
        tool_name=tool_name,
        parameters=parameters,
        conversation_id=conversation_id,
        invocation_id=str(uuid.uuid4()),
        llm_connector=self.llm_connector,  # Pass the connector
    )
    
    # Execute the tool
    return self.tool_registry.execute_tool_input(tool_input)
```

## 5. Potential Challenges and Mitigation

### Challenge 1: Response Format Inconsistencies

Different LLM providers return responses in different formats, which may cause parsing issues.

**Mitigation:**
- Implement provider-specific response parsers in each connector
- Add response validation to ensure consistent output structure
- Use schema validation for responses

### Challenge 2: Prompt Engineering Differences

Different models may require different prompt engineering techniques for optimal results.

**Mitigation:**
- Extend prompt manager to support provider-specific templates
- Add model-specific prompt optimization techniques
- Create provider-specific example formats

### Challenge 3: Error Handling Differences

Each LLM provider has unique error types and handling requirements.

**Mitigation:**
- Standardize error handling across connectors
- Map provider-specific errors to common error types
- Implement robust retry logic with backoff

### Challenge 4: Performance Variations

Different LLM providers have varying performance characteristics and latency.

**Mitigation:**
- Add performance monitoring for each provider
- Implement timeouts tailored to each provider
- Create fallback mechanisms for slow or failed responses

## 6. Task Prioritization

### High Priority
1. Update tool execution flow to accept and pass LLM connector
2. Modify NL parser to use provided connector
3. Update AQL translator to use provided connector
4. Ensure connector configuration works properly

### Medium Priority
1. Standardize error handling across connectors
2. Implement provider-specific response parsing
3. Add performance monitoring for all providers
4. Create comprehensive test suite

### Low Priority
1. Implement advanced features like automatic fallback
2. Add cost tracking and optimization
3. Create provider-specific prompt templates
4. Implement response caching

## 7. Conclusion

Implementing multi-LLM provider support in Indaleko will require careful modification of the core NL processing and query translation components. By using a factory pattern and dependency injection, we can maintain backward compatibility while adding support for new providers.

The key to success will be ensuring consistent response handling across different LLM providers and maintaining the quality of query processing regardless of the underlying LLM service.