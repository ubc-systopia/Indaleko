# Indaleko Database Schema Visualization Tool

This tool automatically generates visual representations of the Indaleko database schema, showing collections, relationships, and key indexes in a format suitable for inclusion in documentation and research papers.

## Features

- **Collection Analysis**: Extracts collection information from ArangoDB, including types, indexes, and document counts
- **Relationship Detection**: Identifies relationships between collections through edge collections and semantic connections
- **Visual Grouping**: Groups collections by functional area (Core Storage, Activity Context, etc.)
- **Index Visualization**: Shows key indexes for important collections
- **Multiple Output Formats**: Generates DOT files that can be converted to PDF, PNG, or SVG

## Installation

The tool is part of the Indaleko project and uses the graphviz Python library. Make sure you have all dependencies installed:

```bash
uv pip install -e .
```

For rendering the GraphViz DOT files to PDF/PNG/SVG, you need to install the Graphviz executables:

```bash
# On Ubuntu/Debian
sudo apt-get install graphviz

# On macOS
brew install graphviz

# On Windows
# Install from https://graphviz.org/download/
```

## Usage

```bash
python -m tools.db_schema_viz [options]
```

### Command Line Options

- `--output`, `-o`: Output file path (default: "schema.pdf")
- `--format`, `-f`: Output format: pdf, png, or svg (default: "pdf")
- `--groups`, `-g`: Show collection groupings (default: enabled)
- `--indexes`, `-i`: Show key indexes (default: enabled)
- `--relationships`, `-r`: Show relationships between collections (default: enabled)
- `--orientation`: Diagram orientation: portrait or landscape (default: "landscape")
- `--config`, `-c`: Path to configuration file
- `--save-config`, `-s`: Save current configuration to file
- `--verbose`, `-v`: Enable verbose logging

### Examples

Generate a PDF schema visualization:
```bash
python -m tools.db_schema_viz --output schema.pdf
```

Generate a PNG visualization without indexes:
```bash
python -m tools.db_schema_viz --output schema.png --format png --indexes=False
```

Generate a SVG visualization with custom configuration:
```bash
python -m tools.db_schema_viz --output schema.svg --format svg --config custom_config.json
```

Generate a DOT file and manually convert it:
```bash
python -m tools.db_schema_viz --output schema.dot
dot -Tpdf -o schema.pdf schema.dot
```

## Configuration

The tool uses a default configuration for collection groupings, but you can customize this by providing a JSON configuration file. For example:

```json
{
  "groups": {
    "Core Storage": [
      "Objects",
      "SemanticData",
      "NamedEntities",
      "Relationships"
    ],
    "Activity Context": [
      "ActivityContext",
      "TempActivityContext",
      "GeoActivityContext",
      "MusicActivityContext",
      "ActivityProviderData_*"
    ],
    "Custom Group": [
      "CustomCollection1",
      "CustomCollection2"
    ]
  }
}
```

You can save the current configuration using the `--save-config` option.

## Output

The tool generates a GraphViz DOT file that represents the database schema. If Graphviz is installed on your system, it will also try to render the DOT file to the requested output format (PDF, PNG, or SVG).

The visualization includes:
- Document collections (blue)
- Edge collections (red)
- Key indexes (green)
- Relationships between collections
- Groupings of related collections
- A legend explaining the visualization elements

## Troubleshooting

If you encounter issues with rendering the output:

1. Check if Graphviz is installed: `dot -V`
2. Make sure the Graphviz executables are in your PATH
3. Try generating just the DOT file and converting it manually:
   ```bash
   python -m tools.db_schema_viz --output schema.dot
   dot -Tpdf -o schema.pdf schema.dot
   ```
4. If you're on Windows, use the full path to the dot executable:
   ```
   "C:\Program Files\Graphviz\bin\dot.exe" -Tpdf -o schema.pdf schema.dot
   ```

## Extending the Tool

To add new relationship definitions or collection descriptions, modify the `schema_extractor.py` file. To customize the visualization style, modify the `graphviz_generator.py` file.