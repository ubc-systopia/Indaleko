# Personal Digital Archivist

## Vision

The Personal Digital Archivist is an advanced evolution of Indaleko that proactively supports users by understanding their work context and history. 

Rather than merely responding to explicit queries, the archivist:

- Recognizes the current project or task context
- Identifies relevant historical work and resources
- Proactively suggests helpful information at appropriate times
- Explains the relevance and connections between current and past work
- Learns from user interactions to improve future suggestions

The ideal experience is exemplified by interactions like:

> **Archivist**: "Tony, I see you're working on a new machine learning project. This is similar to work you did four years ago on customer churn prediction. Would you like me to pull up some relevant files?"

## Architecture

### 1. Project Context Understanding

This component recognizes and understands project-level contexts from user activities:

- **Activity Clustering**: Groups related activities into coherent projects
- **Document Similarity**: Computes semantic similarity between documents
- **Temporal Analysis**: Identifies natural project boundaries and transitions
- **Cross-Project Comparison**: Measures similarity between current work and historical projects

```python
def compare_current_project(current_activities, historical_projects):
    """Compare current work to historical projects."""
    # Generate embeddings for current activities
    current_embedding = embed_project(current_activities)
    
    # Compare to historical projects
    similarities = []
    for project in historical_projects:
        project_embedding = embed_project(project.activities)
        similarity = cosine_similarity(current_embedding, project_embedding)
        
        # Enhance with topic and temporal factors
        topical_overlap = calculate_topic_overlap(current_activities, project)
        temporal_recency = calculate_recency_factor(project.end_date)
        
        # Weighted final score
        adjusted_similarity = similarity * 0.6 + topical_overlap * 0.3 + temporal_recency * 0.1
        
        similarities.append((project, adjusted_similarity))
    
    return sorted(similarities, key=lambda x: x[1], reverse=True)
```

### 2. User Model & Personalization

This component builds a comprehensive model of the user's work patterns:

- **Project History**: Database of past projects and their key resources
- **Activity Patterns**: Model of typical work rhythms and preferences
- **Resource Importance**: Learns which resources are most valuable in different contexts
- **Interaction Preferences**: Adapts to how and when the user prefers suggestions

```python
class UserModel:
    """Models user preferences, work patterns, and information needs."""
    
    def __init__(self, user_id):
        self.user_id = user_id
        self.projects = []
        self.activity_patterns = ActivityPatternLearner()
        self.suggestion_preferences = SuggestionPreferenceModel()
        self.resource_importance = ResourceImportanceModel()
    
    def predict_information_needs(self, context):
        """Predict what information the user might need in a given context."""
        # Find similar historical contexts
        similar_contexts = self.find_similar_contexts(context)
        
        # Extract resources accessed in similar contexts
        candidate_resources = []
        for similar_context, similarity in similar_contexts:
            resources = similar_context.get_accessed_resources()
            for resource in resources:
                predicted_importance = self.resource_importance.predict(
                    resource, context
                )
                candidate_resources.append((resource, predicted_importance * similarity))
        
        return sorted(candidate_resources, key=lambda x: x[1], reverse=True)
```

### 3. Proactive Suggestion Engine

This component decides what to suggest and when:

- **Relevance Scoring**: Ranks potential suggestions by relevance to current context
- **Timing Model**: Determines optimal timing for suggestions
- **Explanation Generation**: Creates natural language explanations for suggestions
- **Suggestion Delivery**: Manages how suggestions are presented to the user

```python
class ProactiveSuggestionEngine:
    """Generates timely, contextual suggestions based on user activities."""
    
    def generate_suggestions(self, current_context):
        # Get relevant historical projects
        similar_projects = find_similar_projects(current_context)
        
        # Extract candidate resources
        candidates = []
        for project, similarity in similar_projects:
            if similarity > 0.7:  # Threshold for relevance
                resources = project.get_key_resources()
                
                for resource in resources:
                    importance = predict_resource_importance(
                        resource, current_context, similarity
                    )
                    
                    candidates.append({
                        "resource": resource,
                        "relevance": similarity,
                        "importance": importance,
                        "source_project": project
                    })
        
        # Determine if this is a good time to suggest
        timing_score = evaluate_suggestion_timing(current_context)
        
        if timing_score > 0.8:  # Good time to suggest
            top_candidates = sort_and_filter_candidates(candidates)
            
            suggestions = []
            for candidate in top_candidates:
                explanation = generate_explanation(
                    candidate["resource"],
                    candidate["source_project"],
                    current_context
                )
                
                suggestions.append({
                    "resource": candidate["resource"],
                    "explanation": explanation,
                    "confidence": candidate["relevance"] * candidate["importance"]
                })
                
            return suggestions
        
        return []  # Not a good time for suggestions
```

### 4. Natural Language Interaction

This component manages the conversation with the user:

- **Dialogue Management**: Handles multi-turn conversations about suggestions
- **Natural Language Generation**: Creates fluent, contextual messages
- **Intent Understanding**: Interprets user responses to suggestions
- **Adaptive Communication**: Learns the user's preferred communication style

```python
def generate_suggestion_message(suggestion, confidence):
    """Generate a natural language message for a suggestion."""
    if confidence > 0.9:
        # High confidence template
        template = "Tony, I see you're working on {current_project}. This is similar to {past_project} from {time_ago}. Would you like me to pull up {resource_type} that might be relevant?"
    elif confidence > 0.7:
        # Medium confidence template
        template = "This reminds me of some work you did on {past_project}. There might be some {resource_type} from that project that could be helpful. Interested?"
    else:
        # Lower confidence template
        template = "You might want to check out some {resource_type} from {past_project} that seem somewhat related to what you're doing now."
    
    # Fill in template
    message = fill_template(
        template,
        current_project=current_context.project_name,
        past_project=suggestion["resource"].source_project.name,
        time_ago=format_relative_time(suggestion["resource"].source_project.end_date),
        resource_type=suggestion["resource"].type_description
    )
    
    return message
```

### 5. Learning from Interactions

This component improves the system based on user feedback:

- **Explicit Feedback**: Learns from direct user responses to suggestions
- **Implicit Feedback**: Observes how users interact with suggested resources
- **Model Updates**: Continuously refines suggestion quality and timing
- **Cold Start Handling**: Strategies for new users or projects

```python
class FeedbackLearningSystem:
    """Learns from explicit and implicit user feedback."""
    
    def record_explicit_feedback(self, suggestion, feedback):
        """Record explicit user feedback on a suggestion."""
        self.explicit_feedback.append({
            "suggestion": suggestion,
            "feedback": feedback,
            "timestamp": datetime.now(),
            "context": current_context
        })
        
        # Update models immediately
        update_models_from_explicit(suggestion, feedback)
    
    def record_implicit_feedback(self, suggestion, user_actions):
        """Record implicit feedback based on user actions."""
        engagement_level = calculate_engagement(user_actions)
        
        self.implicit_feedback.append({
            "suggestion": suggestion,
            "actions": user_actions,
            "engagement": engagement_level,
            "timestamp": datetime.now(),
            "context": current_context
        })
        
        # Update models from implicit feedback
        update_models_from_implicit(suggestion, engagement_level)
```

## Machine Learning Approaches

The Personal Digital Archivist leverages several ML approaches:

### 1. Document and Project Understanding

- **Sentence Transformers**: For semantic document embeddings
  ```python
  from sentence_transformers import SentenceTransformer
  model = SentenceTransformer('all-mpnet-base-v2')
  embeddings = model.encode(documents)
  ```

- **Topic Modeling**: To identify themes across documents
  ```python
  from bertopic import BERTopic
  topic_model = BERTopic()
  topics, probs = topic_model.fit_transform(documents)
  ```

- **Temporal Clustering**: To identify project boundaries
  ```python
  from sklearn.cluster import HDBSCAN
  clusterer = HDBSCAN(min_cluster_size=5, metric='precomputed')
  project_clusters = clusterer.fit_predict(activity_distance_matrix)
  ```

### 2. Personalized Relevance Models

- **Gradient Boosting**: For resource importance prediction
  ```python
  import xgboost as xgb
  features = ['semantic_similarity', 'days_since_last_access', 
              'access_frequency', 'creation_recency', 'topic_overlap']
  importance_model = xgb.XGBRegressor()
  importance_model.fit(X_train[features], y_train)
  ```

- **Collaborative Filtering**: To leverage similar users' patterns
  ```python
  from lightfm import LightFM
  model = LightFM(learning_rate=0.05, loss='warp')
  model.fit(interaction_matrix, epochs=20)
  ```

### 3. Interaction Timing and Preferences

- **Reinforcement Learning**: For optimal suggestion timing
  ```python
  from stable_baselines3 import PPO
  timing_model = PPO("MlpPolicy", timing_env)
  timing_model.learn(total_timesteps=10000)
  ```

- **Classification for User Preferences**:
  ```python
  from sklearn.ensemble import RandomForestClassifier
  pref_model = RandomForestClassifier()
  pref_model.fit(context_features, user_responses)
  ```

### 4. Multimodal Activity Correlation

- **Graph Neural Networks**: For complex activity relationships
  ```python
  import torch
  from torch_geometric.nn import GCNConv
  
  class ActivityGNN(torch.nn.Module):
      def __init__(self):
          super().__init__()
          self.conv1 = GCNConv(node_features, 64)
          self.conv2 = GCNConv(64, 32)
          self.classifier = torch.nn.Linear(32, num_activity_types)
  ```

## Implementation Path

To evolve Indaleko toward a Personal Digital Archivist, we recommend this incremental path:

### Phase 1: Project Recognition (3-4 months)
- Implement activity clustering into projects
- Build document embedding and similarity models
- Create basic project recognition
- Develop simple project comparison

### Phase 2: Basic Suggestions (2-3 months)
- Implement basic suggestion generation
- Create simple relevance ranking
- Add basic user interface for suggestions
- Build feedback collection mechanism

### Phase 3: User Modeling (3-4 months)
- Develop comprehensive user model
- Implement resource importance prediction
- Add suggestion timing model
- Create user preference learning

### Phase 4: Natural Language Interaction (2-3 months)
- Implement conversational suggestion interface
- Add multi-turn dialogue capabilities
- Create explanation generation
- Build adaptive communication style

### Phase 5: Advanced Learning (4-6 months)
- Implement reinforcement learning for timing
- Add graph neural networks for activity understanding
- Create cross-modal correlation models
- Develop advanced personalization

## Example Interactions

### Scenario 1: New Project with Historical Similarity

```
[User opens a new document and starts typing about machine learning approaches]

Archivist: [Notification appears] Tony, I see you're working on a machine learning project. This seems similar to your "Customer Churn Prediction" project from about 4 years ago. Would you like me to pull up some relevant files?

User: Yes, that would be helpful.

Archivist: Here are some files that might be relevant:
1. "churn_model_evaluation.ipynb" - This notebook contains your evaluation methodology for the model
2. "feature_engineering.py" - Contains functions for preprocessing customer data
3. "model_comparison.xlsx" - Spreadsheet comparing different algorithm performance

These were key files in your previous project. Would you like me to open any of these?

User: Open the notebook please.

Archivist: [Opens the notebook] I've opened the notebook. I notice you were using XGBoost and Random Forests for that project. Your current document mentions transformer models - would you like me to find your previous work with transformers as well?

User: Yes, that would be great.

Archivist: I found a project from 2 years ago where you used BERT for text classification. The main files were "bert_classifier.py" and "transformer_training.ipynb". Would you like to see these?
```

### Scenario 2: Related Document Discovery

```
[User is editing a document about security protocols]

Archivist: I noticed you're working on security protocols. Last month you downloaded a research paper on "Zero-Knowledge Proofs in Authentication Systems" that seems relevant to your current work. Would you like to see it?

User: What was that paper about again?

Archivist: The paper discusses implementing zero-knowledge proofs for authentication without revealing sensitive information. It includes implementation examples that might be helpful for the protocol you're describing in your current document.

User: That sounds useful, please open it.

Archivist: [Opens the paper] I've opened the paper. You also had some notes you took while reading this in "zkp_authentication_notes.md". Would you like to see those as well?
```

### Scenario 3: Context Restoration

```
[User opens a project they haven't worked on in several months]

Archivist: Welcome back to the "Data Lake Architecture" project, Tony. It's been about 3 months since you last worked on this. Would you like me to help you get back up to speed?

User: Yes, please.

Archivist: When you last worked on this project, you were focusing on:
1. Implementing partitioning strategies for the data lake
2. Researching query optimization for large datasets
3. Evaluating different file formats for analytical workloads

You left off reviewing the performance of Parquet vs ORC formats. The last files you modified were:
- "format_benchmark_results.py"
- "lake_partitioning_strategy.md"

Would you like me to open these files?
```

## Technical Requirements

- **Python 3.8+**: Core implementation language
- **PyTorch/TensorFlow**: For deep learning models
- **Sentence Transformers**: For document embeddings
- **scikit-learn**: For classical ML algorithms
- **LightFM/Implicit**: For collaborative filtering
- **DGL/PyTorch Geometric**: For graph neural networks
- **Stable Baselines3**: For reinforcement learning
- **FastAPI**: For service APIs
- **SQLAlchemy**: For persistent storage

## Privacy Considerations

The Personal Digital Archivist includes robust privacy protections:

- **Local Processing**: Core ML runs locally to keep sensitive data private
- **Transparency**: Clear explanations of why suggestions are made
- **User Control**: Easy opt-out for sensitive projects or contexts
- **Data Minimization**: Only essential information is stored
- **Configurability**: Granular control over suggestion behavior

## Self-Optimization Capabilities

The Archivist doesn't just learn about users - it also analyzes its own operation to improve system performance:

### 1. Database Performance Optimization

The Archivist monitors query patterns and performance to recommend database optimizations:

```python
class DatabaseOptimizationAnalyzer:
    """Analyzes query patterns to recommend database optimizations."""
    
    def __init__(self, db_connection, query_history_collector):
        self.db = db_connection
        self.query_history = query_history_collector
        self.index_analyzer = IndexAnalyzer(db_connection)
        self.view_analyzer = ViewAnalyzer(db_connection)
        
    def analyze_query_patterns(self, time_period=timedelta(days=7)):
        """Analyze recent query patterns to identify optimization opportunities."""
        # Get recent queries
        recent_queries = self.query_history.get_queries(
            start_time=datetime.now() - time_period
        )
        
        # Analyze for frequently accessed attributes
        attribute_frequency = self._extract_attribute_access_frequency(recent_queries)
        
        # Analyze query performance
        slow_queries = self._identify_slow_queries(recent_queries)
        
        # Generate index recommendations
        index_recommendations = self.index_analyzer.generate_recommendations(
            attribute_frequency, slow_queries
        )
        
        # Generate view recommendations
        view_recommendations = self.view_analyzer.generate_recommendations(
            attribute_frequency, slow_queries
        )
        
        return {
            "index_recommendations": index_recommendations,
            "view_recommendations": view_recommendations,
            "attribute_frequency": attribute_frequency,
            "slow_queries": slow_queries
        }
    
    def _extract_attribute_access_frequency(self, queries):
        """Extract frequency of attribute access in queries."""
        attribute_counts = {}
        
        for query in queries:
            # Extract accessed attributes from query
            attrs = self._extract_attributes_from_query(query)
            
            # Update counts
            for attr in attrs:
                if attr not in attribute_counts:
                    attribute_counts[attr] = 0
                attribute_counts[attr] += 1
        
        return attribute_counts
```

### 2. Index Management

The Archivist can intelligently manage indexes based on query patterns:

- **Index with Stored Values**: Creates ArangoDB indexes with stored values for frequently accessed fields to bypass document retrieval
- **Index Evaluation**: Measures the actual performance improvement of indexes
- **Cost-Benefit Analysis**: Weighs index maintenance costs against query performance improvements
- **Index Pruning**: Identifies and recommends removal of unused or low-value indexes

```python
class IndexRecommendation:
    """Recommendation for a database index."""
    
    def __init__(self, collection, fields, index_type, stored_values=None):
        self.collection = collection
        self.fields = fields
        self.index_type = index_type  # "hash", "skiplist", "persistent", etc.
        self.stored_values = stored_values or []
        self.estimated_impact = 0.0
        self.estimated_cost = 0.0
        self.affected_queries = []
    
    def calculate_impact(self, query_history, db_connection):
        """Calculate estimated impact of this index."""
        # Find queries that would benefit
        self.affected_queries = [
            q for q in query_history 
            if self._query_would_benefit(q)
        ]
        
        # If no affected queries, zero impact
        if not self.affected_queries:
            self.estimated_impact = 0.0
            return
        
        # Estimate execution time improvement
        with_index_time = self._estimate_execution_with_index(db_connection)
        current_time = sum(q.execution_time for q in self.affected_queries)
        time_saved = current_time - with_index_time
        
        # Calculate impact score based on time saved and query frequency
        query_count = len(self.affected_queries)
        self.estimated_impact = time_saved * query_count
        
        # Calculate maintenance cost
        self.estimated_cost = self._estimate_maintenance_cost(db_connection)
    
    def get_creation_command(self):
        """Get the ArangoDB command to create this index."""
        cmd = {
            "collection": self.collection,
            "type": self.index_type,
            "fields": self.fields,
        }
        
        if self.stored_values:
            cmd["storedValues"] = self.stored_values
            
        return cmd
```

### 3. Semantic Metadata Enhancement

The Archivist identifies areas where semantic metadata could be improved:

- **Missing Metadata Detection**: Identifies frequently searched concepts that lack proper semantic attributes
- **Semantic Attribute Refinement**: Suggests refinements to existing semantic attributes based on query effectiveness
- **Attribute Value Analysis**: Examines the distribution and utility of attribute values

```python
class SemanticMetadataAnalyzer:
    """Analyzes semantic metadata effectiveness and recommends improvements."""
    
    def identify_missing_semantic_attributes(self, query_history):
        """Identify potentially missing semantic attributes based on query patterns."""
        # Extract concepts frequently appearing in queries
        query_concepts = self._extract_concepts_from_queries(query_history)
        
        # Get existing semantic attributes
        existing_attributes = self._get_existing_semantic_attributes()
        
        # Identify gaps - concepts frequently queried but not well-represented in metadata
        missing_attributes = []
        for concept, frequency in query_concepts.items():
            coverage = self._calculate_concept_coverage(concept, existing_attributes)
            
            if coverage < 0.3 and frequency > 10:  # Thresholds for recommendation
                missing_attributes.append({
                    "concept": concept,
                    "query_frequency": frequency,
                    "current_coverage": coverage,
                    "suggested_attribute_name": self._suggest_attribute_name(concept)
                })
        
        return sorted(missing_attributes, key=lambda x: x["query_frequency"], reverse=True)
```

### 4. Collection Gap Analysis

The Archivist identifies types of data that would improve query results:

- **Failed Query Analysis**: Examines queries with poor results to identify missing data types
- **Collection Recommendation**: Suggests new data sources that would fill identified gaps
- **Value Estimation**: Estimates the value of collecting new data types based on query patterns

```python
class CollectionGapAnalyzer:
    """Analyzes query failures to identify data collection gaps."""
    
    def identify_collection_gaps(self, query_history):
        """Identify types of data that should be collected based on query patterns."""
        # Get queries with poor results
        poor_result_queries = [q for q in query_history if q.result_quality < 0.3]
        
        # Cluster similar queries
        query_clusters = self._cluster_similar_queries(poor_result_queries)
        
        # Analyze each cluster
        collection_recommendations = []
        for cluster in query_clusters:
            if len(cluster) >= 5:  # Only consider patterns with sufficient examples
                common_concepts = self._extract_common_concepts(cluster)
                existing_data = self._check_existing_data_for_concepts(common_concepts)
                
                if not existing_data:
                    recommendation = {
                        "concepts": common_concepts,
                        "query_count": len(cluster),
                        "sample_queries": [q.text for q in cluster[:3]],
                        "suggested_data_sources": self._suggest_data_sources(common_concepts)
                    }
                    collection_recommendations.append(recommendation)
        
        return collection_recommendations
```

### 5. Query Performance Analytics

The Archivist provides advanced query performance analytics:

- **Performance Trending**: Tracks query performance over time
- **Query Pattern Identification**: Identifies common query patterns and their performance
- **Execution Plan Analysis**: Analyzes query execution plans to find optimization opportunities
- **Bottleneck Detection**: Identifies performance bottlenecks in the query processing pipeline

```python
class QueryPerformanceAnalyzer:
    """Analyzes query performance trends and patterns."""
    
    def generate_performance_report(self, time_period=timedelta(days=30)):
        """Generate a comprehensive query performance report."""
        # Get historical query performance data
        historical_data = self._get_historical_performance(time_period)
        
        # Generate trend analysis
        trends = self._analyze_performance_trends(historical_data)
        
        # Identify problematic query patterns
        problem_patterns = self._identify_problematic_patterns(historical_data)
        
        # Generate execution plan insights
        execution_insights = self._analyze_execution_plans(problem_patterns)
        
        return {
            "performance_trends": trends,
            "problem_patterns": problem_patterns,
            "execution_insights": execution_insights,
            "optimization_opportunities": self._generate_optimization_opportunities(
                trends, problem_patterns, execution_insights
            )
        }
```

These self-optimization capabilities ensure that the Archivist continuously improves not just its understanding of the user, but also its own operation and performance.

## Contribution

This project is in the conceptual phase. Contributions welcome in these areas:

- Document embedding and similarity approaches
- Activity clustering algorithms
- User model development
- Suggestion relevance ranking
- Natural language generation for suggestions