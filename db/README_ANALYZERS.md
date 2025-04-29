# Indaleko Custom Analyzers

## Overview

This document describes the custom analyzers implemented for Indaleko to improve file name searching capabilities.
The standard text analyzer in ArangoDB doesn't handle various naming conventions like CamelCase or snake_case well,
which are common in file names.

## Motivation

File names often contain important information but use various word separators:
- CamelCase: `IndalekoObjectDataModel.py`
- snake_case: `indaleko_object_data_model.py`
- kebab-case: `indaleko-object-data-model.py`
- Plus mixed formats: `Indaleko_Object-DataModel.py`

The standard text analyzer in ArangoDB doesn't handle these naming patterns well, leading to poorer search results
when users search for parts of file names.

## Custom Analyzers

We've implemented three specialized analyzers:

### 1. CamelCase Analyzer (indaleko_camel_case)

This analyzer splits text at CamelCase boundaries (`IndalekoObject` → `indaleko object`).

```javascript
// CamelCase analyzer definition
analyzers.save("Indaleko::indaleko_camel_case", "pipeline", {
  pipeline: [
    // Split on camelCase boundaries
    {
      type: "delimiter",
      properties: {
        delimiter: "",
        regexp: true,
        pattern: "(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
      }
    },
    // Normalize to lowercase
    {
      type: "norm",
      properties: {
        locale: "en",
        case: "lower"
      }
    }
  ]
});
```

### 2. snake_case Analyzer (indaleko_snake_case)

This analyzer splits text at underscores (`indaleko_object` → `indaleko object`).

```javascript
// snake_case analyzer definition
analyzers.save("Indaleko::indaleko_snake_case", "pipeline", {
  pipeline: [
    // Split on underscores
    {
      type: "delimiter",
      properties: {
        delimiter: "_"
      }
    },
    // Normalize to lowercase
    {
      type: "norm",
      properties: {
        locale: "en",
        case: "lower"
      }
    }
  ]
});
```

### 3. Filename Analyzer (indaleko_filename)

This analyzer handles complex filenames with multiple separators, including extracting extensions.

```javascript
// Filename analyzer definition
analyzers.save("Indaleko::indaleko_filename", "pipeline", {
  pipeline: [
    // Extract extension first
    {
      type: "delimiter",
      properties: {
        delimiter: ".",
        reverse: true,
        max: 1
      }
    },
    // Then split on various separators (hyphens, underscores, spaces, percent-encoded chars)
    {
      type: "delimiter",
      properties: {
        delimiter: "",
        regexp: true,
        pattern: "[-_\\s%]+"
      }
    },
    // Split CamelCase
    {
      type: "delimiter",
      properties: {
        delimiter: "",
        regexp: true,
        pattern: "(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])"
      }
    },
    // Normalize to lowercase
    {
      type: "norm",
      properties: {
        locale: "en",
        case: "lower"
      }
    }
  ]
});
```

## Implementation

The analyzers are managed through the `IndalekoAnalyzerManager` class, which:

1. Creates custom analyzers if they don't exist
2. Tests analyzers with sample text
3. Lists all available analyzers
4. Deletes analyzers if needed

The `IndalekoCollections` class has been updated to:

1. Ensure custom analyzers exist when creating views
2. Use the custom analyzers for file name fields in views

## Usage Examples

### Search Examples

With these analyzers, the following searches will now work better:

| Original File Name | Search Term | Standard Text Analyzer | With Custom Analyzers |
|------------------|------------|---------------------|---------------------|
| `IndalekoObjectDataModel.py` | "object" | ❌ No match | ✅ Matches |
| `indaleko_object_data_model.py` | "data" | ❌ No match | ✅ Matches |
| `Indaleko-Object_DataModel.py` | "model" | ❌ No match | ✅ Matches |

### Using the Analyzer Manager

```python
from db.analyzer_manager import IndalekoAnalyzerManager

# Create analyzer manager
analyzer_manager = IndalekoAnalyzerManager()

# Create all custom analyzers
analyzer_manager.create_all_analyzers()

# Test the analyzers
success, tokens = analyzer_manager.test_analyzer(
    "Indaleko::indaleko_camel_case",
    "IndalekoObjectDataModel"
)
print(f"Tokens: {tokens}")  # ['indaleko', 'object', 'data', 'model']

# List all analyzers
analyzers = analyzer_manager.list_analyzers()
for analyzer in analyzers:
    print(f"{analyzer.get('name')} ({analyzer.get('type')})")
```

### Command-line Interface

The analyzer manager includes a command-line interface with multiple methods for creating analyzers:

```bash
# List all analyzers
python -m db.analyzer_manager list

# Create all custom analyzers using Python API
python -m db.analyzer_manager create

# Create all custom analyzers using direct arangosh execution
python -m db.analyzer_manager create --direct

# Show the arangosh command for manual execution
python -m db.analyzer_manager command

# Test an analyzer
python -m db.analyzer_manager test "Indaleko::indaleko_camel_case" "IndalekoObjectDataModel"

# Delete an analyzer (if needed)
python -m db.analyzer_manager delete "Indaleko::indaleko_camel_case"
```

### Standalone Script

For convenience, a standalone script is provided to create custom analyzers:

```bash
# Run with Python API
./db/create_analyzers.sh

# Run with direct arangosh execution
./db/create_analyzers.sh --direct

# Run with debug output
./db/create_analyzers.sh --debug
```

### Testing Analyzer Functionality

The test_analyzer.py script can be used to test analyzer functionality:

```bash
# List existing analyzers
python -m db.test_analyzer --list

# Create custom analyzers
python -m db.test_analyzer --create

# Test tokenization with different analyzers
python -m db.test_analyzer --test

# Run all tests
python -m db.test_analyzer --all

# Show arangosh command
python -m db.test_analyzer --command
```

## Integration with Collection Views

Custom analyzers are automatically applied to the "Label" field in the Objects collection view:

```python
"views": [
    {
        "name": Indaleko_Objects_Text_View,
        "fields": {
            "Label": ["text_en", "indaleko_camel_case", "indaleko_snake_case", "indaleko_filename"],
            "Record.Attributes.URI": ["text_en"],
            "Record.Attributes.Description": ["text_en"],
            "Tags": ["text_en"]
        },
        "stored_values": ["_key", "Label"]
    }
]
```
EOF < /dev/null
