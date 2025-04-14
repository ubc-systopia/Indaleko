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