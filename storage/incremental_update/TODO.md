# Incremental Update Service - Implementation Plan

## Phase 1: Core Infrastructure (DONE)
- [x] Create queue collection schema
- [x] Implement `ResolutionRequest` model
- [x] Implement `EntityResolutionQueue` class
- [x] Implement `ProducerMixin` for recorders
- [x] Add unit tests
- [x] Create documentation (README, DESIGN)

## Phase 2: Windows NTFS Integration
- [ ] Enhance NTFS Hot Tier Recorder
  - [ ] Add ProducerMixin to NtfsHotTierRecorder class
  - [ ] Modify entity lookup to enqueue requests for missing entities
  - [ ] Add configuration options for enabling/disabling resolution
  - [ ] Update error handling to differentiate between missing entities and other errors

## Phase 3: Resolution Service Implementation
- [ ] Complete Windows-specific entity resolution logic
  - [ ] Implement integration with Windows local storage collector
  - [ ] Implement proper entity creation through Windows recorder
  - [ ] Add path extraction for directory creation
  - [ ] Add importance scoring based on context

## Phase 4: CLI and Service Runner
- [ ] Create CLI tool for running the resolution service
  - [ ] Add command-line options for machine ID, batch size, etc.
  - [ ] Implement service mode with graceful shutdown
  - [ ] Add config file support for environment-specific settings
- [ ] Create Windows service wrapper (bat script)
- [ ] Add monitoring and reporting capabilities

## Phase 5: Testing & Verification
- [ ] Integration tests with NTFS recorder
- [ ] Performance testing with varying queue depths
- [ ] End-to-end testing with real journal events
- [ ] Validation of entity resolution accuracy

## Phase 6: Monitoring & Operational Features
- [ ] Create dashboard for queue statistics
- [ ] Add logging for debugging and performance analysis
- [ ] Implement automatic error recovery mechanisms
- [ ] Add configuration for tuning performance parameters

## Future Enhancements
- [ ] Cross-platform support (Linux, macOS)
- [ ] Performance optimizations for high-volume scenarios
- [ ] Integration with importance scoring for prioritization
- [ ] Multiple worker processes for high-volume environments

## Design Considerations for Queue Implementation

### Option 1: Reference-Based Queue (Lightweight)
- Make queue entries reference existing activity records (collection name + _key)
- Benefits: Small queue size, reduced duplication
- Implementation: Update queue schema to store references instead of full entity info

### Option 2: Edge Collection Approach
- Use ArangoDB edge collection to map events to queue agents
- Benefits:
  - Native graph queries for finding related entities
  - Timestamp-based ordering eliminates directory/file priority issues
  - Automatic cleanup when entities are removed
- Implementation: Create edge collection with from=activity record, to=processing agent

### Option 3: Real-Time Processing with Event Collection
- Process entities directly from the activity collection
- Use a processed flag or separate collection to track completion
- Benefits: No separate queue needed, works with existing data flow
- Implementation: Add timestamp-based processing to resolution service
