# ArangoDB Command Wrapper Utility - Implementation Plan

## Overview
This document outlines the implementation plan for a utility wrapper around ArangoDB command-line tools that generates properly formatted command strings with all necessary arguments pre-configured according to the Indaleko database configuration.

## Motivation
Running ArangoDB command-line tools (arangoimport, arangorestore, etc.) requires specifying numerous parameters for authentication, connection details, SSL configuration, and operation-specific settings. This utility will simplify that process by leveraging the existing database configuration infrastructure in Indaleko.

## Implementation Location
- New module: `/db/utils/arango_commands.py`

## Class Structure

### 1. BaseArangoCommandGenerator
Abstract base class that handles:
- Connection parameters (hostname, port, user, password)
- SSL/TLS configuration
- Common parameter formatting
- Integration with IndalekoDBConfig

```python
class BaseArangoCommandGenerator:
    def __init__(self, db_config=None):
        # Use provided config or create new one
        self.db_config = db_config or IndalekoDBConfig()

    def _get_endpoint_string(self):
        # Format endpoint string with proper protocol
        protocol = "ssl" if self.db_config.get_ssl_state() else "tcp"
        return f"{protocol}://{self.db_config.get_hostname()}:{self.db_config.get_port()}"

    def _get_auth_parameters(self):
        # Format authentication parameters
        return [
            f"--server.database {self.db_config.get_database_name()}",
            f"--server.username {self.db_config.get_user_name()}",
            f"--server.password {self.db_config.get_user_password()}"
        ]

    def execute(self, command_string=None):
        # Execute the generated command
        cmd = command_string or self.build_command()
        # Use subprocess to run command and capture output
        return subprocess.run(cmd, shell=True, capture_output=True, text=True)
```

### 2. Tool-Specific Command Generators

#### 2.1 ArangoImportGenerator
Refactored from existing code in IndalekoDBUploader:

```python
class ArangoImportGenerator(BaseArangoCommandGenerator):
    def __init__(self, db_config=None):
        super().__init__(db_config)
        self.file_path = None
        self.collection = None
        self.type = "jsonl"

    def with_file(self, file_path):
        self.file_path = file_path
        return self

    def with_collection(self, collection):
        self.collection = collection
        return self

    def build_command(self):
        # Implementation similar to existing build_load_string method
```

#### 2.2 ArangoRestoreGenerator
New implementation for restore operations:

```python
class ArangoRestoreGenerator(BaseArangoCommandGenerator):
    def __init__(self, db_config=None):
        super().__init__(db_config)
        self.input_directory = None
        self.collections = None
        self.create = True
        self.overwrite = False

    def with_input_directory(self, directory_path):
        self.input_directory = directory_path
        return self

    def with_collections(self, collections=None):
        self.collections = collections
        return self

    def with_create(self, create=True):
        self.create = create
        return self

    def with_overwrite(self, overwrite=True):
        self.overwrite = overwrite
        return self

    def build_command(self):
        # Build complete arangorestore command string
```

#### 2.3 ArangoDumpGenerator
For creating database backups:

```python
class ArangoDumpGenerator(BaseArangoCommandGenerator):
    def __init__(self, db_config=None):
        super().__init__(db_config)
        self.output_directory = None
        self.collections = None

    def with_output_directory(self, directory_path):
        self.output_directory = directory_path
        return self

    def with_collections(self, collections=None):
        self.collections = collections
        return self

    def build_command(self):
        # Build complete arangodump command string
```

#### 2.4 ArangoShellGenerator
For executing ArangoDB shell commands:

```python
class ArangoShellGenerator(BaseArangoCommandGenerator):
    def __init__(self, db_config=None):
        super().__init__(db_config)
        self.command = None
        self.file = None

    def with_command(self, command):
        self.command = command
        return self

    def with_file(self, file_path):
        self.file = file_path
        return self

    def build_command(self):
        # Build complete arangosh command string
```

## Implementation Priorities
1. Implement BaseArangoCommandGenerator - core functionality
2. Implement ArangoRestoreGenerator - immediate need
3. Implement or adapt ArangoImportGenerator - using existing code
4. Implement remaining generators as needed

## Usage Examples

### ArangoRestore Example
```python
from db.utils.arango_commands import ArangoRestoreGenerator

# Create and configure restore command
restore_cmd = ArangoRestoreGenerator()
cmd_string = restore_cmd.with_input_directory("/path/to/backup") \
                  .with_create(True) \
                  .build_command()

# Execute the command
result = restore_cmd.execute()
print(f"Command completed with exit code {result.returncode}")
```

### ArangoImport Example
```python
from db.utils.arango_commands import ArangoImportGenerator

# Create and configure import command
import_cmd = ArangoImportGenerator()
cmd_string = import_cmd.with_file("data.jsonl") \
                  .with_collection("Objects") \
                  .build_command()

print(cmd_string)  # Display command for verification
```

## Considerations for Large Databases
- Set appropriate timeouts for operations on 100M+ record databases
- Default timeout should be 4+ hours for restore operations
- For restore operations, focus on simplicity with single-command approach
- No complex validation needed initially
