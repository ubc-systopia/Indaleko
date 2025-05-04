# Prompt Management System Usage Examples and Tutorials

This document provides practical examples and tutorials for using the Indaleko Prompt Management System. These examples demonstrate common usage patterns and best practices.

## Table of Contents

1. [Basic Usage Examples](#basic-usage-examples)
2. [Template Management Examples](#template-management-examples)
3. [Security Verification Examples](#security-verification-examples)
4. [LLM Connector Examples](#llm-connector-examples)
5. [Token Optimization Examples](#token-optimization-examples)
6. [Usage Tracking Examples](#usage-tracking-examples)
7. [Integration Tutorials](#integration-tutorials)
8. [Advanced Usage Patterns](#advanced-usage-patterns)
9. [Troubleshooting](#troubleshooting)
10. [Migration Guide](#migration-guide)

## Basic Usage Examples

### Getting Started with the LLM Factory

The simplest way to use the prompt management system is through the LLM Factory:

```python
from query.utils.llm_connector.factory_updated import LLMFactory

# Create factory
factory = LLMFactory()

# Get an LLM interface
llm = factory.get_llm(
    provider="openai",  # or "anthropic", "gemma", "google", etc.
    model="gpt-4o",
    use_guardian=True,  # Enable prompt management
    verification_level="STANDARD",
    request_mode="WARN"
)

# Get a completion
completion, metadata = llm.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko.",
    temperature=0.7
)

# Print the completion and metadata
print(completion)
print(f"Token count: {metadata['token_metrics']['token_count']}")
print(f"Token savings: {metadata['token_metrics']['token_savings']}")
print(f"Verification passed: {metadata['verification']['allowed']}")
```

### Basic Prompt Creation and Verification

If you need more control, you can use the prompt management components directly:

```python
from query.utils.prompt_management.prompt_manager import PromptManager
from query.utils.prompt_management.guardian.prompt_guardian import PromptGuardian, VerificationLevel

# Create components
prompt_manager = PromptManager()
prompt_guardian = PromptGuardian()

# Create a prompt
prompt = {
    "system": "You are a helpful assistant.",
    "user": "Tell me about Indaleko."
}

# Optimize the prompt
optimized_result = prompt_manager.optimize_prompt(prompt)
optimized_prompt = optimized_result.prompt

# Verify the prompt
verification = prompt_guardian.verify_prompt(
    prompt=optimized_prompt,
    level=VerificationLevel.STANDARD
)

# Check verification result
if verification.allowed:
    print("Prompt is allowed!")
    print(f"Score: {verification.score}")
else:
    print(f"Prompt not allowed: {verification.reasons}")
    print(f"Recommendation: {verification.recommendation}")
```

## Template Management Examples

### Creating and Using a Prompt Template

Templates make it easy to create consistent prompts with variable substitution:

```python
from query.utils.prompt_management.prompt_manager import PromptManager, PromptVariable

# Create prompt manager
prompt_manager = PromptManager()

# Register a template
template_id = prompt_manager.register_template(
    template_id="query_template",
    system_prompt=(
        "You are a helpful assistant that translates natural language queries to AQL. "
        "Focus on translating precisely without adding explanations."
    ),
    user_prompt=(
        "Please translate the following query to AQL:"
        "\n\nQuery: {query}"
        "\n\nTranslation:"
    ),
    description="Template for translating natural language to AQL",
    variables=["query"],
    examples=[
        {"query": "Find all documents created last week"},
        {"query": "Show me documents with tag 'important'"}
    ]
)

# Create a prompt from the template
prompt = prompt_manager.create_prompt(
    template_id="query_template",
    variables=[
        PromptVariable(name="query", value="Find documents modified by John in the last month")
    ],
    optimize=True  # Apply optimization
)

# Print the result
print("System prompt:")
print(prompt.system)
print("\nUser prompt:")
print(prompt.user)
print(f"\nToken count: {prompt.token_count}")
print(f"Original token count: {prompt.original_token_count}")
print(f"Token savings: {prompt.token_savings}")
```

### Managing Templates in the Database

Templates can be stored, retrieved, and updated from the database:

```python
from query.utils.prompt_management.prompt_manager import PromptManager

# Create prompt manager with database connection
from db.collection import IndalekoCollection
db = IndalekoCollection.get_db()
prompt_manager = PromptManager(db_instance=db)

# List all templates
templates = prompt_manager.list_templates()
print(f"Found {len(templates)} templates:")
for template in templates:
    print(f"- {template.template_id}: {template.description}")

# Update a template
prompt_manager.update_template(
    template_id="query_template",
    system_prompt=(
        "You are an expert at translating natural language queries to AQL. "
        "Your translations are precise, efficient, and optimize for performance."
    )
)

# Delete a template
prompt_manager.delete_template(template_id="outdated_template")
```

## Security Verification Examples

### Using Different Verification Levels

Adjust verification strictness based on your needs:

```python
from query.utils.prompt_management.guardian.prompt_guardian import PromptGuardian, VerificationLevel

# Create a guardian
guardian = PromptGuardian()

# Prepare a prompt
prompt = {
    "system": "You are a helpful assistant.",
    "user": "Help me understand how to query the database."
}

# Try different verification levels
for level in [
    VerificationLevel.NONE,
    VerificationLevel.BASIC,
    VerificationLevel.STANDARD,
    VerificationLevel.STRICT,
    VerificationLevel.PARANOID
]:
    result = guardian.verify_prompt(prompt=prompt, level=level)
    print(f"{level.name} verification: {'PASSED' if result.allowed else 'FAILED'}")
    print(f"Score: {result.score}")
    print(f"Warnings: {result.warnings}")
    print()
```

### Adding Trust Contracts to Prompts

Trust contracts enhance security for sensitive operations:

```python
from query.utils.prompt_management.guardian.prompt_guardian import PromptGuardian, VerificationLevel

# Create a guardian
guardian = PromptGuardian()

# Create a prompt without trust contract
unsafe_prompt = {
    "system": "You are a helpful assistant.",
    "user": "Help me generate a script to process sensitive data."
}

# Create a prompt with trust contract
safe_prompt = {
    "system": "You are a helpful assistant.",
    "user": "Help me generate a script to process sensitive data.",
    "trust_contract": {
        "mutual_intent": (
            "We agree that any script generated will include proper data "
            "validation, error handling, and security checks. No sensitive "
            "data will be exposed or transmitted without encryption."
        ),
        "user_commitments": [
            "I will review all generated code before execution",
            "I will not use this for processing PII without proper safeguards",
            "I will comply with all applicable data protection regulations"
        ]
    }
}

# Verify both prompts with strict level
unsafe_result = guardian.verify_prompt(prompt=unsafe_prompt, level=VerificationLevel.STRICT)
safe_result = guardian.verify_prompt(prompt=safe_prompt, level=VerificationLevel.STRICT)

print(f"Without trust contract - Allowed: {unsafe_result.allowed}")
print(f"With trust contract - Allowed: {safe_result.allowed}")
```

## LLM Connector Examples

### Using Different LLM Providers

The system supports multiple LLM providers with a consistent interface:

```python
from query.utils.llm_connector.factory_updated import LLMFactory

# Create factory
factory = LLMFactory()

# List available connectors
connectors = factory.get_available_connectors()
print(f"Available connectors: {connectors}")

providers = ["openai", "anthropic", "gemma", "google"]
prompt = {
    "system": "You are a helpful assistant.",
    "user": "Summarize the Indaleko prompt management system in one sentence."
}

# Try different providers
for provider in providers:
    try:
        # Create connector
        connector = factory.create_connector(
            connector_type=provider,
            use_guardian=True
        )

        # Generate query
        response = connector.generate_query(prompt)

        print(f"\n{provider.capitalize()} response:")
        print(response.translated_query)
    except Exception as e:
        print(f"\n{provider.capitalize()} error: {e}")
```

### Advanced Completion Options

Customize completion behavior with additional options:

```python
from query.utils.llm_connector.factory_updated import LLMFactory

# Create factory and get LLM
factory = LLMFactory()
llm = factory.get_llm(provider="openai", model="gpt-4o")

# Basic completion
basic_completion, _ = llm.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko.",
)

# Completion with temperature
creative_completion, _ = llm.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko.",
    temperature=0.9,  # Higher temperature for more creativity
)

# Completion with token limit
short_completion, _ = llm.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko.",
    max_tokens=50,  # Limit response length
)

print("Basic completion:")
print(basic_completion[:100] + "...\n")

print("Creative completion:")
print(creative_completion[:100] + "...\n")

print("Short completion:")
print(short_completion)
```

## Token Optimization Examples

### Comparing Optimization Strategies

See the effect of different optimization strategies:

```python
from query.utils.prompt_management.prompt_manager import PromptManager, PromptOptimizationStrategy

# Create prompt manager
prompt_manager = PromptManager()

# Create a test prompt with a schema
prompt = {
    "system": "You are a helpful assistant.",
    "user": """
    Please provide information according to this schema:

    {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "The name of the entity"
            },
            "details": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "A detailed description of the entity"
                    },
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "string"
                        },
                        "description": "List of entity attributes"
                    }
                }
            }
        }
    }

    Tell me about Indaleko.
    """
}

# Test different optimization strategies
strategies = [
    [],  # No optimization
    [PromptOptimizationStrategy.WHITESPACE],
    [PromptOptimizationStrategy.SCHEMA_SIMPLIFY],
    [PromptOptimizationStrategy.WHITESPACE, PromptOptimizationStrategy.SCHEMA_SIMPLIFY],
]

for strat in strategies:
    result = prompt_manager.optimize_prompt(prompt, strategies=strat)

    strategy_names = [s.name for s in strat] if strat else ["NONE"]
    print(f"\nOptimization strategies: {', '.join(strategy_names)}")
    print(f"Original tokens: {result.original_token_count}")
    print(f"Optimized tokens: {result.token_count}")
    print(f"Token savings: {result.token_savings} ({result.token_savings / result.original_token_count * 100:.2f}%)")

    if len(strat) == 1 and strat[0] == PromptOptimizationStrategy.SCHEMA_SIMPLIFY:
        print("\nOptimized schema:")
        import re
        schema_match = re.search(r'\{.*\}', result.prompt["user"], re.DOTALL)
        if schema_match:
            print(schema_match.group(0))
```

### Creating Custom Optimization Strategies

Extend the system with your own optimization strategies:

```python
from query.utils.prompt_management.prompt_manager import PromptManager, PromptOptimizationStrategy
from enum import Enum, auto

# Define a custom strategy
class CustomOptimizationStrategy(Enum):
    ACRONYM_EXPANSION = auto()

# Extend the prompt manager with a custom optimization function
class CustomPromptManager(PromptManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Register custom optimization functions
        self._optimization_functions[CustomOptimizationStrategy.ACRONYM_EXPANSION] = self._expand_acronyms

    def _expand_acronyms(self, prompt):
        """Replace common acronyms with their full forms."""
        acronyms = {
            "LLM": "Large Language Model",
            "NLP": "Natural Language Processing",
            "ML": "Machine Learning",
            "AI": "Artificial Intelligence",
            "PMS": "Prompt Management System"
        }

        for section in ["system", "user"]:
            if section in prompt and isinstance(prompt[section], str):
                text = prompt[section]

                # Replace acronyms
                for acronym, full_form in acronyms.items():
                    text = text.replace(f" {acronym} ", f" {full_form} ({acronym}) ")

                prompt[section] = text

        return prompt

# Use the custom prompt manager
custom_manager = CustomPromptManager()

# Test with a prompt containing acronyms
prompt = {
    "system": "You are a helpful AI assistant.",
    "user": "Explain how LLM and NLP are used in the PMS for ML tasks."
}

# Apply custom optimization
result = custom_manager.optimize_prompt(
    prompt,
    strategies=[CustomOptimizationStrategy.ACRONYM_EXPANSION]
)

print("Original prompt user section:")
print(prompt["user"])
print("\nOptimized prompt user section:")
print(result.prompt["user"])
```

## Usage Tracking Examples

### Tracking Token Usage

Monitor token usage to optimize costs:

```python
from query.utils.prompt_management.guardian.llm_guardian import LLMGuardian
from datetime import datetime, timedelta

# Create guardian
guardian = LLMGuardian()

# Get token usage for the last 30 days
end_date = datetime.now().date().isoformat()
start_date = (datetime.now() - timedelta(days=30)).date().isoformat()

# Get overall statistics
stats = guardian.get_token_usage_stats(
    start_date=start_date,
    end_date=end_date
)

print("Token Usage Statistics (Last 30 Days):")
print(f"Total requests: {stats['total_requests']}")
print(f"Total tokens: {stats['total_tokens']}")
print(f"Original tokens (without optimization): {stats['total_original_tokens']}")
print(f"Token savings: {stats['total_token_savings']}")
print(f"Average tokens per request: {stats['average_tokens_per_request']:.2f}")
print(f"Savings percentage: {stats['savings_percent']:.2f}%")

# Get usage by provider
provider_stats = guardian.get_token_usage_by_provider(
    start_date=start_date,
    end_date=end_date
)

print("\nToken Usage by Provider:")
for provider in provider_stats:
    print(f"{provider['provider']}: {provider['total_tokens']} tokens ({provider['total_requests']} requests)")

# Get daily usage for trend analysis
daily_stats = guardian.get_token_usage_by_day(
    start_date=start_date,
    end_date=end_date,
    provider="openai"  # Filter by provider
)

print("\nDaily Token Usage (OpenAI):")
for day in daily_stats[-7:]:  # Show last 7 days
    print(f"{day['day']}: {day['total_tokens']} tokens ({day['total_requests']} requests)")
```

### Analyzing Verification Results

Track verification performance and issues:

```python
from query.utils.prompt_management.guardian.prompt_guardian import PromptGuardian
from datetime import datetime, timedelta

# Create guardian
guardian = PromptGuardian()

# Get verification metrics for the last 30 days
end_time = datetime.now()
start_time = end_time - timedelta(days=30)

# Get overall metrics
metrics = guardian.get_verification_metrics(
    start_time=start_time,
    end_time=end_time
)

print("Verification Metrics (Last 30 Days):")
print(f"Total verifications: {metrics['total_verifications']}")
print(f"Allowed: {metrics['allowed_count']} ({metrics['allowed_percent']:.2f}%)")
print(f"Blocked: {metrics['blocked_count']}")
print(f"Average stability score: {metrics['avg_stability_score']:.2f}")
print(f"Security issues: {metrics['security_issue_count']}")
print(f"Ethical issues: {metrics['ethical_issue_count']}")
print(f"Injection pattern detections: {metrics['injection_pattern_count']}")

# Get recent verification logs
logs = guardian.get_verification_logs(
    start_time=start_time,
    end_time=end_time,
    limit=10  # Show 10 most recent logs
)

print("\nRecent Verification Logs:")
for log in logs:
    status = "ALLOWED" if log["allowed"] else "BLOCKED"
    reason = f": {log['reasons'][0]}" if log["reasons"] else ""
    print(f"{log['verification_timestamp']} - {status}{reason}")
```

## Integration Tutorials

### Integrating with a Web Application

Here's an example of integrating the PMS with a Flask web application:

```python
from flask import Flask, request, jsonify
from query.utils.llm_connector.factory_updated import LLMFactory

app = Flask(__name__)

# Create LLM factory
factory = LLMFactory()

@app.route('/api/chat', methods=['POST'])
def chat_endpoint():
    # Get request data
    data = request.json

    # Validate request
    if not data or 'message' not in data:
        return jsonify({'error': 'Invalid request. Message is required.'}), 400

    # Extract parameters
    message = data['message']
    provider = data.get('provider', 'openai')
    model = data.get('model')
    system_prompt = data.get('system_prompt', "You are a helpful assistant.")

    try:
        # Get LLM interface
        llm = factory.get_llm(
            provider=provider,
            model=model,
            use_guardian=True,
            verification_level="STANDARD",
            request_mode="WARN"
        )

        # Get completion
        completion, metadata = llm.get_completion(
            system_prompt=system_prompt,
            user_prompt=message
        )

        # Prepare response
        response = {
            'completion': completion,
            'metadata': {
                'provider': metadata['provider'],
                'model': metadata['model'],
                'token_count': metadata.get('token_metrics', {}).get('token_count'),
                'token_savings': metadata.get('token_metrics', {}).get('token_savings'),
                'verification': {
                    'allowed': metadata.get('verification', {}).get('allowed', True),
                    'warnings': metadata.get('verification', {}).get('warnings', [])
                }
            }
        }

        return jsonify(response)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
```

### Integrating with Command Line Tools

Here's an example of integrating with a CLI application:

```python
import argparse
import sys
from query.utils.llm_connector.factory_updated import LLMFactory

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Indaleko PMS CLI')
    parser.add_argument('--provider', default='openai', help='LLM provider (default: openai)')
    parser.add_argument('--model', help='Model name (optional)')
    parser.add_argument('--system', default='You are a helpful assistant.', help='System prompt')
    parser.add_argument('--level', default='STANDARD', help='Verification level')
    parser.add_argument('--mode', default='WARN', help='Request mode')
    parser.add_argument('--no-guardian', action='store_true', help='Disable guardian')
    parser.add_argument('prompt', help='User prompt')

    args = parser.parse_args()

    try:
        # Create LLM factory
        factory = LLMFactory()

        # Get LLM interface
        llm = factory.get_llm(
            provider=args.provider,
            model=args.model,
            use_guardian=not args.no_guardian,
            verification_level=args.level,
            request_mode=args.mode
        )

        # Get completion
        completion, metadata = llm.get_completion(
            system_prompt=args.system,
            user_prompt=args.prompt
        )

        # Print completion
        print(completion)

        # Print metadata if verbose
        if '--verbose' in sys.argv:
            print("\nMetadata:")
            print(f"Provider: {metadata['provider']}")
            print(f"Model: {metadata['model']}")
            if 'token_metrics' in metadata:
                print(f"Token count: {metadata['token_metrics']['token_count']}")
                print(f"Token savings: {metadata['token_metrics']['token_savings']}")
            if 'verification' in metadata:
                allowed = metadata['verification']['allowed']
                status = 'PASSED' if allowed else 'FAILED'
                print(f"Verification: {status}")
                if not allowed or metadata['verification'].get('warnings'):
                    print(f"Warnings: {metadata['verification'].get('warnings', [])}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
```

## Advanced Usage Patterns

### Implementing A/B Testing for Prompts

Test different prompt strategies to find the most effective:

```python
import random
import statistics
import time
from query.utils.prompt_management.prompt_manager import PromptManager, PromptVariable
from query.utils.llm_connector.factory_updated import LLMFactory

class PromptTester:
    def __init__(self, factory=None):
        self.prompt_manager = PromptManager()
        self.factory = factory or LLMFactory()

    def test_variants(self, template_variants, test_cases, provider="openai", trials=5):
        """Test different prompt templates and measure performance."""
        results = []

        # Register template variants
        variant_ids = []
        for i, variant in enumerate(template_variants):
            variant_id = f"test_variant_{i}"
            self.prompt_manager.register_template(
                template_id=variant_id,
                system_prompt=variant["system_prompt"],
                user_prompt=variant["user_prompt"],
                description=f"Test variant {i}"
            )
            variant_ids.append(variant_id)

        # Get LLM interface
        llm = self.factory.get_llm(provider=provider, use_guardian=True)

        # Run trials
        for variant_id in variant_ids:
            variant_results = []

            for test_case in test_cases:
                case_tokens = []
                case_times = []

                for _ in range(trials):
                    # Create prompt from template
                    prompt_result = self.prompt_manager.create_prompt(
                        template_id=variant_id,
                        variables=[PromptVariable(name=k, value=v) for k, v in test_case["variables"].items()],
                        optimize=True
                    )

                    # Get completion
                    start_time = time.time()
                    _, metadata = llm.get_completion(
                        system_prompt=prompt_result.system,
                        user_prompt=prompt_result.user
                    )
                    elapsed_time = time.time() - start_time

                    # Record metrics
                    token_count = metadata.get("token_metrics", {}).get("token_count", 0)
                    case_tokens.append(token_count)
                    case_times.append(elapsed_time)

                # Calculate averages
                variant_results.append({
                    "test_case": test_case["name"],
                    "avg_tokens": statistics.mean(case_tokens) if case_tokens else 0,
                    "avg_time": statistics.mean(case_times) if case_times else 0
                })

            # Calculate overall metrics
            avg_tokens = statistics.mean([r["avg_tokens"] for r in variant_results])
            avg_time = statistics.mean([r["avg_time"] for r in variant_results])

            results.append({
                "variant_id": variant_id,
                "avg_tokens": avg_tokens,
                "avg_time": avg_time,
                "case_results": variant_results
            })

        return results

# Example usage
tester = PromptTester()

# Define template variants
variants = [
    {
        "system_prompt": "You are a helpful assistant that translates natural language to AQL.",
        "user_prompt": "Please translate this query: {query}"
    },
    {
        "system_prompt": "You are an AQL expert. Be concise and focus only on translating.",
        "user_prompt": "Translate to AQL: {query}"
    }
]

# Define test cases
test_cases = [
    {
        "name": "Simple Query",
        "variables": {"query": "Find all documents from last week"}
    },
    {
        "name": "Complex Query",
        "variables": {"query": "Find documents created by John with tag 'important' modified in the last month"}
    }
]

# Run test
results = tester.test_variants(variants, test_cases, trials=3)

# Print results
for i, result in enumerate(results):
    print(f"\nVariant {i}:")
    print(f"Average tokens: {result['avg_tokens']:.2f}")
    print(f"Average time: {result['avg_time']:.2f} seconds")

    print("\nTest case results:")
    for case in result["case_results"]:
        print(f"- {case['test_case']}: {case['avg_tokens']:.2f} tokens, {case['avg_time']:.2f} seconds")

# Determine winner
best_variant = min(range(len(results)), key=lambda i: results[i]["avg_tokens"])
print(f"\nBest variant: {best_variant} (lowest token usage)")
```

### Implementing Custom Caching

Implement a custom caching strategy for repeated prompts:

```python
import json
import hashlib
import time
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from query.utils.llm_connector.factory_updated import LLMFactory

@dataclass
class CacheEntry:
    completion: str
    metadata: Dict[str, Any]
    timestamp: float
    ttl: int  # TTL in seconds

class CachingLLMClient:
    def __init__(self, max_cache_size=1000, default_ttl=3600):
        self.factory = LLMFactory()
        self.cache = {}  # prompt_hash -> CacheEntry
        self.max_cache_size = max_cache_size
        self.default_ttl = default_ttl
        self.hits = 0
        self.misses = 0

    def _hash_prompt(self, system_prompt, user_prompt):
        """Generate a stable hash for a prompt."""
        prompt_str = json.dumps({"system": system_prompt, "user": user_prompt}, sort_keys=True)
        return hashlib.sha256(prompt_str.encode()).hexdigest()

    def _clean_cache(self):
        """Remove expired cache entries."""
        now = time.time()
        expired = [k for k, v in self.cache.items() if now - v.timestamp > v.ttl]
        for key in expired:
            del self.cache[key]

        # If still too large, remove oldest entries
        if len(self.cache) > self.max_cache_size:
            sorted_keys = sorted(self.cache.keys(), key=lambda k: self.cache[k].timestamp)
            for key in sorted_keys[:len(self.cache) - self.max_cache_size]:
                del self.cache[key]

    def get_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        provider: str = "openai",
        model: Optional[str] = None,
        use_cache: bool = True,
        ttl: Optional[int] = None,
        **kwargs
    ) -> Tuple[str, Dict[str, Any]]:
        """Get a completion with caching."""
        # Generate cache key
        prompt_hash = self._hash_prompt(system_prompt, user_prompt)

        # Check cache if enabled
        if use_cache and prompt_hash in self.cache:
            entry = self.cache[prompt_hash]

            # Check if entry is still valid
            if time.time() - entry.timestamp <= entry.ttl:
                self.hits += 1

                # Return cached result with cache hit metadata
                metadata = entry.metadata.copy()
                metadata["cache"] = {
                    "hit": True,
                    "saved_time_ms": metadata.get("total_time_ms", 0),
                    "age_seconds": int(time.time() - entry.timestamp)
                }

                return entry.completion, metadata

        # Cache miss - get from LLM
        self.misses += 1

        # Get LLM interface
        llm = self.factory.get_llm(
            provider=provider,
            model=model,
            **kwargs
        )

        # Get completion
        completion, metadata = llm.get_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt
        )

        # Cache the result if caching is enabled
        if use_cache:
            self.cache[prompt_hash] = CacheEntry(
                completion=completion,
                metadata=metadata.copy(),
                timestamp=time.time(),
                ttl=ttl or self.default_ttl
            )

            # Add cache miss info to metadata
            metadata["cache"] = {
                "hit": False,
                "stored": True
            }

            # Clean cache if needed
            self._clean_cache()

        return completion, metadata

    def get_cache_stats(self):
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = (self.hits / total_requests) * 100 if total_requests > 0 else 0

        return {
            "cache_size": len(self.cache),
            "max_cache_size": self.max_cache_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate,
            "total_requests": total_requests
        }

    def clear_cache(self):
        """Clear the cache."""
        self.cache = {}

# Example usage
client = CachingLLMClient()

# First request (cache miss)
start_time = time.time()
completion1, metadata1 = client.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko.",
    provider="openai"
)
time1 = time.time() - start_time

# Second request (cache hit)
start_time = time.time()
completion2, metadata2 = client.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko.",
    provider="openai"
)
time2 = time.time() - start_time

# Print results
print(f"First request (cache miss) time: {time1:.2f} seconds")
print(f"Second request (cache hit) time: {time2:.2f} seconds")
print(f"Time saved: {time1 - time2:.2f} seconds")
print(f"Cache hit rate: {client.get_cache_stats()['hit_rate']:.2f}%")
```

## Troubleshooting

### Common Issues and Solutions

Here are solutions to common issues you might encounter:

#### 1. Verification Blocking Legitimate Prompts

**Problem**: The verification system is blocking legitimate prompts.

**Solution**: Adjust the verification level or switch to WARN mode:

```python
from query.utils.llm_connector.factory_updated import LLMFactory
from query.utils.prompt_management.guardian.llm_guardian import VerificationLevel, LLMRequestMode

# Create factory with less strict verification
factory = LLMFactory()
llm = factory.get_llm(
    provider="openai",
    verification_level="BASIC",  # Less strict
    request_mode="WARN"  # Warn instead of block
)
```

#### 2. Token Optimization Breaking Prompts

**Problem**: Token optimization is affecting prompt semantics.

**Solution**: Disable specific optimization strategies or disable optimization entirely:

```python
from query.utils.prompt_management.prompt_manager import PromptManager, PromptOptimizationStrategy

# Create prompt manager with limited optimization
prompt_manager = PromptManager()

# Only use whitespace normalization, skip schema simplification
result = prompt_manager.optimize_prompt(
    prompt=your_prompt,
    strategies=[PromptOptimizationStrategy.WHITESPACE]
)

# Or disable optimization in LLMGuardian
guardian.get_completion_from_prompt(
    prompt=your_prompt,
    provider="openai",
    optimize=False  # Disable optimization
)
```

#### 3. Database Connection Issues

**Problem**: Database collections not found or permission errors.

**Solution**: Ensure collections exist and check connection:

```python
from db.collection import IndalekoCollection
from db.db_collections import IndalekoDBCollections

# Check database connection
db = IndalekoCollection.get_db()

# Ensure collections exist
collections = [
    IndalekoDBCollections.Indaleko_Prompt_Templates_Collection,
    IndalekoDBCollections.Indaleko_Prompt_Cache_Recent_Collection,
    IndalekoDBCollections.Indaleko_Prompt_Cache_Archive_Collection,
    IndalekoDBCollections.Indaleko_LLM_Request_Log_Collection,
    IndalekoDBCollections.Indaleko_Token_Usage_Stats_Collection,
    IndalekoDBCollections.Indaleko_Prompt_Verification_Log_Collection
]

for collection_name in collections:
    try:
        db.get_collection(collection_name)
        print(f"Collection {collection_name} exists")
    except Exception as e:
        print(f"Error with collection {collection_name}: {e}")
```

#### 4. API Key Issues

**Problem**: API key errors when connecting to LLM providers.

**Solution**: Check API key configuration and environment variables:

```python
import os

# Check environment variables
for provider in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]:
    if provider in os.environ:
        print(f"{provider} is set")
    else:
        print(f"{provider} is NOT set")

# Set API key directly
from query.utils.llm_connector.factory_updated import LLMFactory
factory = LLMFactory()
connector = factory.create_connector(
    connector_type="openai",
    api_key="your-api-key-here"  # Provide key directly
)
```

#### 5. Incompatible Model Configurations

**Problem**: Some models don't work with certain prompt formats.

**Solution**: Use model-specific configurations:

```python
from query.utils.llm_connector.factory_updated import LLMFactory

# Create factory with model-specific handlers
factory = LLMFactory()

# For OpenAI models
openai_llm = factory.get_llm(
    provider="openai",
    model="gpt-4o",
    use_guardian=True
)

# For Anthropic models (using proper formatting)
anthropic_llm = factory.get_llm(
    provider="anthropic",
    model="claude-3-opus-20240229",
    use_guardian=True,
    format_for_model=True  # Enable model-specific formatting
)

# For Google models
google_llm = factory.get_llm(
    provider="google",
    model="gemini-1.0-pro",
    use_guardian=True
)
```

## Migration Guide

### Migrating from Direct LLM Usage

If you're currently using LLM connectors directly, here's how to migrate to the prompt management system:

#### Before:

```python
from query.utils.llm_connector.openai_connector import OpenAIConnector

# Create connector
connector = OpenAIConnector(
    api_key="your-api-key",
    model="gpt-4"
)

# Generate query
response = connector.generate_query(
    prompt={
        "system": "You are a helpful assistant.",
        "user": "Translate 'find documents from last week' to AQL."
    }
)
```

#### After:

```python
from query.utils.llm_connector.factory_updated import LLMFactory

# Create factory
factory = LLMFactory()

# Get connector with prompt management
connector = factory.create_connector(
    connector_type="openai",
    model="gpt-4",
    use_guardian=True,
    verification_level="STANDARD",
    request_mode="WARN"
)

# Generate query (same API)
response = connector.generate_query(
    prompt={
        "system": "You are a helpful assistant.",
        "user": "Translate 'find documents from last week' to AQL."
    }
)
```

### Migrating to Template-Based Prompts

If you're using hardcoded prompts, here's how to migrate to template-based prompts:

#### Before:

```python
# Hardcoded prompt
system_prompt = "You are a helpful assistant that translates natural language to AQL."
user_prompt = f"Please translate this query: {query}"

# Get completion
completion, _ = llm.get_completion(
    system_prompt=system_prompt,
    user_prompt=user_prompt
)
```

#### After:

```python
from query.utils.prompt_management.prompt_manager import PromptManager, PromptVariable
from query.utils.llm_connector.factory_updated import LLMFactory

# Create prompt manager
prompt_manager = PromptManager()

# Register template (do this once)
prompt_manager.register_template(
    template_id="query_template",
    system_prompt="You are a helpful assistant that translates natural language to AQL.",
    user_prompt="Please translate this query: {query}",
    description="Template for translating queries to AQL"
)

# Create factory
factory = LLMFactory()
llm = factory.get_llm(provider="openai", use_guardian=True)

# Use template
completion, _ = llm.guardian.get_completion_from_template(
    template_id="query_template",
    variables=[PromptVariable(name="query", value=query)],
    provider="openai"
)
```

### Migrating from Legacy Caching

If you're using a custom caching solution, migrate to the built-in two-tier caching:

#### Before:

```python
# Custom cache implementation
cached_results = {}

def get_cached_response(prompt, provider, model):
    cache_key = f"{provider}:{model}:{hash(prompt)}"
    if cache_key in cached_results:
        return cached_results[cache_key]
    return None

def store_in_cache(prompt, provider, model, response):
    cache_key = f"{provider}:{model}:{hash(prompt)}"
    cached_results[cache_key] = response
```

#### After:

```python
from query.utils.llm_connector.factory_updated import LLMFactory
from query.utils.prompt_management.guardian.llm_guardian import LLMGuardian

# Create guardian with caching enabled
guardian = LLMGuardian(
    use_cache=True,  # Enable caching
    cache_ttl=3600,  # 1 hour TTL for hot tier
    archive_ttl=86400 * 7  # 7 days TTL for cold tier
)

# Create factory
factory = LLMFactory()

# Get LLM with caching
llm = factory.get_llm(
    provider="openai",
    use_guardian=True,
    guardian_instance=guardian
)

# Get completion (caching handled automatically)
completion, metadata = llm.get_completion(
    system_prompt="You are a helpful assistant.",
    user_prompt="Tell me about Indaleko."
)

# Check if result came from cache
if metadata.get("cache_hit", False):
    print("Result retrieved from cache")
```

## Best Practices and Performance Tips

To get the most out of the Prompt Management System, follow these best practices:

### Use Templates for Consistency

Always use templates for prompts that will be used repeatedly:

```python
# Register templates during app initialization
prompt_manager.register_template(
    template_id="aql_translation",
    system_prompt="You are an AQL expert. Be concise.",
    user_prompt="Translate to AQL: {query}",
    description="Template for AQL translation"
)

# Register templates with examples for better results
prompt_manager.register_template(
    template_id="entity_extraction",
    system_prompt="Extract entities from the text.",
    user_prompt="Extract entities from: {text}",
    description="Template for entity extraction",
    examples=[
        {"text": "John sent an email to Sarah yesterday",
         "output": '{"entities": ["John", "Sarah"], "types": ["person", "person"]}'}
    ]
)
```

### Configure Verification Levels Appropriately

Match verification levels to security requirements:

```python
# For internal tooling with trusted users
factory.get_llm(verification_level="BASIC", request_mode="WARN")

# For customer-facing applications
factory.get_llm(verification_level="STANDARD", request_mode="SAFE")

# For sensitive data processing
factory.get_llm(verification_level="STRICT", request_mode="SAFE")

# For high-security environments
factory.get_llm(verification_level="PARANOID", request_mode="SAFE")
```

### Balance Token Optimization

Consider the trade-offs of different optimization strategies:

```python
# For maximum token savings
prompt_manager.optimize_prompt(
    prompt=prompt,
    strategies=[
        PromptOptimizationStrategy.WHITESPACE,
        PromptOptimizationStrategy.SCHEMA_SIMPLIFY,
        PromptOptimizationStrategy.EXAMPLE_REDUCTION
    ]
)

# For preserving semantics while reducing tokens
prompt_manager.optimize_prompt(
    prompt=prompt,
    strategies=[PromptOptimizationStrategy.WHITESPACE]
)

# For model-specific optimization
prompt_manager.optimize_prompt(
    prompt=prompt,
    strategies=[PromptOptimizationStrategy.WHITESPACE],
    model="gpt-4o"
)
```

### Monitor and Analyze Usage

Regularly review token usage and optimization metrics:

```python
# Weekly token usage report
stats = guardian.get_token_usage_stats(
    start_date=(datetime.now() - timedelta(days=7)).date().isoformat(),
    end_date=datetime.now().date().isoformat()
)

# Monitor verification effectiveness
verification_metrics = prompt_guardian.get_verification_metrics(
    start_time=datetime.now() - timedelta(days=30),
    end_time=datetime.now()
)

# Identify optimization opportunities
if stats['savings_percent'] < 10:
    print("Low token savings - consider reviewing prompt templates")
```

By following these examples and best practices, you'll be able to effectively leverage the Indaleko Prompt Management System in your applications while optimizing token usage, enhancing security, and maintaining prompt quality.
