# ArangoDB Command Wrapper Utility

This utility provides a streamlined interface for generating and executing ArangoDB command-line tool commands with proper authentication, connection parameters, and configuration settings.

## Overview

Indaleko uses ArangoDB for database storage, and frequently needs to perform operations using ArangoDB's command-line tools:

- `arangoimport` - Import data into collections
- `arangorestore` - Restore database backups
- `arangodump` - Create database backups
- `arangosh` - Execute JavaScript commands in the ArangoDB shell

This utility simplifies these operations by:
1. Automatically handling authentication parameters
2. Setting the correct endpoint with SSL/TLS if needed
3. Providing a fluent interface for command configuration
4. Supporting large database operations with proper timeouts

## Installation

The utility is included as part of the Indaleko codebase in the `db/utils` directory.

## Basic Usage

### Import the required command generator:

```python
from db.utils import ArangoRestoreGenerator  # Or other generator as needed
```

### Create a command generator and configure it:

```python
restore_cmd = ArangoRestoreGenerator()
restore_cmd.with_input_directory("/path/to/backup") \
          .with_collections("MyCollection") \
          .with_create(True)
```

### Get the command string:

```python
cmd_string = restore_cmd.build_command()
print(cmd_string)
```

### Execute the command:

```python
result = restore_cmd.execute()
print(f"Command exited with code: {result.returncode}")
```

## Command Generators

### ArangoImportGenerator

Generates commands for importing data into ArangoDB collections.

```python
import_cmd = ArangoImportGenerator()
import_cmd.with_file("data.jsonl") \
         .with_collection("Objects") \
         .with_type("jsonl") \
         .with_overwrite(True)

cmd = import_cmd.build_command()
# Executes: arangoimport --collection Objects --server.username user --server.password pass...
```

#### Options:
- `with_file(file_path)` - Set input file path
- `with_collection(collection)` - Set target collection
- `with_type(type)` - Set file type (jsonl, json, csv)
- `with_overwrite(bool)` - Set overwrite flag

### ArangoRestoreGenerator

Generates commands for restoring ArangoDB backups.

```python
restore_cmd = ArangoRestoreGenerator()
restore_cmd.with_input_directory("/path/to/backup") \
          .with_collections(["Collection1", "Collection2"]) \
          .with_create(True) \
          .with_timeout_hours(5)

cmd = restore_cmd.build_command()
# Executes: arangorestore --input-directory /path/to/backup --collection Collection1 --collection Collection2...
```

#### Options:
- `with_input_directory(dir_path)` - Set backup directory path
- `with_collections(collections)` - Set collections to restore (string or list)
- `with_create(bool)` - Create collections if they don't exist
- `with_overwrite(bool)` - Overwrite existing data
- `with_timeout_hours(float)` - Set timeout in hours (important for large databases)

### ArangoDumpGenerator

Generates commands for creating ArangoDB backups.

```python
dump_cmd = ArangoDumpGenerator()
dump_cmd.with_output_directory("/path/to/backup") \
       .with_collections("MyCollection") \
       .with_compress(True)

cmd = dump_cmd.build_command()
# Executes: arangodump --output-directory /path/to/backup --collection MyCollection...
```

#### Options:
- `with_output_directory(dir_path)` - Set output directory path
- `with_collections(collections)` - Set collections to dump (string or list)
- `with_include_system(bool)` - Include system collections
- `with_compress(bool)` - Enable compression

### ArangoShellGenerator

Generates commands for executing JavaScript in the ArangoDB shell.

```python
shell_cmd = ArangoShellGenerator()
shell_cmd.with_command('db._collections().forEach(c => print(c.name() + ": " + c.count()))')
       .with_quiet(True)

cmd = shell_cmd.build_command()
# Executes: arangosh --server.username user --server.password pass --quiet true --javascript.execute-string "db._collections()..."
```

#### Options:
- `with_command(js_command)` - Set JavaScript command to execute
- `with_file(file_path)` - Set JavaScript file to execute
- `with_quiet(bool)` - Enable quiet mode

## Command Line Examples

### Restore Example

The utility includes a command-line script for restoring databases:

```bash
python -m db.utils.restore_example --input-directory /path/to/backup
```

#### Options:
- `--input-directory`, `-i` - Path to backup directory (required)
- `--collections`, `-c` - Comma-separated list of collections to restore
- `--create` - Create collections if they don't exist (default: true)
- `--overwrite` - Overwrite existing data (default: false)
- `--timeout-hours` - Timeout in hours (default: 5.0)
- `--dry-run` - Show the command without executing it
- `--verbose`, `-v` - Enable verbose logging

### Test All Commands

```bash
python -m db.utils.test_arango_commands
```

## Considerations for Large Databases

When working with large databases (100M+ records):

1. Set appropriate timeouts using `with_timeout_hours()`
2. For restore operations, expect 3-4+ hours for completion
3. Consider using `--dry-run` to validate commands before execution
4. Ensure sufficient disk space for dump operations and memory for restores

## Integration with Indaleko Database Configuration

The command generators automatically use the Indaleko database configuration:

- Database name, username, and password
- Host and port
- SSL/TLS settings

This ensures consistency across different environments without hardcoding credentials.

## Advanced Usage

### Custom DB Configuration

```python
from db.db_config import IndalekoDBConfig

# Load specific config file
custom_config = IndalekoDBConfig(config_file="/path/to/custom/config.ini")

# Use with command generator
restore_cmd = ArangoRestoreGenerator(db_config=custom_config)
```

### Executing with Custom Timeout

```python
# Very long timeout for huge datasets (8 hours)
restore_cmd = ArangoRestoreGenerator()
restore_cmd.with_input_directory("/path/to/backup") \
          .with_timeout_hours(8)

# Execute with the timeout
result = restore_cmd.execute()
```

### Capturing Output

```python
result = shell_cmd.execute()
if result.returncode == 0:
    output = result.stdout
    print(f"Command output: {output}")
else:
    error = result.stderr
    print(f"Command failed: {error}")
```
