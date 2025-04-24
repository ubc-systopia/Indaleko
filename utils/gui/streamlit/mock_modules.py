"""
Mock implementations of Indaleko modules for GUI development

This module provides mock implementations of Indaleko classes when the
real modules cannot be imported. This allows the GUI to run with limited
functionality even when imports fail.

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

# Mock IndalekoConstants
from datetime import UTC


class IndalekoConstants:
    default_prefix = "indaleko"


# Mock file_name_management functions
def find_candidate_files(patterns, directory):
    return []


def extract_keys_from_file_name(file_name):
    return {}


def generate_file_name(**kwargs):
    return "mock_file.json"


# Mock database classes
class MockDb:
    class aql:
        @staticmethod
        def execute(query, bind_vars=None, max_runtime=None):
            # Return mock data for different query types
            if "Storage" in query or "Volume" in query:
                return [
                    {"storage": "C:", "count": 1200},
                    {"storage": "D:", "count": 800},
                    {"storage": "OneDrive", "count": 450},
                    {"storage": "Dropbox", "count": 200},
                ]
            elif "extension" in query:
                return [
                    {"extension": "pdf", "count": 250},
                    {"extension": "docx", "count": 180},
                    {"extension": "jpg", "count": 320},
                    {"extension": "png", "count": 150},
                    {"extension": "xlsx", "count": 90},
                ]
            elif "Activity" in query or "timestamp" in query:
                # Generate dates for the past 7 days with decreasing counts
                from datetime import datetime, timedelta

                dates = []
                for i in range(7):
                    date = (datetime.now(UTC) - timedelta(days=i)).strftime(
                        "%Y-%m-%d",
                    )
                    count = 15 + (45 - 15) * (1 - i / 7)  # Decreasing trend
                    dates.append({"date": date, "count": int(count)})
                return dates
            else:
                # Generic search results
                import uuid
                from datetime import datetime

                return [
                    {
                        "_id": f"Objects/{i}",
                        "_key": str(uuid.uuid4()),
                        "Label": f"document{i}.pdf",
                        "type": "file",
                        "size": 1024 * (i + 1),
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                    for i in range(1, 6)
                ]

        @staticmethod
        def explain(query, bind_vars=None):
            """
            Generate a mock query execution plan.

            Args:
                query: The AQL query string
                bind_vars: Optional bind variables for the query

            Returns:
                Dictionary containing the query plan
            """
            # Create a mock execution plan with more comprehensive data
            return {
                "_is_explain_result": True,
                "plan": {
                    "nodes": [
                        {
                            "type": "SingletonNode",
                            "dependencies": [],
                            "id": 1,
                            "estimatedCost": 1,
                            "estimatedNrItems": 1,
                        },
                        {
                            "type": "EnumerateCollectionNode",
                            "dependencies": [1],
                            "id": 2,
                            "estimatedCost": 12.5,
                            "estimatedNrItems": 5,
                            "collection": "Objects",
                            "random": False,
                            "indexHint": None,
                        },
                        {
                            "type": "FilterNode",
                            "dependencies": [2],
                            "id": 3,
                            "estimatedCost": 17.5,
                            "estimatedNrItems": 3,
                            "condition": {
                                "type": "n-ary or",
                                "subNodes": [
                                    {
                                        "type": "n-ary and",
                                        "subNodes": [
                                            {
                                                "type": "compare !=",
                                                "subNodes": [
                                                    {
                                                        "type": "attribute access",
                                                        "name": "Label",
                                                        "subNodes": [
                                                            {
                                                                "type": "reference",
                                                                "name": "obj",
                                                                "id": 0,
                                                            },
                                                        ],
                                                    },
                                                    {"type": "value", "value": None},
                                                ],
                                            },
                                        ],
                                    },
                                ],
                            },
                        },
                        {
                            "type": "LimitNode",
                            "dependencies": [3],
                            "id": 4,
                            "estimatedCost": 18.5,
                            "estimatedNrItems": 3,
                            "offset": 0,
                            "limit": 20,
                        },
                        {
                            "type": "ReturnNode",
                            "dependencies": [4],
                            "id": 5,
                            "estimatedCost": 21.5,
                            "estimatedNrItems": 3,
                            "inVariable": {"id": 0, "name": "obj"},
                        },
                    ],
                    "rules": [
                        "move-calculations-up",
                        "remove-redundant-calculations",
                        "remove-unnecessary-calculations",
                        "move-filters-up",
                        "remove-unnecessary-filters",
                    ],
                    "collections": [{"name": "Objects", "type": "read"}],
                    "variables": [{"id": 0, "name": "obj"}],
                    "estimatedCost": 21.5,
                    "estimatedNrItems": 3,
                    "isModificationQuery": False,
                },
                "cacheable": True,
                "warnings": [],
                "stats": {"rulesExecuted": 17, "rulesSkipped": 33, "plansCreated": 1},
            }


class MockServiceManager:
    def __init__(self, *args, **kwargs):
        pass

    def is_connected(self):
        return True

    def get_collections_metadata(self):
        return {}

    def get_db(self):
        return MockDb()


class MockDBConfig:
    def __init__(self, *args, **kwargs):
        pass


class MockDBInfo:
    def __init__(self, *args, **kwargs):
        pass

    def get_collections_count(self):
        return 5

    def get_documents_count(self):
        return 1250

    def get_indexes_count(self):
        return 15

    def get_database_size(self):
        return "125.5 MB"

    def get_collections(self):
        return [
            {"name": "Objects", "type": "document", "status": "loaded", "count": 800},
            {"name": "Relationships", "type": "edge", "status": "loaded", "count": 450},
        ]

    def get_host(self):
        return "localhost"

    def get_port(self):
        return 8529

    def get_database_name(self):
        return "indaleko"

    def get_username(self):
        return "indaleko"


# Mock query processing classes
class EnhancedNLParser:
    def __init__(self, *args, **kwargs):
        pass

    def parse(self, query_text):
        return {"query": query_text, "entities": [], "collections": ["Objects"]}

    def parse_enhanced(self, query_text, **kwargs):
        return self.parse(query_text)


class EnhancedAQLTranslator:
    def __init__(self, *args, **kwargs):
        pass

    def translate(self, parsed_query):
        return type(
            "obj",
            (object,),
            {
                "query": "FOR doc IN Objects FILTER doc.Label != null RETURN doc",
                "bind_vars": {},
            },
        )

    def translate_enhanced(self, parsed_query, **kwargs):
        query_text = parsed_query.get("query", "") if isinstance(parsed_query, dict) else str(parsed_query)

        # Create a more realistic looking query based on the input text
        if "file" in query_text.lower() or "document" in query_text.lower():
            return type(
                "obj",
                (object,),
                {
                    "query": 'FOR obj IN Objects FILTER obj.type == "file" AND obj.Label != null RETURN obj',
                    "bind_vars": {},
                },
            )
        elif "image" in query_text.lower() or "photo" in query_text.lower():
            return type(
                "obj",
                (object,),
                {
                    "query": 'FOR obj IN Objects FILTER obj.type == "file" AND REGEX_TEST(obj.Label, ".jpg|.png|.gif$", true) RETURN obj',
                    "bind_vars": {},
                },
            )
        else:
            return type(
                "obj",
                (object,),
                {
                    "query": f'FOR obj IN Objects FILTER obj.Label != null AND LIKE(obj.Label, "%{query_text}%", true) RETURN obj',
                    "bind_vars": {"query_text": query_text},
                },
            )


class MockQueryProcessor:
    def __init__(self, *args, **kwargs):
        pass

    def execute(self, query_text, explain=False, **kwargs):
        """
        Execute a query.

        Args:
            query_text: The natural language query text
            explain: Whether to explain the query instead of executing it
            **kwargs: Additional parameters

        Returns:
            Results or explanation
        """
        if explain:
            # Return a more detailed plan with _is_explain_result marker
            result = MockDb.aql.explain(query_text)
            result["_is_explain_result"] = True
            return result
        else:
            # Always return at least some results for testing
            results = MockDb.aql.execute(query_text)
            if not results or len(results) == 0:
                # If no results, return mock data
                import uuid
                from datetime import datetime

                # Generate mock search results based on query
                search_term = query_text.lower()
                results = []

                # Add matching mock items - always add at least 5 items
                for i in range(1, 6):
                    filename = f"document{i}.pdf"
                    results.append(
                        {
                            "_id": f"Objects/{i}",
                            "_key": str(uuid.uuid4()),
                            "Label": filename,
                            "type": "file",
                            "size": 1024 * i,
                            "timestamp": datetime.now(UTC).isoformat(),
                            "Result": "Mock result",
                        },
                    )

                # Add a few extra results for queries that mention documents
                if "doc" in search_term or "file" in search_term:
                    for i in range(6, 9):
                        results.append(
                            {
                                "_id": f"Objects/{i}",
                                "_key": str(uuid.uuid4()),
                                "Label": f"report{i}.docx",
                                "type": "file",
                                "size": 2048 * i,
                                "timestamp": datetime.now(UTC).isoformat(),
                                "Result": "Mock result",
                            },
                        )

            return results


class AQLQueryExecutor:
    def __init__(self, *args, **kwargs):
        pass

    def execute(self, query, bind_vars=None, explain_only=False, **kwargs):
        # Return sample results or explanation
        if explain_only:
            return MockDb.aql.explain(query, bind_vars)
        else:
            return MockDb.aql.execute(query, bind_vars)


class FacetGenerator:
    def __init__(self, *args, **kwargs):
        pass

    def generate(self, results):
        """Generate dynamic facets from search results."""
        # For mock results, examine the structure and generate appropriate facets
        if not results or (not isinstance(results, list) and not isinstance(results, dict)):
            return {}

        facets = {}

        # If it's a list of dictionaries
        if isinstance(results, list) and results and isinstance(results[0], dict):
            # Extract keys from the first item
            sample = results[0]

            # Generate facets based on common fields
            if "type" in sample:
                facets["type"] = {"document": 8, "image": 5, "spreadsheet": 3}

            if "size" in sample:
                facets["size"] = {
                    "small (<100KB)": 6,
                    "medium (100KB-1MB)": 8,
                    "large (>1MB)": 4,
                }

            if "Label" in sample or "name" in sample:
                facets["extension"] = {
                    "pdf": 5,
                    "docx": 4,
                    "jpg": 3,
                    "xlsx": 2,
                    "txt": 1,
                }

        # Add some default facets if we didn't get any
        if not facets:
            facets = {
                "type": {"document": 10, "image": 5, "spreadsheet": 3},
                "size": {"small": 8, "medium": 6, "large": 4},
                "created_by": {"current_user": 12, "shared": 6},
            }

        return facets


# Mock platform classes
class IndalekoMachineConfig:
    def __init__(self, *args, **kwargs):
        pass


# Mock main Indaleko class
class Indaleko:
    def __init__(self, *args, **kwargs):
        pass

    def connect(self):
        return True

    def get_collection(self, name):
        return None
