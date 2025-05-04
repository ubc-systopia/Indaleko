
# Prompt Management System Design (Updated)

## Overview

This design addresses critical challenges in Indaleko's prompt handling: prompt bloat, duplication, contradiction, and safety. It proposes a layered prompt system with structured caching and verification guided by the Ayni principle.

## Design Goals

1. **Reduce Token Usage**: Cut prompt sizes from 45-50k tokens to 4-5k
2. **Improve Response Quality**: Reduce contradictions and ambiguity
3. **Efficient Caching**: Avoid recomputing optimized prompts
4. **Automatic Validation**: Detect and prevent inconsistencies
5. **Separation of Concerns**: Clearly distinguish templates, schemas, and dynamic content
6. **Prompt Safety**: Detect instability and protect LLMs from conflicting or manipulative inputs

## New Enhancements

### Prompt Stability and Contradiction Formalism

- Introduce a `PromptStabilityScore` (0 to 1):
  - Logical contradictions (e.g., `MUST x` and `MUST NOT x`)
  - Cognitive dissonance indicators (e.g., conflicting goals)
  - Ambiguity score (entropy from reviewer)

- Stability score used to block, warn, or adapt prompts dynamically.

### Trust Contract Layer (Optional)

- Prompts may include a `trust_contract`:
```json
{
  "mutual_intent": "maximize understanding, minimize confusion",
  "user_commitments": ["Avoid conflicting constraints"],
  "ai_commitments": ["Flag inconsistencies"]
}
```

- Lays foundation for future meta-prompting and alignment.

### LLM Reviewer Identity Separation

- Reviewer is:
  - A separate LLM instance
  - Provided prompt history
  - Returns confidence for each issue

### Cache-Aware Safety

- Track prompt cache instability:
  - Token delta across versions
  - Prompt contradiction recurrence
  - Prompt aging and eviction behavior

## Tooling and Development Requirements

- Use **real database only** (no mock data for core tests or usage)
- Require **Python 3.12+**
- Mandatory tooling:
  - `uv` for dependencies
  - `ruff` for linting/type checking
  - `pre-commit`, `pytest`, 100% test coverage before merge

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


## AyniGuard: Pre-Filter for Prompt Integrity

Before prompt layering begins, the system applies an AyniGuard check. This component analyzes the prompt for internal coherence, ethical intent, and mutual respect across tiers. AyniGuard produces:

- `AyniScore` (0.0–1.0): Measures mutualism and stability
- Tier-specific contradiction analysis:
  - **Tier 1** (Context): must be contradiction-free
  - **Tier 2** (Constraints): no conflict allowed
  - **Tier 3** (Preferences): may conflict, but weighted
- Blocking, flagging, or refinement based on severity

This pre-filter acts as a semantic firewall and reduces the risk of prompt injection and unintended LLM behaviors.