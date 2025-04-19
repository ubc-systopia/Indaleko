"""
Database services for Indaleko Streamlit GUI

These services handle database operations and data retrieval.

Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import streamlit as st
from datetime import datetime, timezone, timedelta
from utils.gui.streamlit.mock_modules import MockDb

def get_db_stats(db_info):
    """
    Get database statistics for dashboard display
    
    Args:
        db_info: IndalekoDBInfo or MockDBInfo object
        
    Returns:
        dict: Statistics about the database (collections, documents, indexes, size)
    """
    try:
        stats = {}

        # Handle both mock and real IndalekoDBInfo objects
        if hasattr(db_info, 'get_collections'):
            # Real IndalekoDBInfo
            collections = db_info.get_collections()
            stats["collections"] = len(collections)

            # Count documents across all collections
            doc_count = 0
            for collection in collections:
                try:
                    coll_obj = db_info.db_config.db.collection(collection)
                    doc_count += coll_obj.count()
                except Exception:
                    pass
            stats["documents"] = doc_count

            # Count indexes
            indexes_count = 0
            for collection in collections:
                try:
                    coll_obj = db_info.db_config.db.collection(collection)
                    indexes = coll_obj.indexes()
                    indexes_count += len(indexes)
                except Exception:
                    pass
            stats["indexes"] = indexes_count

            # Get size from DB statistics
            try:
                db_stats = db_info.db_config.db.statistics()
                stats["size"] = f"{db_stats.get('database', {}).get('file_size', 0) / (1024*1024):.1f} MB"
            except Exception:
                stats["size"] = "Unknown"

        else:
            # Mock object with get_collections_count() method
            stats["collections"] = db_info.get_collections_count()
            stats["documents"] = db_info.get_documents_count()
            stats["indexes"] = db_info.get_indexes_count()
            stats["size"] = db_info.get_database_size()

        return stats
    except Exception as e:
        st.error(f"Error getting database stats: {e}")
        return None

def get_storage_summary(db_service):
    """
    Get storage volume distribution data for charts
    
    Args:
        db_service: IndalekoServiceManager or MockServiceManager object
        
    Returns:
        list: List of dictionaries with storage volume counts
    """
    try:
        # Determine if this is a real service manager or a mock
        if hasattr(db_service, 'db_config') and hasattr(db_service.db_config, 'db'):
            # Real IndalekoServiceManager
            db = db_service.db_config.db
            # Check if the Objects collection exists
            collections = db.collections()
            collection_names = [c["name"] for c in collections]

            if "Objects" in collection_names:
                try:
                    # Try to query the Objects collection - without timeout parameter
                    cursor = db.aql.execute(
                        """
                        FOR obj IN Objects
                        FILTER obj.Record != null AND obj.Record.Attributes != null
                        COLLECT storage = obj.Record.Attributes.Volume WITH COUNT INTO count
                        RETURN {storage, count}
                        """
                    )
                    results = list(cursor)
                    if results:
                        return results
                except Exception as e:
                    st.warning(f"Error querying Objects collection: {e}. Trying alternative query.")

                # Try alternative fields
                try:
                    cursor = db.aql.execute(
                        """
                        FOR obj IN Objects
                        FILTER obj.type == 'file' OR obj.Label != null
                        COLLECT storage = (obj.volume != null ? obj.volume :
                                         (obj.Record != null && obj.Record.Attributes != null &&
                                          obj.Record.Attributes.Volume != null ?
                                          obj.Record.Attributes.Volume : "Unknown"))
                        WITH COUNT INTO count
                        RETURN {storage, count}
                        """
                    )
                    results = list(cursor)
                    if results:
                        return results
                except Exception as e:
                    st.warning(f"Error running alternative query: {e}. Falling back to mock data.")
            else:
                st.warning("Objects collection not found. Falling back to mock data.")
        else:
            # Mock object
            return db_service.get_db().aql.execute(
                "FOR obj IN Objects FILTER obj.type == 'file' COLLECT storage = obj.volume WITH COUNT INTO count RETURN {storage, count}"
            )
    except Exception as e:
        st.error(f"Error getting storage summary: {e}")

    # Return mock data as fallback
    return [
        {"storage": "C:", "count": 1200},
        {"storage": "D:", "count": 800},
        {"storage": "OneDrive", "count": 450},
        {"storage": "Dropbox", "count": 200}
    ]

def get_file_type_distribution(db_service):
    """
    Get file extension distribution data for charts
    
    Args:
        db_service: IndalekoServiceManager or MockServiceManager object
        
    Returns:
        list: List of dictionaries with file extension counts
    """
    try:
        # Determine if this is a real service manager or a mock
        if hasattr(db_service, 'db_config') and hasattr(db_service.db_config, 'db'):
            # Real IndalekoServiceManager
            db = db_service.db_config.db
            # Check if the Objects collection exists
            collections = db.collections()
            collection_names = [c["name"] for c in collections]

            if "Objects" in collection_names:
                try:
                    # Try to query the Objects collection with proper field names - without timeout
                    cursor = db.aql.execute(
                        """
                        FOR obj IN Objects
                        FILTER obj.Label != null
                        LET ext = REVERSE(SPLIT(obj.Label, '.', 1))[0]
                        FILTER ext != obj.Label
                        COLLECT extension = ext WITH COUNT INTO count
                        SORT count DESC LIMIT 10
                        RETURN {extension, count}
                        """
                    )
                    results = list(cursor)
                    if results:
                        return results
                except Exception as e:
                    st.warning(f"Error querying Objects collection: {e}. Trying alternative query.")

                # Try alternative fields
                try:
                    cursor = db.aql.execute(
                        """
                        FOR obj IN Objects
                        FILTER obj.type == 'file' OR obj.name != null OR obj.Label != null
                        LET filename = (obj.Label != null ? obj.Label : (obj.name != null ? obj.name : "unknown"))
                        LET ext = REVERSE(SPLIT(filename, '.', 1))[0]
                        FILTER ext != filename
                        COLLECT extension = ext WITH COUNT INTO count
                        SORT count DESC LIMIT 10
                        RETURN {extension, count}
                        """
                    )
                    results = list(cursor)
                    if results:
                        return results
                except Exception as e:
                    st.warning(f"Error running alternative query: {e}. Falling back to mock data.")
            else:
                st.warning("Objects collection not found. Falling back to mock data.")
        else:
            # Mock object
            return db_service.get_db().aql.execute(
                "FOR obj IN Objects FILTER obj.type == 'file' LET ext = REVERSE(SPLIT(obj.name, '.', 1))[0] FILTER ext != obj.name COLLECT extension = ext WITH COUNT INTO count SORT count DESC LIMIT 10 RETURN {extension, count}"
            )
    except Exception as e:
        st.error(f"Error getting file type distribution: {e}")

    # Return mock data as fallback
    return [
        {"extension": "pdf", "count": 250},
        {"extension": "docx", "count": 180},
        {"extension": "jpg", "count": 320},
        {"extension": "png", "count": 150},
        {"extension": "xlsx", "count": 90}
    ]

def get_activity_timeline(db_service):
    """
    Get activity timeline data for charts
    
    Args:
        db_service: IndalekoServiceManager or MockServiceManager object
        
    Returns:
        list: List of dictionaries with activity dates and counts
    """
    try:
        # Determine if this is a real service manager or a mock
        if hasattr(db_service, 'db_config') and hasattr(db_service.db_config, 'db'):
            # Real IndalekoServiceManager
            db = db_service.db_config.db

            # Check for collections that might contain activity data
            collections = db.collections()
            collection_names = [c["name"] for c in collections]

            activity_collections = [name for name in collection_names if "Activity" in name]

            if activity_collections:
                # Try each possible activity collection
                for collection_name in activity_collections:
                    try:
                        # Try to query this collection
                        aql_query = f"""
                        FOR act IN {collection_name}
                        FILTER act.timestamp != null
                        COLLECT date = DATE_TRUNC(act.timestamp, 'day')
                        WITH COUNT INTO count
                        SORT date
                        RETURN {{date: DATE_ISO8601(date), count}}
                        """

                        cursor = db.aql.execute(aql_query)
                        results = list(cursor)
                        if results:
                            return results
                    except Exception as e:
                        st.warning(f"Error querying {collection_name}: {e}")

                # Try ActivityContext collection if it exists
                if "ActivityContext" in collection_names:
                    try:
                        aql_query = """
                        FOR act IN ActivityContext
                        FILTER act.Timestamp != null
                        COLLECT date = DATE_TRUNC(act.Timestamp, 'day')
                        WITH COUNT INTO count
                        SORT date
                        RETURN {date: DATE_ISO8601(date), count}
                        """

                        cursor = db.aql.execute(aql_query)
                        results = list(cursor)
                        if results:
                            return results
                    except Exception as e:
                        st.warning(f"Error querying ActivityContext: {e}")
            else:
                st.warning("No activity collections found. Falling back to mock data.")
        else:
            # Mock object
            return db_service.get_db().aql.execute(
                "FOR act IN Activity COLLECT date = DATE_TRUNC(act.timestamp, 'day') WITH COUNT INTO count SORT date RETURN {date: DATE_ISO8601(date), count}"
            )
    except Exception as e:
        st.error(f"Error getting activity timeline: {e}")

    # Return mock data as fallback
    return [
        {"date": "2025-04-01", "count": 45},
        {"date": "2025-04-02", "count": 62},
        {"date": "2025-04-03", "count": 38},
        {"date": "2025-04-04", "count": 51},
        {"date": "2025-04-05", "count": 29},
        {"date": "2025-04-06", "count": 15},
        {"date": "2025-04-07", "count": 42}
    ]

def get_cross_source_patterns(db_service):
    """
    Get cross-source pattern data for visualization
    
    Args:
        db_service: IndalekoServiceManager or MockServiceManager object
        
    Returns:
        dict: Dictionary with patterns, correlations, and suggestions data
    """
    try:
        # Determine if this is a real service manager or a mock
        if hasattr(db_service, 'db_config') and hasattr(db_service.db_config, 'db'):
            # Real IndalekoServiceManager
            db = db_service.db_config.db
            
            # Get patterns, correlations, and suggestions
            patterns = _get_patterns_from_db(db)
            correlations = _get_correlations_from_db(db)
            suggestions = _get_suggestions_from_db(db)
            
            if patterns or correlations or suggestions:
                recent_correlations = [c for c in correlations if c.get("is_recent", False)]
                active_suggestions = [s for s in suggestions if not s.get("is_expired", False)]
                
                return {
                    "patterns": patterns,
                    "correlations": correlations,
                    "suggestions": suggestions,
                    "recent_correlations": recent_correlations,
                    "active_suggestions": active_suggestions
                }
        else:
            # Mock object
            if hasattr(db_service, 'get_cross_source_patterns'):
                return db_service.get_cross_source_patterns()
    except Exception as e:
        st.error(f"Error getting cross-source pattern data: {e}")
    
    # Return mock data as fallback
    return _get_mock_pattern_data()

def _get_patterns_from_db(db):
    """Get patterns from database"""
    collection_name = "CrossSourcePatterns"
    if not db.has_collection(collection_name):
        return []
        
    try:
        collection = db.collection(collection_name)
        cursor = collection.all(
            limit=100  # Limit to 100 patterns
        )
        
        return list(cursor)
    except Exception as e:
        st.warning(f"Error getting patterns from database: {e}")
        return []
    
def _get_correlations_from_db(db):
    """Get correlations from database"""
    collection_name = "CrossSourceCorrelations"
    if not db.has_collection(collection_name):
        return []
        
    try:
        collection = db.collection(collection_name)
        now = datetime.now(timezone.utc)
        one_day_ago = (now - timedelta(days=1)).isoformat()
        
        # Get all correlations, mark recent ones
        cursor = collection.all(
            limit=100  # Limit to 100 correlations
        )
        
        # Process results to add is_recent flag
        results = []
        for doc in cursor:
            # Add is_recent flag
            if "timestamp" in doc:
                doc["is_recent"] = doc["timestamp"] > one_day_ago
            results.append(doc)
            
        return results
    except Exception as e:
        st.warning(f"Error getting correlations from database: {e}")
        return []
    
def _get_suggestions_from_db(db):
    """Get suggestions from database"""
    collection_name = "ProactiveSuggestions"
    if not db.has_collection(collection_name):
        return []
        
    try:
        collection = db.collection(collection_name)
        now = datetime.now(timezone.utc)
        
        # Get active (not expired, not dismissed) suggestions
        cursor = db.aql.execute(
            f"""
            FOR s IN {collection_name}
            FILTER s.dismissed != true
            FILTER s.expires_at == null OR s.expires_at > "{now.isoformat()}"
            SORT s.priority ASC, s.confidence DESC
            LIMIT 20
            RETURN s
            """
        )
        
        # Process results to add is_expired flag
        results = []
        for doc in cursor:
            # Add is_expired flag
            if "expires_at" in doc and doc["expires_at"]:
                doc["is_expired"] = doc["expires_at"] < now.isoformat()
            else:
                doc["is_expired"] = False
            results.append(doc)
            
        return results
    except Exception as e:
        st.warning(f"Error getting suggestions from database: {e}")
        return []

def _get_mock_pattern_data():
    """Return mock pattern data for testing"""
    now = datetime.now(timezone.utc)
    
    # Create mock patterns
    patterns = [
        {
            "pattern_id": "p1",
            "pattern_name": "Cross-source pattern: ntfs + collaboration",
            "description": "File activities followed by collaboration events",
            "confidence": 0.82,
            "source_types": ["ntfs", "collaboration"],
            "observation_count": 15,
            "last_observed": (now - timedelta(hours=3)).isoformat()
        },
        {
            "pattern_id": "p2",
            "pattern_name": "Cross-source pattern: location + ntfs",
            "description": "File activities associated with specific locations",
            "confidence": 0.67,
            "source_types": ["location", "ntfs"],
            "observation_count": 8,
            "last_observed": (now - timedelta(hours=5)).isoformat()
        },
        {
            "pattern_id": "p3",
            "pattern_name": "Cross-source pattern: ambient + collaboration",
            "description": "Music activity followed by collaboration events",
            "confidence": 0.75,
            "source_types": ["ambient", "collaboration"],
            "observation_count": 12,
            "last_observed": (now - timedelta(hours=8)).isoformat()
        },
        {
            "pattern_id": "p4",
            "pattern_name": "Hour pattern: ntfs at 14:00",
            "description": "File activity frequently occurs around 14:00-15:00",
            "confidence": 0.79,
            "source_types": ["ntfs"],
            "observation_count": 21,
            "last_observed": (now - timedelta(hours=2)).isoformat()
        },
        {
            "pattern_id": "p5",
            "pattern_name": "Day pattern: collaboration on Tuesday",
            "description": "Collaboration activity frequently occurs on Tuesdays",
            "confidence": 0.63,
            "source_types": ["collaboration"],
            "observation_count": 9,
            "last_observed": (now - timedelta(days=2)).isoformat()
        }
    ]
    
    # Create mock correlations
    correlations = [
        {
            "correlation_id": "c1",
            "description": "Correlation between Ntfs and Collaboration events",
            "confidence": 0.85,
            "source_types": ["ntfs", "collaboration"],
            "timestamp": (now - timedelta(hours=2)).isoformat(),
            "is_recent": True
        },
        {
            "correlation_id": "c2",
            "description": "Correlation between Location and Ntfs events",
            "confidence": 0.72,
            "source_types": ["location", "ntfs"],
            "timestamp": (now - timedelta(hours=4)).isoformat(),
            "is_recent": True
        },
        {
            "correlation_id": "c3",
            "description": "Correlation between Ambient and Collaboration events",
            "confidence": 0.68,
            "source_types": ["ambient", "collaboration"],
            "timestamp": (now - timedelta(hours=6)).isoformat(),
            "is_recent": True
        },
        {
            "correlation_id": "c4",
            "description": "Correlation between Query and Ntfs events",
            "confidence": 0.76,
            "source_types": ["query", "ntfs"],
            "timestamp": (now - timedelta(hours=12)).isoformat(),
            "is_recent": False
        }
    ]
    
    # Create mock suggestions
    suggestions = [
        {
            "suggestion_id": "s1",
            "suggestion_type": "content",
            "title": "Files relevant to your location",
            "content": "Based on your patterns, we've noticed you typically access certain files when at this location. Would you like to see them?",
            "priority": "medium",
            "confidence": 0.78,
            "created_at": (now - timedelta(hours=1)).isoformat(),
            "expires_at": (now + timedelta(days=1)).isoformat(),
            "is_expired": False,
            "dismissed": False
        },
        {
            "suggestion_id": "s2",
            "suggestion_type": "search_strategy",
            "title": "Search strategy suggestion",
            "content": "Your search patterns and file activities show a connection. Consider using more specific file-related terms in your searches.",
            "priority": "low",
            "confidence": 0.65,
            "created_at": (now - timedelta(hours=3)).isoformat(),
            "expires_at": (now + timedelta(days=3)).isoformat(),
            "is_expired": False,
            "dismissed": False
        },
        {
            "suggestion_id": "s3",
            "suggestion_type": "related_content",
            "title": "Connection between Ambient and Collaboration",
            "content": "We've noticed a correlation between your Ambient and Collaboration activities. Would you like to explore this connection?",
            "priority": "high",
            "confidence": 0.81,
            "created_at": (now - timedelta(hours=0.5)).isoformat(),
            "expires_at": (now + timedelta(days=2)).isoformat(),
            "is_expired": False,
            "dismissed": False
        }
    ]
    
    return {
        "patterns": patterns,
        "correlations": correlations,
        "suggestions": suggestions,
        "recent_correlations": [c for c in correlations if c.get("is_recent", False)],
        "active_suggestions": [s for s in suggestions if not s.get("is_expired", False)]
    }