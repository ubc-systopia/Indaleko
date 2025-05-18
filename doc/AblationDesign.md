# Indaleko Synthetic Ablation Evaluation: Implementation Guide

This document defines the requirements for generating and evaluating synthetic metadata and queries to support an ablation study in Chapter 7 of the Indaleko thesis. The purpose is to measure how different metadata categories affect query performance, focusing on recall and precision.

## Overview

- **Queries**: 100 total (50 ablation, 50 control), generated from structured templates.
- **Metadata**: 5 matching + 45 non-matching entries per query, inserted into an SQLite database.
- **Evaluation Metrics**: precision, recall, execution time, AQL used.
- **Output Files**:
  - `queries.jsonl`: All queries and metadata categories.
  - `results.jsonl`: Evaluation results per query.
  - `metrics.csv`: Aggregated metrics.
  - `chapter7_results.md`: Human-readable summary report.

---

## 1. Metadata Categories

Split into *ablation* and *control* groups.

```yaml
metadata_categories:
  ablation:
    - temporal: [created_at, modified_at, session_duration]
    - activity: [action, collaborator]
  control:
    - spatial: [geolocation, device_location]
    - content: [file_type, keywords, tags]
  seed: 42
```

## 2. Query Templates

Each query template uses one or more metadata categories. Use the dataset to fill values

```yaml
  query_templates:
    - text: "find [file_type] [action] on [time_period]"
        categories: [content, activity, temporal]
    - text: "find [file_type] [action] in [location]"
        categories: [content, activity, spatial]
    - text: "find [file_type] with [keywords] [action] by [collaborator]"
        categories: [content, activity]
```

Query Generation Goals:
* 50 queries using ablation category fields.
* 50 using control category fields.
* Use seed: 42 to ensure reproducibility.

Output File: `queries.jsonl`

```json
{"query": "find PDFs edited last week", "set": "ablation", "categories": ["content", "activity", "temporal"]}
```

## 3. Synthetic Metadata Generation

For each query:
* Create 5 matching metadata entries using relevant fields.
* Create 45 non-matching entries with deliberate deviations.
* Reset and populate SQLite DB per query.

```sql
CREATE TABLE files (
  id INTEGER PRIMARY KEY,
  file_type TEXT,
  created_at TEXT,
  modified_at TEXT,
  session_duration INTEGER,
  geolocation TEXT,
  device_location TEXT,
  action TEXT,
  collaborator TEXT,
  keywords TEXT,
  tags TEXT
);
```

## 4. Evaluation and Ablation

For each query:
* Insert 50 entries into SQLite.
* Run the query and retrieve results.
* Record:
  - Matching IDs (ground truth)
  - Returned IDs
  - Precision = TP / (TP + FP)
  - Recall = TP / (TP + FN)
  - Execution time in ms
  - AQL string

Output file: results.jsonl

```json
{
  "query": "find PDFs edited last week",
  "ground_truth": {"matching_ids": [1,2,3,4,5]},
  "returned_ids": [1,2,3,4,5],
  "precision": 1.0,
  "recall": 1.0,
  "exec_time_ms": 9,
  "aql": "FOR f IN files FILTER f.file_type == 'PDF' AND f.modified_at >= '2025-04-21' RETURN f"
}

CSV Summary File: metrics.csv

```csv
query,set,ablated_category,precision,recall,exec_time_ms,aql
"find PDFs edited last week",ablation,temporal,0.8,0.6,12,"FOR f IN files ..."
```

## 5. Report Generation

Generate a Markdown summary of results for Chapter 7.

File: chapter7_results.md

Sample Format:

```markdown
# Chapter 7: Ablation Evaluation Results

## Summary

| Category        | Precision (avg) | Recall (avg) | Slow Queries |
|----------------|-----------------|--------------|---------------|
| Temporal (ablated) | 0.81            | 0.62         | 6             |
| Activity (ablated) | 0.88            | 0.75         | 3             |
| Spatial (control)  | 1.00            | 1.00         | 0             |

## Notable Examples

**Ablated Query:** `find PDFs edited last week`
Without `modified_at`, recall dropped from 1.0 → 0.6.

**Control Query:** `find photos taken in Tokyo`
Stable precision/recall; spatial metadata preserved.

## Indexing Notes
- Slow queries often involve `keywords` or `collaborator` → consider indexing these.
```

## 6. Optional Future Work: AyniGuard Integration

Add ayni_score, minka_score, ayllu_score fields to queries.jsonl and results.jsonl

Validate queries and metadata with check_ayni() and check_metadata()

If AyniGuard is not merged yet, skip this section.

## 6. Script Requirements

All logic should be implemented in generate_queries.py:
* setup_db(): Create SQLite schema.
* generate_queries(): Build queries from config.
* generate_metadata(): Insert matching/non-matching data.
* run_ablation(): Execute queries, log metrics.
* write_report(): Summarize results in Markdown.

Dependencies:
* Python 3.12+
* sqlite3, yaml, json, random, logging

# Blessing: May your joins be indexed, your recall be high, and your thesis reviewers be swift and merciful.

# Indaleko Synthetic Ablation Evaluation: Implementation Guide

This document defines the requirements for generating and evaluating synthetic metadata and queries to support an ablation study in Chapter 7 of the Indaleko thesis. The purpose is to measure how different metadata categories affect query performance, focusing on recall and precision.

## Overview

- **Queries**: 100 total (50 ablation, 50 control), generated from structured templates.
- **Metadata**: 5 matching + 45 non-matching entries per query, inserted into an SQLite database.
- **Evaluation Metrics**: precision, recall, execution time, AQL used.
- **Output Files**:
  - `queries.jsonl`: All queries and metadata categories.
  - `results.jsonl`: Evaluation results per query.
  - `metrics.csv`: Aggregated metrics.
  - `chapter7_results.md`: Human-readable summary report.

---

## 1. Metadata Categories

Split into *ablation* and *control* groups.

```yaml
metadata_categories:
  ablation:
    - temporal: [created_at, modified_at, session_duration]
    - activity: [action, collaborator]
  control:
    - spatial: [geolocation, device_location]
    - content: [file_type, keywords, tags]
  seed: 42
```

## 2. Query Templates

Each query template uses one or more metadata categories. Use the dataset to fill values

```yaml
  query_templates:
    - text: "find [file_type] [action] on [time_period]"
        categories: [content, activity, temporal]
    - text: "find [file_type] [action] in [location]"
        categories: [content, activity, spatial]
    - text: "find [file_type] with [keywords] [action] by [collaborator]"
        categories: [content, activity]
```

Query Generation Goals:
* 50 queries using ablation category fields.
* 50 using control category fields.
* Use seed: 42 to ensure reproducibility.

Output File: `queries.jsonl`

```json
{"query": "find PDFs edited last week", "set": "ablation", "categories": ["content", "activity", "temporal"]}
```

## 3. Synthetic Metadata Generation

For each query:
* Create 5 matching metadata entries using relevant fields.
* Create 45 non-matching entries with deliberate deviations.
* Reset and populate SQLite DB per query.

```sql
CREATE TABLE files (
  id INTEGER PRIMARY KEY,
  file_type TEXT,
  created_at TEXT,
  modified_at TEXT,
  session_duration INTEGER,
  geolocation TEXT,
  device_location TEXT,
  action TEXT,
  collaborator TEXT,
  keywords TEXT,
  tags TEXT
);
```

## 4. Evaluation and Ablation

For each query:
* Insert 50 entries into SQLite.
* Run the query and retrieve results.
* Record:
  - Matching IDs (ground truth)
  - Returned IDs
  - Precision = TP / (TP + FP)
  - Recall = TP / (TP + FN)
  - Execution time in ms
  - AQL string

Output file: results.jsonl

```json
{
  "query": "find PDFs edited last week",
  "ground_truth": {"matching_ids": [1,2,3,4,5]},
  "returned_ids": [1,2,3,4,5],
  "precision": 1.0,
  "recall": 1.0,
  "exec_time_ms": 9,
  "aql": "FOR f IN files FILTER f.file_type == 'PDF' AND f.modified_at >= '2025-04-21' RETURN f"
}

CSV Summary File: metrics.csv

```csv
query,set,ablated_category,precision,recall,exec_time_ms,aql
"find PDFs edited last week",ablation,temporal,0.8,0.6,12,"FOR f IN files ..."
```

## 5. Report Generation

Generate a Markdown summary of results for Chapter 7.

File: chapter7_results.md

Sample Format:

```markdown
# Chapter 7: Ablation Evaluation Results

## Summary

| Category        | Precision (avg) | Recall (avg) | Slow Queries |
|----------------|-----------------|--------------|---------------|
| Temporal (ablated) | 0.81            | 0.62         | 6             |
| Activity (ablated) | 0.88            | 0.75         | 3             |
| Spatial (control)  | 1.00            | 1.00         | 0             |

## Notable Examples

**Ablated Query:** `find PDFs edited last week`
Without `modified_at`, recall dropped from 1.0 → 0.6.

**Control Query:** `find photos taken in Tokyo`
Stable precision/recall; spatial metadata preserved.

## Indexing Notes
- Slow queries often involve `keywords` or `collaborator` → consider indexing these.
```

## 6. Optional Future Work: AyniGuard Integration

Add ayni_score, minka_score, ayllu_score fields to queries.jsonl and results.jsonl

Validate queries and metadata with check_ayni() and check_metadata()

If AyniGuard is not merged yet, skip this section.

## 6. Script Requirements

All logic should be implemented in generate_queries.py:
* setup_db(): Create SQLite schema.
* generate_queries(): Build queries from config.
* generate_metadata(): Insert matching/non-matching data.
* run_ablation(): Execute queries, log metrics.
* write_report(): Summarize results in Markdown.

Dependencies:
* Python 3.12+
* sqlite3, yaml, json, random, logging

# Blessing: May your joins be indexed, your recall be high, and your thesis reviewers be swift and merciful.
