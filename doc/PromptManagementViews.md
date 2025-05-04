# Prompt Management ArangoDB Views

## Overview

This document describes the ArangoDB views implemented for the Prompt Management System in Indaleko. These views are designed to enable efficient full-text search capabilities across prompt templates, cache entries, and metrics data.

## Purpose

ArangoDB views provide significant performance improvements for text-based searches:
- Reduce query execution time from minutes to milliseconds
- Enable complex full-text search capabilities
- Support advanced features like relevance ranking and search term highlighting
- Optimize resource usage during query execution

## Views Implementation

The following views have been created for the Prompt Management System collections:

### 1. PromptTemplatesTextView

This view indexes the prompt templates collection for efficient search and retrieval.

**Collection**: `PromptTemplates`

**Indexed Fields**:
- `template_text`: The actual template content
- `description`: The template description
- `tags`: Template categorization tags

**Analyzers**: `text_en`

**Stored Values**: `_key`, `name`, `template_type`, `version`

**Use Cases**:
- Finding templates containing specific keywords
- Searching for templates by description
- Locating templates based on functionality tags
- Finding templates with similar content

### 2. PromptCacheTextView

This view indexes the recent prompt cache for searching through prompt data and results.

**Collection**: `PromptCacheRecent`

**Indexed Fields**:
- `prompt_data`: The serialized prompt data
- `result.issues`: Any issues identified in the prompt
- `result.details`: Detailed results from prompt evaluation

**Analyzers**: `text_en`

**Stored Values**: `_key`, `prompt_hash`, `created_at`, `expires_at`

**Use Cases**:
- Finding prompts with specific patterns
- Searching for prompts with particular issues
- Analyzing prompt evaluation results
- Monitoring prompt cache trends

### 3. PromptArchiveTextView

This view enables searching through the archived prompt data for historical analysis.

**Collection**: `PromptCacheArchive`

**Indexed Fields**:
- `prompt_data`: The serialized prompt data
- `result.issues`: Any issues identified in the prompt
- `result.details`: Detailed results from prompt evaluation

**Analyzers**: `text_en`

**Stored Values**: `_key`, `prompt_hash`, `created_at`, `archived_at`

**Use Cases**:
- Historical analysis of prompt patterns
- Researching past prompt issues
- Longitudinal studies of prompt effectiveness
- Compliance auditing and review

### 4. PromptMetricsTextView

This view supports searching through prompt stability metrics for performance analysis.

**Collection**: `PromptStabilityMetrics`

**Indexed Fields**:
- `prompt_hash`: The hash identifier of the prompt
- `action`: The action taken (block, warn, proceed)
- `issue_count`: Number of issues identified

**Analyzers**: `text_en`

**Stored Values**: `_key`, `prompt_hash`, `score`, `timestamp`

**Use Cases**:
- Tracking prompts with high issue counts
- Monitoring stability trends
- Identifying prompts requiring attention
- Performance analysis and reporting

## Usage Examples

### Example 1: Finding Templates with Specific Content

```aql
FOR doc IN PromptTemplatesTextView
  SEARCH ANALYZER(
    TOKENS('contradiction detection', 'text_en') ALL == doc.template_text,
    'text_en'
  )
  SORT BM25(doc) DESC
  LIMIT 10
  RETURN {
    name: doc.name,
    type: doc.template_type,
    version: doc.version
  }
```

### Example 2: Searching for Prompts with Issues

```aql
FOR doc IN PromptCacheTextView
  SEARCH ANALYZER(
    TOKENS('contradiction ambiguity', 'text_en') ANY == doc.result.issues,
    'text_en'
  )
  SORT doc.created_at DESC
  LIMIT 20
  RETURN {
    hash: doc.prompt_hash,
    created: doc.created_at,
    issues: doc.result.issues
  }
```

### Example 3: Analyzing High-Issue Metrics

```aql
FOR doc IN PromptMetricsTextView
  FILTER doc.issue_count > 5
  SORT doc.timestamp DESC
  LIMIT 50
  RETURN {
    hash: doc.prompt_hash,
    score: doc.score,
    issues: doc.issue_count,
    action: doc.action,
    time: doc.timestamp
  }
```

## Performance Considerations

- Views are automatically updated when the underlying collections change
- Indexing may temporarily increase CPU and memory usage during updates
- Query performance improvements typically show a 100-1000x speedup for text searches
- Views increase disk usage requirements but significantly reduce query execution time

## Maintenance

Views are created and updated through the centralized database configuration in `db/db_collections.py`. Do not directly modify views using ArangoDB APIs; instead, update their definitions in the configuration.
