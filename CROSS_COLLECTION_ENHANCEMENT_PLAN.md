# Cross-Collection Dependencies Enhancement Plan

This document outlines the implementation plan to address the zero correlative effect observed between Collaboration and Task activity data providers in our ablation study. The goal is to create meaningful relationships between these collections and enhance the query generation and translation processes to properly reflect real-world dependencies.

## Background

Our ablation testing revealed that removing the Collaboration collection had no measurable impact on Task-related queries, and vice versa (both showed 0.000 impact). This indicates that our synthetic data and query testing methodology do not capture the real-world relationships that should exist between these activity types.

## Implementation Objectives

1. **Create Entity References**: Establish shared entity references between collections
2. **Enhance Query Generation**: Produce queries that span multiple activity types
3. **Improve AQL Translation**: Generate AQL with JOINs between related collections
4. **Develop Meaningful Relationships**: Model realistic relationships between activities

## Detailed Implementation Plan

### 1. Implement Entity References Between Collections

The current implementation generates synthetic data for each collection in isolation. We need to modify our collectors and recorders to share entity references:

```python
# Example changes to TaskActivityCollector
def generate_task(self, collaboration_entities=None):
    """
    Generate a synthetic task with references to collaboration entities.
    """
    task = {
        "id": str(uuid.uuid4()),
        "task_type": random.choice(self.task_types),
        "status": random.choice(self.statuses),
        "timestamp": self.generate_timestamp(),
        # Link to collaboration entities when available
        "related_entities": [],
        "related_collections": []
    }
    
    # Create references to collaboration events when available
    if collaboration_entities and random.random() < 0.7:  # 70% chance
        related_collaboration = random.choice(collaboration_entities)
        task["related_entities"].append(related_collaboration["id"])
        task["related_collections"].append("Collaboration")
        task["assigned_in_meeting"] = related_collaboration["id"]  # Direct reference
        
    return task
```

The `BaseActivityRecorder` class should be enhanced to include methods for handling cross-collection references:

```python
def record_with_references(self, data, related_collections=None):
    """
    Record data with references to other collections.
    
    Args:
        data: Activity data to record
        related_collections: Dictionary mapping collection names to entity IDs
    """
    # Process standard recording
    result = self.record(data)
    
    # Add cross-collection references if provided
    if related_collections:
        for collection_name, entity_ids in related_collections.items():
            self.add_references(result["_id"], collection_name, entity_ids)
            
    return result
            
def add_references(self, entity_id, collection_name, referenced_ids):
    """
    Add relationships between entity and referenced entities.
    
    Args:
        entity_id: ID of the entity to reference from
        collection_name: Name of the collection containing referenced entities
        referenced_ids: List of entity IDs to reference
    """
    # Implementation would update relationship documents
```

### 2. Enhance Query Generation for Cross-Collection Queries

Our current query generation creates queries targeting single collections. We need to enhance this to create queries that naturally span multiple activity types:

```python
class EnhancedQueryGenerator:
    def __init__(self):
        # Add cross-collection templates
        self.cross_collection_templates = [
            "What tasks were assigned during {meeting_name} meeting?",
            "Show me all tasks with pending feedback from {participant}",
            "Which tasks were discussed in yesterday's {meeting_type} meeting?",
            "Compile {participant}'s feedback on {task_name} task",
            "When is the deadline for the tasks assigned in the {project} kickoff meeting?"
        ]
    
    def generate_cross_collection_query(self, activity_types=None):
        """
        Generate query that spans multiple activity types.
        
        Args:
            activity_types: List of activity types to include (e.g., ["Task", "Collaboration"])
                           If None, random activity types will be selected.
        """
        if not activity_types:
            # Select 2-3 random activity types
            activity_types = random.sample(self.activity_types, random.randint(2, 3))
            
        # Ensure we have task and collaboration if requested
        if "Task" in activity_types and "Collaboration" in activity_types:
            template = random.choice(self.cross_collection_templates)
            
            # Fill in the template with realistic values
            meeting_name = random.choice(["quarterly planning", "sprint review", "team sync", "project kickoff"])
            participant = random.choice(["Sarah", "John", "Maria", "Ahmed", "Taylor"])
            meeting_type = random.choice(["standup", "retrospective", "planning", "demo"])
            task_name = random.choice(["documentation", "bug fix", "feature implementation", "code review"])
            project = random.choice(["mobile app", "web portal", "database migration", "API redesign"])
            
            return template.format(
                meeting_name=meeting_name,
                participant=participant,
                meeting_type=meeting_type,
                task_name=task_name,
                project=project
            )
        
        # Fallback to standard query generation if needed
        return self.generate_query(activity_types[0])
```

### 3. Improve AQL Translation with JOINs and Relationships

Our AQL translator should detect opportunities for JOINs between collections:

```python
def translate_to_aql(self, query_text, collection=None):
    """
    Translate a natural language query to AQL.
    
    Args:
        query_text: Natural language query
        collection: Target collection (or None for auto-detection)
    
    Returns:
        AQL query string
    """
    # Detect if query could involve multiple collections
    related_collections = self.detect_related_collections(query_text)
    
    if len(related_collections) > 1 and "Task" in related_collections and "Collaboration" in related_collections:
        # Generate query with JOIN between task and collaboration
        return self.generate_cross_collection_aql(query_text, related_collections)
        
    # Fallback to standard single-collection query
    return self.generate_single_collection_aql(query_text, collection)
    
def generate_cross_collection_aql(self, query_text, collections):
    """
    Generate AQL with JOINs between collections.
    
    Args:
        query_text: Natural language query
        collections: List of collections to join
    
    Returns:
        AQL query with JOINs
    """
    # Example JOIN between Task and Collaboration
    if "Task" in collections and "Collaboration" in collections:
        aql = """
        FOR task IN AblationTaskActivity
            FOR meeting IN AblationCollaborationActivity
                FILTER task.related_entities ANY == meeting._id OR
                      (task.timestamp >= meeting.timestamp AND 
                       task.timestamp <= meeting.timestamp + 86400)
                FILTER {task_conditions} AND {meeting_conditions}
                RETURN { task: task, meeting: meeting }
        """
        
        # Extract conditions specific to each collection
        task_conditions = self.extract_conditions(query_text, "Task")
        meeting_conditions = self.extract_conditions(query_text, "Collaboration")
        
        return aql.format(
            task_conditions=task_conditions,
            meeting_conditions=meeting_conditions
        )
```

### 4. Create Meaningful Relationships in Synthetic Data

Implement realistic scenarios that create dependencies between collections:

```python
class CollaborationActivityCollector(ISyntheticCollector):
    def generate_meeting_with_tasks(self):
        """
        Generate a meeting that results in task assignments.
        
        Returns:
            Tuple of (meeting_data, list_of_tasks)
        """
        meeting = self.generate_meeting()
        
        # Generate tasks assigned during this meeting
        tasks = []
        for i in range(random.randint(1, 5)):
            task = {
                "id": str(uuid.uuid4()),
                "task_type": "action_item",
                "status": "pending",
                "description": f"Task assigned during {meeting['event_title']}",
                "assignee": random.choice(meeting["participants"])["name"],
                "assigned_in_meeting": meeting["id"],
                "timestamp": meeting["timestamp"] + random.randint(300, 1800)  # 5-30 min after meeting
            }
            tasks.append(task)
            
        # Update meeting with references to created tasks
        meeting["created_tasks"] = [task["id"] for task in tasks]
        
        return meeting, tasks

class TaskActivityCollector(ISyntheticCollector):
    def generate_feedback_sequence(self, task_id):
        """
        Generate a sequence of collaboration events providing feedback on a task.
        
        Args:
            task_id: ID of the task receiving feedback
            
        Returns:
            List of collaboration events (feedback, comments, reviews)
        """
        feedback_events = []
        for i in range(random.randint(1, 3)):
            feedback = {
                "id": str(uuid.uuid4()),
                "event_type": "feedback",
                "event_title": f"Feedback on task {task_id}",
                "participants": [
                    {"name": random.choice(self.participants), "role": "reviewer"},
                    {"name": random.choice(self.participants), "role": "assignee"}
                ],
                "target_task": task_id,
                "timestamp": self.generate_timestamp()
            }
            feedback_events.append(feedback)
            
        return feedback_events
```

### 5. Testing and Validation Approach

To validate our implementation:

1. Create unit tests for the cross-collection functionality:
```python
def test_task_meeting_relationship():
    """Test that tasks can be linked to collaboration meetings."""
    collector = CollaborationActivityCollector()
    meeting, tasks = collector.generate_meeting_with_tasks()
    
    # Verify meeting has task references
    assert "created_tasks" in meeting
    assert len(meeting["created_tasks"]) > 0
    
    # Verify tasks reference the meeting
    for task in tasks:
        assert "assigned_in_meeting" in task
        assert task["assigned_in_meeting"] == meeting["id"]
```

2. Run comprehensive ablation tests against the enhanced implementation

3. Validate that cross-collection impact metrics now show non-zero values, specifically:
   - Collaboration → Task should be > 0
   - Task → Collaboration should be > 0

4. Compare results before and after implementation to confirm we've resolved the zero-correlation issue

## Timeline and Priorities

1. First, implement entity references between collections (2 days)
2. Next, create meaningful relationships in synthetic data (2 days)
3. Then, enhance query generation for cross-collection queries (2 days)
4. Finally, improve AQL translation with JOINs (3 days)
5. Testing and validation of all changes (2 days)

## Expected Outcome

After implementation, we expect to see:

1. Non-zero impact values in the cross-collection dependency matrix
2. More realistic query behavior in the ablation testing
3. Better insights into how collections depend on each other
4. More scientifically valid ablation results

By implementing these changes, we'll create a more realistic model of how activity data is interconnected, providing better insights into the actual impact of data ablation in real-world scenarios.