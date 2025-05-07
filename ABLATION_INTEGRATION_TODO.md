# Ablation Study Integration TODO List

This document outlines the tasks needed to integrate the ablation testing framework with real data generators to produce publishable results.

## Phase 1: Diagnose Generator Issues

- [ ] Inspect generator interfaces and parameters
  - [ ] Review StorageMetadataGeneratorImpl constructor and methods
  - [ ] Review ActivityMetadataGeneratorImpl constructor and methods
  - [ ] Review SemanticMetadataGeneratorImpl constructor and methods
  - [ ] Document expected parameters and return values for each

- [ ] Extract working generator code from existing components
  - [ ] Extract call patterns from run_comprehensive_ablation.py
  - [ ] Extract call patterns from test_db_integration.py
  - [ ] Document the parameters used in working examples

- [ ] Create test harness to validate generators in isolation
  - [ ] Test StorageMetadataGeneratorImpl with various configs
  - [ ] Test ActivityMetadataGeneratorImpl with various configs
  - [ ] Verify that data is generated correctly and matches schemas

## Phase 2: Fix Generator Integration

- [ ] Create adapter classes for each generator
  - [ ] Implement StorageGeneratorAdapter with proper interface
  - [ ] Implement ActivityGeneratorAdapter with proper interface
  - [ ] Implement SemanticGeneratorAdapter with proper interface
  - [ ] Add default configurations based on working examples

- [ ] Update ablation_integration_test.py
  - [ ] Replace direct generator usage with adapter classes
  - [ ] Fix data generation methods to use working patterns
  - [ ] Add robust error handling and validation

- [ ] Implement proper data conversion
  - [ ] Add methods to convert generated data to database format
  - [ ] Add validation to ensure data integrity
  - [ ] Fix any data type or schema mismatches

## Phase 3: Implement Minimal Test Case

- [ ] Create single file minimal test
  - [ ] Generate exactly 5 storage objects with fixed attributes
  - [ ] Create 3 activity records linked to these objects
  - [ ] Add 2 queries targeting specific metadata types
  - [ ] Perform ablation test on one collection
  - [ ] Capture and validate metrics

- [ ] Add detailed database logging
  - [ ] Log all AQL queries executed
  - [ ] Capture execution times
  - [ ] Verify ablation is working correctly

- [ ] Document exact test data
  - [ ] Create data manifests for all generated objects
  - [ ] Verify that Truth data is correctly recorded

## Phase 4: Verify Data Validity

- [ ] Implement data validation checks
  - [ ] Add validation for storage objects
  - [ ] Add validation for activity records
  - [ ] Add validation for truth data records
  - [ ] Ensure all required fields are present

- [ ] Create reproducibility tools
  - [ ] Implement database dump functionality 
  - [ ] Implement database restore functionality
  - [ ] Add options to reuse the same test data

- [ ] Add data statistical verification
  - [ ] Verify storage object distributions
  - [ ] Verify activity record distributions
  - [ ] Ensure representative test data

## Phase 5: Complete End-to-End Test

- [ ] Run small-scale end-to-end test
  - [ ] Generate 10 storage objects
  - [ ] Create 5 activity records
  - [ ] Run complete ablation test series
  - [ ] Generate detailed metrics report

- [ ] Validate result quality
  - [ ] Verify precision and recall calculations
  - [ ] Check F1 and impact metrics
  - [ ] Ensure metrics match expected patterns

- [ ] Generate publication-ready results
  - [ ] Create detailed report with metrics
  - [ ] Generate visualizations of results
  - [ ] Ensure all data is traceable and verifiable

## Phase 6: Scale to Full Study

- [ ] Increase dataset size incrementally
  - [ ] Test with 50 storage objects
  - [ ] Test with 100 storage objects 
  - [ ] Test with 200+ storage objects

- [ ] Implement performance optimizations
  - [ ] Add batch processing for large datasets
  - [ ] Optimize database queries
  - [ ] Add progress tracking for long-running tests

- [ ] Run full study with multiple clusters
  - [ ] Run tests with 3 different cluster configurations
  - [ ] Compare results across configurations
  - [ ] Generate comprehensive report

## Resources Needed

- Database access with write permissions
- Sufficient storage for test data (~1GB)
- 6-10 days of focused development time
- Knowledge of existing data generators and database schema