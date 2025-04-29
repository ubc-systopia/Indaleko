# Pre-commit Hooks for Indaleko

This repository uses pre-commit hooks to ensure code quality and consistency across the codebase.

## Installed Hooks

The following hooks are configured in our pre-commit setup:

1. **Trailing Whitespace**: Removes trailing whitespace from files (preserves Markdown line breaks)
2. **End of File Fixer**: Ensures files end with a newline
3. **YAML Syntax Check**: Validates YAML files for correct syntax
4. **TOML Syntax Check**: Validates TOML files for correct syntax
5. **Large File Check**: Prevents committing files larger than 500KB
6. **Black Formatter**: Formats Python code according to Black style guidelines
7. **Ruff Linter**: Runs the Ruff linter to check code quality and fix simple issues
8. **isort**: Sorts imports according to standards (configured to work with Black)
9. **Check No Pip Usage**: Prevents direct use of pip (use uv instead)
10. **Check Create Collection Usage**: Ensures create_collection is only called from authorized locations
11. **Check Collection Constants**: Ensures collection names are referenced via IndalekoDBCollections constants

## Installation

If you haven't installed pre-commit yet, you can do so using:

```bash
uv pip install pre-commit
```

Then, install the pre-commit hooks:

```bash
pre-commit install
```

## Usage

The hooks will run automatically when you commit changes. If any hook fails, the commit will be aborted.

### Running Hooks Manually

You can run the hooks manually on all files:

```bash
pre-commit run --all-files
```

Or on specific files:

```bash
pre-commit run --files path/to/file1.py path/to/file2.py
```

### Skipping Hooks

In rare cases, you may need to skip the pre-commit hooks:

```bash
git commit -m "Your message" --no-verify
```

**Note**: This should be used sparingly and only with a good reason.

## Troubleshooting

If you encounter issues with the pre-commit hooks:

1. Make sure you have the latest version of pre-commit installed
2. Try updating the hooks: `pre-commit autoupdate`
3. For issues with specific hooks, check their documentation

### Common Issues

- **Black formatting conflicts**: Black and isort might conflict if not configured properly. Our configuration ensures they work together.
- **Ruff errors**: Ruff is configured to enforce a strict set of rules. The error messages should provide clear guidance on how to fix issues.

## Configuration

The pre-commit configuration is in `.pre-commit-config.yaml`. Ruff linter rules are configured in `ruff.toml`.

### Semantically Meaningful Error Messages

The hooks are configured to provide clear, semantically meaningful error messages that explain:

1. What the issue is
2. Why it's a problem
3. How to fix it

This helps developers understand and resolve issues quickly rather than just enforcing rules without explanation.

## Custom Hooks

### No Pip Usage Check

This hook prevents direct use of pip in Python files, enforcing the project standard of using `uv` for package management instead. It checks for:

- Direct pip imports (`import pip` or `from pip import ...`)
- Calls to `pip.main()`
- Subprocess calls that invoke pip (`subprocess.call(["pip", ...])`)
- Shell commands with pip (`os.system("pip install ...")`)

**Why**: The project standardizes on `uv` for faster, more consistent package management across platforms.

**Fix**: Use `uv pip install -e .` or update your dependencies in `pyproject.toml`.

### Create Collection Usage Check

This hook ensures that `create_collection` is only called from authorized locations:

1. `db/db_collections.py` - For static collections
2. `utils/registration_service.py` - For dynamic collections

**Why**: Centralized collection management is a critical security feature that ensures:
- Consistent schema validation
- Proper indexing
- UUID-based collection names for security
- Controlled security checks at a single point

**Fix**: Replace direct `create_collection` calls with:
- `IndalekoCollections.get_collection()` for static collections
- Registration service for dynamic collections

This enforces the architectural pattern described in CLAUDE.md that reduces attack surface area and allows for security monitoring.

### Collection Constants Check

This hook ensures that collection names are referenced using the constants defined in the IndalekoDBCollections class rather than hardcoded strings:

- BAD: `db.get_collection("Objects")`
- GOOD: `db.get_collection(IndalekoDBCollections.Indaleko_Object_Collection)`

**Why**: Using constants instead of hardcoded strings provides several benefits:
- Makes collection name changes easier (only need to update in one place)
- Prevents typos in collection names
- Improves code readability by self-documenting the intent
- Makes references to collections easier to find with automated tools

**Fix**: Import and use the appropriate constant from `IndalekoDBCollections` instead of the hardcoded string:
```python
from db.db_collections import IndalekoDBCollections

# Instead of this:
db.get_collection("Objects")

# Do this:
db.get_collection(IndalekoDBCollections.Indaleko_Object_Collection)
```
