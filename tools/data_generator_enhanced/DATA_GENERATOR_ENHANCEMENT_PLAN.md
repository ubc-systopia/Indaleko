# Indaleko Data Generator Enhancement Plan

## Overview

This document outlines a comprehensive plan to enhance the Indaleko data generator tools to produce rich, diverse metadata that can be used to evaluate the effectiveness of Indaleko's query capabilities. The goal is to simulate a variety of metadata sources (semantic, storage, activity, etc.) with proper semantic attributes, enabling testing of how queries adapt and improve when different sources are available.

## Current Status

We have completed the following:

1. ✅ Fixed the `FileMetadataGeneratorTool` to properly generate semantic attributes
2. ✅ Fixed the `ActivityGeneratorTool` to properly generate semantic attributes
3. ✅ Created test suites to verify both tools work properly
4. ✅ Documented the changes and provided patch files

## Enhancement Priorities

Based on our analysis, the following enhancements are prioritized to achieve maximum metadata diversity:

### 1. Location Metadata (HIGH)

Enhancing the generation of location metadata would allow testing of location-based queries such as:
- "Find all files I accessed while in New York"
- "Show me documents I worked on while at the coffee shop"
- "Which files did I access during my trip to Europe?"

**Generator to enhance**: LocationGeneratorTool or integrate into ActivityGeneratorTool

### 2. EXIF Metadata (HIGH)

EXIF metadata is critical for image and media files, enabling queries like:
- "Find photos taken with a Canon camera"
- "Show me images taken in portrait orientation" 
- "Which photos were taken in low light conditions?"

**Generator to enhance**: SemanticMetadataGeneratorTool

### 3. Checksum and File Integrity Metadata (MEDIUM)

Checksum metadata enables content-based identification and duplication detection:
- "Find duplicate files across my devices"
- "Which files have been modified since the last backup?"
- "Show me all versions of this document"

**Generator to enhance**: SemanticMetadataGeneratorTool

### 4. Music and Media Metadata (MEDIUM)

Media metadata allows content-based queries for audio and video:
- "Find all songs by a specific artist"
- "Show me videos longer than 10 minutes"
- "Which podcasts did I listen to last month?"

**Generator to enhance**: SemanticMetadataGeneratorTool + integration with ActivityGeneratorTool

### 5. Environmental/Temperature Metadata (LOW)

Environmental context provides ambient information:
- "Find documents I worked on when it was raining"
- "Show me activities performed in hot weather"
- "Which tasks did I complete in coffee shops?"

**Generator to enhance**: Create new EnvironmentalMetadataGeneratorTool

### 6. Relationship Metadata (HIGH)

Relationship metadata connects different entities:
- "Show me files related to this project"
- "Find documents shared with Alice"
- "Which files are referenced in this email?"

**Generator to enhance**: RelationshipGeneratorTool (appears to be working correctly)

## Implementation Approach

For each priority area, we will:

1. **Analyze**: Examine the current generator implementation
2. **Enhance**: Add or fix methods to generate appropriate semantic attributes
3. **Test**: Create unit and integration tests to verify the enhancements
4. **Document**: Provide implementation details and usage examples

## Testing Strategy

1. **Unit Tests**: Test each generator in isolation
2. **Integration Tests**: Test generators working together
3. **Query Tests**: Verify that generated metadata can be queried effectively
4. **Ablation Tests**: Demonstrate how query effectiveness changes when specific metadata sources are removed

## Comprehensive Test Queries

We will develop 20 test queries that leverage multiple metadata types, such as:

1. "Find all Word documents I edited last week while in the office"
2. "Show me photos taken in New York that I shared with my team"
3. "Which presentations did I work on during meetings with the marketing department?"
4. "Find documents related to the project I was working on while listening to jazz music"

## Timeline and Dependencies

1. **Phase 1**: Location and EXIF metadata enhancements
2. **Phase 2**: Checksum and Media metadata enhancements
3. **Phase 3**: Environmental metadata and relationship enhancements
4. **Phase 4**: Comprehensive testing and query effectiveness evaluation

## Next Steps

1. Prioritize enhancement of Location metadata in the ActivityGeneratorTool
2. Enhance EXIF metadata generation in the SemanticMetadataGeneratorTool
3. Develop a standard testing framework to evaluate query effectiveness
4. Create a mechanism to selectively enable/disable metadata sources to demonstrate their impact on query results

## Success Criteria

The enhanced data generator will be considered successful when:

1. It can generate diverse, realistic metadata from at least 6-8 different sources
2. The semantic attributes in each metadata type conform to Indaleko's data model
3. All test queries can be executed successfully against the generated data
4. We can demonstrate measurable improvements in query results when multiple metadata sources are available