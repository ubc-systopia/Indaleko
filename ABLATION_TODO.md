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
- ✅ Expanded framework to include all 6 activity sources (music, geo, task, collaboration, storage, media)

## Current Tasks
- 🔄 Run the comprehensive ablation test with all 6 activity sources
- 🔄 Analyze impact of each activity type on query precision and recall
- 🔄 Document AQL transformations applied during ablation testing

## Future Tasks
- Create visualizations of ablation results
- Expand test dataset to more query types
- Implement statistical significance testing for results
- Formalize results for academic publication

## Implementation Notes

### Comprehensive Activity Sources
The enhanced ablation framework now tests all 6 major activity sources in Indaleko:

1. **Music Activity** - Music listening data from sources like Spotify
2. **Geographic Activity** - Location data from GPS, WiFi, and other sources
3. **Task Activity** - To-do lists, calendar events, and project tasks
4. **Collaboration Activity** - File sharing, meetings, and communication
5. **Storage Activity** - File operations like open, save, and delete
6. **Media Activity** - Video consumption, webinars, and streaming

### Enhanced Data Generation
The data generator creates files with explicit dependencies on activity data:

1. **Direct match files**: Match query criteria without activity data (~50% of positive examples)
2. **Activity-dependent files**: Only match when specific activity data is present (~50% of positive examples)
   - Each activity type gets an equal share of the activity-dependent files
   - Files are designed to only match when their specific activity data is present
3. **Negative files**: Should NOT match query criteria

This approach creates a clear dependency between activity data and query results, ensuring that ablation has a measurable impact on precision and recall.

### Truth Data Tracking
The truth data tracker records which files depend on which activity type, enabling detailed analysis of ablation impact:

- `positive_examples`: Tracks which files should match each query
- `negative_examples`: Tracks which files should not match
- `activity_dependency`: Tracks which files depend on which activity collections

### Running Comprehensive Tests
To run the comprehensive ablation test with all activity sources:
```bash
./run_comprehensive_ablation.sh
```

This will:
1. Reset the database
2. Generate test data for all 6 activity types
3. Run the comprehensive ablation test
4. Display a summary of the results

### Expected Results
The expected impact of ablation with this comprehensive setup:
- Baseline F1 Score: 1.0
- When ablating any single activity collection: Expected F1 ≈ 0.92 (specific to activity type)
- When ablating all activity collections: Expected F1 ≈ 0.5
EOF < /dev/null
