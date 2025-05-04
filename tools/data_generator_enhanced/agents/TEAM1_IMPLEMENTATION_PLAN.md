# Team 1: Data Generation Agent Implementation Plan

This document outlines the implementation steps for creating the Data Generation Agent system as defined in the architecture document.

## Phase 1: Foundation Components

### Step 1: Project Structure

Create the basic project structure:

```
agents/
├── data_gen/
│   ├── __init__.py
│   ├── core/             # Core framework
│   │   ├── __init__.py
│   │   ├── controller.py
│   │   ├── llm.py
│   │   ├── state.py
│   │   └── tools.py
│   ├── agents/           # Domain-specific agents
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── storage.py
│   │   ├── semantic.py
│   │   ├── activity.py
│   │   ├── relationship.py
│   │   └── machine_config.py
│   ├── tools/            # Tool implementations
│   │   ├── __init__.py
│   │   ├── db.py
│   │   ├── stats.py
│   │   └── validation.py
│   ├── config/           # Configuration
│   │   ├── __init__.py
│   │   ├── defaults.py
│   │   └── scenarios.py
│   └── utils/            # Utilities
│       ├── __init__.py
│       ├── logging.py
│       └── reporting.py
├── examples/
│   ├── basic_generation.py
│   └── truth_generation.py
└── tests/
    ├── __init__.py
    ├── test_storage_agent.py
    └── test_db_tools.py
```

### Step 2: LLM Interface

Implement the core LLM interface with support for multiple providers:

```python
# core/llm.py

class LLMProvider:
    """Base class for LLM providers."""

    def __init__(self, config):
        self.config = config

    def generate(self, prompt, tools=None):
        """Generate a response or tool call."""
        raise NotImplementedError

    def stream_generate(self, prompt, tools=None):
        """Stream a response or tool calls."""
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""

    def __init__(self, config):
        super().__init__(config)
        self.client = OpenAI(api_key=config.get("api_key"))
        self.model = config.get("model", "gpt-4o")

    def generate(self, prompt, tools=None):
        # Implementation using OpenAI client
        pass


class AnthropicProvider(LLMProvider):
    """Anthropic implementation of LLM provider."""

    def __init__(self, config):
        super().__init__(config)
        self.client = Anthropic(api_key=config.get("api_key"))
        self.model = config.get("model", "claude-3-opus-20240229")

    def generate(self, prompt, tools=None):
        # Implementation using Anthropic client
        pass
```

### Step 3: Tool Registry

Implement the tool registry and base tool interface:

```python
# core/tools.py

class Tool:
    """Base class for all tools."""

    def __init__(self, name, description):
        self.name = name
        self.description = description

    def execute(self, parameters):
        """Execute the tool with provided parameters."""
        raise NotImplementedError

    def get_schema(self):
        """Return the JSON schema for this tool."""
        raise NotImplementedError


class ToolRegistry:
    """Registry for all available tools."""

    def __init__(self):
        self.tools = {}

    def register_tool(self, tool):
        """Register a tool with the registry."""
        self.tools[tool.name] = tool

    def get_tool(self, name):
        """Get a tool by name."""
        return self.tools.get(name)

    def get_all_tools(self):
        """Get all registered tools."""
        return list(self.tools.values())

    def get_tool_schemas(self):
        """Get schemas for all registered tools."""
        return [tool.get_schema() for tool in self.tools.values()]
```

### Step 4: Database Tools

Implement the database interaction tools:

```python
# tools/db.py

class DatabaseQueryTool(Tool):
    """Tool for querying the database."""

    def __init__(self, db_config):
        super().__init__(
            name="database_query",
            description="Query the database using AQL"
        )
        self.db_config = db_config

    def execute(self, parameters):
        query = parameters.get("query")
        bind_vars = parameters.get("bind_vars", {})

        # Execute the query and return results
        cursor = self.db_config.db.aql.execute(query, bind_vars=bind_vars)
        return list(cursor)


class DatabaseInsertTool(Tool):
    """Tool for inserting documents into the database."""

    def __init__(self, db_config):
        super().__init__(
            name="database_insert",
            description="Insert documents into a database collection"
        )
        self.db_config = db_config

    def execute(self, parameters):
        collection_name = parameters.get("collection")
        documents = parameters.get("documents", [])

        collection = self.db_config.db.collection(collection_name)
        results = []

        for doc in documents:
            try:
                result = collection.insert(doc)
                results.append({"success": True, "key": result["_key"]})
            except Exception as e:
                results.append({"success": False, "error": str(e)})

        return results
```

## Phase 2: Agent Implementation

### Step 5: Base Agent Interface

Implement the base agent interface:

```python
# agents/base.py

class Agent:
    """Base class for all agents."""

    def __init__(self, llm_provider, tool_registry, config=None):
        self.llm = llm_provider
        self.tools = tool_registry
        self.config = config or {}
        self.state = {}

    def initialize(self):
        """Initialize the agent."""
        pass

    def run(self, instruction, input_data=None):
        """Run the agent with the given instruction and input data."""
        context = self._build_context(instruction, input_data)
        response = self.llm.generate(context, tools=self.tools.get_tool_schemas())
        return self._process_response(response)

    def _build_context(self, instruction, input_data):
        """Build the context for the LLM."""
        raise NotImplementedError

    def _process_response(self, response):
        """Process the response from the LLM."""
        raise NotImplementedError
```

### Step 6: Domain-Specific Agents

Implement the storage metadata generator agent:

```python
# agents/storage.py

class StorageGeneratorAgent(Agent):
    """Agent for generating storage metadata."""

    def __init__(self, llm_provider, tool_registry, config=None):
        super().__init__(llm_provider, tool_registry, config)
        self.collection_name = IndalekoDBCollections.Indaleko_Object_Collection

    def generate(self, count, criteria=None):
        """Generate storage metadata records."""
        instruction = f"Generate {count} realistic storage metadata records"
        if criteria:
            instruction += f" matching these criteria: {json.dumps(criteria)}"

        input_data = {
            "count": count,
            "criteria": criteria,
            "config": self.config,
            "collection_name": self.collection_name
        }

        return self.run(instruction, input_data)

    def generate_truth(self, count, criteria):
        """Generate truth storage records with specific characteristics."""
        instruction = f"Generate {count} truth storage records"
        instruction += f" matching these criteria: {json.dumps(criteria)}"

        input_data = {
            "count": count,
            "criteria": criteria,
            "truth": True,
            "config": self.config,
            "collection_name": self.collection_name
        }

        return self.run(instruction, input_data)

    def _build_context(self, instruction, input_data):
        """Build the context for the LLM."""
        return f"""
        You are a specialized agent for generating realistic file and directory metadata.

        Your task: {instruction}

        Generate metadata that follows these guidelines:
        1. Create realistic file paths, names, and extensions
        2. Assign appropriate timestamps for creation, modification, and access
        3. Include file sizes that follow typical statistical distributions
        4. Ensure all records have required fields for database insertion

        Available tools:
        - database_query: Query the ArangoDB database
        - database_insert: Insert documents into the database
        - statistical_distribution: Generate values following statistical distributions

        Input data: {json.dumps(input_data)}
        """
```

## Phase 3: Controller Implementation

### Step 7: Controller and Orchestration

Implement the main controller:

```python
# core/controller.py

class GenerationController:
    """Main controller for the data generation process."""

    def __init__(self, config):
        self.config = config
        self.db_config = IndalekoDBConfig()

        # Initialize LLM provider
        provider_name = config.get("llm_provider", "openai")
        if provider_name == "openai":
            self.llm = OpenAIProvider(config.get("openai_config", {}))
        elif provider_name == "anthropic":
            self.llm = AnthropicProvider(config.get("anthropic_config", {}))
        else:
            raise ValueError(f"Unknown LLM provider: {provider_name}")

        # Initialize tool registry
        self.tool_registry = ToolRegistry()
        self._register_tools()

        # Initialize agents
        self.agents = {}
        self._initialize_agents()

        # Statistics and reporting
        self.stats = {}

    def _register_tools(self):
        """Register all tools with the registry."""
        self.tool_registry.register_tool(DatabaseQueryTool(self.db_config))
        self.tool_registry.register_tool(DatabaseInsertTool(self.db_config))
        # Register other tools...

    def _initialize_agents(self):
        """Initialize all agents."""
        self.agents["storage"] = StorageGeneratorAgent(
            self.llm,
            self.tool_registry,
            self.config.get("storage_config", {})
        )
        # Initialize other agents...

    def generate_dataset(self, scenario=None):
        """Generate a complete dataset according to the scenario."""
        scenario_config = self.config.get("scenarios", {}).get(scenario, {})

        # Generate storage metadata
        storage_count = scenario_config.get("storage_count", 100)
        storage_records = self.agents["storage"].generate(storage_count)
        self.stats["storage"] = {"count": len(storage_records)}

        # Generate semantic metadata
        # Generate activity metadata
        # Generate relationships
        # Generate machine configurations

        return self.stats

    def generate_truth_dataset(self, scenario=None):
        """Generate truth data for testing specific queries."""
        scenario_config = self.config.get("scenarios", {}).get(scenario, {})
        truth_criteria = scenario_config.get("truth_criteria", {})

        # Generate truth records for each agent
        storage_truth = self.agents["storage"].generate_truth(
            scenario_config.get("storage_truth_count", 5),
            truth_criteria.get("storage", {})
        )

        # Generate other truth records

        return {
            "storage": storage_truth,
            # Other truth records...
        }
```

## Phase 4: Integration and Testing

### Step 8: Scenario Configuration

Define scenario configurations:

```python
# config/scenarios.py

DEFAULT_SCENARIOS = {
    "basic": {
        "description": "Basic dataset with minimal complexity",
        "storage_count": 100,
        "semantic_count": 80,
        "activity_count": 50,
        "relationship_count": 150,
        "machine_config_count": 5,
        "truth_criteria": {
            "storage": {
                "name_pattern": "ProjectReport%",
                "extension": ".pdf",
                "days_ago": 5
            },
            "activity": {
                "location": {
                    "city": "New York",
                    "days_ago": 4
                }
            }
        }
    },
    "large": {
        "description": "Large dataset for performance testing",
        "storage_count": 10000,
        "semantic_count": 8000,
        "activity_count": 5000,
        "relationship_count": 15000,
        "machine_config_count": 20
    },
    "mobile_focus": {
        "description": "Dataset focused on mobile device usage",
        "storage_count": 500,
        "semantic_count": 400,
        "activity_count": 300,
        "relationship_count": 750,
        "machine_config_count": 10,
        "truth_criteria": {
            "machine_config": {
                "device_type": "mobile",
                "os": "iOS"
            },
            "activity": {
                "location": {
                    "city": "San Francisco"
                }
            }
        }
    }
}
```

### Step 9: Command-Line Interface

Implement a command-line interface:

```python
# cli.py

import argparse
import json
import sys

from data_gen.core.controller import GenerationController
from data_gen.config.defaults import DEFAULT_CONFIG
from data_gen.config.scenarios import DEFAULT_SCENARIOS


def main():
    parser = argparse.ArgumentParser(description="Indaleko Data Generation Agent")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--scenario", help="Scenario to generate data for", default="basic")
    parser.add_argument("--count", type=int, help="Number of records to generate")
    parser.add_argument("--truth", action="store_true", help="Generate truth records only")
    parser.add_argument("--output", help="Output path for generation report")

    args = parser.parse_args()

    # Load configuration
    config = DEFAULT_CONFIG
    if args.config:
        with open(args.config, 'r') as f:
            config.update(json.load(f))

    # Override count if specified
    if args.count:
        if args.scenario in config.get("scenarios", {}):
            config["scenarios"][args.scenario]["storage_count"] = args.count

    # Initialize controller
    controller = GenerationController(config)

    # Generate data
    try:
        if args.truth:
            results = controller.generate_truth_dataset(args.scenario)
            print(f"Generated truth dataset for scenario '{args.scenario}'")
        else:
            results = controller.generate_dataset(args.scenario)
            print(f"Generated complete dataset for scenario '{args.scenario}'")

        # Output results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2)
        else:
            print(json.dumps(results, indent=2))

    except Exception as e:
        print(f"Error generating data: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
```

### Step 10: Example and Testing

Create an example application:

```python
# examples/basic_generation.py

from data_gen.core.controller import GenerationController
from data_gen.config.defaults import DEFAULT_CONFIG


def main():
    # Initialize controller with default configuration
    controller = GenerationController(DEFAULT_CONFIG)

    # Generate a basic dataset
    stats = controller.generate_dataset("basic")

    print("Generation complete:")
    print(f"Storage records: {stats.get('storage', {}).get('count', 0)}")
    print(f"Semantic records: {stats.get('semantic', {}).get('count', 0)}")
    print(f"Activity records: {stats.get('activity', {}).get('count', 0)}")
    print(f"Relationship records: {stats.get('relationship', {}).get('count', 0)}")
    print(f"Machine configuration records: {stats.get('machine_config', {}).get('count', 0)}")


if __name__ == "__main__":
    main()
```

## Implementation Timeline

1. **Week 1: Foundation Components**
   - Project structure setup
   - LLM interface implementation
   - Tool registry and basic tools
   - Database integration

2. **Week 2: Agent Implementation**
   - Base agent interface
   - Storage generator agent
   - Semantic generator agent
   - Testing and validation

3. **Week 3: Additional Agents**
   - Activity generator agent
   - Relationship generator agent
   - Machine configuration agent
   - Integration between agents

4. **Week 4: Controller and Integration**
   - Controller implementation
   - Scenario configuration
   - CLI implementation
   - Documentation and examples

5. **Week 5: Testing and Refinement**
   - End-to-end testing
   - Performance optimization
   - Bug fixes and improvements
   - Final documentation
