# Prompt Management System Architecture

## Overview

The Prompt Management System (PMS) for Indaleko is an architectural layer designed to optimize, secure, and manage interactions with Large Language Models (LLMs). This document outlines the system's architecture, component relationships, data flows, and integration with the broader Indaleko ecosystem.

## Architectural Principles

The PMS architecture is guided by several key principles:

1. **Separation of Concerns**: Each component has a well-defined responsibility and minimal dependencies.
2. **Defense in Depth**: Multiple layers of validation and verification ensure prompt security.
3. **Efficiency First**: Optimization of prompts prioritizes token reduction without semantic loss.
4. **Flexibility**: Support for multiple LLM providers with a consistent interface.
5. **Observability**: Comprehensive metrics and logging for system transparency.
6. **The Ayni Principle**: Two-way validation between AI systems for mutual benefit.

## System Components

The system consists of the following primary components:

![Prompt Management System Architecture Diagram](figures/prompt-management-architecture.png)

### 1. Prompt Manager

**Responsibility**: Template processing, variable binding, prompt optimization

**Key Classes**:
- `PromptManager`: Main class for template management and prompt creation
- `PromptTemplate`: Data model for prompt templates
- `PromptVariable`: Data model for template variables
- `PromptEvaluationResult`: Results of prompt evaluation and optimization

**Database Collections**:
- `Prompt_Templates`: Stores registered prompt templates

### 2. Prompt Guardian

**Responsibility**: Security verification, ethical validation, trust contract enforcement

**Key Classes**:
- `PromptGuardian`: Main class for prompt verification
- `SecurityPolicy`: Configuration for security policies
- `VerificationLevel`: Enum for verification strictness levels
- `VerificationResult`: Results of prompt verification

**Database Collections**:
- `Prompt_Verification_Log`: Logs all verification activities

### 3. LLM Guardian

**Responsibility**: Coordination of all prompt management components, metrics tracking

**Key Classes**:
- `LLMGuardian`: Main coordinator class
- `LLMRequestMode`: Enum for request handling modes
- `LLMRequestLog`: Log entry for LLM requests
- `TokenUsageStats`: Token usage statistics

**Database Collections**:
- `LLM_Request_Log`: Logs all LLM requests
- `Token_Usage_Stats`: Stores token usage statistics

### 4. AyniGuard

**Responsibility**: Prompt stability evaluation, contradiction detection, caching

**Key Classes**:
- `AyniGuard`: Main class for stability evaluation
- `AyniResult`: Results of stability evaluation
- `ContradictionPattern`: Pattern for detecting contradictions
- `PatternCatalog`: Collection of contradiction patterns

**Database Collections**:
- `Prompt_Cache_Recent`: Recent prompt cache (hot tier)
- `Prompt_Cache_Archive`: Archived prompt cache (cold tier)
- `Prompt_Stability_Metrics`: Stability metrics for prompts

### 5. Schema Manager

**Responsibility**: Schema processing and optimization

**Key Classes**:
- `SchemaManager`: Main class for schema operations
- `SchemaOptimizationResult`: Results of schema optimization

### 6. LLM Connectors

**Responsibility**: Interface with various LLM providers

**Key Classes**:
- `OpenAIConnector`: Connector for OpenAI models
- `AnthropicConnector`: Connector for Anthropic's Claude models
- `GemmaConnector`: Connector for Gemma models
- `GoogleConnector`: Connector for Google's Gemini models
- `IndalekoLLMBase`: Base class for all connectors

### 7. LLM Factory

**Responsibility**: Creation and management of LLM connectors

**Key Classes**:
- `LLMFactory`: Factory for creating connectors
- `LLMInterface`: Interface for LLM interactions

## Component Interactions

### Initialization Flow

1. The system is initialized through the `LLMFactory`:
   ```
   LLM Factory
       ├── Creates LLMGuardian
       │       ├── Creates PromptManager
       │       ├── Creates PromptGuardian
       │       ├── Creates AyniGuard
       │       └── Creates SchemaManager
       └── Creates LLM Connector
   ```

2. The `LLMFactory` can create different types of LLM connectors as needed:
   ```
   LLM Factory
       ├── Creates OpenAIConnector
       ├── Creates AnthropicConnector
       ├── Creates GemmaConnector
       ├── Creates GoogleConnector
       └── etc.
   ```

### Prompt Creation and Verification Flow

1. A prompt is created using the `PromptManager`:
   ```
   PromptManager.create_prompt()
       ├── Retrieves template
       ├── Binds variables
       ├── Optimizes prompt
       │       ├── SchemaManager.optimize_schema()
       │       └── Applies optimization strategies
       └── Evaluates stability (optional)
               └── AyniGuard.evaluate()
   ```

2. The prompt is verified using the `PromptGuardian`:
   ```
   PromptGuardian.verify_prompt()
       ├── Checks for banned patterns
       ├── Verifies trust contract
       ├── Evaluates stability
       │       └── AyniGuard.evaluate()
       ├── Extracts security/ethical issues
       └── Logs verification
   ```

### LLM Request Flow

1. A request is processed by the `LLMGuardian`:
   ```
   LLMGuardian.get_completion_from_prompt()
       ├── Generates request ID
       ├── Optimizes prompt (optional)
       │       └── PromptManager._optimize_schema_objects()
       ├── Verifies prompt
       │       └── PromptGuardian.verify_prompt()
       ├── Checks verification result
       │       └── Blocks request if needed
       ├── Gets LLM connector
       │       └── LLMFactory.get_llm()
       ├── Sends request to LLM
       │       └── LLMConnector.get_completion()
       └── Logs request and token usage
   ```

2. Template-based requests follow a similar flow but start with template processing:
   ```
   LLMGuardian.get_completion_from_template()
       ├── Creates prompt from template
       │       └── PromptManager.create_prompt()
       └── [Continues as above]
   ```

## Data Flow

### Token Optimization Flow

1. **Input**: Raw prompt or template
2. **Processing**:
   - Whitespace normalization
   - Schema simplification via SchemaManager
   - Example reduction
   - Context windowing
3. **Output**: Optimized prompt with token metrics

### Security Verification Flow

1. **Input**: Prompt (raw or optimized)
2. **Processing**:
   - Pattern-based checks for security issues
   - Trust contract validation
   - Stability evaluation via AyniGuard
   - Policy enforcement based on verification level
3. **Output**: Verification result with recommendation

### Caching Flow

1. **Input**: Prompt hash and evaluation request
2. **Processing**:
   - Check hot tier cache (recent)
   - If miss, check cold tier cache (archive)
   - If miss, perform full evaluation
   - Update cache with result
3. **Output**: Cached or new evaluation result

## Database Schema

### Collections

1. **Prompt_Templates**
   - `_key`: Template ID
   - `system_prompt`: System prompt template
   - `user_prompt`: User prompt template
   - `description`: Template description
   - `version`: Template version
   - `author`: Template author
   - `variables`: List of variable names
   - `examples`: Example variable bindings
   - `created_at`: Creation timestamp
   - `updated_at`: Last update timestamp

2. **Prompt_Cache_Recent**
   - `_key`: Prompt hash
   - `prompt`: Prompt content
   - `evaluation`: Evaluation result
   - `created_at`: Creation timestamp
   - `accessed_at`: Last access timestamp
   - `access_count`: Number of accesses

3. **Prompt_Cache_Archive**
   - `_key`: Prompt hash
   - `prompt`: Prompt content
   - `evaluation`: Evaluation result
   - `created_at`: Creation timestamp
   - `archived_at`: Archival timestamp
   - `access_count`: Number of accesses

4. **Prompt_Stability_Metrics**
   - `_key`: Metric ID
   - `prompt_hash`: Prompt hash
   - `stability_score`: Overall stability score
   - `contradiction_score`: Contradiction score
   - `ambiguity_score`: Ambiguity score
   - `consistency_score`: Consistency score
   - `created_at`: Creation timestamp

5. **LLM_Request_Log**
   - `_key`: Request ID
   - `prompt_hash`: Prompt hash
   - `template_id`: Template ID (if used)
   - `user_id`: User ID
   - `provider`: LLM provider
   - `model`: Model name
   - `verification_level`: Verification level
   - `request_mode`: Request mode
   - `allowed`: Whether the prompt was allowed
   - `blocked`: Whether the request was blocked
   - `token_count`: Final token count
   - `original_token_count`: Original token count
   - `token_savings`: Token savings
   - `verification_time_ms`: Verification time in ms
   - `total_time_ms`: Total request time in ms
   - `stability_score`: Stability score
   - `timestamp`: Request timestamp

6. **Token_Usage_Stats**
   - `_key`: Stat ID
   - `user_id`: User ID
   - `provider`: LLM provider
   - `model`: Model name
   - `total_requests`: Total requests
   - `total_tokens`: Total tokens used
   - `total_original_tokens`: Total original tokens
   - `total_token_savings`: Total token savings
   - `avg_token_savings_percent`: Average savings percentage
   - `day`: Day (YYYY-MM-DD)
   - `timestamp`: Last update timestamp

7. **Prompt_Verification_Log**
   - `_key`: Log ID
   - `prompt_hash`: Prompt hash
   - `user_id`: User ID
   - `allowed`: Whether the prompt was allowed
   - `action`: Action taken
   - `score`: Stability score
   - `verification_level`: Verification level
   - `verification_time_ms`: Verification time in ms
   - `reasons`: Reasons for action
   - `warnings`: Warnings
   - `trust_contract_valid`: Trust contract validity
   - `has_injection_patterns`: Presence of injection patterns
   - `security_issue_count`: Number of security issues
   - `ethical_issue_count`: Number of ethical issues
   - `verification_timestamp`: Verification timestamp

## Integration with Indaleko

### Integration with Query Subsystem

The PMS integrates with the Indaleko query subsystem through the following interfaces:

1. **LLM Connectors**: The query system uses LLM connectors for:
   - Natural language parsing
   - Query translation
   - Result explanation

2. **LLMFactory**: The factory provides a unified interface for accessing different LLM providers.

### Integration with Database Subsystem

The PMS uses the Indaleko database subsystem for:

1. **Template Storage**: Storing and retrieving prompt templates
2. **Caching**: Two-tier caching system for evaluations
3. **Metrics**: Storing and analyzing token usage and verification metrics

### Integration with Authentication and Authorization

The PMS integrates with Indaleko's authentication system for:

1. **User-specific Policies**: Applying different security policies based on user roles
2. **Usage Tracking**: Tracking token usage by user
3. **Auditing**: Logging all LLM interactions for audit purposes

## Deployment Architecture

The PMS is designed to be deployed in various configurations:

### Standalone Mode

In standalone mode, all components run within the same process:

```
Application
  └── Prompt Management System
       ├── PromptManager
       ├── PromptGuardian
       ├── LLMGuardian
       ├── AyniGuard
       ├── SchemaManager
       └── LLM Connectors
```

### Distributed Mode

In distributed mode, components can be distributed across multiple services:

```
Frontend Service
  └── LLM Interface
       └── API Gateway

Prompt Management Service
  ├── PromptManager
  ├── PromptGuardian
  ├── LLMGuardian
  ├── AyniGuard
  └── SchemaManager

LLM Provider Services
  ├── OpenAI Service
  ├── Anthropic Service
  ├── Google Service
  └── Local Model Service
```

## Performance Considerations

The PMS is designed with performance in mind:

1. **Caching**: Two-tier caching reduces redundant evaluations
2. **Concurrent Processing**: Components operate concurrently where possible
3. **Lazy Loading**: Components are loaded on-demand
4. **Batch Processing**: Bulk operations for efficiency
5. **Streaming**: Support for streaming responses from LLMs

## Security Considerations

The PMS implements several security measures:

1. **Prompt Injection Protection**: Pattern-based detection of prompt injection attempts
2. **Rate Limiting**: Control over token usage
3. **Verification Levels**: Configurable verification strictness
4. **Trust Contracts**: Explicit agreements for sensitive operations
5. **Auditing**: Comprehensive logging of all operations

## Extensibility

The PMS is designed to be extensible:

1. **New LLM Providers**: Easy addition of new LLM providers through the connector interface
2. **Custom Policies**: Support for custom security policies
3. **Custom Optimizations**: Extensible optimization strategies
4. **Custom Patterns**: Support for custom contradiction patterns
5. **Event Hooks**: Support for custom event handlers

## Future Architecture Directions

1. **Multi-LLM Verification**: Using multiple LLMs for verification
2. **Federated Evaluation**: Distributed evaluation of prompts
3. **Dynamic Security Policies**: Context-aware security policies
4. **Advanced Caching Strategies**: Predictive caching based on usage patterns
5. **Cross-Model Optimization**: Model-specific optimizations

## References

1. [Prompt Management System Component Documentation](/doc/PromptManagementSystem.md)
2. [Prompt Management System API Documentation](/doc/PromptManagementAPI.md)
3. [Prompt Management System Design](/PROMPT_MANAGEMENT_DESIGN_UPDATED.md)
4. [LLM Integration Summary](/LLM_INTEGRATION_SUMMARY.md)