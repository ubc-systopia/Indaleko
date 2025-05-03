# Prompt Management System Design (Revised)

## Overview

This design addresses critical challenges in Indaleko's prompt handling: prompt bloat, duplication, contradiction, and safety. It proposes a layered prompt system with structured caching and verification guided by the Ayni principle.

## Design Goals

1. **Reduce Token Usage**: Cut prompt sizes from 45-50k tokens to 4-5k
2. **Improve Response Quality**: Reduce contradictions and ambiguity
3. **Efficient Caching**: Avoid recomputing optimized prompts
4. **Automatic Validation**: Detect and prevent inconsistencies
5. **Separation of Concerns**: Clearly distinguish templates, schemas, and dynamic content
6. **Prompt Safety**: Detect instability and protect LLMs from conflicting or manipulative inputs

## Core Components

### Prompt Stability and Contradiction Detection

- Implement a `PromptStabilityScore` (0 to 1):
  - Logical contradictions (e.g., `MUST x` and `MUST NOT x`)
  - Cognitive dissonance indicators (e.g., conflicting goals)
  - Ambiguity score (entropy from reviewer)
  - Extensive pattern library for common contradictions

- Stability score used to block, warn, or adapt prompts dynamically.

### Trust Contract Layer

- Prompts may include a `trust_contract`:
```json
{
  "mutual_intent": "maximize understanding, minimize confusion",
  "user_commitments": ["Avoid conflicting constraints"],
  "ai_commitments": ["Flag inconsistencies"]
}
```

- Lays foundation for future meta-prompting and alignment.

### LLM Reviewer Implementation

- Reviewer is implemented using existing LLM connector factory
- Uses separate LLM instance (conceptually separate, may be same model type)
- Maintains separation of concerns between execution and review
- Leverages existing authentication and connection patterns
- Returns confidence for each detected issue

### Cache Architecture (Two-Tier)

- **Recent Tier**: 
  - Rapid access for frequently used prompts (30-day retention)
  - Full metadata and scoring history
  - High-performance indices

- **Archive Tier**:
  - Historical prompt patterns (long-term storage)
  - Compressed representation with essential metadata
  - Used for trend analysis and pattern learning

- Track prompt cache stability metrics:
  - Token delta across versions
  - Prompt contradiction recurrence
  - Prompt aging and eviction behavior

## Components (Revised Overview)

- **SchemaManager**: De-duplicates and compresses schemas
- **PromptManager**: Template-based, layered prompt constructor
- **PromptGuardian**: Detects contradictions, computes stability, and verifies prompts
- **LLMGuardian**: High-level coordinator, includes metrics and cache oversight

## Metrics Tracked

- Token savings (original vs. optimized)
- PromptStabilityScore distribution
- Frequency of contradiction types
- Cache hit ratio and TTL impact
- Prompt verification rate and latency

## Integration

- Templates loaded from disk or DB
- Prompts include layered content blocks and optional trust contracts
- Refactor all prompt generation through `LLMGuardian`
- All database interactions follow Indaleko's collection management principles

## AyniGuard Implementation

AyniGuard serves as a pre-filter for prompt integrity before prompt layering begins. Key implementation details:

- Integrated with existing Indaleko database structure via proper collection registration
- Uses existing LLM connector factory rather than direct API calls
- Shares contradiction detection patterns with PromptStabilityScore calculation
- Produces `AyniScore` (0.0–1.0) measuring mutualism and stability
- Implements tier-specific contradiction analysis:
  - **Tier 1** (Context): must be contradiction-free
  - **Tier 2** (Constraints): no conflict allowed
  - **Tier 3** (Preferences): may conflict, but weighted
- Provides blocking, flagging, or refinement based on severity
- Extensive pattern library for detecting common contradictions, such as:
  - Format conflicts (JSON vs. prose vs. XML)
  - Numerical range contradictions
  - Mutually exclusive operation requests
  - Competing priorities
  - Temporal consistency issues
  - Role/identity conflicts

This pre-filter acts as a semantic firewall and reduces the risk of prompt injection and unintended LLM behaviors.

## Contradiction Pattern Library

To ensure robust contradiction detection, we'll build an extensive pattern library including:

1. **Logical Contradictions**:
   - Opposite directives (`MUST` vs. `MUST NOT`)
   - Mutually exclusive formats (JSON, XML, prose)
   - Range conflicts (e.g., "between 1-5" and "greater than 7")

2. **Semantic Contradictions**:
   - Entity relationship conflicts
   - Role definition inconsistencies 
   - Conflicting metaphors or mental models

3. **Structural Contradictions**:
   - Context that undermines constraints
   - Preferences that conflict with context
   - Trust contract violations

4. **Temporal Contradictions**:
   - Conflicting time references
   - Impossible sequencing requirements

5. **Identity/Role Contradictions**:
   - Unclear or conflicting agent identity
   - Contradictory ethical frameworks
   - Mixed guidance on tone or style

The pattern library will be continuously expanded by analyzing real-world prompt issues and using multi-LLM sourcing to increase diversity of patterns.