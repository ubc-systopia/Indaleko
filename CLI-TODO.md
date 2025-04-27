# CLI Migration Plan for Indaleko

This document identifies CLI tools in the Indaleko codebase and evaluates whether they should be migrated to use the common CLI template located in `tools/cli_template/`.

## Common CLI Template Overview

The CLI template in `tools/cli_template/` provides a standardized framework for building CLI utilities with:

- Consistent argument parsing
- Configuration loading
- Logging setup
- Performance recording
- Error handling
- Extensibility through handler mixins

## Currently Using Template Pattern

The following scripts are already using the CLI template pattern or similar implementation:

1. **`activity/collectors/storage/ntfs/ntfs_collector_v2.py`**
   - Uses `IndalekoCLIRunner` with custom handler mixin
   - Has robust argument handling and help output
   - Already follows the pattern - no migration needed

2. **`storage/recorders/cloud/cloud_base.py`**
   - Already extends `IndalekoCLIRunner`
   - Similar pattern to the template

3. **`storage/collectors/cloud/cloud_base.py`**
   - Already extends `IndalekoCLIRunner`
   - Similar pattern to the template

4. **`storage/collectors/local/local_base.py`**
   - Already extends `IndalekoCLIRunner`
   - Similar pattern to the template

5. **`storage/recorders/local/local_base.py`**
   - Already extends `IndalekoCLIRunner`
   - Similar pattern to the template

## Top Priority for Migration

These scripts have CLI functionality but don't use the template pattern and would benefit the most from migration:

1. **`run_ntfs_activity.py`**
   - **Purpose**: Integrated NTFS Activity Collection and Recording
   - **Current CLI**: Custom argparse implementation
   - **Help Output**: Comprehensive help with default values
   - **Migration Benefit**: High - this is a core script that would benefit from the standardized error handling and logging

2. **`run_tier_transition.py`**
   - **Purpose**: NTFS Tier Transition between memory tiers
   - **Current CLI**: Custom argparse implementation
   - **Help Output**: Clear help with default values
   - **Migration Benefit**: High - frequently used script that would benefit from standardization

3. **`run_incremental_indexer.py`**
   - **Purpose**: Incremental File System Indexer
   - **Current CLI**: Custom argparse implementation
   - **Help Output**: Good help output with required arguments noted
   - **Migration Benefit**: High - important functionality that would benefit from the template pattern

4. **`semantic/run_bg_processor.py`**
   - **Purpose**: Indaleko Background Processor Service
   - **Current CLI**: Custom argparse implementation
   - **Help Output**: Clear help output with service management options
   - **Migration Benefit**: High - service management would benefit from standardization

5. **`semantic/run_scheduled.py`**
   - **Purpose**: Scheduled semantic extractors
   - **Current CLI**: Custom implementation (errored on test but likely important)
   - **Migration Benefit**: High - scheduled tasks should use standardized patterns

## Medium Priority for Migration

These scripts have CLI functionality that could benefit from migration but may have specialized needs:

1. **`query/cli.py`**
   - **Purpose**: Indaleko Query CLI with interactive mode
   - **Current CLI**: Complex custom implementation with subcommands
   - **Help Output**: Very comprehensive help with many options and tips
   - **Migration Benefit**: Medium - Complex UI with subcommands, but core functionality could benefit
   - **Migration Challenges**: Interactive mode and existing subcommand structure

2. **`query/assistants/cli.py`**
   - **Purpose**: Indaleko Assistant CLI
   - **Current CLI**: Simple custom implementation
   - **Help Output**: Limited options (batch, model, debug)
   - **Migration Benefit**: Medium - simple enough that migration should be straightforward

3. **`query/memory/proactive_cli.py`**
   - **Purpose**: Proactive CLI Integration for memory system
   - **Current CLI**: Specialized implementation with custom commands
   - **Help Output**: Command-based help instead of flags
   - **Migration Benefit**: Medium - specialized UI pattern, migration may be complex

4. **`activity/collectors/storage/ntfs/activity_generator.py`**
   - **Purpose**: NTFS Activity Generator
   - **Current CLI**: Simple argparse implementation
   - **Help Output**: Clear help with default values
   - **Migration Benefit**: Medium - testing tool that would benefit from standardization

## Low Priority or Specialized Cases

These scripts have CLI aspects but may not be suitable for migration due to specialized needs or test-only usage:

1. **`activity/collectors/collaboration/calendar/calendar_cli.py`**
   - **Purpose**: Calendar integration CLI
   - **Current CLI**: Failed to run help (import errors)
   - **Migration Benefit**: Unknown - would need to fix imports first

2. Various test scripts and examples (numerous .py files in the codebase)
   - **Purpose**: Testing and examples only
   - **Current CLI**: Typically simple argparse implementations
   - **Migration Benefit**: Low - example/test scripts may not need full framework

## Migration Plan

### Phase 1: High Priority Scripts
1. Start with `run_ntfs_activity.py` - core system functionality
2. Migrate `run_tier_transition.py` - memory management
3. Migrate `run_incremental_indexer.py` - indexing system
4. Migrate `semantic/run_bg_processor.py` - background services
5. Migrate `semantic/run_scheduled.py` - scheduled tasks

### Phase 2: Medium Priority Scripts
1. Evaluate feasibility of migrating `query/cli.py` or parts of it
2. Migrate simpler scripts like `query/assistants/cli.py`
3. Migrate `activity/collectors/storage/ntfs/activity_generator.py`

### Phase 3: Low Priority and Specialized Cases
1. Fix imports in `activity/collectors/collaboration/calendar/calendar_cli.py` and evaluate
2. Evaluate remaining scripts for migration on a case-by-case basis

## Migration Steps for Each Script

1. Create a new handler mixin extending `IndalekoHandlermixin`
2. Map existing command-line arguments to the mixin's `get_pre_parser()` method
3. Implement core logic in a static `run()` method
4. Update main function to use `IndalekoCLIRunner`
5. Test thoroughly to ensure all functionality is preserved
6. Document the migration in commit messages

## Benefits of Migration

1. **Consistency**: Unified approach to CLI implementation
2. **Maintainability**: Easier to understand and modify tools
3. **Robustness**: Better error handling and logging
4. **Features**: All tools benefit from built-in performance tracking and logging
5. **Documentation**: Consistent help output format