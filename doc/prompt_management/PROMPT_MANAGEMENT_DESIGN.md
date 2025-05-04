# Prompt Management System Design

## Overview

This document outlines the design of the Prompt Management System (PMS) for Indaleko, addressing the challenges of prompt optimization, schema duplication, and contradiction detection.

## Design Goals

1. **Reduce Token Usage**: Cut prompt sizes from 45-50k tokens to 4-5k
2. **Improve Response Quality**: Reduce contradictions and ambiguity
3. **Efficient Caching**: Avoid recomputing optimized prompts
4. **Automatic Validation**: Detect and prevent inconsistencies
5. **Separation of Concerns**: Clearly distinguish templates, schemas, and dynamic content

## Core Components

### 1. SchemaManager

Responsible for optimizing and caching schema definitions.

```python
class SchemaManager:
    def __init__(self, db_config):
        self.db = db_config.db
        self.schema_collection = "SchemaCacheCollection"
        self._ensure_collection_exists()
        
    def get_optimized_schema(self, schema_obj):
        """Get an optimized version of the schema, using cache when possible"""
        schema_hash = self._compute_hash(schema_obj)
        cached = self._lookup_in_db(schema_hash)
        if cached:
            self._update_last_used(schema_hash)
            return cached["optimized_schema"]
            
        optimized = self._optimize_schema(schema_obj)
        self._store_in_db(schema_hash, optimized)
        return optimized
        
    def _optimize_schema(self, schema_obj):
        """Optimize a schema by removing redundancy and compressing it"""
        # Implementation strategies:
        # 1. Remove redundant field descriptions
        # 2. Reduce example count
        # 3. Simplify nested structures
        # 4. Truncate lengthy descriptions
        # 5. Remove non-essential metadata
        return optimized_schema
```

### 2. PromptManager

Manages prompt templates, composition, and caching.

```python
class PromptManager:
    def __init__(self, db_config, schema_manager):
        self.db = db_config.db
        self.schema_manager = schema_manager
        self.prompt_collection = "PromptCacheCollection"
        self._ensure_collection_exists()
        
    def get_optimized_prompt(self, template, dynamic_parts):
        """Get an optimized prompt, using cache when possible"""
        prompt_hash = self._compute_hash(template, dynamic_parts)
        cached = self._lookup_in_db(prompt_hash)
        if cached:
            self._update_last_used(prompt_hash)
            return cached["optimized_prompt"]
            
        # Process schemas in dynamic parts
        processed_parts = self._process_dynamic_parts(dynamic_parts)
        
        # Build layered prompt
        draft_prompt = self._build_layered_prompt(template, processed_parts)
        
        # This will be handled by the PromptGuardian
        return draft_prompt
        
    def _process_dynamic_parts(self, dynamic_parts):
        """Process dynamic parts, optimizing schemas"""
        processed = dynamic_parts.copy()
        if "schema" in processed:
            processed["schema"] = self.schema_manager.get_optimized_schema(
                processed["schema"]
            )
        return processed
        
    def _build_layered_prompt(self, template, dynamic_parts):
        """Build a prompt with the layered structure"""
        prompt = {
            "immutable_context": {
                "schema": dynamic_parts.get("schema", {}),
                "facts": dynamic_parts.get("facts", [])
            },
            "hard_constraints": {
                "rules": dynamic_parts.get("rules", [])
            },
            "soft_preferences": {
                "preferences": dynamic_parts.get("preferences", [])
            }
        }
        
        # Format according to template
        return self._format_prompt(template, prompt)
```

### 3. PromptGuardian

Acts as a sentinel for all LLM communications, ensuring quality and safety.

```python
class PromptGuardian:
    def __init__(self, db_config, prompt_manager):
        self.db = db_config.db
        self.prompt_manager = prompt_manager
        self.verification_collection = "PromptVerificationCollection"
        self._ensure_collection_exists()
        
    def process_prompt(self, template, dynamic_parts, verify=True):
        """Process, optimize, verify and store a prompt"""
        # Get optimized draft from PromptManager
        draft_prompt = self.prompt_manager.get_optimized_prompt(
            template, dynamic_parts
        )
        
        # Skip verification if not required
        if not verify:
            return draft_prompt
            
        # Compute hash for verification
        verification_hash = self._compute_hash(draft_prompt)
        
        # Check if already verified
        cached_verification = self._lookup_verification(verification_hash)
        if cached_verification:
            return draft_prompt
            
        # Verify prompt for contradictions and quality
        verification_result = self._verify_prompt(draft_prompt)
        
        if verification_result["has_critical_issues"]:
            # Handle critical issues - could throw exception or fix automatically
            raise PromptContradictionError(verification_result["issues"])
            
        if verification_result["has_warnings"]:
            # Log warnings but proceed
            pass
            
        # Store verification result
        self._store_verification(verification_hash, verification_result)
        
        # Return verified prompt
        return draft_prompt
        
    def _verify_prompt(self, prompt):
        """Verify prompt for contradictions and quality"""
        # Rule-based checks
        rule_issues = self._check_rule_contradictions(prompt)
        
        # Optional: LLM-based review
        llm_issues = self._llm_review_prompt(prompt)
        
        # Combine and classify issues
        all_issues = rule_issues + llm_issues
        critical_issues = [i for i in all_issues if i["severity"] == "critical"]
        warnings = [i for i in all_issues if i["severity"] == "warning"]
        
        return {
            "has_critical_issues": len(critical_issues) > 0,
            "has_warnings": len(warnings) > 0,
            "issues": all_issues
        }
        
    def _llm_review_prompt(self, prompt):
        """Use a separate LLM to review prompt for issues (Ayni principle)"""
        # Implementation uses a separate LLM to review
        # This embodies the Ayni principle (LLM reviewing instructions for another LLM)
        pass
```

### 4. LLMGuardian

High-level wrapper that serves as the entry point for all LLM interactions.

```python
class LLMGuardian:
    def __init__(self, db_config):
        self.schema_manager = SchemaManager(db_config)
        self.prompt_manager = PromptManager(db_config, self.schema_manager)
        self.prompt_guardian = PromptGuardian(db_config, self.prompt_manager)
        
    def prepare_prompt(self, template, dynamic_parts, verify=True):
        """Prepare an optimized and verified prompt"""
        return self.prompt_guardian.process_prompt(
            template, dynamic_parts, verify
        )
        
    def get_token_stats(self):
        """Get statistics on token usage and savings"""
        # Implementation to track and report token usage
        pass
        
    def refresh_cache(self, max_age_days=30):
        """Clean up old cache entries"""
        # Implementation to remove stale cache entries
        pass
```

## Database Schema

### Schema Cache Collection
```json
{
  "hash": "sha256_hash_of_schema",
  "original_schema": { /* Original schema object */ },
  "optimized_schema": { /* Optimized schema object */ },
  "token_counts": {
    "original": 1500,
    "optimized": 350
  },
  "created_at": "ISO_TIMESTAMP",
  "last_used": "ISO_TIMESTAMP"
}
```

### Prompt Cache Collection
```json
{
  "hash": "sha256_hash_of_template_and_parts",
  "template_id": "identifier",
  "dynamic_parts_hash": "hash_of_dynamic_parts",
  "optimized_prompt": "final_layered_prompt",
  "token_counts": {
    "original": 5000,
    "optimized": 1200
  },
  "created_at": "ISO_TIMESTAMP",
  "last_used": "ISO_TIMESTAMP"
}
```

### Prompt Verification Collection
```json
{
  "hash": "sha256_hash_of_prompt",
  "verification_result": {
    "has_critical_issues": false,
    "has_warnings": true,
    "issues": [
      {
        "severity": "warning",
        "type": "ambiguity",
        "description": "Potential ambiguity between rule X and preference Y"
      }
    ]
  },
  "verified_at": "ISO_TIMESTAMP"
}
```

## Layered Prompt Structure

All optimized prompts will follow this layered structure:

```
# Immutable Context (FACTUAL)
SCHEMA: {...}  
FACTS: [...]

# Hard Constraints (NO AMBIGUITY)
RULES: [
  "creation_date MUST be after 2023",
  "file_size MUST be less than 10MB"
]  

# Soft Preferences (WEIGHTED)
PREFERENCES: [
  {"directive": "filter_by_social", "confidence": 0.8},
  {"directive": "sort_by_recent", "confidence": 0.6}
]
```

## Integration with Existing Code

To integrate with existing code like `enhanced_aql_translator.py`:

1. Extract template strings to external files
2. Replace direct schema inclusion with SchemaManager calls
3. Structure dynamic content according to the layered model
4. Use LLMGuardian as the entry point for all LLM communication

## Implementation Plan

1. Create database collections for caching and verification
2. Implement SchemaManager with optimization logic
3. Implement PromptManager with template handling
4. Implement PromptGuardian with verification logic
5. Create LLMGuardian as the facade for the system
6. Update existing code to use the new system
7. Add metrics collection and reporting

## Metrics and Monitoring

The system will track:

1. Token count reduction (original vs. optimized)
2. Cache hit rates
3. Contradiction detection statistics
4. Response quality metrics
5. Performance impact (latency)

## Conclusion

This Prompt Management System will address both the immediate needs for optimization and contradiction detection while providing a foundation for ongoing improvements. The estimated 90% reduction in token usage (from 45-50k to 4-5k) should significantly reduce costs while improving response quality.

The Ayni principle (having an LLM review instructions meant for another LLM) provides a novel approach to contradiction detection that leverages the strengths of these systems.