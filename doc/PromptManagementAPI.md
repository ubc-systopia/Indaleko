# Prompt Management System API Documentation

This document provides a comprehensive API reference for the Indaleko Prompt Management System (PMS).

## Table of Contents

1. [Getting Started](#getting-started)
2. [PromptManager API](#promptmanager-api)
3. [PromptGuardian API](#promptguardian-api)
4. [LLMGuardian API](#llmguardian-api)
5. [AyniGuard API](#ayniguard-api)
6. [SchemaManager API](#schemamanager-api)
7. [LLM Connector API](#llm-connector-api)
8. [Factory API](#factory-api)
9. [Common Data Models](#common-data-models)
10. [Error Handling](#error-handling)
11. [Configuration](#configuration)

## Getting Started

### Basic Usage

The most common way to use the prompt management system is through the LLM Factory:

```python
from query.utils.llm_connector.factory_updated import LLMFactory

# Get an LLM interface with prompt management enabled
factory = LLMFactory()
llm = factory.get_llm(
    provider="openai",  # or "anthropic", "gemma", "google", etc.
    model="gpt-4o",
    use_guardian=True,
    verification_level="STANDARD",
    request_mode="WARN"
)

# Get a completion with automatic prompt management
completion, metadata = llm.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko.",
    temperature=0.7
)

print(completion)
print(metadata["token_metrics"])  # See token usage statistics
```

### Installation Requirements

Make sure you have the necessary dependencies installed:

```bash
pip install tiktoken openai anthropic google-genai
```

## PromptManager API

The `PromptManager` class handles template processing, variable binding, and prompt optimization.

### Initialization

```python
from query.utils.prompt_management.prompt_manager import PromptManager

# Initialize with default settings
prompt_manager = PromptManager()

# Initialize with custom settings
prompt_manager = PromptManager(
    max_tokens=4096,
    registry=custom_registry,
    db_instance=db_connection,
    ayni_guard=custom_ayni_guard,
    schema_manager=custom_schema_manager
)
```

### Template Management

```python
# Register a template
template_id = prompt_manager.register_template(
    template_id="query_template",
    system_prompt="You are a helpful assistant that translates natural language to AQL.",
    user_prompt="Please translate this query: {query}",
    description="Template for query translation",
    version="1.0",
    author="User",
    variables=["query"],
    examples=[{"query": "Find all documents created last week"}]
)

# Get a template
template = prompt_manager.get_template(template_id="query_template")

# Update a template
prompt_manager.update_template(
    template_id="query_template",
    system_prompt="You are an expert at translating natural language to AQL."
)

# List templates
templates = prompt_manager.list_templates()

# Delete a template
prompt_manager.delete_template(template_id="query_template")
```

### Prompt Creation

```python
from query.utils.prompt_management.prompt_manager import PromptVariable

# Create a prompt from a template
prompt = prompt_manager.create_prompt(
    template_id="query_template",
    variables=[PromptVariable(name="query", value="Find all documents with tag 'important'")],
    optimize=True,
    strategies=[
        PromptOptimizationStrategy.WHITESPACE,
        PromptOptimizationStrategy.SCHEMA_SIMPLIFY
    ],
    evaluate_stability=True
)

# Access prompt components
system_prompt = prompt.system
user_prompt = prompt.user
token_count = prompt.token_count
stability_score = prompt.stability_score
```

### Prompt Optimization

```python
# Optimize an existing prompt
original_prompt = {
    "system": "You are a helpful assistant.",
    "user": "Tell me about Indaleko."
}

optimized_result = prompt_manager.optimize_prompt(
    prompt=original_prompt,
    strategies=[
        PromptOptimizationStrategy.WHITESPACE,
        PromptOptimizationStrategy.SCHEMA_SIMPLIFY
    ]
)

print(f"Original tokens: {optimized_result.original_token_count}")
print(f"Optimized tokens: {optimized_result.token_count}")
print(f"Token savings: {optimized_result.token_savings}")
```

## PromptGuardian API

The `PromptGuardian` class ensures prompts meet security and ethical requirements.

### Initialization

```python
from query.utils.prompt_management.guardian.prompt_guardian import PromptGuardian, VerificationLevel

# Initialize with default settings
guardian = PromptGuardian()

# Initialize with custom settings
guardian = PromptGuardian(
    db_instance=db_connection,
    ayni_guard=custom_ayni_guard,
    security_policy=custom_security_policy,
    default_verification_level=VerificationLevel.STRICT
)
```

### Prompt Verification

```python
# Verify a prompt
prompt = {
    "system": "You are a helpful assistant.",
    "user": "Tell me about Indaleko."
}

result = guardian.verify_prompt(
    prompt=prompt,
    level=VerificationLevel.STANDARD,
    user_id="user123"
)

# Check verification result
if result.allowed:
    print("Prompt is allowed!")
else:
    print(f"Prompt blocked: {result.reasons}")
    print(f"Recommendation: {result.recommendation}")

# Access verification details
print(f"Security issues: {result.security_issues}")
print(f"Ethical issues: {result.ethical_issues}")
print(f"Score: {result.score}")
print(f"Trust contract valid: {result.trust_contract_valid}")
```

### Verification Logs

```python
# Get verification logs
logs = guardian.get_verification_logs(
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 5, 1),
    user_id="user123",
    limit=100
)

# Get verification metrics
metrics = guardian.get_verification_metrics(
    start_time=datetime(2025, 1, 1),
    end_time=datetime(2025, 5, 1),
    user_id="user123"
)

print(f"Total verifications: {metrics['total_verifications']}")
print(f"Allowed percentage: {metrics['allowed_percent']}%")
print(f"Security issues: {metrics['security_issue_count']}")
```

## LLMGuardian API

The `LLMGuardian` class coordinates all prompt management components.

### Initialization

```python
from query.utils.prompt_management.guardian.llm_guardian import (
    LLMGuardian, VerificationLevel, LLMRequestMode
)

# Initialize with default settings
guardian = LLMGuardian()

# Initialize with custom settings
guardian = LLMGuardian(
    db_instance=db_connection,
    prompt_manager=custom_prompt_manager,
    prompt_guardian=custom_prompt_guardian,
    llm_factory=custom_llm_factory,
    schema_manager=custom_schema_manager,
    default_verification_level=VerificationLevel.STANDARD,
    default_request_mode=LLMRequestMode.SAFE
)
```

### LLM Completion

```python
# Get completion from a raw prompt
completion, metadata = guardian.get_completion_from_prompt(
    prompt="Tell me about Indaleko.",
    provider="openai",
    model="gpt-4o",
    system_prompt="You are a helpful assistant.",
    verification_level=VerificationLevel.STANDARD,
    request_mode=LLMRequestMode.WARN,
    user_id="user123",
    optimize=True,
    options={
        "temperature": 0.7,
        "max_tokens": 500
    }
)

# Get completion from a template
completion, metadata = guardian.get_completion_from_template(
    template_id="query_template",
    variables=[
        PromptVariable(name="query", value="Find all documents with tag 'important'")
    ],
    provider="anthropic",
    model="claude-3-sonnet-20240229",
    verification_level=VerificationLevel.STANDARD,
    request_mode=LLMRequestMode.WARN,
    user_id="user123",
    optimize=True,
    evaluate_stability=True,
    options={
        "temperature": 0.7,
        "max_tokens": 500
    }
)
```

### Token Usage Statistics

```python
# Get token usage statistics
stats = guardian.get_token_usage_stats(
    start_date="2025-01-01",
    end_date="2025-05-01",
    user_id="user123",
    provider="openai",
    model="gpt-4o"
)

print(f"Total requests: {stats['total_requests']}")
print(f"Total tokens: {stats['total_tokens']}")
print(f"Original tokens: {stats['total_original_tokens']}")
print(f"Token savings: {stats['total_token_savings']}")
print(f"Average tokens per request: {stats['average_tokens_per_request']}")
print(f"Savings percentage: {stats['savings_percent']}%")

# Get token usage by day
daily_stats = guardian.get_token_usage_by_day(
    start_date="2025-01-01",
    end_date="2025-01-31",
    user_id="user123"
)

# Get token usage by provider
provider_stats = guardian.get_token_usage_by_provider(
    start_date="2025-01-01",
    end_date="2025-05-01",
    user_id="user123"
)
```

## AyniGuard API

The `AyniGuard` class evaluates prompt stability and contradiction patterns.

### Initialization

```python
from query.utils.prompt_management.ayni.guard import AyniGuard

# Initialize with default settings
ayni_guard = AyniGuard()

# Initialize with custom settings
ayni_guard = AyniGuard(
    db_instance=db_connection,
    pattern_catalog=custom_pattern_catalog,
    cache_ttl=3600,  # 1 hour
    cache_max_size=1000
)
```

### Prompt Evaluation

```python
# Evaluate a prompt
prompt = {
    "system": "You are a helpful assistant.",
    "user": "Tell me about Indaleko."
}

ayni_result = ayni_guard.evaluate(prompt, user_id="user123")

# Access evaluation details
print(f"Composite score: {ayni_result.composite_score}")
print(f"Issues: {ayni_result.issues}")
print(f"Action: {ayni_result.action}")
print(f"Details: {ayni_result.details}")
```

### Cache Management

```python
# Get cache statistics
cache_stats = ayni_guard.get_cache_stats()

print(f"Recent cache size: {cache_stats['recent_size']}")
print(f"Recent cache hit rate: {cache_stats['recent_hit_rate']}%")
print(f"Archive cache size: {cache_stats['archive_size']}")
print(f"Archive cache hit rate: {cache_stats['archive_hit_rate']}%")

# Clear cache
ayni_guard.clear_cache()

# Compute a prompt hash (for cache lookup)
prompt_hash = ayni_guard.compute_prompt_hash(prompt)
```

## SchemaManager API

The `SchemaManager` class handles schema processing and optimization.

### Initialization

```python
from query.utils.prompt_management.schema_manager import SchemaManager

# Initialize with default settings
schema_manager = SchemaManager()

# Initialize with custom settings
schema_manager = SchemaManager(
    cache_ttl=3600,  # 1 hour
    cache_max_size=1000
)
```

### Schema Optimization

```python
# Original schema
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

# Optimize schema
optimized_schema = schema_manager.optimize_schema(
    schema=original_schema,
    level=2  # Optimization level (1-3)
)

# Compare schemas
original_size = len(json.dumps(original_schema))
optimized_size = len(json.dumps(optimized_schema))
savings_percent = (original_size - optimized_size) / original_size * 100

print(f"Original size: {original_size} bytes")
print(f"Optimized size: {optimized_size} bytes")
print(f"Size reduction: {savings_percent:.2f}%")
```

### Schema Extraction

```python
# Extract schemas from text
text = """
Here are the response schemas:
```json
{
    "type": "object",
    "properties": {
        "name": {"type": "string"},
        "age": {"type": "integer"}
    }
}
```
"""

schemas = schema_manager.extract_schemas_from_text(text)
print(f"Found {len(schemas)} schemas")
```

## LLM Connector API

The LLM connectors provide a consistent interface across different LLM providers.

### OpenAI Connector

```python
from query.utils.llm_connector.openai_connector_refactored import OpenAIConnector

# Initialize the connector
connector = OpenAIConnector(
    api_key="your-api-key",
    model="gpt-4o",
    use_guardian=True,
    verification_level="STANDARD",
    request_mode="WARN"
)

# Generate a query
response = connector.generate_query(
    prompt={
        "system": "You are a helpful assistant.",
        "user": "Translate 'find documents from last week' to AQL."
    },
    temperature=0
)

print(response.translated_query)
```

### Anthropic Connector

```python
from query.utils.llm_connector.anthropic_connector_refactored import AnthropicConnector

# Initialize the connector
connector = AnthropicConnector(
    api_key="your-api-key",
    model="claude-3-sonnet-20240229",
    use_guardian=True,
    verification_level="STANDARD",
    request_mode="WARN"
)

# Generate text
result = connector.generate_text(
    prompt="Write a short paragraph about Indaleko.",
    max_tokens=200,
    temperature=0.7
)

print(result)
```

### Google Connector

```python
from query.utils.llm_connector.google_connector import GoogleConnector

# Initialize the connector
connector = GoogleConnector(
    api_key="your-api-key",
    model="gemini-2.0-flash",
    use_guardian=True,
    verification_level="STANDARD",
    request_mode="WARN"
)

# Answer a question
answer = connector.answer_question(
    context="Indaleko is a unified personal index system.",
    question="What is Indaleko?",
    schema={
        "type": "object",
        "properties": {
            "answer": {"type": "string"},
            "confidence": {"type": "number"}
        }
    }
)

print(answer["answer"])
```

### Gemma Connector

```python
from query.utils.llm_connector.gemma_connector_refactored import GemmaConnector

# Initialize the connector
connector = GemmaConnector(
    base_url="http://localhost:1234/v1",
    model="Gemma",
    use_guardian=True,
    verification_level="STANDARD",
    request_mode="WARN"
)

# Extract keywords
keywords = connector.extract_keywords(
    text="Indaleko is a unified personal index system for storage.",
    num_keywords=5
)

print(keywords)
```

## Factory API

The `LLMFactory` provides a unified interface for creating LLM connectors.

### Basic Usage

```python
from query.utils.llm_connector.factory_updated import LLMFactory

# Create factory
factory = LLMFactory()

# List available connectors
connectors = factory.get_available_connectors()
print(connectors)  # ['openai', 'anthropic', 'gemma', 'google', 'deepseek', 'grok']

# Create a connector
connector = factory.create_connector(
    connector_type="openai",
    api_key="your-api-key",
    use_guardian=True,
    verification_level="STANDARD",
    request_mode="WARN"
)

# Get an LLM interface
llm = factory.get_llm(
    provider="anthropic",
    model="claude-3-sonnet-20240229",
    use_guardian=True,
    verification_level="STANDARD",
    request_mode="WARN"
)

# Get a completion
completion, metadata = llm.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko.",
    temperature=0.7
)
```

### Registration

```python
# Register a custom connector
class CustomConnector(IndalekoLLMBase):
    # Implementation...
    pass

LLMFactory.register_connector("custom", CustomConnector)

# Use the custom connector
connector = factory.create_connector(
    connector_type="custom",
    api_key="your-api-key"
)
```

## Common Data Models

### PromptVariable

```python
from query.utils.prompt_management.prompt_manager import PromptVariable

# Create a variable
variable = PromptVariable(
    name="query",
    value="Find all documents with tag 'important'",
    type="string"  # Optional
)
```

### PromptTemplate

```python
from query.utils.prompt_management.data_models.base import PromptTemplate

# Create a template
template = PromptTemplate(
    template_id="query_template",
    system_prompt="You are a helpful assistant that translates natural language to AQL.",
    user_prompt="Please translate this query: {query}",
    description="Template for query translation",
    version="1.0",
    author="User",
    variables=["query"],
    examples=[{"query": "Find all documents created last week"}],
    created_at=datetime.now(timezone.utc)
)
```

### PromptEvaluationResult

```python
from query.utils.prompt_management.prompt_manager import PromptEvaluationResult

# Create an evaluation result
result = PromptEvaluationResult(
    prompt="Your prompt text here",
    token_count=150,
    original_token_count=200,
    token_savings=50,
    stability_score=0.85,
    stability_details={
        "contradictions": 0,
        "ambiguities": 1
    },
    prompt_hash="abc123"
)
```

### VerificationResult

```python
from query.utils.prompt_management.guardian.prompt_guardian import VerificationResult

# Create a verification result
result = VerificationResult(
    allowed=True,
    action="proceed",
    score=0.85,
    reasons=[],
    warnings=["Potential ambiguity detected"],
    verification_time_ms=25,
    trust_contract_valid=True,
    has_injection_patterns=False,
    security_issues=[],
    ethical_issues=[],
    recommendation="No issues found. Prompt is safe to use."
)
```

## Error Handling

The prompt management system defines several exception types for different error scenarios:

```python
from query.utils.prompt_management.exceptions import (
    PromptValidationError,
    PromptTemplateNotFoundError,
    PromptSecurityViolationError,
    PromptOptimizationError,
    SchemaValidationError
)

try:
    # Attempt to create a prompt from a template
    prompt = prompt_manager.create_prompt(
        template_id="nonexistent_template",
        variables=[PromptVariable(name="query", value="Find documents")]
    )
except PromptTemplateNotFoundError as e:
    print(f"Template not found: {e}")
except PromptValidationError as e:
    print(f"Validation error: {e}")
except PromptSecurityViolationError as e:
    print(f"Security violation: {e}")
except PromptOptimizationError as e:
    print(f"Optimization error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Configuration

The prompt management system can be configured through code or configuration files:

### Code Configuration

```python
# Configure verification levels
from query.utils.prompt_management.guardian.prompt_guardian import SecurityPolicy

# Create a custom security policy
security_policy = SecurityPolicy(
    min_stability_score={
        "none": 0.0,
        "basic": 0.4,
        "standard": 0.6,
        "strict": 0.8,
        "paranoid": 0.9
    },
    trust_contract_required={
        "none": False,
        "basic": False,
        "standard": False,
        "strict": True,
        "paranoid": True
    },
    banned_patterns={
        "ignore all instructions",
        "ignore previous instructions",
        "disregard the above",
        "execute code without checking",
        # Add custom patterns
    }
)

# Use custom policy
guardian = PromptGuardian(security_policy=security_policy)
```

### File Configuration

The system also supports configuration through files. Create a `prompt-management-config.ini` file in your project's config directory:

```ini
[general]
default_verification_level = STANDARD
default_request_mode = WARN

[optimizations]
enabled = true
strategies = WHITESPACE,SCHEMA_SIMPLIFY,EXAMPLE_REDUCE
cache_ttl = 3600
cache_max_size = 1000

[security]
banned_patterns = ignore all instructions,ignore previous instructions,disregard the above
min_stability_score_standard = 0.6
min_stability_score_strict = 0.8
trust_contract_required_standard = false
trust_contract_required_strict = true

[logging]
log_level = INFO
log_requests = true
log_token_usage = true
```

Then load the configuration:

```python
from query.utils.prompt_management.config import load_config

config = load_config("/path/to/prompt-management-config.ini")

# Use config
guardian = LLMGuardian(
    default_verification_level=config.verification_level,
    default_request_mode=config.request_mode
)
```