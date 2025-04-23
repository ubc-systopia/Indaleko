# Tony's Development Guide

## Project Overview

### PhD Thesis: The Unified Personal Index (UPI)
This PhD research explores the concept of a Unified Personal Index (UPI) that addresses challenges in personal data management across diverse platforms and sources. The thesis:
- Introduces a new paradigm shifting from "searching" to "finding" based on human memory patterns
- Proposes UPI as a framework for integrating heterogeneous metadata (storage, semantic, activity context)
- Focuses on human-centric design principles for personal data retrieval
- Includes detailed evaluation of retrieval precision, recall, and system performance
- Demonstrates benefits of activity context integration for improving data retrieval

The research is structured around integrating cross-platform metadata, preserving privacy, incorporating human activity context, and creating a extensible architecture that works at personal computing scale.

### Indaleko
Indaleko is the prototype implementation of the UPI concept from the PhD thesis. It's an advanced data management system with components for:
- Activity collection and recording (file system, cloud storage, collaboration tools)
- Semantic metadata extraction
- Natural language querying
- Cross-source pattern detection
- Knowledge base management

The architecture follows a collector/recorder pattern with cognitive memory tiers and implements a biomimetic approach to data management.

#### Indaleko Architectural Details

##### Database Design
- **Development Database**: A development ArangoDB instance is available and should be used for testing
- **Mock Data Policy**: Only use mock data when real database testing is not viable
- **Collection Management**: Central collection definitions in `db/db_collections.py`
- **Security Model**:
  - Production design uses UUID collection names instead of descriptive names
  - UUIDs will be generated during installation/setup
  - UUID-to-name mapping stored in user-controlled location
  - Allows secure storage in external databases with reduced information exposure
- **Database Connection**: Implemented as a singleton object requiring no additional setup
- **Collection Creation Rule**: Never call `create_collection` directly
  - Use static definitions in `db/db_collections.py`
  - Or use dynamic registration services (for semantic metadata or activity data providers)

##### Collector/Recorder Pattern Implementation
- **Collector Responsibilities**:
  - Gather data from sources
  - Store as JSON records (file or memory)
  - Never interact with database directly
- **Recorder Responsibilities**:
  - Preserve collector data using standard compression and UUENCODE
  - Extract and normalize elements of interest
  - Use UUID labels where semantic meaning is separated from identifiers
  - Generate JSON records for ArangoDB insertion
- **Data Flow Options**:
  - Direct insertion (common for activity and semantic providers)
  - Indirect insertion via files (common for storage data due to size)
  - Bulk loading via `arangoimport` or `bulk_import` function

##### Command Line Interface Standard
- **CLI Framework**: Common CLI model demonstrated in storage collectors/recorders
  - Example: `storage/collectors/local/linux/collector.py`
  - Example: `storage/recorders/local/linux/recorder.py`
- **Standard Features**:
  - Log file location configuration
  - Input/output file specification
  - Debugging options
  - Performance data collection (database or file storage)
- **Extension**: Supports custom switches while maintaining consistent structure

##### Cross-Platform Development Guidelines
- **Universal Help Command**: All scripts must work with `-help` flag on all platforms
  - Ensures cross-platform development efficiency
  - Import failures should not prevent help text display
- **Platform-Specific Imports**: Handle conditionally after CLI parsing
  - Example: `win32` libraries should be imported optionally
  - Platform verification after command line parsing: "This script can only be used on Windows"
- **Error Handling**:
  - Do NOT mask import errors for non-platform-specific packages
  - Do NOT use try/except around imports (except platform-specific ones)
  - Do NOT create dummy versions of packages
  - These practices hide environment problems and complicate debugging
- **Code Quality**:
  - Do NOT disable Ruff warnings without explicit approval
  - If you believe a warning should be disabled, request review first

### Fire Circle
Fire Circle is a protocol and system for facilitating meaningful dialogue between multiple AI models in a structured, reciprocal environment. Inspired by indigenous wisdom concepts (particularly "ayni" - reciprocity), it's designed around:
- Creating a non-hierarchical communication protocol between diverse AI models
- Implementing a structured dialogue system based on turn-taking and consensus
- Building memory and context systems that preserve conversational history
- Developing visualization tools for conversation topology and knowledge emergence

Key technical components include:
- **Message Protocol**: A standardized format for inter-model communication
- **Adapter Layer**: Unified adapters for different AI services (OpenAI, Anthropic, etc.)
- **Orchestrator**: Manages conversation flow, turn-taking, and state transitions
- **Memory Store**: Persists dialogue history with semantic retrieval capabilities
- **Tool Integration**: Framework for AI models to interact with external systems

This project is tangential to the UPI research but reflects a similar philosophical approach to emergent intelligence through the interaction of multiple systems rather than within a single system.

## Coding Standards

### Style Guidelines
- **Imports**: standard library → third-party → local (with blank lines between)
- **Types**: Use type hints for all functions and variable declarations
- **Formatting**: 4 spaces, ~100 char line length, docstrings with triple quotes
- **Naming**: CamelCase for classes, snake_case for functions/vars, UPPER_CASE for constants
- **Interfaces**: Prefix with 'I' (IObject, IRelationship)
- **Error Handling**: Specific exceptions with descriptive messages
- **Documentation**: All modules, classes and methods need docstrings (Args/Returns sections)
- **Module Organization**: Copyright header, imports, constants, classes, functions, main

### Data Model Standards
- Extend `IndalekoBaseModel` (not directly Pydantic's BaseModel) when data may be stored in ArangoDB
- Use timezone-aware datetimes for ArangoDB compatibility
- Use the `model_dump()` method from Pydantic v2 (not deprecated `dict()`)

## Key Architectural Patterns

### Collector/Recorder Pattern
- **Collectors**: Only collect raw data, never normalize or write to database
- **Recorders**: Process/normalize data, write to database, implement queries
- Strict separation of concerns with loose or tight coupling

### Cognitive Memory Architecture
- **Sensory Memory**: High-fidelity recent data (TTL: 4 days)
- **Short-Term Memory**: Efficient storage with aggregation (30 days)
- **Long-Term Memory**: Archival tier for historical data
- **Automatic Consolidation**: Based on importance scoring

### Archivist System
- Maintains context across sessions
- Learns from interactions
- Includes database optimization
- Cross-source pattern detection

### Database Collection Management
- Never directly create collections
- Use centralized mechanisms in `db/db_collections.py` or registration service
- Define indices and views alongside collections

## Development Workflows

### Environment Setup
- Use `uv` for package management
- Maintain separate virtual environments for each platform:
  - `.venv-win32-python3.12` - Windows
  - `.venv-linux-python3.13` - Linux
  - `.venv-macos-python3.12` - macOS
- Always activate the appropriate environment before running any code

### Testing
- Use pytest with unittest for unit tests
- Include tests for both happy and error paths
- Mock external dependencies
- Aim for comprehensive coverage of critical paths

### Performance
- Use performance mixins for automatic tracking
- Consider database query optimization
- Use batch processing for large datasets
- Include timeouts for potentially long-running operations

### Error Handling
- Use specific exceptions and custom exception hierarchy
- Include context in error messages
- Log before raising exceptions higher
- Use appropriate log levels

## Development Environment

### System Architecture
- **Primary Development Platform**: Windows with Windows Subsystem for Linux (WSL2)
- **WSL Distribution**: Ubuntu 22.04.5 LTS
- **Development IDE**: Visual Studio Code with Remote WSL extension
- **Source Code Management**: Git with GitHub for repository hosting
- **Project Structure**: Each project exists in Windows file system at `/mnt/c/Users/TonyMason/source/repos/` with symbolic links in Linux home directory (`~/projects/`)
- **WSL Limitations**: Some tools are unavailable to Claude in WSL, requiring manual execution and feedback
- **Symbolic Link Issues**: Symbolic links may not work the same as in pure Linux environment, causing potential complications

### Virtual Environment Strategy
- **Environment Management**: Each project maintains its own isolated virtual environment
- **Python Version Support**: Only Python 3.12+ is supported across all projects
- **Package Management**: Exclusively use `uv` for package management; never use naked `pip` commands
- **Package Installation Process**: Add package to `pyproject.toml`, then run `uv pip install -e .` to update the environment
- **Virtual Environment Naming**: Environment names MUST include platform and Python version (e.g., `.venv-linux-python3.12`)
- **Environment Activation**: Always activate the appropriate environment before running project code
- **Dependencies**: Defined in `pyproject.toml` using modern packaging standards
- **Cross-Platform Compatibility**: All code must run across Linux, Windows, and macOS

### Code Quality and Standards
- **Linting**: Use `ruff` for code linting, installed in each virtual environment
- **API Usage**: Always use current API methods, avoiding deprecated functions
  - Example: Use Pydantic's `model_dump()`/`model_dump_json()` instead of deprecated `dict()`

### Version Control and Testing
- **Git Workflow**: All changes must be tracked in git
- **Definition of "Done"**: Code is only considered complete when it has been tested
- **Testing Requirements**:
  - Use automated testing (pytest) whenever possible
  - When automated testing isn't available, request manual testing
  - Only commit code after confirming it works via testing
- **Commit Practice**: Each commit should:
  - Include a descriptive message explaining the change
  - Contain related changes (atomic commits)
  - Reference issue numbers when applicable
- **Branch Strategy**: Feature branches are created for new functionality
- **Pre-Commit Hooks**: Automated code formatting and linting before commits
- **Documentation**: Inline docstrings and separate documentation files
- **Code Review**: All significant changes undergo review

## Common Commands

### Core Commands
- Run all tests: `pytest tests/`
- Run single test: `pytest tests/path/to/test.py::test_function_name -v`
- Lint code: `flake8` or `pylint`
- Format code: `black .`
- Build package: `python -m build`

### Query System
- Test query: `python -m query.cli --query "Your query here" --enhanced-nl --context-aware`
- Run with Archivist: `python -m query.cli --archivist --optimizer`
- Show advanced features: `python -m query.cli --help`

### GUI Application
- Run Streamlit GUI: `cd utils/gui/streamlit && streamlit run app.py`
- Run Windows GUI script: `run_gui.bat`
- Run Linux/macOS GUI script: `./run_gui.sh`
