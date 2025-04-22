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
