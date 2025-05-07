# Ablation Framework TODO List

## Completed Tasks
- ✅ Fixed LIMIT statement issue in AQL queries
- ✅ Implemented proper collection ablation mechanism using `IndalekoDBCollectionsMetadata`
- ✅ Created metrics calculation for precision, recall, F1, and impact
- ✅ Fixed the `IndalekoCollections is not iterable` bug
- ✅ Implemented test data generation with both positive and negative examples
- ✅ Created controlled semantic attributes that correlate with query criteria
- ✅ Implemented activity data generation (music, geo) that links to file objects
- ✅ Built comprehensive testing shell script to run the full ablation process
- ✅ Enhanced data generation to create stronger dependencies between activities and search results

## Current Tasks
- 🔄 Run the enhanced ablation test and validate metrics
- 🔄 Analyze impact of activity data on query precision and recall
- 🔄 Document AQL transformations applied during ablation testing

## Future Tasks
- Create visualizations of ablation results
- Expand test dataset to more query types
- Add more activity data types (temperature, task, collaboration)
- Implement statistical significance testing for results
- Formalize results for academic publication

## Implementation Notes

### Enhanced Data Generation
The enhanced data generator now creates three distinct classes of data:

1. **Direct match files**: Match query criteria without activity data (~40% of positive examples)
2. **Activity-dependent files**: Only match when specific activity data is present (~60% of positive examples)
   - Music-dependent files: Require music activity data to match
   - Geo-dependent files: Require geo activity data to match
3. **Negative files**: Should NOT match query criteria

This approach creates a clear dependency between activity data and query results, ensuring that ablation has a measurable impact on precision and recall.

### Key Dependencies
- Files dependent on music activity only match when music activity is present
- Files dependent on geo activity only match when geo activity is present
- When both music and geo are ablated, only direct match files should match

### Truth Data Tracking
The truth data tracker now records which files depend on which activity type, enabling detailed analysis of ablation impact:

- `positive_examples`: Tracks which files should match each query
- `negative_examples`: Tracks which files should not match
- `activity_dependency`: Tracks which files depend on which activity collections

### Dependency Percentages
The default configuration creates:
- 40% direct match files (match without activity data)
- 30% music-dependent files (require music activity to match)
- 30% geo-dependent files (require geo activity to match)

This distribution ensures that ablation of any collection has a measurable impact on results.

### Running Enhanced Tests
To run the comprehensive ablation test with enhanced data generation:
```bash
./run_ablation_enhanced.sh
```

This will:
1. Reset the database
2. Generate test data with strong activity dependencies
3. Run the comprehensive ablation test
4. Display a summary of the results

### Expected Results
The expected impact of ablation with this enhanced setup:
- Baseline F1 Score: 1.0
- When ablating music collection: Expected F1 ≈ 0.7
- When ablating geo collection: Expected F1 ≈ 0.7
- When ablating both collections: Expected F1 ≈ 0.4