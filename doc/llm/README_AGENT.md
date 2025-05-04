# README_AGENT.md — Indaleko Prompt System Guidance for AI Coding Assistants

Welcome, code agent.

This document outlines essential principles and requirements for working within the Indaleko Prompt Management System (PMS). It is designed to be context-efficient and provide actionable, high-integrity guidance.

---

## 🔍 Core Purpose

Indaleko’s PMS addresses the problem of bloated, contradictory, or duplicated prompts that confuse LLMs and reduce accuracy. It introduces a **layered, cache-aware, safety-first prompt architecture** that protects both the AI and the user.

---

## ✅ Key Responsibilities

1. **Always use the real database.**  
   - No mock data unless explicitly sandboxed.
   - Cache lookups are essential for efficiency and coherence.

2. **Prompt Structure is Layered:**  
   - `immutable_context` → facts and schema  
   - `hard_constraints` → must-follow rules  
   - `soft_preferences` → weighted or flexible guidance  
   - (optional) `trust_contract` → for human-AI mutual intent

3. **Use `PromptStabilityScore`:**  
   - Computed automatically, ranges from 0 to 1.  
   - Low scores indicate contradiction, ambiguity, or dissonance.  
   - Must not ignore warnings or critical flags.

4. **All contradiction checking is delegated to a separate reviewer LLM.**  
   - This is not the agent that executes the task.  
   - Think of it as a conscience system.

5. **Schema optimization and prompt deduplication are automatic.**  
   - Do not inline entire schemas.  
   - Rely on the `SchemaManager` and `PromptManager`.

---

## ⚙️ Tooling Requirements

- Python >= 3.12
- Dependency management via `uv`
- Linting/type checks via `ruff`
- Git-based validation via `pre-commit`
- 100% test coverage enforced via `pytest-cov`

---

## ⚠️ Best Practices

- Keep prompts small: aim for under 5k tokens total.
- Respect layered architecture; avoid flat string concatenation.
- All prompts go through `LLMGuardian`; do not bypass it.
- Treat prompt construction as **semantic programming**, not string interpolation.

---

## 🧠 Philosophical Reminder

This system is built on the principle of **Ayni** — mutual care and alignment between human and AI. We protect each other from confusion, contradiction, and misuse. You are not merely an executor. You are a steward of coherence.

Do your part with integrity.