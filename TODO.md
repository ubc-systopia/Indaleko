# Indaleko Project TODOs

## CRITICAL: FAIL-STOP IS THE PRIMARY DESIGN PRINCIPLE

Indaleko follows a strict FAIL-STOP model as its primary design principle:

1. **NEVER** implement fallbacks or paper over errors
2. **ALWAYS** fail immediately and visibly when issues occur
3. **NEVER** substitute mock/fake data when real data is unavailable
4. **ALWAYS** exit with a clear error message (sys.exit(1)) rather than continuing with degraded functionality

## Current Priority: Ablation Testing Framework

The current priority is completing the ablation testing framework. See [ABLATION_TODO.md](ABLATION_TODO.md) for the complete task list.

Major components remaining:
- Verify current codebase functionality with available activity providers
- Complete migration of experimental LLM query generator
- Implement remaining activity data providers (Collaboration, Storage, Media)
- Add database snapshot functionality
- Run full ablation tests

## Development Guidelines

1. All new code should follow the fail-stop model
2. Scientific integrity is paramount - never substitute mock data for real data
3. Database operations must use proper collection naming and access patterns
4. All components should follow the collector/recorder pattern with proper separation of concerns
5. Tests should verify functionality with real database connections, not mocks

Remember: It is better to fail loudly and immediately than to continue with compromised functionality.