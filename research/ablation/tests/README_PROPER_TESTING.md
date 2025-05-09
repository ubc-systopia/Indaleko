# Proper Testing with Fail-Stop Principle

## Critical: Fail-Stop Is The Primary Design Principle

Indaleko follows a strict FAIL-STOP model as its primary design principle, especially for scientific experiments like the ablation framework:

1. **NEVER implement fallbacks or paper over errors**
2. **ALWAYS fail immediately and visibly when issues occur**
3. **NEVER substitute mock/fake data when real data is unavailable**
4. **ALWAYS exit with a clear error message (sys.exit(1)) rather than continuing with degraded functionality**

This is ESPECIALLY important for our ablation framework, where data integrity is critical. Silently substituting template-based data or using mocks when LLM generation fails would invalidate experimental results and is strictly prohibited.

## Proper Test Files

The following test files have been implemented to follow the fail-stop principle:

1. **Unit Tests**
   - `test_cross_collection_query_generator_proper.py`: Tests for CrossCollectionQueryGenerator with real connections

2. **Integration Tests**
   - `test_cross_collection_aql_proper.py`: Tests AQL translation with real database connections
   - `test_cross_collection_queries_proper.py`: Tests cross-collection query generation with real registry and database
   - `test_ablation_cross_collection_proper.py`: Tests ablation framework with cross-collection queries

## Running the Proper Tests

To run all the proper tests that follow the fail-stop principle, use:

```bash
python -m research.ablation.tests.run_all_proper_tests
```

## Deprecated Test Files

The following test files use mocks and patches, violating the fail-stop principle:

1. ~~`test_cross_collection_query_generator.py`~~ - DEPRECATED
2. ~~`test_cross_collection_aql.py`~~ - DEPRECATED
3. ~~`test_cross_collection_queries.py`~~ - DEPRECATED

These files have been marked with explicit warnings and should not be used. They are maintained only for reference and will be removed in a future update.

## Why Mock-Free Testing is Critical for Scientific Experiments

For the ablation framework specifically, using mocks would undermine the scientific validity of our experiments:

1. **Data Integrity**: Using real connections ensures that query generation, translation, and execution work with real data
2. **Realistic Error Handling**: Real services may fail in ways that mocks don't accurately simulate
3. **Scientific Validity**: Mock data might inadvertently bias our ablation results
4. **Complete System Testing**: We need to verify that all components work together in the real system

## Implementation Guidelines

When implementing new tests:

1. **Never Mock Database Connections**: Always use `IndalekoDBConfig().get_arangodb()` to get a real database connection
2. **Never Mock LLM Services**: Always use real LLM connectors to test query generation
3. **Fail-Stop on Connection Failures**: Use `sys.exit(1)` when critical connections fail
4. **No Error Masking**: Don't catch exceptions that would hide real errors
5. **Real Entity Registration**: Use real entity registry with real keys and relationships
6. **Real Expected Matches**: Generate expected matches based on real entities, not synthetic ones

## Common Anti-Patterns to Avoid

1. ❌ Using `patch()` to replace database connections with mocks
2. ❌ Using `MagicMock()` for LLM responses
3. ❌ Catching exceptions without re-raising them
4. ❌ Returning fake data when real data isn't available
5. ❌ Using mock query generators instead of real ones

Remember: It is better to fail loudly and immediately than to continue with compromised functionality that could invalidate scientific results.
