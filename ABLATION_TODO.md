# Ablation Testing Framework TODO List

## CRITICAL: FAIL-STOP IS REQUIRED FOR ALL IMPLEMENTATIONS

This project follows a strict FAIL-STOP model as its primary design principle:

1. **NEVER** implement fallbacks or paper over errors 
2. **ALWAYS** fail immediately and visibly when issues occur
3. **NEVER** substitute mock/fake data when real data is unavailable
4. **ALWAYS** exit with a clear error message (sys.exit(1)) rather than continuing with degraded functionality

This is **REQUIRED** for the ablation testing framework as it is a scientific experiment where data integrity is critical. 
Silently substituting template-based data when LLM generation fails would invalidate experimental results.

## Tasks Remaining

- [ ] Confirm that the current code base can successfully run the full pipeline with the available activity data providers
- [ ] Migrate experimental LLM query generator from scratch to research/ablation/query
- [ ] Update imports and references in run_comprehensive_ablation.py to use the migrated query generator
- [ ] Test the full ablation pipeline after migration to verify functionality
- [ ] Fix any bugs found during post-migration testing
- [ ] Commit working code with --no-verify flag

- [ ] Implement CollaborationActivityCollector and CollaborationActivityRecorder
- [ ] Verify pipeline works with Collaboration activity data provider
- [ ] Commit collaboration activity implementation with --no-verify flag

- [ ] Implement StorageActivityCollector and StorageActivityRecorder
- [ ] Verify pipeline works with Storage activity data provider
- [ ] Commit storage activity implementation with --no-verify flag

- [ ] Implement MediaActivityCollector and MediaActivityRecorder
- [ ] Verify pipeline works with Media activity data provider
- [ ] Commit media activity implementation with --no-verify flag

- [ ] Create database snapshot mechanism using arangobackup utility
- [ ] Integrate database snapshot creation at end of successful ablation run

## Future Enhancements

- [ ] Improve truth data generation to create more semantically meaningful matches
- [ ] Create more non-match case generation with controlled variety
- [ ] Enhance diversity calculation for query generation using Jaro-Winkler similarity
- [ ] Improve ablation report visualizations with more detailed metrics
- [ ] Create end-to-end ablation study script following full protocol

## Implementation Notes

1. All activity data providers must follow the same pattern:
   - Collectors generate synthetic activity data but NEVER interact with the database
   - Recorders process collector data and insert it into the database
   - Each provider must handle fail-stop error cases properly

2. The LLM query generator must:
   - Fail immediately if API connection fails
   - Fail immediately if response parsing fails
   - Fail immediately if diversity evaluation fails
   - NEVER substitute template-based queries as fallbacks

3. The comprehensive ablation test runner must:
   - Validate all prerequisites before starting
   - Fail immediately if any component is missing
   - Never attempt to continue with partial functionality
   - Properly clean up resources even when failing

Remember: It is better to fail loudly and immediately than to continue with compromised functionality.