# Indaleko Synthetic Metadata Implementation Roadmap

## Overview

This document outlines our plan for implementing the remaining synthetic metadata generators for the Indaleko data generator. It prioritizes implementation order, defines dependencies, establishes success criteria, and ensures all necessary integrations for realistic search scenarios.

## Completed Implementations

- ✅ **LocationGeneratorTool** - Generates realistic location metadata with temporal patterns
- ✅ **EXIFGeneratorTool** - Generates comprehensive EXIF metadata for images

## Prioritized Implementation Plan

### Phase 1: Core Content & Entity Recognition

1. ✅ **UnstructuredMetadataGeneratorTool**
   - Extracts and generates content metadata from various file types
   - Produces text summaries, key phrases, entities mentioned
   - Includes both targeted content and random noise for realistic precision
   - **Success Criteria**: Generate content metadata with varying relevance to sample queries
   - **Key Integration**: Seed files must contain specific trigger content surrounded by noise

2. 🔲 **NamedEntityGeneratorTool**
   - Creates synthetic named entities (people, places, organizations)
   - Establishes entity relationships and references
   - Includes common reference points ("Home", "Work", "Dr. Oobi", "my sister")
   - **Success Criteria**: Entities must be queryable by natural language references
   - **Dependencies**: Must align with locations, calendar events, and unstructured content

### Phase 2: Activity & Social Contexts

3. 🔲 **SocialMediaActivityGeneratorTool**
   - Instagram-like posts with captions, locations, timestamps
   - User interactions, comments, and engagement patterns
   - **Success Criteria**: Enables cross-domain queries (like widget/sandwich example)
   - **Dependencies**: Integrates with EXIF data, unstructured content, and NER entities

4. ✅ **CalendarEventGeneratorTool**
   - Meeting events with attendees, locations, and topics
   - Recurring patterns and scheduling behaviors
   - **Success Criteria**: Events must be discoverable through natural language time references
   - **Dependencies**: Integrates with named entities and locations

### Phase 3: Storage Activity & File Integrity

5. ✅ **CloudStorageActivityGeneratorTool**
   - Google Drive and Dropbox activity patterns (creation, modification, sharing)
   - Cross-service integration with calendar events
   - **Success Criteria**: Activities show temporal relationships with other data
   - **Dependencies**: Aligns with file metadata and calendar events

6. ✅ **ChecksumGeneratorTool**
   - File integrity hashes (MD5, SHA-1, SHA-256, SHA-512, Dropbox)
   - File similarity markers and duplication support
   - **Success Criteria**: Enables deduplication and integrity verification queries
   - **Dependencies**: Must operate on existing file metadata records

### Phase 4: Media & Environmental Context

7. ✅ **MusicActivityGeneratorTool**
   - Spotify-like listening history with temporal patterns
   - Artist, genre, and preference metadata
   - **Success Criteria**: Music context must correlate with other activities
   - **Dependencies**: Temporal alignment with location and calendar data

8. ✅ **EnvironmentalMetadataGeneratorTool**
   - Weather conditions aligned with activities
   - Indoor climate data (temperature, humidity)
   - **Success Criteria**: Environmental data enables contextual queries
   - **Dependencies**: Must align with location data and timestamps

## Key Integration Requirements

### Named Entity Resolution

All implementations must consider named entity recognition:
- Create synthetic identities for entities mentioned in queries
- Establish relationships between entities
- Ensure entities are properly stored in NER collections
- Map informal references ("my sister") to specific entities

### Temporal Consistency

Time is the primary memory anchor:
- All metadata must have consistent timestamps
- Activity patterns should follow realistic temporal flows
- Historical patterns must emerge from the data (workdays vs. weekends)
- Time references in queries must map to appropriate metadata

### Spatial Correlation

Location provides critical context:
- Activities should be spatially coherent
- Location references must resolve to specific coordinates
- Common locations ("Home", "Work") must align across datasets
- Travel patterns must be realistic (no teleporting)

### Cross-Domain Correlations

The true power emerges from correlated data:
- Calendar events should align with locations
- File activities should correlate with application usage
- Media consumption should align with locations and times
- Social media posts should reference real activities

## Implementation Approach

For each generator, we will:

1. **Study Existing Collectors**:
   - Analyze corresponding real collectors in the Indaleko codebase
   - Use their data models as templates
   - Understand their semantic attribute patterns

2. **Develop the Generator Tool**:
   - Implement the core generation logic
   - Ensure proper semantic attribute creation
   - Add realistic variability and patterns

3. **Create Integration Tests**:
   - Test database persistence
   - Verify proper semantic attribute registration
   - Ensure cross-domain references work

4. **Document Usage Patterns**:
   - Create README documentation
   - Add example queries that utilize the metadata
   - Document expected search patterns

## Success Criteria

The enhanced data generator will be successful when:

1. It can generate a complete synthetic dataset that enables complex queries like:
   - "Files about widgets on the same day I had an amazing ham sandwich and posted it on Instagram"
   - "Documents I worked on when I was meeting with Dr. Oobi last month"
   - "Photos from my vacation in Nairobi last summer"

2. The synthetic data demonstrates:
   - Proper temporal consistency
   - Realistic activity patterns
   - Meaningful semantic attributes
   - Cross-domain correlations

3. Queries achieve appropriate precision and recall metrics:
   - High precision for specific queries with multiple constraints
   - Appropriate recall for broader contextual queries
   - Realistic false positives that mirror real-world scenarios

## Implementation Tracking

| Generator Tool | Dependencies | Started | Completed | Tests | Documentation | Integration |
|----------------|--------------|---------|-----------|-------|---------------|------------|
| LocationGeneratorTool | None | ✅ | ✅ | ✅ | ✅ | ✅ |
| EXIFGeneratorTool | Location | ✅ | ✅ | ✅ | ✅ | ✅ |
| UnstructuredMetadataGeneratorTool | None | ✅ | ✅ | ✅ | ✅ | ✅ |
| NamedEntityGeneratorTool | Location | ✅ | ✅ | ✅ | ✅ | ✅ |
| SocialMediaActivityGeneratorTool | EXIF, NER | ✅ | ✅ | ✅ | ✅ | ✅ |
| CalendarEventGeneratorTool | NER, Location | ✅ | ✅ | ✅ | ✅ | ✅ |
| CloudStorageActivityGeneratorTool | Calendar | ✅ | ✅ | ✅ | ✅ | ✅ |
| ChecksumGeneratorTool | None | ✅ | ✅ | ✅ | ✅ | ✅ |
| MusicActivityGeneratorTool | Location | ✅ | ✅ | ✅ | ✅ | ✅ |
| EnvironmentalMetadataGeneratorTool | Location | ✅ | ✅ | ✅ | ✅ | ✅ |
