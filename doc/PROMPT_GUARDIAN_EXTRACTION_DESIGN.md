# PromptGuardian & AyniGuard Extraction – Design Document

This document captures the requirements, goals, non-goals, and high-level design for extracting PromptGuardian and AyniGuard from Indaleko into an independent Python package.

## 1. Context & Motivation
PromptGuardian and AyniGuard form a mutual-benefit system for verifying and stabilizing prompts before they are submitted to LLMs. Extracting them into a standalone package provides:
- Independent reuse across projects
- Simplified dependency management (SQLite, in-memory) instead of ArangoDB
- Clear extension points for storage and LLM integration

## 2. Requirements

### 2.1 Functional Requirements
- Evaluate raw or structured prompts for:
  - Banned/injection patterns (e.g. “ignore instructions”)  
  - Trust-contract presence and validity  
  - Stability score (coherence, ethicality, mutualism via AyniGuard)  
  - Security and ethical issues extraction  
  - Final decision: proceed, warn, or block  
  - Human-readable reasons, warnings, and recommendations
- Support configurable verification levels: none, basic, standard, strict, paranoid
- Cache prompt evaluations per hash and level to optimize performance
- Log each verification attempt for audit

### 2.2 Non-Functional Requirements
- Pure-Python core, compatible with Python ≥3.12
- Minimal external dependencies (pydantic, sqlite3, etc.)
- Abstract storage interface to swap in-memory, SQLite, or external DB backends
- Testability with an in-memory default backend
- Clear API surface and configuration models

## 3. Goals & Non-Goals

### 3.1 Goals
- Extract core logic into `PromptGuardian` and `AyniGuard` modules
- Define a `StorageBackend` interface for persistence and caching
- Provide sample backends: InMemory, SQLite, ArangoDB
- Migrate and adapt existing tests to cover the new package

### 3.2 Non-Goals
- Implementing high-availability or distributed storage
- Bundling a specific LLM connector; instead rely on host-injection of an LLM client
- Incorporating UI/CLI frontends beyond minimal examples

## 4. High-Level Design

### 4.1 Core Modules
- **guardian/**  
  • `PromptGuardian`: orchestrates prompt verification  
  • Models: `VerificationLevel`, `VerificationResult`, `SecurityPolicy`  
  • Banned-patterns and trust-contract checks  
- **ayni/**  
  • `AyniGuard`: computes stability scores  
  • `AyniResult`, internal checks (contradictions, ethicality, mutualism)  

### 4.2 Storage Abstraction
Define a minimal protocol:
```python
from typing import Protocol, Any, Sequence, Mapping

class StorageBackend(Protocol):
    def get(self, collection: str, key: str) -> Mapping[str, Any] | None: ...
    def insert(self, collection: str, document: Mapping[str, Any]) -> None: ...
    def update(self, collection: str, key: str, document: Mapping[str, Any]) -> None: ...
    def query(self, collection: str, filter: Mapping[str, Any], limit: int = 100) -> Sequence[Mapping[str, Any]]: ...
```  
- Collections:
  - `cache_recent`, `cache_archive` for prompt results  
  - `verification_log` for audit  

### 4.3 Sample Connectors
- **InMemoryBackend**: Python dicts for tests and quick demos  
- **SQLiteBackend**: using `sqlite3` for file-based persistence  
- **ArangoDBBackend** (optional): adapter to `python-arango` for backward compatibility  

## 5. Next Steps
1. Review and refine this design document  
2. Define the `StorageBackend` interface and its location in the package  
3. Scaffold the package structure and basic modules  
4. Implement `InMemoryBackend` and write core tests  
5. Proceed to SQLite and ArangoDB connectors  

---
*Drafted by Indaleko team for PromptGuardian extraction*  
