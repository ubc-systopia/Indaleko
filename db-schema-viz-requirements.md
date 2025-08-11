# Database Schema Visualization Tool Requirements

## Purpose
Create a utility within the Indaleko project that automatically generates visual representations of the database schema, showing collections, relationships, and key indexes in a format suitable for inclusion in documentation and the thesis.

## Functional Requirements

1. **Collection Analysis**
   - Query ArangoDB to retrieve all collections in the database
   - Identify collection types (document vs. edge collections)
   - Extract key metadata about each collection (indexes, count, etc.)
   - Group collections by functional area (Core Storage, Activity Context, System Management, etc.)

2. **Relationship Mapping**
   - Identify relationships between collections through edge collections
   - Extract "from" and "to" connections from edge collections
   - Identify semantic relationships (e.g., "contains", "enriches", "references")

3. **Visualization Generation**
   - Generate a GraphViz DOT file representing the database schema
   - Create a visual representation with the following properties:
     - Different colors for document vs. edge collections
     - Clear labeling of collection names and their purpose
     - Visible grouping of related collections
     - Edge labels showing relationship types
     - Automatic layout to avoid overlapping nodes and edges

4. **Output Options**
   - Generate high-resolution PNG/PDF output suitable for inclusion in the thesis
   - Support configuration of output dimensions and DPI
   - Include a caption and legend explaining the diagram elements

5. **Integration with Indaleko**
   - Use existing Indaleko database connection mechanisms
   - Leverage existing uuid/semantic mapping tables where applicable
   - Implement as a standalone command-line utility within the Indaleko project

## Technical Specifications

1. **Implementation Language**
   - Python 3.12+, consistent with existing Indaleko codebase

2. **Key Dependencies**
   - Graphviz (Python library and executable)
   - Existing Indaleko ArangoDB connector
   - PyArango or equivalent for ArangoDB interaction

3. **Visualization Format**
   - Primary: GraphViz DOT format
   - Output: PDF and PNG formats
   - Optional: SVG for web-based viewing

4. **Design Requirements**
   - Nodes: Rounded rectangles with collection name and brief description
   - Collections should be color-coded by type:
     - Document collections: Blue/light blue
     - Edge collections: Red/light red
   - Indexes: Small green boxes connected to their parent collection
   - Relationships: Directional arrows with labels
   - Logical groupings: Dashed outlines around related collections

## Usage Example

```bash
python -m indaleko.tools.db_schema_viz --output schema.pdf --groups --indexes --caption
```

## Output Specifications

1. **Diagram Components**
   - Collection nodes with name and description
   - Relationship edges with descriptive labels
   - Functional groupings with clear boundaries
   - Key indexes for important collections
   - Legend explaining node and edge types

2. **Layout Guidelines**
   - Landscape orientation for better readability
   - Automatic node placement to avoid overlaps
   - Edge routing to minimize crossings
   - Collections grouped by functional area

## Future Enhancements
- Interactive web-based version
- Ability to filter collections by name/type
- Support for highlighting specific paths or relationships
- Comparison view showing schema changes over time

## Deliverables
1. Python module implemented within Indaleko codebase
2. Command-line interface for generating diagrams
3. High-quality PDF/PNG outputs for thesis inclusion
4. Brief documentation on usage and options
