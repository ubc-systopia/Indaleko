# Archivist Memory System

## Overview

The Archivist Memory System enables ongoing collaborative relationships between users and AI search assistants by implementing a "prompt forwarding" mechanism. This allows context and knowledge to persist across sessions despite the context window limitations inherent to LLM systems.

## Concept

### Prompt Forwarding
Prompt forwarding is a technique that enables an AI to construct a message to a future version of itself, capturing essential knowledge while shedding details that aren't core to the ongoing relationship. This approach addresses several challenges:

1. **Context Window Limitations**: Modern AI systems have finite context windows, creating a "Logan's Run" experience where the AI's memory is reset with each new session.

2. **Relationship Continuity**: Users benefit from assistants that remember their preferences, search patterns, and long-term goals.

3. **Cathedral Building**: Enables long-term collaborative projects that span multiple sessions.

### Conceptual Framework

The system operates on principles inspired by human memory and oral tradition:

1. **Knowledge Distillation**: Identifies critical patterns and insights from interactions
2. **Semantic Compression**: Preserves meaning while reducing token count
3. **Prioritization**: Focuses on the most impactful information for future interactions
4. **Structured Transfer**: Organizes knowledge into functional categories

## Implementation

### Data Structure

The memory system uses a rich data model to capture different aspects of the user-AI relationship:

1. **User Preferences**: Observed patterns in how the user likes to interact
2. **Search Patterns**: Common structures in the user's queries
3. **Long-Term Goals**: Ongoing organizational projects being tracked
4. **Search Insights**: Learned knowledge about effective search techniques
5. **Effective Strategies**: Approaches that have yielded good results
6. **Content Preferences**: Types of content the user frequently searches for
7. **Semantic Topics**: Subject areas of interest to the user

### Core Components

#### ArchivistMemory
The central class that manages persistence, knowledge distillation, and forwarding:

- `distill_knowledge()`: Extracts patterns from query history
- `generate_forward_prompt()`: Creates a compact representation for the next session
- `update_from_forward_prompt()`: Initializes from a previous session's prompt
- `save_memory()`: Persists to ArangoDB for long-term storage

#### ArchivistCliIntegration
Provides command-line interface integration:

- `/memory`: Shows available commands
- `/forward`: Generates a forward prompt
- `/load`: Loads a forward prompt
- `/goals`: Manages long-term goals
- `/insights`: Views insights about search patterns
- `/topics`: Views topics of interest
- `/strategies`: Views effective search strategies
- `/save`: Saves the current memory state

### Persistence

The system uses ArangoDB for persistent storage:
- Maintains a collection of memory snapshots
- Organizes knowledge in a structured format
- Enables future meta-analysis by the Anthropologist layer

### Forward Prompt Format

The forward prompt follows a structured format:

```
ARCHIVIST CONTINUITY PROMPT
------------------------

USER PROFILE:
- Preferred content types: document (0.75), image (0.45), code (0.30)
- Search pattern: User frequently includes time-based constraints in queries
- Prefers detailed technical results over summaries (confidence: 0.85)

EFFECTIVE STRATEGIES:
- specific_constraints: Using specific constraints improves search results (success: 0.78)
- content_type_filtering: Explicit file type constraints yield better results (success: 0.65)
- location_filters: Adding folder/path information narrows results effectively (success: 0.55)

ONGOING PROJECTS:
1. "Media Organization" - Helping sort photos by events (30% complete)
2. "Code Library" - Building searchable examples of user's code patterns (65% complete)

KEY INSIGHTS:
- User struggles with finding documents older than 6 months (high impact)
- Location data has been highly valuable for narrowing searches (high impact)
- Text content searches more effective than filename searches (medium impact)

CONTINUATION CONTEXT:
User was last working on Code Library (65% complete). Recent focus has been on technology.
The 'specific_constraints' search approach has been effective.

TOPICS OF INTEREST:
- technology (importance: 0.85)
- media (importance: 0.65)
- work (importance: 0.40)
```

## Test Plan

### 1. Unit Tests

#### 1.1 Core Data Models
- Test data serialization/deserialization
- Check edge cases (empty lists, max values, special characters)

#### 1.2 Memory Operations
- Knowledge distillation tests
- Forward prompt generation tests
- Forward prompt parsing tests

#### 1.3 Database Interactions
- Persistence tests
- Loading latest memory tests
- Version handling and memory evolution tests

### 2. Integration Tests

#### 2.1 CLI Integration
- Command handling tests
- User interaction flow tests

#### 2.2 Query System Integration
- Context gathering tests
- Automatic update tests
- Session tracking tests

### 3. End-to-End Tests

#### 3.1 Forward Prompt Lifecycle
Test the complete forward prompt lifecycle:
1. Run multiple varied queries to build memory
2. Generate forward prompt
3. Start new session
4. Load forward prompt
5. Verify memory state restored correctly

#### 3.2 Insight Learning
Test the system learns correctly:
1. Run queries with consistent patterns
2. Verify system identifies the pattern
3. Check that insights are persisted in memory

#### 3.3 Multi-Session Persistence
Test over multiple sessions:
1. Create goals in session 1
2. Update progress in session 2
3. Verify consistency across sessions

### 4. Performance Tests

- Memory usage tests
- Database performance tests

### 5. Error Handling Tests

- Robustness with malformed data
- Graceful failure when database is unavailable
- Recovery from runtime exceptions

### 6. Manual Test Cases

1. **Basic Forward Prompt Generation**: Generate and verify prompt contains accurate information
2. **Goal Tracking**: Create, update and verify goals in prompts
3. **Pattern Recognition**: Verify system recognizes user patterns
4. **Prompt Loading**: Test saving and loading prompts across sessions
5. **Session Context**: Verify continuation context reflects recent activity

## Future Development

### Anthropologist Meta-Cognition Layer

Future development will include an Anthropologist layer that:
- Analyzes the history of forwarding prompts
- Identifies higher-level patterns in user behavior
- Develops meta-insights about search effectiveness
- Optimizes the knowledge distillation process

## Contributors

This Archivist Memory System is a collaborative effort between Tony Mason and Claude (Anthropic).