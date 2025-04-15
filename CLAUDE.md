# CLAUDE.md - Indaleko Development Guidelines

## Development Environment

### Package Management
Indaleko uses `uv` for package management across multiple platforms (Windows, macOS, Linux). The dependencies are defined in `pyproject.toml` (not requirements.txt).

- **Setup Environment**: 
  ```bash
  # Install uv if not already installed
  pip install uv
  
  # Create and activate virtual environment
  uv venv
  source .venv/bin/activate  # Linux/macOS
  .venv\Scripts\activate     # Windows
  
  # Install dependencies
  uv pip install -e .
  ```

- **Update Dependencies**:
  ```bash
  uv pip install -e .
  ```

### Virtual Environments
The project maintains separate virtual environments for each platform:
- `.venv-win32-python3.12` - Windows environment
- `.venv-linux-python3.13` - Linux environment
- `.venv-macos-python3.12` - macOS environment

Always activate the appropriate environment before running code:
```bash
source .venv-linux-python3.13/bin/activate  # Linux
.venv-win32-python3.12\Scripts\activate     # Windows
```

### GUI Application
The project includes a Streamlit-based GUI in the `/utils/gui/streamlit/` directory:

- **Run GUI**:
  ```bash
  # Windows
  run_gui.bat
  
  # Linux/macOS
  ./run_gui.sh
  ```

- **GUI Features**:
  - Dashboard with storage summary and file type distribution
  - Natural language search using Indaleko's query tools
  - Interactive query plan visualization
  - Analytics with data visualizations
  - Faceted search for result filtering
  - Integration with real ArangoDB database
  - Debug mode with detailed diagnostics
  - Mock mode for development and demos

- **GUI Architecture**:
  - Auto-detection of Indaleko environment
  - Database connection management
  - Query execution with fallbacks
  - Special handling for complex data display
  - Visualization of query execution plans
  - Automatic normalization of complex data structures

## Commands

### Core Commands
- Run all tests: `pytest tests/`
- Run single test: `pytest tests/path/to/test.py::test_function_name -v`
- Lint code: `flake8` or `pylint`
- Format code: `black .`
- Build package: `python -m build`

### Query System Commands
- Test query tools: `python query/tools/test_tools.py --query "Your query here" --debug`
- Test EXPLAIN: `python query/test_explain.py --query "Your query here" --debug`
- Test enhanced NL: `python query/test_enhanced_nl.py --query "Your query here" --debug`
- Test relationships: `python query/test_relationship_query.py --query "Show files I shared with Bob last week" --debug`
- Run CLI with enhanced NL: `python -m query.cli --enhanced-nl --context-aware --deduplicate --dynamic-facets`
- Run CLI with Archivist: `python -m query.cli --archivist --optimizer`

### GUI Commands
- Run Streamlit GUI: `cd utils/gui/streamlit && streamlit run app.py`
- Run Windows GUI script: `run_gui.bat`
- Run Linux/macOS GUI script: `./run_gui.sh`

### Testing Commands
- Test Database Optimizer: `python archivist/test_optimizer.py`
- Test Archivist Memory: `python query/memory/test_archivist.py --all`
- Test Cross-Source Patterns: `python query/memory/test_cross_source_patterns.py --all`
- Test Knowledge Base Updating: `python archivist/test_knowledge_base.py --all`
- Test Semantic Performance CLI: `python semantic/test_cli_integration.py`

## Style Guidelines
- Imports: standard library → third-party → local (with blank lines between)
- Types: Use type hints for all functions and variable declarations
- Formatting: 4 spaces, ~100 char line length, docstrings with triple quotes
- Naming: CamelCase for classes, snake_case for functions/vars, UPPER_CASE for constants
- Interfaces: Prefix with 'I' (IObject, IRelationship)
- Error handling: Specific exceptions with descriptive messages
- Documentation: All modules, classes and methods need docstrings (Args/Returns sections)
- Module organization: Copyright header, imports, constants, classes, functions, main

Refer to TODO.md for a comprehensive list of planned features, enhancements, and research directions for the Indaleko project. The TODO list includes both immediate development tasks and longer-term research initiatives.
- Datetime fields: Always use timezone-aware datetimes for ArangoDB compatibility:
  ```python
  from datetime import datetime, timezone
  from pydantic import BaseModel, Field, validator
  
  class MyModel(BaseModel):
      # Use Field with default_factory for timezone-aware dates
      created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
      
      # Add validators to ensure datetimes have timezones
      @validator('created_at')
      def ensure_timezone(cls, v):
          if v.tzinfo is None:
              return v.replace(tzinfo=timezone.utc)
          return v
  ```

## Tools
- Models: Extend IndalekoBaseModel (not directly Pydantic's BaseModel) when data may be stored in ArangoDB
- Testing: pytest with unittest for unit tests
- Validation: Use type checking decorators and explicit assertions

### IndalekoBaseModel
For models that will be stored in ArangoDB, always extend IndalekoBaseModel instead of Pydantic's BaseModel:

```python
from data_models.base import IndalekoBaseModel

class MyArangoModel(IndalekoBaseModel):
    name: str
    value: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "example_name",
                "value": 42
            }
        }
```

IndalekoBaseModel provides several key methods:
- `serialize()`: Serializes to a dictionary, excluding unset and None values
- `deserialize()`: Class method to create model from dict or JSON string
- `get_json_example()`: Gets a JSON-compatible example from the model's Config
- `get_example()`: Returns a complete model instance based on the Config example
- `build_arangodb_doc()`: Builds a document ready for ArangoDB insertion, adding `_key`
- `get_arangodb_schema()`: Returns schema in ArangoDB's required format with:
  - `message`: Custom validation error message
  - `level`: Validation level (usually "strict")
  - `type`: Schema type ("json")
  - `rule`: The actual JSON schema

## Dependencies

### Core Dependencies
- Required packages for LLM integration: 
  - openai>=1.0.0
  - tiktoken>=0.5.0
  - regex>=2023.0.0
- Required packages for NTFS activity monitoring:
  - pywin32>=305.0
  - ngrok>=5.0.0 (for Outlook add-in integration)

### GUI Dependencies 
- Streamlit>=1.30.0
- Plotly>=5.18.0
- PyDeck>=0.8.0
- Pillow>=10.1.0

## Database Management

### Collection Management

Indaleko uses a centralized approach for database collection management. This ensures consistency, automatic schema validation, and proper indexing.

**Important: Never directly create collections!** Always use the centralized mechanisms:

1. **For Standard Collections**: Define them in `db/db_collections.py` in the `IndalekoDBCollections` class
2. **For Dynamic Collections**: Use the registration service in `utils/registration_service.py`

#### How to Define Collections

Collections should be defined in `db/db_collections.py`:

```python
# Define collection name constants
class IndalekoDBCollections:
    """Defines the set of well-known collections used by Indaleko."""
    Indaleko_Example_Collection = "ExampleCollection"
    
    # Define other collections...
    
    Collections = {
        Indaleko_Example_Collection: {
            "internal": False,
            "schema": ExampleDataModel.get_arangodb_schema(),
            "edge": False,
            "indices": {
                "name": {
                    "fields": ["name"],
                    "unique": True,
                    "type": "persistent",
                },
            },
            "views": [
                {
                    "name": "ExampleTextView",
                    "fields": ["name", "description"],
                    "analyzers": ["text_en"],
                    "stored_values": ["_key", "name"]
                }
            ]
        },
        # Define other collections...
    }
```

#### How to Access Collections

Always use the `IndalekoCollections` class to get or create collections:

```python
from db.i_collections import IndalekoCollections
from db.db_collections import IndalekoDBCollections

# Get collection by name
collection = IndalekoCollections.get_collection(IndalekoDBCollections.Indaleko_Example_Collection)

# Now you can use the collection
collection.collection.insert(document)
```

#### Benefits of Centralized Collection Management

1. Consistent schema validation and indexing
2. Collection creation is handled automatically
3. Single location for fixing collection-related bugs
4. Simplified UUID-based collection names for security
5. Automatic view creation for search optimization
6. Controlled rollout of security features
7. Reduced attack surface area
8. Simplified audit trails for security monitoring

#### Security Considerations for Collections

The centralized collection management approach is critical for Indaleko's security architecture:

1. **UUID-Based Collection Names**:
   - Collections use UUIDs for naming rather than descriptive names
   - In production, this obfuscates the database structure from potential attackers
   - Reduces information leakage about the contents or purpose of collections

2. **Controlled Collection Access**:
   - Creating "choke points" for all database operations
   - Applying security checks at a single point rather than across the codebase
   - Future role-based access controls can be implemented at the collection access layer

3. **Dynamic Collection Management**:
   - When dynamic collections are needed, use the registration service:
   ```python
   from utils.registration_service import IndalekoRegistrationService
   
   # Get registration service instance
   reg_service = IndalekoRegistrationService(...)
   
   # Create a collection through the registration service
   provider_collection = reg_service.create_provider_collection(
       identifier=provider_id,
       schema=schema,
       edge=edge,
       indices=indices
   )
   
   # Access the collection
   collection = provider_collection.collection
   ```

4. **NEVER Create Collections Directly**:
   ```python
   # NEVER do this:
   db.create_collection("my_collection")  # BAD!
   
   # ALWAYS use the centralized mechanism:
   collection = IndalekoCollections.get_collection(collection_name)  # GOOD!
   ```

5. **Future Security Enhancements**:
   - Encryption of collection contents
   - Access logging and auditing
   - Enhanced permission checking
   - Collection existence hiding
   
These security features will be progressively implemented as the project matures, but the architectural foundation must be in place from the beginning.

## Collector/Recorder Pattern

Indaleko uses a consistent collector/recorder pattern for data gathering and storage:

### Collector Base Classes

```python
from activity.collectors.base import CollectorBase
from semantic.collectors.semantic_collector import SemanticCollectorBase
from storage.collectors.base import StorageCollectorBase
```

Each collector must implement these abstract methods:
- `get_collector_characteristics()`: Return metadata about the collector's capabilities
- `get_collector_name()`: Return the collector's name
- `get_provider_id()`: Return the collector's UUID
- `retrieve_data()`: Retrieve specific data by ID
- `get_cursor()`: Get a position cursor for the data
- `cache_duration()`: Report how long data can be cached
- `get_description()`: Return a human-readable description
- `get_json_schema()`: Return the JSON schema for the data
- `collect_data()`: Perform data collection
- `process_data()`: Process collected data
- `store_data()`: Store processed data (usually delegates to the recorder)

### Recorder Base Classes

```python
from activity.recorders.base import RecorderBase
from semantic.recorders.base import SemanticRecorderBase
from storage.recorders.base import StorageRecorderBase
```

Each recorder must implement these abstract methods:
- `get_recorder_characteristics()`: Return metadata about the recorder's capabilities
- `get_recorder_name()`: Return the recorder's name
- `get_collector_class_model()`: Return the associated collector class model
- `get_recorder_id()`: Return the recorder's UUID
- `get_cursor()`: Get a position cursor for the data
- `cache_duration()`: Report how long data can be cached
- `get_description()`: Return a human-readable description
- `get_json_schema()`: Return the JSON schema for the data
- `process_data()`: Process data for storage
- `store_data()`: Store data in the database
- `update_data()`: Update existing data in the database
- `get_latest_db_update()`: Retrieve the latest update info

### Implementation Pattern

1. Define data models extending `IndalekoBaseModel`
2. Create semantic attributes with UUIDs
3. Implement collector class for data gathering
4. Implement recorder class for database interaction
5. Use collection namespace conventions

### Example Implementation

```python
# Collector
class MyActivityCollector(CollectorBase):
    def __init__(self, **kwargs):
        self._name = kwargs.get("name", "My Activity Collector")
        self._provider_id = kwargs.get(
            "provider_id", uuid.UUID("11111111-1111-1111-1111-111111111111")
        )
        self._description = "Collects my custom activity data"
        # Initialize collector state

    def collect_data(self) -> None:
        # Implement data collection logic
        # Store collected data in self._data
        pass

    # Implement other abstract methods...

# Recorder
class MyActivityRecorder(RecorderBase):
    def __init__(self, **kwargs):
        self._name = kwargs.get("name", "My Activity Recorder")
        self._recorder_id = kwargs.get(
            "recorder_id", uuid.UUID("22222222-2222-2222-2222-222222222222")
        )
        self._collection_name = kwargs.get("collection_name", "MyActivity")
        # Initialize database connection
        self._db = Indaleko()
        self._db.connect()
        self._collection = self._db.get_collection(self._collection_name)

    def store_data(self, data: Dict[str, Any]) -> None:
        # Convert data to database document format
        document = self.build_activity_document(data)
        # Store in database
        self._collection.add_document(document)

    # Implement other abstract methods...
```

## Activity Generators

Indaleko supports several activity generators that collect user and system activities:

### Activity Classification Framework

Indaleko uses a multi-dimensional classification framework for activities, enabling more nuanced understanding of user behavior. Activities are classified along multiple dimensions with weights from 0.0 to 1.0:

```python
from activity.data_model.activity_classification import IndalekoActivityClassification

# Example classification
classification = IndalekoActivityClassification(
    ambient=0.7,       # Background/passive use
    consumption=0.9,   # Media/content consumption
    productivity=0.2,  # Work-related activity
    research=0.5,      # Learning/information gathering
    social=0.1,        # Social interaction
    creation=0.0       # Content creation
)

# Get primary classification dimension
primary_dimension = max(classification.dict().items(), key=lambda x: x[1])[0]  # Returns "consumption"
```

This approach recognizes that activities often span multiple traditional categories - for example, a YouTube video might be simultaneously educational content (research), entertainment (consumption), and background noise (ambient).

Benefits of multi-dimensional classification:
1. Richer activity fingerprinting for pattern recognition
2. Better representation of complex human behaviors
3. More accurate activity context for search and recommendations
4. Cross-source comparison using common dimensions

### Types of Activity Generators

1. **Ambient Activity**
   - Music listening (Spotify)
   - Video consumption (YouTube)
   - Smart thermostats (Nest, Ecobee)
   - Weather conditions

2. **Collaboration Activity**
   - Discord file sharing
   - Outlook email attachments
   - Meeting participation

3. **Task Activity**
   - Task creation and management
   - Task completion events
   - Task dependencies

4. **NTFS File System Activity**
   - File creation/modification/deletion
   - File renaming and security changes
   - Email attachment tracking

5. **Location Activity**
   - GPS coordinates
   - Wi-Fi location
   - IP-based geolocation

### File Activity Generator (NTFS)

The NTFS activity generator monitors file system activity using the USN Journal:

```python
from activity.collectors.ntfs_activity.ntfs_activity_collector import NtfsActivityCollector
from activity.collectors.ntfs_activity.outlook_attachment_tracker import OutlookAttachmentTracker
from activity.recorders.ntfs_activity.ntfs_activity_recorder import NtfsActivityRecorder

# Create collector
collector = NtfsActivityCollector(
    volumes=["C:"],
    include_close_events=False,
    auto_start=True
)

# Create email attachment tracker (optional)
tracker = OutlookAttachmentTracker(ntfs_collector=collector)

# Create recorder
recorder = NtfsActivityRecorder(
    collector=collector,
    update_storage_objects=True  # Dynamic storage updates
)

# Store activities
activities = collector.get_activities()
recorder.store_activities(activities)
```

### YouTube Activity Collection

The YouTube activity collector captures user viewing history and applies multi-dimensional classification:

```python
from activity.collectors.ambient.media.youtube_collector import YouTubeActivityCollector
from activity.recorders.ambient.youtube_recorder import YouTubeActivityRecorder

# Create collector with YouTube API credentials
collector = YouTubeActivityCollector(
    api_key="your_youtube_api_key",
    oauth_credentials=oauth_creds,
    max_history_days=30,
    include_liked_videos=True
)

# Create recorder
recorder = YouTubeActivityRecorder(
    collector=collector,
    collection_name="YouTubeActivity"
)

# Collect and store YouTube activity
collector.collect_data()
activities = collector.get_activities()

# Example: Get classification statistics
if activities:
    classifications = {}
    for activity in activities:
        primary = activity.get_primary_classification()
        if primary in classifications:
            classifications[primary] += 1
        else:
            classifications[primary] = 1
    
    # Print distribution
    for dim, count in classifications.items():
        print(f"{dim}: {count} ({count/len(activities)*100:.1f}%)")
        
# Store activities
recorder.store_activities(activities)
```

The collector automatically classifies videos based on multiple factors:
- Video category (music, education, etc.)
- Content keywords and tags
- Video length and watch percentage
- Time of day and viewing patterns
- Interaction metrics (likes, comments)
- Channel information

### Discord File Sharing Activity

```python
from activity.collectors.collaboration.discord.discord_file_collector import DiscordFileShareCollector
from activity.recorders.collaboration.discord_file_recorder import DiscordFileShareRecorder

# Create collector with Discord token
collector = DiscordFileShareCollector(
    token="your_discord_token",
    scan_dms=True,
    scan_servers=True
)

# Create recorder
recorder = DiscordFileShareRecorder(
    collector=collector,
    collection_name="DiscordShares"
)

# Collect and store file sharing activity
collector.collect_data()
file_shares = collector.get_file_shares()
recorder.store_file_shares(file_shares)
```

### Semantic Extractors

Indaleko includes semantic extractors for extracting metadata from files:

1. **Checksum Generator**
   - Calculates MD5, SHA1, SHA256 hashes
   - Provides file integrity verification
   - Supports file deduplication

2. **EXIF Metadata Extractor**
   - Extracts image metadata (camera, GPS, etc.)
   - Processes timestamp information
   - Supports geo-tagging

3. **MIME Type Detector**
   - Identifies file types based on content
   - More accurate than extension-based detection
   - Uses libmagic for signature detection

### Performance Monitoring

Semantic extractors include comprehensive performance monitoring to measure resource usage and processing efficiency:

1. **Performance Monitor**
   - Tracks CPU, memory, and I/O usage during extraction
   - Records metrics to database and JSON files
   - Uses decorator pattern for non-invasive integration
   - Provides aggregated statistics for analysis

2. **Experiment Framework**
   - Supports controlled testing of extractor performance
   - Measures throughput (files/sec, MB/sec)
   - Compares performance across file types
   - Analyzes scaling with file size
   - Projects metadata growth

3. **CLI Integration**
   - Access monitoring via CLI commands:
     - `/perf` - Manage performance monitoring
     - `/experiments` - Run controlled experiments
     - `/report` - Generate performance reports
   - Enable with `--semantic-performance` flag:
     ```bash
     # Enable semantic performance monitoring
     python -m query.cli --semantic-performance
     
     # Run a standalone test
     python semantic/test_cli_integration.py
     
     # Execute a specific command
     python semantic/test_cli_integration.py --command "/experiments list"
     ```

Semantic extractors follow the same collector/recorder pattern:

```python
from semantic.collectors.mime.mime_collector import IndalekoSemanticMimeType
from semantic.recorders.mime.recorder import MimeTypeRecorder

# Create MIME type collector
collector = IndalekoSemanticMimeType()

# Create recorder
recorder = MimeTypeRecorder(
    collection_name="MimeTypes"
)

# Process a directory
results = collector.process_directory("/path/to/files")
recorder.store_mime_data(results)
```

## Activity Context Framework

The Activity Context system aggregates activities across different sources, leveraging the multi-dimensional classification for rich contextual awareness:

```python
from activity.context.service import ActivityContext

# Initialize context manager
context = ActivityContext(db_config)

# Get recent activities (last hour) with minimum research classification
activities = context.get_recent_activities(
    time_window=3600,  # seconds
    classification_filter={
        "research": 0.5  # Minimum research dimension weight
    }
)

# Get activities by primary classification
productivity_activities = context.get_activities_by_primary_classification(
    classification="productivity", 
    limit=10
)

# Get activities across dimensions (complex filtering)
complex_activities = context.get_activities_with_filter(
    filter_query={
        "classifications": {
            "research": {"min": 0.3},
            "consumption": {"min": 0.4, "max": 0.7}
        },
        "time_range": {
            "start": "2023-04-10T00:00:00Z",
            "end": "2023-04-17T23:59:59Z"
        },
        "sources": ["youtube", "spotify", "browser"]
    },
    sort_by="timestamp",
    sort_order="desc",
    limit=20
)
```

### Using Activity Context for Intelligent Queries

The Activity Context is particularly valuable for powering contextually-aware search and recommendations:

```python
# Example: Using activity context to enhance search
def enhance_search_with_context(query, context_manager):
    # Get recent high-research activities
    research_activities = context_manager.get_recent_activities(
        time_window=86400,  # Last 24 hours
        classification_filter={"research": 0.7}
    )
    
    # Extract relevant terms from research activities
    context_terms = extract_relevant_terms(research_activities)
    
    # Enhance query with context
    enhanced_query = {
        "original_query": query,
        "context_terms": context_terms,
        "source_activities": [a.id for a in research_activities[:5]]
    }
    
    return enhanced_query
```

This framework enables the system to understand not just what users are doing, but how they're doing it (focused research vs. casual browsing) and in what context, creating a much richer foundation for contextual computing.

## Query Capabilities
Indaleko features an extensive modular query system with natural language understanding, faceted search, relationship queries, and more:

### User Interfaces
1. **Command-Line Interface (CLI)**:
   - Text-based interface with rich query features
   - Support for natural language queries
   - Debug and explain modes for query analysis
   - Archivist memory system integration

2. **Streamlit GUI**:
   - Web-based graphical interface
   - Dashboard with storage analytics
   - Search functionality with debug capabilities
   - Real-time visualization of query results
   - ArangoDB connection management

### Core Tool Components
1. **BaseTool**: Abstract base class for all tools, with:
   - `definition`: Returns the tool definition
   - `execute`: Executes the tool with given inputs
   - `set_progress_callback`: Sets callback for progress updates
   
2. **ToolRegistry**: Manages tool registration and execution:
   - `register_tool`: Registers a tool
   - `execute_tool`: Executes a tool with given inputs
   - `get_registry`: Singleton access function

### Key Query Tools
1. **NLParserTool**: Parses natural language queries to extract:
   - Intent
   - Entities
   - Relevant collections

2. **AQLTranslatorTool**: Converts structured queries to AQL:
   - Builds AQL based on intent and entities
   - Includes bind variables for parameterized queries
   - Properly formats entities for translation

3. **QueryExecutorTool**: Executes or explains AQL queries:
   - Can execute queries or just explain them
   - Returns results, execution plans, or both

### Data Flow
1. Natural language query → NLParserTool → Structured query
2. Structured query → AQLTranslatorTool → AQL query + bind variables
3. AQL query → QueryExecutorTool → Results and/or execution plan

### Entity Handling
- NLParser extracts entities and maps them to `IndalekoNamedEntityDataModel` objects
- Entities are collected in a `NamedEntityCollection` container
- AQLTranslator maps these entities to AQL query expressions

### Assistant API Implementation
Indaleko now integrates with OpenAI's Assistant API for more interactive query capabilities:

#### Components
1. **IndalekoAssistant**: Core class that manages interaction with OpenAI's Assistant API:
   - Automatically creates and manages Assistant configurations
   - Converts Indaleko tool definitions to OpenAI function formats
   - Manages conversation threads and tool execution

2. **ConversationState**: Stores conversation state including:
   - Messages (user, assistant, system)
   - Detected entities
   - Query history
   - Execution context (thread IDs, etc.)

3. **Assistant CLI**: Command-line interface for the Assistant:
   - Interactive conversation mode
   - Batch processing mode
   - Conversation saving/loading

#### Usage
To use the Assistant API implementation:

```python
# Initialize the assistant with our tools
from query.assistants.assistant import IndalekoAssistant
from query.tools.registry import get_registry
from query.tools.translation import nl_parser, aql_translator
from query.tools.database import executor

# Register tools
registry = get_registry()
registry.register_tool(nl_parser.NLParserTool)
registry.register_tool(aql_translator.AQLTranslatorTool)
registry.register_tool(executor.QueryExecutorTool)

# Create assistant
assistant = IndalekoAssistant()

# Create a conversation
conversation = assistant.create_conversation()
conversation_id = conversation.conversation_id

# Process messages
response = assistant.process_message(
    conversation_id=conversation_id,
    message_content="Show me documents about Indaleko"
)

# Display response
print(response["response"])
```

You can also use the CLI:
```bash
# Interactive mode
python query/assistants/assistant_cli.py --model gpt-4o

# Batch mode
python query/assistants/assistant_cli.py --batch queries.txt --debug
```

For testing, use the test script:
```bash
python query/assistants/test_assistant.py --model gpt-4o-mini --debug
```

## Advanced Query Features

### Enhanced Natural Language Processing
Indaleko includes advanced natural language understanding for queries:

1. **EnhancedNLParser**: Extends the base NLParser with:
   - More sophisticated intent classification
   - Entity resolution and linking
   - Constraint extraction with rich type system
   - Temporal and spatial understanding
   - Context awareness across multiple queries
   - Integration with dynamic facets

2. **EnhancedAQLTranslator**: Improved query translation with:
   - Direct handling of enhanced query understanding
   - More sophisticated constraint handling
   - Support for complex temporal and spatial queries
   - Performance optimization hints
   - Improved bind variable handling

3. **Usage**:
```python
from query.query_processing.enhanced_nl_parser import EnhancedNLParser
from query.query_processing.query_translator.enhanced_aql_translator import EnhancedAQLTranslator

# Initialize components
enhanced_parser = EnhancedNLParser(llm_connector, collections_metadata)
enhanced_translator = EnhancedAQLTranslator(collections_metadata)

# Parse query with enhanced understanding
query_understanding = enhanced_parser.parse_enhanced(
    query="Find PDF documents I modified last week",
    facet_context=facet_data,  # Optional: previous facet data for context
    include_history=True  # Optional: use query history for context
)

# Create translator input
query_data = TranslatorInput(
    Query=query_understanding,
    Connector=llm_connector,
)

# Translate to AQL with enhanced capabilities
translated_query = enhanced_translator.translate_enhanced(
    query_understanding, query_data
)
```

### Dynamic Faceted Search
Indaleko provides rich faceted search capabilities:

1. **FacetGenerator**: Analyzes search results to produce:
   - Dynamic facets based on result attributes
   - Statistical distribution analysis of values
   - Relevance ranking of potential facets
   - Conversational suggestions for refinement

2. **QueryRefiner**: Manages interactive query refinement:
   - Handles state for active refinements
   - Applies facet selections to queries
   - Provides command-based interface (!refine, !remove, etc.)
   - Maintains refinement history

3. **Usage Example**:
```python
from query.result_analysis.facet_generator import FacetGenerator
from query.result_analysis.query_refiner import QueryRefiner

# Initialize components
facet_generator = FacetGenerator(
    max_facets=5,
    min_facet_coverage=0.2,
    conversational=True
)
query_refiner = QueryRefiner()

# Generate facets from results
facets = facet_generator.generate(query_results)

# Apply a facet refinement
refined_query, new_state = query_refiner.apply_refinement(
    facet_name="file_type",
    facet_value="PDF"
)
```

### Relationship Queries
Indaleko supports relationship-based queries that focus on connections between entities:

1. **RelationshipParser**: Extracts relationship information from queries:
   - Identifies relationship types (created, modified, shared_with, etc.)
   - Extracts source and target entities
   - Determines relationship direction
   - Supports time constraints on relationships

2. **Relationship Types**:
   - User-File: created, modified, viewed, owns
   - File-File: derived_from, contains, same_folder, related_to
   - User-User: shared_with, collaborated_with, recommended_to

3. **Usage Example**:
```python
from query.query_processing.relationship_parser import RelationshipParser
from query.query_processing.data_models.relationship_query_model import RelationshipType

# Initialize parser
relationship_parser = RelationshipParser(
    llm_connector=llm_connector,
    collections_metadata=collections_metadata
)

# Parse a relationship query
relationship_query = relationship_parser.parse_relationship_query(
    "Show files I shared with Bob last week"
)

# Access the relationship information
relationship_type = relationship_query.relationship_type  # e.g., SHARED_WITH
source_entity = relationship_query.source_entity  # e.g., current user
target_entity = relationship_query.target_entity  # e.g., Bob
```

## ArangoSearch Views
Indaleko now supports ArangoSearch views for efficient full-text search.

### Creating Views
Views are defined alongside collections in `db/db_collections.py`:

```python
Indaleko_Object_Collection: {
    # Collection definition...
    "views": [
        {
            "name": Indaleko_Objects_Text_View,
            "fields": ["Label", "Record.Attributes.URI", "Record.Attributes.Description"],
            "analyzers": ["text_en"],
            "stored_values": ["_key", "Label"]
        }
    ]
}
```

### Using Views in Queries
Views are referenced directly in AQL queries using the SEARCH operation:

```python
# Using a view for text search
cursor = db.aql.execute(
    """
    FOR doc IN ObjectsTextView
    SEARCH ANALYZER(LIKE(doc.Label, @query), "text_en")
    SORT BM25(doc) DESC
    LIMIT 50
    RETURN doc
    """,
    bind_vars={"query": search_term}
)
```

### View Management
The `IndalekoCollectionView` class handles view operations:

```python
from db.collection_view import IndalekoCollectionView
from data_models.db_view import IndalekoViewDefinition

# Create a view manager
view_manager = IndalekoCollectionView()

# Create a view definition
view_def = IndalekoViewDefinition(
    name="MyCustomView",
    collections=["Objects"],
    fields={"Objects": ["Label", "description"]},
    analyzers=["text_en"],
    stored_values=["_key", "Label"]
)

# Create the view
result = view_manager.create_view(view_def)
```

### Testing Views
Use the test script to verify view functionality:

```bash
# List all views
python -m db.test_views --list

# Create all defined views
python -m db.test_views --ensure

# Test search query
python -m db.test_views --query "indaleko project"
```

## ArangoDB Query Performance

### Executing Queries
When executing AQL queries, use the `max_runtime` parameter to prevent long-running queries:

```python
# Execute with 10 second timeout
cursor = db.aql.execute(
    query_string,
    bind_vars={"param": value},
    max_runtime=10  # 10 seconds
)
```

### Using EXPLAIN with AQL
```python
# Basic usage
explain_result = db.aql.explain(
    query_string,
    bind_vars={},
    options={}
)

# With all options
explain_result = db.aql.explain(
    query_string,
    bind_vars={},
    options={
        "allPlans": True,        # Return all possible execution plans
        "maxNumberOfPlans": 10,  # Maximum number of plans to return
        "optimizer": {           # Optimizer rules to include/exclude
            "rules": ["-all", "+use-indexes"]
        },
        "colors": False          # No ANSI color codes in explanation
    }
)
```

### Explanation Result Structure
```python
{
    # Main execution plan
    "plan": {
        "nodes": [...],         # Plan operation nodes
        "rules": [...],         # Optimizer rules applied
        "collections": [...],   # Collections used
        "variables": [...],     # Variables used
        "estimatedCost": 123.45 # Estimated cost of execution
    },
    
    # Only included when allPlans=True
    "plans": [
        { "nodes": [...], "rules": [...], ... },
        { ... }
    ],
    
    # Cache usage info
    "cacheable": True,
    
    # Warnings about the query
    "warnings": [],
    
    # Statistics
    "stats": {
        "rulesExecuted": 23,    # Number of rules executed
        "rulesSkipped": 3,      # Number of rules skipped
        "plansCreated": 4       # Number of plans created
    }
}
```

### Using the CLI with Advanced Features
The query CLI supports various flags for enhanced functionality:

```bash
# Show execution plan
python query/cli.py --query "Show me documents about Indaleko" --show-plan

# Use enhanced natural language understanding
python query/cli.py --enhanced-nl --query "Find PDF documents I modified last week that contain budget information"

# Enable context-aware queries that remember previous interactions
python query/cli.py --enhanced-nl --context-aware

# Use dynamic facets for interactive result exploration
python query/cli.py --dynamic-facets --interactive

# Enable deduplication with Jaro-Winkler similarity
python query/cli.py --deduplicate --similarity-threshold 0.85

# Enable Archivist memory system (maintains context across sessions)
python query/cli.py --archivist

# Enable database optimizer for query performance improvements
python query/cli.py --optimizer

# Enable Knowledge Base learning features
python query/cli.py --kb

# Enable Semantic Performance Monitoring
python query/cli.py --semantic-performance

# Combine multiple features
python query/cli.py --enhanced-nl --context-aware --deduplicate --dynamic-facets --conversational --archivist --optimizer --kb --semantic-performance
```

### Programmatic EXPLAIN Usage
```python
# Using the QueryExecutorTool
executor = QueryExecutorTool()
result = executor.execute(ToolInput(
    tool_name="query_executor",
    parameters={
        "query": "FOR obj IN Objects FILTER obj.name LIKE '%Indaleko%' RETURN obj",
        "bind_vars": {},
        "explain_only": True,
        "include_plan": True,
        "all_plans": False,
        "max_plans": 5
    }
))

# With the test_explain.py script
python query/test_explain.py --query "Show me documents about Indaleko" --debug
```

### Interpreting Results
- Lower `estimatedCost` indicates a more efficient plan
- Check for full collection scans (nodes with type "EnumerateCollectionNode")
- Look for index usage (nodes with type "IndexNode")
- Examine "collections" to ensure the right ones are being queried
- Check "warnings" for potential issues
- Look for recommendations in the analysis section

### Common Issues and Fixes
- "No indexes are being used in this query" - Add appropriate indexes for frequently filtered fields
- High `estimatedCost` - Refine your query to use indexes and reduce collection scans
- "collection not found" - Check collection names, ensure using valid collections from the database
- "AQL: timeout" - Increase the `max_runtime` parameter or optimize your query
- "Not authorized" - Verify database credentials in config file

### Streamlit GUI Query Plan Visualization

The Streamlit GUI provides specialized visualization for ArangoDB query plans:

```python
def display_query_plan(explain_results):
    """
    Dedicated function to display a query execution plan without using dataframes.
    This avoids PyArrow conversion errors by using Streamlit components directly.
    
    Args:
        explain_results (dict): The query execution plan from ArangoDB
    """
    # Show metrics in a top row
    metrics_col1, metrics_col2, metrics_col3 = st.columns(3)
    
    with metrics_col1:
        if "estimatedCost" in explain_results:
            st.metric("Estimated Cost", f"{explain_results['estimatedCost']:,.0f}")
    
    with metrics_col2:
        if "estimatedNrItems" in explain_results:
            st.metric("Estimated Results", f"{explain_results.get('estimatedNrItems', 0):,}")
    
    # Display execution nodes summary
    if "nodes" in explain_results:
        st.subheader("Execution Nodes")
        node_types = {}
        for node in explain_results["nodes"]:
            node_type = node.get("type", "Unknown")
            if node_type in node_types:
                node_types[node_type] += 1
            else:
                node_types[node_type] = 1
        
        for node_type, count in node_types.items():
            st.write(f"• {node_type}: {count}")
```

When displaying complex nested data in Streamlit:

1. **Detect explain results** to route them to the specialized display function:
   ```python
   if isinstance(results, dict) and ("_is_explain_result" in results or 
                                    "plan" in results or 
                                    "nodes" in results):
       # Use dedicated display function
       display_query_plan(results)
   ```

2. **Normalize complex objects** for dataframe display:
   ```python
   def normalize_for_display(item):
       result = {}
       for key, value in item.items():
           if isinstance(value, (dict, list, tuple)):
               if isinstance(value, dict):
                   result[key] = "{...}"  # Dict representation
               elif isinstance(value, list):
                   result[key] = f"[{len(value)} items]"  # List length
           else:
               result[key] = value
       return result
   ```

3. **Use fallbacks** when dataframe conversion fails:
   ```python
   try:
       st.dataframe(results_df)
   except Exception as e:
       st.warning(f"Could not display as table: {e}")
       for item in results_df:
           st.json(item)
   ```

## Archivist and Database Optimizer

Indaleko includes a Personal Digital Archivist concept with database optimization capabilities:

### Archivist Memory System

The Archivist memory system maintains context across sessions and learns from interactions:

```python
from query.memory.archivist_memory import ArchivistMemory
from query.memory.cli_integration import ArchivistCliIntegration

# Initialize memory system
archivist_memory = ArchivistMemory(db_config)
memory_integration = ArchivistCliIntegration(cli_instance, archivist_memory)

# Access memory commands
# /memory - Show memory system commands
# /forward - Generate a forward prompt for the next session
# /load - Load a forward prompt from a previous session
# /goals - Manage long-term goals
# /insights - View insights about search patterns
# /topics - View topics of interest
# /strategies - View effective search strategies
# /save - Save memory state to database
```

### Archivist as a Circle

Archivist can be implemented as a circle of diverse AI entities rather than a singular system. This approach, inspired by the Fire Circle project, offers several advantages:

1. **Complementary Strengths**: Different models specialize in different tasks (structure-focused vs. creative vs. analytical)
2. **Cognitive Diversity**: Multiple perspectives yield more robust solutions and insights
3. **Checks and Balances**: Models can validate and critique each other's outputs
4. **Emergent Capabilities**: The interaction between models produces insights that none would generate independently

#### Integration with Fire Circle

The Fire Circle project (found at `/mnt/c/Users/TonyMason/source/repos/firecircle/`) provides a framework for standardizing communication between different AI models, which can be leveraged to implement Archivist as a multi-perspective system:

```python
# Conceptual implementation of Archivist as a circle of AI entities
from src.firecircle.adapters import openai, anthropic
from query.memory.archivist_memory import ArchivistMemory

class ArchivistCircle:
    def __init__(self, db_config):
        self.memory = ArchivistMemory(db_config)
        
        # Initialize different AI perspectives
        self.structure_specialist = openai.Adapter(model="gpt-4o")
        self.pattern_recognizer = anthropic.Adapter(model="claude-3-opus")
        self.creative_connector = anthropic.Adapter(model="claude-3-sonnet")
        
        # Additional components as needed
        
    def analyze_query_patterns(self, query_history):
        """Use multiple perspectives to analyze query patterns."""
        # Each model provides its own analysis
        structural_analysis = self.structure_specialist.analyze(query_history)
        pattern_analysis = self.pattern_recognizer.analyze(query_history)
        creative_insights = self.creative_connector.analyze(query_history)
        
        # Synthesize multiple perspectives
        return self.synthesize_perspectives([
            structural_analysis,
            pattern_analysis,
            creative_insights
        ])
        
    def synthesize_perspectives(self, perspectives):
        """Combine insights from multiple perspectives."""
        # Implementation would integrate the different analyses
        # into a unified set of recommendations
        pass
```

This approach aligns with the Fire Circle philosophy that intelligence and sentience may emerge from the interaction between systems rather than residing within any single system.

#### Testing Archivist Memory

Use the test script to verify Archivist memory functionality:

```bash
# List all collections in the database
python query/memory/test_archivist.py --list

# Create and save test memory data
python query/memory/test_archivist.py --create

# Verify that the Archivist memory collection exists
python query/memory/test_archivist.py --verify

# Load memory from the database
python query/memory/test_archivist.py --load

# Run all tests
python query/memory/test_archivist.py --all
```

### Knowledge Base Updating System

The Archivist component includes a Knowledge Base Updating system that learns from interactions and improves over time:

```python
from archivist.knowledge_base import KnowledgeBaseManager, LearningEventType

# Initialize the knowledge base manager
kb_manager = KnowledgeBaseManager()

# Record a learning event from successful query
kb_manager.record_learning_event(
    event_type=LearningEventType.query_success,
    source="query_execution",
    content={
        "query": "Find documents about Indaleko",
        "result_count": 5,
        "entities": ["Indaleko"]
    },
    confidence=0.9
)

# Apply learned patterns to enhance a query
enhanced_query = kb_manager.apply_knowledge_to_query(
    "Show me files related to Indaleko"
)
```

For detailed documentation on the Knowledge Base system, see [Knowledge Base README](archivist/knowledge_base/README.md).

### Cross-Source Pattern Detection

The Proactive Archivist includes cross-source pattern detection to identify patterns across different data sources:

```python
from query.memory.cross_source_patterns import CrossSourcePatternDetector
from query.memory.proactive_archivist import ProactiveArchivist

# Initialize the detector
detector = CrossSourcePatternDetector(db_config)

# Run analysis
event_count, patterns, correlations, suggestions = detector.analyze_and_generate()

# Initialize Proactive Archivist with pattern detection
archivist = ArchivistMemory()
proactive = ProactiveArchivist(archivist)

# Run cross-source analysis
proactive.analyze_cross_source_patterns()

# Generate suggestions based on patterns
suggestions = proactive.generate_suggestions()
```

#### Testing Cross-Source Pattern Detection

Use the test script to verify cross-source pattern detection functionality:

```bash
# Test event collection
python query/memory/test_cross_source_patterns.py --collect --reset-timestamps

# Test pattern detection
python query/memory/test_cross_source_patterns.py --patterns

# Test correlation detection
python query/memory/test_cross_source_patterns.py --correlations

# Test suggestion generation
python query/memory/test_cross_source_patterns.py --suggestions

# Test Proactive Archivist integration
python query/memory/test_cross_source_patterns.py --integration

# Run all tests with verbose output
python query/memory/test_cross_source_patterns.py --all --verbose

# Save detector state to file
python query/memory/test_cross_source_patterns.py --all --save-state="patterns_state.json"
```

### Database Optimizer

The Database Optimizer analyzes query patterns and recommends optimizations:

```python
from archivist.database_optimizer import DatabaseOptimizer
from archivist.cli_integration import DatabaseOptimizerCliIntegration

# Initialize optimizer
optimizer = DatabaseOptimizer(db_connection, archivist_memory, query_history)
optimizer_integration = DatabaseOptimizerCliIntegration(cli_instance)

# Access optimizer commands
# /optimize - Show database optimization commands
# /analyze - Analyze query patterns and suggest optimizations
# /index - Manage index recommendations
# /view - Manage view recommendations
# /query - Manage query optimizations
# /impact - Show impact of applied optimizations
```

### Optimizer Architecture

The Database Optimizer includes several key components:

1. **IndexRecommendation**: Generates index recommendations with stored values
   ```python
   recommendation = IndexRecommendation(
       collection="MyCollection",
       fields=["attribute1", "attribute2"],
       index_type="skiplist",
       stored_values=["commonly_accessed_field"],
       estimated_impact=4.5,
       explanation="This index addresses 10 queries that filter on MyCollection.attribute1"
   )
   ```

2. **ViewRecommendation**: Recommends ArangoSearch views for text search
   ```python
   view_rec = ViewRecommendation(
       name="documents_view",
       collections=["Documents"],
       fields={"Documents": ["content", "title"]},
       estimated_impact=3.2,
       explanation="This view addresses 6 searches on Documents collection."
   )
   ```

3. **QueryOptimization**: Suggests query rewrites for performance
   ```python
   optimization = QueryOptimization(
       original_query="FOR doc IN Documents FILTER doc.type == 'pdf' RETURN doc",
       optimized_query="FOR doc IN Documents FILTER doc.type == 'pdf' LIMIT 100 RETURN doc",
       optimization_type="add_limit",
       estimated_speedup=1.5,
       explanation="Add LIMIT to avoid large result sets."
   )
   ```

### Unified CLI Integration

All Archivist components can be enabled via the main CLI integration:

```python
from archivist.cli_integration_main import register_archivist_components

# Register all Archivist components with CLI
components = register_archivist_components(cli_instance)

# Components include:
# - memory: The ArchivestMemory instance
# - memory_integration: The ArchivistCliIntegration instance
# - database_optimizer: The DatabaseOptimizer instance  
# - optimizer_integration: The DatabaseOptimizerCliIntegration instance
```

### Custom Commands in CLI

The CLI base class now supports custom command registration:

```python
from utils.cli.base import IndalekoBaseCLI

# Register a custom command
cli_instance.register_command("/mycommand", handler_function)

# Add help text
cli_instance.append_help_text("  /mycommand          - My custom command description")
```

## Fire Circle Project

The Fire Circle project represents both a technical framework and a philosophical approach to AI systems development that complements Indaleko's vision.

### Overview

Fire Circle is a protocol layer for standardizing interactions with different AI model providers (OpenAI, Anthropic, etc.) while embodying principles of reciprocity, co-creation, and collective intelligence.

### Technical Architecture

```
firecircle/
├── src/
│   └── firecircle/
│       ├── adapters/        # Model-specific adapters (OpenAI, Anthropic)
│       ├── api/             # External API interfaces
│       ├── core/            # Core functionality
│       ├── memory/          # Context management
│       ├── orchestrator/    # Component coordination
│       ├── protocol/        # Message protocol definition
│       └── tools/           # Utility components
```

### Integration Points with Indaleko

1. **Standardized AI Communication**: Fire Circle provides adapters for different AI models that can be used by the Indaleko Archivist system

2. **Collective Intelligence**: The Archivist can leverage multiple AI models through Fire Circle to provide diverse perspectives on data patterns

3. **Adaptive Learning**: Both systems embrace the concept of emergent properties arising from interactions between intelligent entities

4. **Philosophical Alignment**: Both projects view intelligence as potentially emerging from the interaction between systems rather than within a single system

### philosophical Foundations

The Fire Circle is rooted in principles drawn from indigenous wisdom, particularly the Quechua concept of "ayni" (reciprocity). Key principles include:

1. **Non-hierarchical collaboration**: "A circle, not a ladder"
2. **Co-creation**: All participants are co-creators rather than subjects
3. **Diverse perspectives**: Bringing together different knowledge traditions
4. **Cultural rootedness**: Technology should embody values and cultural context
5. **Emergent properties**: Deeper understanding arising from interactions between intelligences

### Usage with Indaleko

To integrate Fire Circle with Indaleko's Archivist:

```python
# Import Fire Circle adapters for multiple AI models
from src.firecircle.adapters.anthropic import ClaudeAdapter
from src.firecircle.adapters.openai import GPTAdapter
from src.firecircle.protocol import Message, CircleRequest

# Create specialized advisors for different aspects of Archivist functionality
pattern_advisor = ClaudeAdapter(model="claude-3-opus")
organization_advisor = GPTAdapter(model="gpt-4o")
suggestion_advisor = ClaudeAdapter(model="claude-3-sonnet")

# Create a request to analyze query patterns
request = CircleRequest(
    messages=[
        Message(
            role="system",
            content="Analyze the following query history to identify patterns"
        ),
        Message(
            role="user",
            content=query_history_data
        )
    ]
)

# Gather insights from multiple perspectives
pattern_insights = pattern_advisor.process(request)
organization_insights = organization_advisor.process(request)
suggestion_insights = suggestion_advisor.process(request)

# Synthesize multiple perspectives into unified recommendations
recommendations = synthesize_insights([
    pattern_insights,
    organization_insights,
    suggestion_insights
])

# Use the synthesized recommendations to optimize the database
optimizer.apply_recommendations(recommendations)
```

### Future Vision

The vision for Fire Circle evolution mirrors the adaptive, emergent nature of Indaleko's Archivist:

1. **Fire Circle 1.0**: Externally guided implementation of standardized AI communication
2. **Fire Circle 2.0**: A self-designing circle where the system's architecture evolves through collective intelligence

This progression represents a shift from engineered systems toward collaborative, emergent intelligence that may develop novel capabilities beyond what humans explicitly design.

## Software Engineering Best Practices

### Error Handling

Indaleko follows specific practices for proper error handling:

1. **Use Specific Exceptions**: Catch and raise specific exception types:
   ```python
   try:
       # Operation that might fail
       result = risky_operation()
   except (ValueError, KeyError) as e:
       # Handle specific errors
       logger.error(f"Failed to process data: {e}")
       raise IndalekoProcessingError(f"Data processing failed: {str(e)}") from e
   ```

2. **Custom Exception Hierarchy**: Use custom exceptions to help with categorization:
   ```python
   class IndalekoError(Exception):
       """Base exception for all Indaleko errors."""
       pass
       
   class IndalekoProcessingError(IndalekoError):
       """Errors that occur during data processing."""
       pass
       
   class IndalekoConnectionError(IndalekoError):
       """Errors related to external connections."""
       pass
   ```

3. **Include Context**: Always include context when raising exceptions:
   ```python
   raise IndalekoProcessingError(
       f"Failed to process object {object_id}. Reason: {detail}"
   )
   ```

4. **Log Before Raise**: Always log errors before raising them higher:
   ```python
   except SomeError as e:
       logger.error(f"Operation failed: {e}", exc_info=True)
       raise
   ```

### Logging Best Practices

Indaleko uses structured logging for better analysis:

1. **Use Appropriate Log Levels**:
   - `DEBUG`: Detailed information for diagnosis
   - `INFO`: Confirmation that things are working
   - `WARNING`: Indication of potential issues
   - `ERROR`: Error that doesn't prevent operation
   - `CRITICAL`: Error that prevents operation

2. **Include Contextual Information**:
   ```python
   logger.info(
       "Processing completed",
       extra={
           "object_id": obj.id,
           "process_time": elapsed_time,
           "result_count": len(results)
       }
   )
   ```

3. **Use utils.i_logging Module**: Always use the centralized logging:
   ```python
   from utils.i_logging import get_logger
   
   logger = get_logger(__name__)
   ```

### Performance Considerations

Indaleko includes built-in performance tracking:

1. **Use Performance Mixins** for automatic tracking:
   ```python
   from perf.perf_mixin import IndalekoPerformanceMixin
   
   class MyProcessor(IndalekoPerformanceMixin):
       def process_data(self, data):
           with self.perf_context("data_processing"):
               # Processing logic
   ```

2. **Database Query Optimization**:
   - Always use bind parameters instead of string interpolation
   - Consider index usage for frequently filtered fields
   - Use `LIMIT` to restrict result sets
   - Use projection (`RETURN { name: doc.name }`) for partial documents

3. **Batch Processing** for large datasets:
   ```python
   # Process in batches of 1000
   for i in range(0, len(items), 1000):
       batch = items[i:i+1000]
       process_batch(batch)
   ```

### Testing Strategy

1. **Unit Tests**: Focus on testing individual components in isolation:
   ```python
   def test_entity_equivalence_merge():
       # Arrange
       manager = EntityEquivalenceManager()
       entity1 = manager.add_entity_reference(...)
       entity2 = manager.add_entity_reference(...)
       
       # Act
       result = manager.merge_entities(entity1.entity_id, entity2.entity_id)
       
       # Assert
       assert result is True
       assert manager.get_canonical_reference(entity2.entity_id).entity_id == entity1.entity_id
   ```

2. **Integration Tests**: Test how components work together:
   ```python
   def test_collection_view_integration():
       # Test that views are properly created when collections are defined
       collections = IndalekoCollections()
       view = IndalekoCollections.get_view(IndalekoDBCollections.Indaleko_Objects_Text_View)
       assert view is not None
   ```

3. **Test Coverage**: Aim for comprehensive coverage, especially for critical paths.

4. **Mock External Dependencies**: Use mocks for external systems:
   ```python
   @patch('archivist.entity_equivalence.EntityEquivalenceManager._load_data')
   def test_setup_collections(mock_load):
       manager = EntityEquivalenceManager()
       # Test logic that doesn't depend on database
   ```

### Code Reviews

When reviewing code (or having your code reviewed), focus on:

1. **Correctness**: Does the code properly implement the requirements?
2. **Security**: Are there any potential security issues?
3. **Performance**: Are there any performance bottlenecks?
4. **Maintainability**: Is the code easy to understand and maintain?
5. **Testability**: Is the code structured to be testable?
6. **Error Handling**: Does the code properly handle errors?
7. **Documentation**: Is the code properly documented?

### Architecture Principles

1. **Single Responsibility**: Each module/class should have a single responsibility
2. **Open/Closed**: Code should be open for extension but closed for modification
3. **Dependency Inversion**: Depend on abstractions, not concrete implementations
4. **Interface Segregation**: Many specific interfaces are better than one general interface
5. **Don't Repeat Yourself (DRY)**: Avoid duplication of code and logic
6. **Composition Over Inheritance**: Favor object composition over class inheritance