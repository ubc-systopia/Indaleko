# CLAUDE.md - Indaleko Development Guidelines

## Commands
- Run all tests: `pytest tests/`
- Run single test: `pytest tests/path/to/test.py::test_function_name -v`
- Lint code: `flake8` or `pylint`
- Format code: `black .`
- Build package: `python -m build`

## Style Guidelines
- Imports: standard library → third-party → local (with blank lines between)
- Types: Use type hints for all functions and variable declarations
- Formatting: 4 spaces, ~100 char line length, docstrings with triple quotes
- Naming: CamelCase for classes, snake_case for functions/vars, UPPER_CASE for constants
- Interfaces: Prefix with 'I' (IObject, IRelationship)
- Error handling: Specific exceptions with descriptive messages
- Documentation: All modules, classes and methods need docstrings (Args/Returns sections)
- Module organization: Copyright header, imports, constants, classes, functions, main

## Tools
- Models: Extend Pydantic BaseModel where appropriate
- Testing: pytest with unittest for unit tests
- Validation: Use type checking decorators and explicit assertions