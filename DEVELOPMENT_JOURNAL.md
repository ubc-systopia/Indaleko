## Development Journal

This journal records the development plan and checklist for implementing the file picker and related background processing tasks.

### Plan
1. Random-file picker as a low-priority background task
   - Expose a picker module with job queue or daemon.
   - Use `os.nice(+10)` or a task queue for low priority.
   - CLI subcommand: `scan start`.

2. File-type filtering
   - Configurable extension whitelist (e.g. `.py`, `.txt`, `.md`, `.json`, `.yaml`).
   - Overrides via CLI flags or config file.

3. Batch-upload helper
   - CLI subcommands: `scan batch-export`, `scan batch-import`.
   - Bundle files (tar + compression + optional encryption), transfer via scp, unpack on remote.

4. Platform-agnostic code & testing
   - Pure Python core logic.
   - Dockerfile for Linux-based integration tests.
   - Remote invocation on indexed Linux VM via SSH.

5. Documentation & error recovery
   - Document each step and recovery checkpoints.
   - Record logs to restart from last known good state.

### Checklist
- [ ] Create `picker.py` module with background task structure
- [ ] Implement low-priority scheduling (using `os.nice` or task queue)
- [ ] Write unit tests for file picker logic
- [ ] Add extension whitelist support and configuration
- [ ] Write tests for extension filtering
- [ ] Implement `scan batch-export` CLI command
- [ ] Implement `scan batch-import` CLI command
- [ ] Write tests for batch-export/import functionality
- [ ] Create Dockerfile for integration testing
- [ ] Write integration test script (cover background tasks and CLI commands)
- [ ] Add documentation about recovery procedures
- [ ] Update README with new subcommands and usage guide
- [ ] Verify CI (pre-commit, etc.) passes on both Windows/WSL and Linux
- [ ] Plan and execute deployment to remote Linux VM
