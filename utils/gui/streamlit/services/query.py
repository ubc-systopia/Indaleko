"""
Query services for Indaleko Streamlit GUI

These services handle query execution and translation.

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

from utils.gui.streamlit.mock_modules import MockQueryProcessor


def execute_query(query_text, db_service, explain=False, debug=False):
    """
    Execute a query against the database.

    Args:
        query_text (str): The natural language query text
        db_service: IndalekoServiceManager or MockServiceManager object
        explain (bool): Whether to explain the query instead of executing it
        debug (bool): Whether to show debug information

    Returns:
        Results or explanation
    """
    # Create debug log area if in debug mode
    if debug:
        debug_container = st.expander("Debug Info", expanded=True)
        debug_log = debug_container.empty()
        debug_log.info("Starting query execution...")

        # Create progress container
        progress_container = debug_container.empty()
        progress_bars = {}
        progress_messages = {}
    else:
        debug_container = None
        debug_log = None
        progress_container = None
        progress_bars = {}
        progress_messages = {}

    # Log helper function
    def log_debug(message):
        if debug and debug_log:
            debug_log.info(message)

    # Progress callback function to visualize tool progress
    def progress_callback(progress_data):
        if debug and progress_container:
            tool_name = progress_data.tool_name
            stage = progress_data.stage
            message = progress_data.message
            progress = progress_data.progress

            # Create a unique key for this tool+stage combination
            key = f"{tool_name}_{stage}"

            # Update display in a thread-safe way (for Streamlit)
            with progress_container:
                # Create a progress bar for this stage if it doesn't exist
                if key not in progress_bars:
                    progress_bars[key] = st.progress(0, text=f"{tool_name} - {stage}")
                    progress_messages[key] = st.empty()

                # Update the progress bar and message
                if key in progress_bars:
                    progress_bars[key].progress(progress, text=f"{tool_name} - {stage} ({int(progress*100)}%)")
                    progress_messages[key].info(message)

                    # Display any additional data if available
                    if progress_data.data:
                        st.json(progress_data.data)

    try:
        # Try to import and use the Indaleko query tools first
        use_enhanced_query = False
        log_debug("Checking for Indaleko query tools...")

        try:
            # Import the query tools
            import query.tools.registry as registry
            from query.tools.database.executor import QueryExecutorTool
            from query.tools.translation.aql_translator import AQLTranslatorTool
            from query.tools.translation.nl_parser import NLParserTool

            log_debug("✅ Successfully imported query tools")
            use_enhanced_query = True
        except ImportError as e:
            log_debug(f"❌ Could not import query tools: {e}")
            use_enhanced_query = False

        # Use Indaleko's query tools if available
        if use_enhanced_query:
            log_debug("Using Indaleko query tools for translation")
            try:
                # Get the tool registry
                tool_registry = registry.get_registry()

                # Set progress callback if in debug mode
                if debug:
                    tool_registry.set_progress_callback(progress_callback)

                # Register tools if not already registered
                if not hasattr(tool_registry, "has_tool") or not tool_registry.has_tool("nl_parser"):
                    log_debug("Registering NLParserTool")
                    tool_registry.register_tool(NLParserTool)

                if not hasattr(tool_registry, "has_tool") or not tool_registry.has_tool("aql_translator"):
                    log_debug("Registering AQLTranslatorTool")
                    tool_registry.register_tool(AQLTranslatorTool)

                if not hasattr(tool_registry, "has_tool") or not tool_registry.has_tool("query_executor"):
                    log_debug("Registering QueryExecutorTool")
                    tool_registry.register_tool(QueryExecutorTool)

                # Execute the NL parser
                log_debug(f"Parsing query: {query_text}")
                parser_result = tool_registry.execute_tool(
                    "nl_parser",
                    {"query": query_text},
                )
                log_debug(f"Parser result: {parser_result}")

                # Execute the AQL translator
                log_debug("Translating to AQL")
                translator_result = tool_registry.execute_tool(
                    "aql_translator",
                    {"structured_query": parser_result.result},
                )
                log_debug(f"Translator result: {translator_result}")

                # Get the AQL query and bind vars
                aql_query = translator_result.result.get("aql_query", "")
                bind_vars = translator_result.result.get("bind_vars", {})

                # Display the AQL query
                if debug:
                    debug_container.code(aql_query, language="sql")
                    debug_container.json(bind_vars)

                # Execute or explain the query
                if explain:
                    log_debug("Explaining query")
                    executor_result = tool_registry.execute_tool(
                        "query_executor",
                        {
                            "query": aql_query,
                            "bind_vars": bind_vars,
                            "explain_only": True,
                            "include_plan": True,
                        },
                    )
                    result = executor_result.result

                    # Mark this as an explain result to handle it specially in the UI
                    if isinstance(result, dict):
                        result["_is_explain_result"] = True

                    return result
                else:
                    log_debug("Executing query")
                    executor_result = tool_registry.execute_tool(
                        "query_executor",
                        {
                            "query": aql_query,
                            "bind_vars": bind_vars,
                        },
                    )
                    log_debug(f"Found {len(executor_result.result)} results")
                    return executor_result.result

            except Exception as e:
                log_debug(f"❌ Error using query tools: {e}")
                log_debug("Falling back to direct AQL query")

        # Fall back to direct AQL if query tools not available or failed
        log_debug("Using direct AQL query execution")

        # Check if we have a real service manager with db_config
        if hasattr(db_service, 'db_config') and hasattr(db_service.db_config, 'db'):
            db = db_service.db_config.db
            log_debug("Connected to real ArangoDB database")

            # Use ArangoSearch views if available, otherwise fall back to regular queries
            # First, check if views exist
            views = db.views()
            if "ObjectsTextView" in views:
                log_debug("Using ArangoSearch view for text search")
                # Use the ArangoSearch view for more efficient text search
                query = """
                FOR doc IN ObjectsTextView
                SEARCH ANALYZER(
                    LIKE(doc.Label, @query) OR
                    LIKE(doc.Record.Attributes.URI, @query) OR
                    LIKE(doc.Record.Attributes.Description, @query) OR
                    LIKE(doc.Tags, @query),
                    "text_en"
                )
                SORT BM25(doc) DESC
                LIMIT 50
                RETURN doc
                """
            else:
                # Fall back to collections if views aren't available
                log_debug("No ArangoSearch views found, using regular collection query")
                # Check the collections in the database
                collections = db.collections()
                collection_names = [c["name"] for c in collections]

                if "Objects" in collection_names:
                    # Adapt query to the real DB schema
                    query = """
                    FOR obj IN Objects
                    FILTER obj.Label != null AND LIKE(obj.Label, CONCAT('%', @query, '%'), true)
                    LIMIT 50
                    RETURN obj
                    """

                if explain:
                    # Return execution plan
                    log_debug("Explaining AQL query")

                    try:
                        # Simple explain without options parameter which might not be supported
                        log_debug(f"Query to explain: {query}")
                        log_debug(f"Bind vars: {{'query': '{query_text}'}}")
                        plan = db.aql.explain(
                            query,
                            bind_vars={"query": query_text},
                        )
                        log_debug("Explain successful!")
                    except Exception as explain_error:
                        log_debug(f"Error in explain: {explain_error}")

                        # Try without bind vars
                        try:
                            log_debug("Trying explain without bind vars")
                            plan = db.aql.explain(query)
                            log_debug("Explain without bind vars successful!")
                        except Exception as second_error:
                            log_debug(f"Second explain error: {second_error}")
                            # Return error information in a usable format
                            plan = {
                                "_is_explain_result": True,
                                "error": str(explain_error),
                                "query": query,
                            }

                    # Mark this as an explain result to handle it specially in the UI
                    if isinstance(plan, dict):
                        plan["_is_explain_result"] = True

                    return plan
                else:
                    # Execute the query with max_runtime parameter
                    try:
                        # Show query being executed
                        if debug:
                            debug_container.code(query, language="sql")
                            debug_container.info(f"Searching for objects with Label like '%{query_text}%'")

                        # Execute query with 10 second max runtime
                        log_debug("Executing AQL query with 10s max_runtime")
                        cursor = db.aql.execute(
                            query,
                            bind_vars={"query": query_text},
                            max_runtime=10,  # 10 seconds
                        )
                        results = list(cursor)
                        log_debug(f"Query returned {len(results)} results")

                        if len(results) == 0:
                            log_debug("No results found, trying alternative query")
                            # Try with other views if available
                            if "NamedEntityTextView" in views:
                                log_debug("Trying NamedEntityTextView")
                                alt_query = """
                                FOR doc IN NamedEntityTextView
                                SEARCH ANALYZER(
                                    LIKE(doc.name, @query) OR
                                    LIKE(doc.description, @query) OR
                                    LIKE(doc.address, @query) OR
                                    LIKE(doc.tags, @query),
                                    "text_en"
                                )
                                SORT BM25(doc) DESC
                                LIMIT 30
                                RETURN doc
                                """
                            else:
                                # Fall back to a more permissive collection query
                                log_debug("No additional views found, using permissive collection query")
                                alt_query = """
                                FOR obj IN Objects
                                FILTER (obj.Label != null AND LIKE(obj.Label, CONCAT('%', @query, '%'), true))
                                   OR (obj.name != null AND LIKE(obj.name, CONCAT('%', @query, '%'), true))
                                   OR (obj._key != null AND CONTAINS(obj._key, @query, true))
                                LIMIT 30
                                RETURN obj
                                """

                            if debug:
                                debug_container.code(alt_query, language="sql")
                                debug_container.info("Trying alternative query...")

                            cursor = db.aql.execute(
                                alt_query,
                                bind_vars={"query": query_text},
                                max_runtime=10,  # 10 seconds
                            )
                            results = list(cursor)
                            log_debug(f"Alternative query returned {len(results)} results")

                        if len(results) == 0:
                            # Try with Activity view if available
                            if "ActivityTextView" in views:
                                log_debug("Trying ActivityTextView")
                                fallback_query = """
                                FOR doc IN ActivityTextView
                                SEARCH ANALYZER(
                                    LIKE(doc.Description, @query) OR
                                    LIKE(doc.Location, @query) OR
                                    LIKE(doc.Notes, @query) OR
                                    LIKE(doc.Tags, @query),
                                    "text_en"
                                )
                                SORT BM25(doc) DESC
                                LIMIT 30
                                RETURN doc
                                """
                            else:
                                # Try querying against Record.Attributes if it exists
                                log_debug("No activity view found, trying Record.Attributes query")
                                fallback_query = """
                                FOR obj IN Objects
                                FILTER obj.Record != null AND obj.Record.Attributes != null
                                LET filename = obj.Record.Attributes.URI
                                FILTER filename != null AND LIKE(filename, CONCAT('%', @query, '%'), true)
                                LIMIT 30
                                RETURN obj
                                """
                            if debug:
                                debug_container.code(fallback_query, language="sql")
                                debug_container.info("Trying Record.Attributes query...")

                            cursor = db.aql.execute(
                                fallback_query,
                                bind_vars={"query": query_text},
                                max_runtime=10,  # 10 seconds
                            )
                            results = list(cursor)
                            log_debug(f"Record.Attributes query returned {len(results)} results")

                        return results

                    except Exception as e:
                        log_debug(f"AQL query failed: {e}")

                        # Try a more generic query without LIKE operator
                        log_debug("Trying a more generic query")
                        generic_query = """
                        FOR obj IN Objects
                        LIMIT 20
                        RETURN obj
                        """

                        try:
                            if debug:
                                debug_container.code(generic_query, language="sql")
                                debug_container.info("Getting sample objects...")

                            cursor = db.aql.execute(generic_query, max_runtime=5)
                            results = list(cursor)
                            log_debug(f"Generic query returned {len(results)} results")

                            if isinstance(results, (list, tuple)) and len(results) > 0:
                                # We got some results, now let's check the schema
                                if debug:
                                    debug_container.info("Database schema sample:")
                                    debug_container.json(results[0])
                            elif isinstance(results, dict) and results:
                                # Dict result
                                if debug:
                                    debug_container.info("Database schema sample (dict):")
                                    debug_container.json(results)
                                return results
                            else:
                                log_debug("No results found, falling back to mock data")
                                return MockQueryProcessor().execute(query_text, explain)
                        except Exception as e2:
                            log_debug(f"Generic query failed: {e2}")
                            log_debug("Falling back to mock data")
                            return MockQueryProcessor().execute(query_text, explain)
            else:
                log_debug("Objects collection not found, falling back to mock data")
                return MockQueryProcessor().execute(query_text, explain)
        else:
            # Use mock processor if no real database
            log_debug("Using mock query processor")
            processor = MockQueryProcessor()
            return processor.execute(query_text, explain)
    except Exception as e:
        if debug:
            debug_container.error(f"Error executing query: {e}")
        else:
            st.error(f"Error executing query: {e}")

        # Return mock data if query fails
        log_debug("Returning mock data due to error")
        processor = MockQueryProcessor()
        return processor.execute(query_text, explain)
