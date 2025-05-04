# Prompt Management System

## Overview

The Prompt Management System (PMS) is a comprehensive framework for optimizing, securing, and managing prompts sent to Large Language Models (LLMs) within the Indaleko ecosystem. The system implements the Ayni principle - the concept of mutual cooperation and verification between AI systems - to ensure prompts are efficient, secure, and effective.

This document provides a detailed overview of the components, architecture, and usage patterns of the Prompt Management System.

## Core Components

The PMS consists of several interconnected components that work together to provide a comprehensive prompt management solution:

### 1. Prompt Manager

**Purpose:** Handles template processing, variable binding, and prompt optimization.

**Key Features:**
- Template-based prompt generation
- Variable binding with validation
- Optimization strategies (whitespace normalization, schema simplification, etc.)
- Token counting and usage tracking

**Location:** `/query/utils/prompt_management/prompt_manager.py`

**Usage Example:**
```python
from query.utils.prompt_management.prompt_manager import PromptManager, PromptVariable

# Create a prompt manager
prompt_manager = PromptManager()

# Register a template
prompt_manager.register_template(
    template_id="query_template",
    system_prompt="You are a helpful assistant...",
    user_prompt="Please answer the following question: {query}",
    description="Template for answering queries"
)

# Create a prompt from a template with variables
prompt = prompt_manager.create_prompt(
    template_id="query_template",
    variables=[PromptVariable(name="query", value="What is Indaleko?")],
    optimize=True
)

# Print optimized prompt
print(prompt)
```

### 2. Prompt Guardian

**Purpose:** Ensures prompts meet security and ethical requirements.

**Key Features:**
- Multiple verification levels (NONE, BASIC, STANDARD, STRICT, PARANOID)
- Pattern-based security checks
- Trust contract verification
- Integration with AyniGuard for stability analysis

**Location:** `/query/utils/prompt_management/guardian/prompt_guardian.py`

**Usage Example:**
```python
from query.utils.prompt_management.guardian.prompt_guardian import PromptGuardian, VerificationLevel

# Create a prompt guardian
guardian = PromptGuardian()

# Verify a prompt
prompt = {
    "system": "You are a helpful assistant.",
    "user": "Tell me about Indaleko."
}

result = guardian.verify_prompt(
    prompt=prompt,
    level=VerificationLevel.STANDARD
)

# Check verification result
if result.allowed:
    print("Prompt is allowed!")
else:
    print(f"Prompt verification failed: {result.reasons}")
```

### 3. LLM Guardian

**Purpose:** Coordinates the interaction between all components of the prompt management system.

**Key Features:**
- Integration of all system components
- Request modes (SAFE, WARN, FORCE)
- Comprehensive logging and metrics
- Cache oversight

**Location:** `/query/utils/prompt_management/guardian/llm_guardian.py`

**Usage Example:**
```python
from query.utils.prompt_management.guardian.llm_guardian import LLMGuardian, LLMRequestMode, VerificationLevel

# Create an LLM guardian
guardian = LLMGuardian(
    default_verification_level=VerificationLevel.STANDARD,
    default_request_mode=LLMRequestMode.SAFE
)

# Get completion from a prompt
completion, metadata = guardian.get_completion_from_prompt(
    prompt="Tell me about Indaleko.",
    provider="openai",
    model="gpt-4o",
    optimize=True
)

# Check for completion and metadata
print(completion)
print(f"Verification: {metadata['verification']}")
print(f"Token metrics: {metadata['token_metrics']}")
```

### 4. AyniGuard

**Purpose:** Evaluates prompt stability and contradiction patterns.

**Key Features:**
- Core evaluation logic
- Prompt hashing
- Contradiction detection
- Two-tier caching system

**Location:** `/query/utils/prompt_management/ayni/guard.py`

**Usage Example:**
```python
from query.utils.prompt_management.ayni.guard import AyniGuard

# Create an AyniGuard instance
ayni_guard = AyniGuard()

# Evaluate a prompt
prompt = {
    "system": "You are a helpful assistant.",
    "user": "Tell me about Indaleko."
}

ayni_result = ayni_guard.evaluate(prompt)

# Check evaluation results
print(f"Stability score: {ayni_result.composite_score}")
print(f"Issues detected: {ayni_result.issues}")
```

### 5. Schema Manager

**Purpose:** Handles schema processing and optimization for prompts.

**Key Features:**
- Schema parsing and normalization
- De-duplication logic
- Type simplification
- Schema caching

**Location:** `/query/utils/prompt_management/schema_manager.py`

**Usage Example:**
```python
from query.utils.prompt_management.schema_manager import SchemaManager

# Create a schema manager
schema_manager = SchemaManager()

# Optimize a schema
original_schema = {
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"},
        "address": {
            "type": "object",
            "properties": {
                "street": {"type": "string"},
                "city": {"type": "string"},
                "state": {"type": "string"},
                "zip": {"type": "string"}
            }
        }
    }
}

optimized_schema = schema_manager.optimize_schema(original_schema)

# Compare sizes
print(f"Original size: {len(str(original_schema))}")
print(f"Optimized size: {len(str(optimized_schema))}")
```

### 6. LLM Connectors

**Purpose:** Interface with various LLM providers with integrated prompt management.

**Key Features:**
- Direct and guardian-managed modes
- Token tracking
- Consistent interface across providers
- Backward compatibility

**Locations:**
- `/query/utils/llm_connector/openai_connector_refactored.py`
- `/query/utils/llm_connector/anthropic_connector_refactored.py`
- `/query/utils/llm_connector/gemma_connector_refactored.py`
- `/query/utils/llm_connector/google_connector.py`

**Usage Example:**
```python
from query.utils.llm_connector.factory_updated import LLMFactory

# Get connector through factory
factory = LLMFactory()
llm = factory.get_llm(
    provider="openai",
    model="gpt-4o",
    use_guardian=True,
    verification_level="STANDARD",
    request_mode="WARN"
)

# Get completion
completion, metadata = llm.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko.",
    temperature=0.7
)

print(completion)
```

## System Architecture

The Prompt Management System follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     LLM Connectors                          │
│  (OpenAI, Anthropic, Gemma, Google, etc. with PMS support)  │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────▼─────────────────────────────────┐
│                      LLM Guardian                           │
│     (Coordinator for all prompt management components)      │
└─┬─────────────────────────┬────────────────────────────────┬┘
  │                         │                                │
┌─▼───────────────┐  ┌──────▼──────────┐  ┌─────────────────┐
│ Prompt Manager  │  │ Prompt Guardian │  │    AyniGuard    │
│  (Templates &   │  │  (Security &    │  │(Stability &     │
│  Optimization)  │  │   Verification) │  │ Contradictions) │
└─┬───────────────┘  └─────────────────┘  └────────┬────────┘
  │                                                │
┌─▼───────────────────────────────────────────────▼────────┐
│                   Schema Manager                         │
│           (Schema processing & optimization)             │
└──────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Initialization**: LLM connectors are initialized with the option to use guardian-managed mode.
2. **Prompt Creation**: Prompts are created from templates with variables or provided directly.
3. **Optimization**: Prompts are optimized using strategies like whitespace normalization and schema simplification.
4. **Verification**: Prompts are verified for security and ethical compliance.
5. **Execution**: If verification passes, prompts are sent to the appropriate LLM provider.
6. **Tracking**: Token usage and verification statistics are tracked and stored.

## Configuration Options

### Verification Levels

The system supports multiple verification levels:

- **NONE**: No verification performed
- **BASIC**: Basic pattern checks only
- **STANDARD**: Standard verification (default)
- **STRICT**: Strict verification with additional checks
- **PARANOID**: Highest level of verification

### Request Modes

Different modes for handling verification results:

- **SAFE**: Block prompts that don't pass verification
- **WARN**: Warn on prompts that don't pass verification but proceed anyway
- **FORCE**: Force execution even if verification fails

### Optimization Strategies

Available optimization strategies:

- **WHITESPACE**: Normalize whitespace in prompts
- **SCHEMA_SIMPLIFY**: Simplify JSON schemas in prompts
- **EXAMPLE_REDUCE**: Reduce the number of examples in prompts
- **CONTEXT_WINDOW**: Apply windowing to long context

## Integration with Database

The Prompt Management System uses the following collections in ArangoDB:

1. **Prompt_Templates**: Stores registered prompt templates
2. **Prompt_Cache_Recent**: Stores recently used prompts (hot tier)
3. **Prompt_Cache_Archive**: Stores archived prompts (cold tier)
4. **Prompt_Stability_Metrics**: Stores prompt stability metrics
5. **LLM_Request_Log**: Logs all LLM requests with verification details
6. **Token_Usage_Stats**: Stores token usage statistics

## Best Practices

### Prompt Templates

1. **Use descriptive template IDs**: Make template IDs clear and descriptive.
2. **Document variables**: Clearly document all variables used in templates.
3. **Avoid contradictions**: Ensure system and user prompts don't contradict each other.
4. **Include trust contracts**: Consider adding trust contracts for sensitive operations.

### Verification

1. **Start conservative**: Begin with the STANDARD verification level and adjust as needed.
2. **Use WARN mode during development**: This allows you to see issues without blocking execution.
3. **Test with STRICT mode**: Periodically test with STRICT mode to catch potential issues.

### Optimization

1. **Always optimize**: Enable optimization by default to save tokens.
2. **Review optimized prompts**: Periodically review optimized prompts to ensure they maintain fidelity.
3. **Use all strategies**: Apply all optimization strategies unless you have a specific reason not to.

## Metrics and Monitoring

The system provides comprehensive metrics:

1. **Token Usage**: Track token usage by provider, model, and user.
2. **Verification Metrics**: Monitor verification results and common issues.
3. **Cache Performance**: Track cache hit rates and efficiency.

## Future Directions

1. **Additional Optimization Strategies**: Develop more sophisticated optimization techniques.
2. **Enhanced Contradiction Detection**: Improve detection of subtle contradictions.
3. **Dynamic Verification Levels**: Adjust verification levels based on context and usage patterns.
4. **Multi-LLM Verification**: Use multiple LLMs for verification in critical applications.
5. **User-Specific Policies**: Support user-specific security policies and trust levels.

## References

- [AyniGuard Technical Paper](/doc/technical/ayni_guard.md)
- [Prompt Management System Design](/PROMPT_MANAGEMENT_DESIGN_UPDATED.md)
- [Implementation Plan](/PROMPT_MANAGEMENT_IMPLEMENTATION_UPDATED.md)
- [LLM Integration Summary](/LLM_INTEGRATION_SUMMARY.md)
