"""
Common UI utility functions and components.

This module provides shared UI components and helper functions
used across the Indaleko GUI.

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


def normalize_for_display(item):
    """
    Normalize a dictionary item for display in a dataframe.
    Flattens nested structures and converts non-primitive values to strings.

    Args:
        item (dict): The dictionary to normalize

    Returns:
        dict: A normalized dictionary suitable for dataframe display
    """
    if not isinstance(item, dict):
        return {"value": str(item)}

    result = {}
    for key, value in item.items():
        # Skip complex nested objects or convert them to strings
        if isinstance(value, (dict, list, tuple)) and key not in {"_key", "_id"}:
            # For complex objects, just store a string representation
            if isinstance(value, dict):
                result[key] = "{...}"  # Dict representation
            elif isinstance(value, list):
                result[key] = f"[{len(value)} items]"  # List length
            else:
                result[key] = str(value)  # Other complex types
        else:
            # Pass simple values through directly
            result[key] = value
    return result


def display_search_results(search_results) -> None:
    """
    Display search results in the UI, with proper handling of different result types.
    This function uses a simple, direct approach that avoids dataframe conversion issues.

    Args:
        search_results: The search results to display (can be list, dict, or other)
    """
    # Safety check
    if search_results is None:
        st.warning("No results to display")
        return

    # Check if this is an explain result that needs special handling
    if isinstance(search_results, dict) and (
        "_is_explain_result" in search_results
        or "plan" in search_results
        or ("nodes" in search_results
        and len(search_results.get("nodes", [])) > 0)
    ):
        # It's a query plan, use dedicated display function
        display_query_plan(search_results)
        return

    # Display list of results
    if isinstance(search_results, (list, tuple)):
        if len(search_results) > 0:
            # Display up to 20 items
            items_to_show = search_results[:20] if len(search_results) > 20 else search_results

            # Use a simple table for display first
            table_data = []
            headers = []

            # Find common keys for headers (from first 5 items)
            for item in items_to_show[:5]:
                if isinstance(item, dict):
                    for key in item:
                        if key not in headers and not key.startswith("_"):
                            # Prioritize common fields
                            if key in ["Label", "name", "type", "size", "timestamp"]:
                                headers.insert(0, key)
                            else:
                                headers.append(key)

            # If we found headers, create table data
            if headers:
                for item in items_to_show:
                    if isinstance(item, dict):
                        row = {}
                        for header in headers:
                            value = item.get(header, "")
                            # Simplify complex types
                            if isinstance(value, (dict, list, tuple)):
                                if isinstance(value, dict):
                                    row[header] = "{...}"
                                elif isinstance(value, list):
                                    row[header] = f"[{len(value)} items]"
                                else:
                                    row[header] = str(value)
                            else:
                                row[header] = value
                        table_data.append(row)

            # Display table if we have data
            if table_data and headers:
                # Use markdown table for simple display
                header_row = " | ".join(headers)
                separator = " | ".join(["---"] * len(headers))
                table_rows = []

                for row in table_data:
                    values = []
                    for header in headers:
                        values.append(str(row.get(header, "")))
                    table_rows.append(" | ".join(values))

                table_md = f"| {header_row} |\n| {separator} |\n"
                for row in table_rows:
                    table_md += f"| {row} |\n"

                st.markdown(table_md)

            # Also show expandable details for each item
            for i, item in enumerate(items_to_show):
                if isinstance(item, dict):
                    # Get a display name for the item
                    item_name = item.get("Label", item.get("name", f"Result {i+1}"))
                    with st.expander(f"Details: {item_name}", expanded=i == 0):
                        st.json(item)
                else:
                    # For non-dict items
                    with st.expander(f"Result {i+1}", expanded=i == 0):
                        st.code(str(item))
        else:
            st.info("No results found")

    # Display single result
    elif isinstance(search_results, dict):
        item_name = search_results.get("Label", search_results.get("name", "Result"))
        with st.expander(f"Details: {item_name}", expanded=True):
            st.json(search_results)

    # Display other types
    else:
        st.code(str(search_results))


def display_query_plan(explain_results) -> None:
    """
    Dedicated function to display a query execution plan without using dataframes.
    This avoids PyArrow conversion errors by using Streamlit components directly.

    Args:
        explain_results (dict): The query execution plan from ArangoDB
    """
    # Check for error information
    if isinstance(explain_results, dict) and "error" in explain_results:
        st.error(f"Query explanation failed: {explain_results['error']}")
        if "query" in explain_results:
            st.code(explain_results["query"], language="sql")
        return

    # Show a user-friendly message
    st.info(
        "This is a query execution plan showing how ArangoDB would execute this query.",
    )

    # Format metrics in a top row
    metrics_col1, metrics_col2, metrics_col3 = st.columns(3)

    # Handle estimated cost
    with metrics_col1:
        if isinstance(explain_results, dict) and "estimatedCost" in explain_results:
            st.metric("Estimated Cost", f"{explain_results['estimatedCost']:,.0f}")
        elif (
            isinstance(explain_results, dict)
            and "plan" in explain_results
            and "estimatedCost" in explain_results["plan"]
        ):
            st.metric(
                "Estimated Cost",
                f"{explain_results['plan']['estimatedCost']:,.0f}",
            )

    # Handle estimated number of items
    with metrics_col2:
        if isinstance(explain_results, dict):
            if "estimatedNrItems" in explain_results:
                st.metric(
                    "Estimated Results",
                    f"{explain_results.get('estimatedNrItems', 0):,}",
                )
            elif "plan" in explain_results and "estimatedNrItems" in explain_results["plan"]:
                st.metric(
                    "Estimated Results",
                    f"{explain_results['plan'].get('estimatedNrItems', 0):,}",
                )

    # Handle execution time if available
    with metrics_col3:
        exec_time = None
        if isinstance(explain_results, dict):
            if "stats" in explain_results and "executionTime" in explain_results["stats"]:
                exec_time = explain_results["stats"]["executionTime"]
            elif (
                "plan" in explain_results
                and "stats" in explain_results["plan"]
                and "executionTime" in explain_results["plan"]["stats"]
            ):
                exec_time = explain_results["plan"]["stats"]["executionTime"]

        if exec_time is not None:
            if exec_time < 0.001:
                # Convert to microseconds for very fast queries
                st.metric("Execution Time", f"{exec_time*1000000:.1f} μs")
            else:
                st.metric("Execution Time", f"{exec_time*1000:.1f} ms")

    # Display collections used
    collections = []
    if isinstance(explain_results, dict):
        if "collections" in explain_results:
            collections = explain_results["collections"]
        elif "plan" in explain_results and "collections" in explain_results["plan"]:
            collections = explain_results["plan"]["collections"]

    if collections:
        st.subheader("Collections Used")
        collection_list = []
        for coll in collections:
            if isinstance(coll, dict) and "name" in coll:
                collection_list.append(coll["name"])
            elif isinstance(coll, str):
                collection_list.append(coll)

        # Display collections as a comma-separated list
        st.write(", ".join(collection_list))

    # Extract and display execution nodes
    nodes = []
    if isinstance(explain_results, dict):
        if "nodes" in explain_results:
            nodes = explain_results["nodes"]
        elif "plan" in explain_results and "nodes" in explain_results["plan"]:
            nodes = explain_results["plan"]["nodes"]

    if nodes:
        st.subheader("Execution Nodes")
        node_types = {}

        for node in nodes:
            if isinstance(node, dict):
                node_type = node.get("type", "Unknown")
                if node_type in node_types:
                    node_types[node_type] += 1
                else:
                    node_types[node_type] = 1

        # Display node types summary
        for node_type, count in node_types.items():
            st.write(f"• {node_type}: {count}")

        # Show detailed nodes in an expander
        with st.expander("Node Details", expanded=False):
            for i, node in enumerate(nodes):
                st.markdown(f"**Node {i+1}**: {node.get('type', 'Unknown')}")
                st.json(node)

    # Show any optimizer rules applied
    rules = []
    if isinstance(explain_results, dict):
        if "rules" in explain_results:
            rules = explain_results["rules"]
        elif "plan" in explain_results and "rules" in explain_results["plan"]:
            rules = explain_results["plan"]["rules"]

    if rules:
        with st.expander("Optimizer Rules", expanded=False):
            for rule in rules:
                st.write(f"• {rule}")

    # Show any warnings
    warnings = []
    if isinstance(explain_results, dict) and "warnings" in explain_results:
        warnings = explain_results["warnings"]

    if warnings:
        st.warning("Query warnings detected:")
        for warning in warnings:
            st.write(f"• {warning}")

    # Show the full execution plan in an expander
    with st.expander("Full Execution Plan", expanded=False):
        # Remove internal markers before displaying
        if isinstance(explain_results, dict):
            display_results = explain_results.copy()
            if "_is_explain_result" in display_results:
                del display_results["_is_explain_result"]
            st.json(display_results)
        else:
            st.json(explain_results)
