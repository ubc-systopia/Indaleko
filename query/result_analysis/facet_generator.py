"""
Facet generation for Indaleko search results.

Project Indaleko
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

import math
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.result_analysis.data_models.facet_data_model import (
    DynamicFacets,
    Facet,
    FacetType,
    FacetValue,
)
from query.result_analysis.result_formatter import (
    extract_categorization_info,
    extract_timestamp,
)


class FacetGenerator:
    """
    Generates dynamic facets for query refinement based on search results.
    """

    def __init__(
        self,
        max_facets: int = 5,
        min_facet_coverage: float = 0.2,
        min_value_count: int = 2,
        conversational: bool = True,
    ):
        """
        Initialize the FacetGenerator.

        Args:
            max_facets (int): Maximum number of facets to generate
            min_facet_coverage (float): Minimum percentage of results a facet should cover (0.0-1.0)
            min_value_count (int): Minimum count for a facet value to be included
            conversational (bool): Whether to generate conversational hints
        """
        self.max_facets = max_facets
        self.min_facet_coverage = min_facet_coverage
        self.min_value_count = min_value_count
        self.conversational = conversational

    def generate(
        self,
        analyzed_results: list[dict[str, Any]],
    ) -> list[str] | DynamicFacets:
        """
        Generate facets based on the analyzed search results.

        Args:
            analyzed_results (List[Dict[str, Any]]): The analyzed search results

        Returns:
            DynamicFacets: A list of DynamicFacets object
        """
        if not analyzed_results or len(analyzed_results) == 0:
            return DynamicFacets(
                original_count=0,
                suggestions=["No results found"],
                conversational_hints=[
                    "I couldn't find any results matching your query.",
                ],
            )

        # Extract all metadata for faceting
        file_types = self._extract_file_types(analyzed_results)
        dates = self._extract_dates(analyzed_results)
        locations = self._extract_locations(analyzed_results)
        sizes = self._extract_sizes(analyzed_results)
        semantic_attrs = self._extract_semantic_attributes(analyzed_results)

        # Generate facets from extracted metadata
        file_type_facet = self._generate_file_type_facet(
            file_types,
            len(analyzed_results),
        )
        date_facet = self._generate_date_facet(dates, len(analyzed_results))
        location_facet = self._generate_location_facet(locations, len(analyzed_results))
        size_facet = self._generate_size_facet(sizes, len(analyzed_results))
        semantic_facets = self._generate_semantic_facets(
            semantic_attrs,
            len(analyzed_results),
        )

        # Combine all facets and rank them by utility
        all_facets = []
        if file_type_facet:
            all_facets.append(file_type_facet)
        if date_facet:
            all_facets.append(date_facet)
        if location_facet:
            all_facets.append(location_facet)
        if size_facet:
            all_facets.append(size_facet)
        all_facets.extend(semantic_facets)

        # Rank facets by their utility (coverage and entropy)
        ranked_facets = self._rank_facets(all_facets)
        selected_facets = ranked_facets[: self.max_facets]

        # Generate suggestions and conversational hints
        suggestions = self._generate_suggestions(selected_facets, len(analyzed_results))
        conversational_hints = []
        if self.conversational:
            conversational_hints = self._generate_conversational_hints(
                selected_facets,
                len(analyzed_results),
            )

        # Generate statistics
        facet_statistics = self._generate_facet_statistics(
            selected_facets,
            file_types,
            dates,
            sizes,
            len(analyzed_results),
        )

        # Build the DynamicFacets object
        dynamic_facets = DynamicFacets(
            facets=selected_facets,
            suggestions=suggestions,
            original_count=len(analyzed_results),
            facet_statistics=facet_statistics,
            conversational_hints=conversational_hints,
        )

        return dynamic_facets

    def _extract_file_types(self, results: list[dict[str, Any]]) -> dict[str, int]:
        """
        Extract file types from results with their counts.

        Args:
            results: The search results

        Returns:
            Dictionary mapping file types to their counts
        """
        file_types = Counter()

        for result in results:
            # Extract from file name extension
            if "name" in result:
                name = result["name"]
                ext = os.path.splitext(name)[1].lower()
                if ext:
                    # Remove the leading dot
                    ext = ext[1:]
                    file_types[ext] += 1

            # Extract from MIME type
            if "Record" in result and "Attributes" in result["Record"]:
                attrs = result["Record"]["Attributes"]
                if "mimeType" in attrs:
                    mime = attrs["mimeType"]
                    # Extract subtype from MIME (e.g., 'pdf' from 'application/pdf')
                    subtype = mime.split("/")[-1]
                    file_types[subtype] += 1

            # Extract from categories
            categories = extract_categorization_info(result)
            for category in categories:
                if not category.startswith("mime:") and not category.startswith(
                    "semantic:",
                ):
                    file_types[category] += 1

        return dict(file_types)

    def _extract_dates(self, results: list[dict[str, Any]]) -> list[datetime]:
        """
        Extract dates from results.

        Args:
            results: The search results

        Returns:
            List of datetime objects
        """
        dates = []

        for result in results:
            timestamp = extract_timestamp(result)
            if timestamp:
                dates.append(timestamp)

        return dates

    def _extract_locations(self, results: list[dict[str, Any]]) -> dict[str, int]:
        """
        Extract locations from results with their counts.

        Args:
            results: The search results

        Returns:
            Dictionary mapping locations to their counts
        """
        locations = Counter()

        for result in results:
            # Extract from path
            path = None
            if "path" in result:
                path = result["path"]
            elif "Record" in result and "Attributes" in result["Record"]:
                attrs = result["Record"]["Attributes"]
                if "Path" in attrs:
                    path = attrs["Path"]
                elif "LocalPath" in attrs:
                    path = attrs["LocalPath"]

            if path:
                # Extract directory parts (up to 3 levels)
                parts = os.path.normpath(path).split(os.sep)
                if len(parts) > 1:
                    # Get the first meaningful directory
                    for part in parts[:-1]:  # Skip the filename
                        if part and part not in ("/", "\\", ".", "..", "home", "Users"):
                            locations[part] += 1
                            break

                    # Also add the parent directory
                    parent = os.path.dirname(path)
                    if parent and os.path.basename(parent) not in (
                        "/",
                        "\\",
                        ".",
                        "..",
                        "home",
                        "Users",
                    ):
                        locations[os.path.basename(parent)] += 1

        return dict(locations)

    def _extract_sizes(self, results: list[dict[str, Any]]) -> list[int]:
        """
        Extract file sizes from results.

        Args:
            results: The search results

        Returns:
            List of file sizes in bytes
        """
        sizes = []

        for result in results:
            size = None
            if "size" in result:
                size = result["size"]
            elif "Record" in result and "Attributes" in result["Record"]:
                attrs = result["Record"]["Attributes"]
                if "Size" in attrs:
                    size = attrs["Size"]
                elif "st_size" in attrs:
                    size = attrs["st_size"]

            if size is not None and isinstance(size, (int, float)) and size >= 0:
                sizes.append(int(size))

        return sizes

    def _extract_semantic_attributes(
        self,
        results: list[dict[str, Any]],
    ) -> dict[str, dict[str, int]]:
        """
        Extract semantic attributes from results.

        Args:
            results: The search results

        Returns:
            Dictionary mapping attribute names to dictionaries of value counts
        """
        semantic_attrs = defaultdict(Counter)

        for result in results:
            if "SemanticAttributes" in result:
                for attr in result["SemanticAttributes"]:
                    if "Identifier" in attr and "Label" in attr["Identifier"]:
                        label = attr["Identifier"]["Label"]
                        if "Value" in attr:
                            value = attr["Value"]
                            semantic_attrs[label][value] += 1

        return {k: dict(v) for k, v in semantic_attrs.items()}

    def _generate_file_type_facet(
        self,
        file_types: dict[str, int],
        total_results: int,
    ) -> Facet | None:
        """
        Generate a facet for file types.

        Args:
            file_types: Dictionary of file types and their counts
            total_results: Total number of results

        Returns:
            Facet object for file types, or None if insufficient data
        """
        if not file_types:
            return None

        # Calculate coverage
        coverage = sum(file_types.values()) / total_results if total_results > 0 else 0

        # Skip if coverage is too low
        if coverage < self.min_facet_coverage:
            return None

        # Filter values by minimum count
        filtered_types = {k: v for k, v in file_types.items() if v >= self.min_value_count}
        if not filtered_types:
            return None

        # Create facet values
        values = []
        for file_type, count in sorted(
            filtered_types.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            value = FacetValue(
                value=file_type,
                count=count,
                query_refinement=f"file_type:{file_type}",
            )
            values.append(value)

        # Calculate entropy
        entropy = self._calculate_entropy(list(filtered_types.values()), total_results)

        # Create the facet
        return Facet(
            name="File Type",
            field="file_type",
            type=FacetType.FILE_TYPE,
            values=values,
            coverage=coverage,
            distribution_entropy=entropy,
        )

    def _generate_date_facet(
        self,
        dates: list[datetime],
        total_results: int,
    ) -> Facet | None:
        """
        Generate a facet for date ranges.

        Args:
            dates: List of datetime objects
            total_results: Total number of results

        Returns:
            Facet object for dates, or None if insufficient data
        """
        if not dates or len(dates) < self.min_value_count:
            return None

        # Calculate coverage
        coverage = len(dates) / total_results if total_results > 0 else 0

        # Skip if coverage is too low
        if coverage < self.min_facet_coverage:
            return None

        # Determine date ranges
        if not dates:
            return None

        min_date = min(dates)
        max_date = max(dates)

        # If range is less than a day, no point in faceting
        if (max_date - min_date).total_seconds() < 86400:
            return None

        # Determine if we should group by day, month, or year
        range_days = (max_date - min_date).days

        # Create appropriate date bins
        date_bins = Counter()
        if range_days <= 30:
            # Group by day
            for date in dates:
                bin_key = date.strftime("%Y-%m-%d")
                date_bins[bin_key] += 1
            bin_type = "day"
        elif range_days <= 365:
            # Group by month
            for date in dates:
                bin_key = date.strftime("%Y-%m")
                date_bins[bin_key] += 1
            bin_type = "month"
        else:
            # Group by year
            for date in dates:
                bin_key = date.strftime("%Y")
                date_bins[bin_key] += 1
            bin_type = "year"

        # Filter bins by minimum count
        filtered_bins = {k: v for k, v in date_bins.items() if v >= self.min_value_count}
        if not filtered_bins:
            return None

        # Create facet values
        values = []
        for bin_key, count in sorted(
            filtered_bins.items(),
            key=lambda x: x[0],
            reverse=True,
        ):
            # Create a human-readable label based on bin type
            if bin_type == "day":
                date_obj = datetime.strptime(bin_key, "%Y-%m-%d")
                label = date_obj.strftime("%b %d, %Y")
            elif bin_type == "month":
                date_obj = datetime.strptime(bin_key, "%Y-%m")
                label = date_obj.strftime("%b %Y")
            else:  # year
                label = bin_key

            value = FacetValue(
                value=label,
                count=count,
                query_refinement=f"date:{bin_key}",
            )
            values.append(value)

        # Calculate entropy
        entropy = self._calculate_entropy(list(filtered_bins.values()), total_results)

        # Create the facet
        return Facet(
            name="Date",
            field="date",
            type=FacetType.DATE,
            values=values,
            coverage=coverage,
            distribution_entropy=entropy,
        )

    def _generate_location_facet(
        self,
        locations: dict[str, int],
        total_results: int,
    ) -> Facet | None:
        """
        Generate a facet for file locations.

        Args:
            locations: Dictionary of locations and their counts
            total_results: Total number of results

        Returns:
            Facet object for locations, or None if insufficient data
        """
        if not locations:
            return None

        # Calculate coverage
        coverage = sum(locations.values()) / total_results if total_results > 0 else 0

        # Skip if coverage is too low
        if coverage < self.min_facet_coverage:
            return None

        # Filter values by minimum count
        filtered_locations = {k: v for k, v in locations.items() if v >= self.min_value_count}
        if not filtered_locations:
            return None

        # Create facet values
        values = []
        for location, count in sorted(
            filtered_locations.items(),
            key=lambda x: x[1],
            reverse=True,
        ):
            value = FacetValue(
                value=location,
                count=count,
                query_refinement=f"location:{location}",
            )
            values.append(value)

        # Calculate entropy
        entropy = self._calculate_entropy(
            list(filtered_locations.values()),
            total_results,
        )

        # Create the facet
        return Facet(
            name="Location",
            field="location",
            type=FacetType.LOCATION,
            values=values,
            coverage=coverage,
            distribution_entropy=entropy,
        )

    def _generate_size_facet(
        self,
        sizes: list[int],
        total_results: int,
    ) -> Facet | None:
        """
        Generate a facet for file sizes.

        Args:
            sizes: List of file sizes in bytes
            total_results: Total number of results

        Returns:
            Facet object for sizes, or None if insufficient data
        """
        if not sizes or len(sizes) < self.min_value_count:
            return None

        # Calculate coverage
        coverage = len(sizes) / total_results if total_results > 0 else 0

        # Skip if coverage is too low
        if coverage < self.min_facet_coverage:
            return None

        # Create size bins
        size_bins = {
            "Small (<100KB)": 0,
            "Medium (100KB-1MB)": 0,
            "Large (1MB-10MB)": 0,
            "Very Large (>10MB)": 0,
        }

        for size in sizes:
            if size < 102400:  # 100KB
                size_bins["Small (<100KB)"] += 1
            elif size < 1048576:  # 1MB
                size_bins["Medium (100KB-1MB)"] += 1
            elif size < 10485760:  # 10MB
                size_bins["Large (1MB-10MB)"] += 1
            else:
                size_bins["Very Large (>10MB)"] += 1

        # Filter bins by minimum count
        filtered_bins = {k: v for k, v in size_bins.items() if v >= self.min_value_count}
        if not filtered_bins:
            return None

        # Create facet values
        values = []
        for bin_name, count in filtered_bins.items():
            # Create query refinement based on bin
            if bin_name == "Small (<100KB)":
                refinement = "size:<100KB"
            elif bin_name == "Medium (100KB-1MB)":
                refinement = "size:100KB-1MB"
            elif bin_name == "Large (1MB-10MB)":
                refinement = "size:1MB-10MB"
            else:  # Very Large
                refinement = "size:>10MB"

            value = FacetValue(
                value=bin_name,
                count=count,
                query_refinement=refinement
            )
            values.append(value)

        # Calculate entropy
        entropy = self._calculate_entropy(list(filtered_bins.values()), total_results)

        # Create the facet
        return Facet(
            name="File Size",
            field="size",
            type=FacetType.SIZE,
            values=values,
            coverage=coverage,
            distribution_entropy=entropy,
        )

    def _generate_semantic_facets(
        self,
        semantic_attrs: dict[str, dict[str, int]],
        total_results: int,
    ) -> list[Facet]:
        """
        Generate facets from semantic attributes.

        Args:
            semantic_attrs: Dictionary mapping attribute names to dictionaries of value counts
            total_results: Total number of results

        Returns:
            List of Facet objects for semantic attributes
        """
        facets = []

        for attr_name, values in semantic_attrs.items():
            # Calculate coverage
            coverage = sum(values.values()) / total_results if total_results > 0 else 0

            # Skip if coverage is too low
            if coverage < self.min_facet_coverage:
                continue

            # Filter values by minimum count
            filtered_values = {k: v for k, v in values.items() if v >= self.min_value_count}
            if not filtered_values:
                continue

            # Create facet values
            facet_values = []
            for value_name, count in sorted(
                filtered_values.items(),
                key=lambda x: x[1],
                reverse=True,
            ):
                facet_value = FacetValue(
                    value=str(value_name),
                    count=count,
                    query_refinement=f"{attr_name}:{value_name}",
                )
                facet_values.append(facet_value)

            # Calculate entropy
            entropy = self._calculate_entropy(
                list(filtered_values.values()),
                total_results,
            )

            # Create the facet
            facet = Facet(
                name=attr_name,
                field=attr_name.lower(),
                type=FacetType.SEMANTIC,
                values=facet_values,
                coverage=coverage,
                distribution_entropy=entropy,
            )
            facets.append(facet)

        return facets

    def _rank_facets(self, facets: list[Facet]) -> list[Facet]:
        """
        Rank facets by their utility for query refinement.

        A good facet has high coverage and balanced distribution of values.

        Args:
            facets: List of facets to rank

        Returns:
            Ranked list of facets
        """

        # Define a utility function that combines coverage and entropy
        def utility(facet):
            # Higher coverage and entropy are better
            return (facet.coverage * 0.7) + (facet.distribution_entropy * 0.3)

        return sorted(facets, key=utility, reverse=True)

    def _calculate_entropy(self, counts: list[int], total: int) -> float:
        """
        Calculate Shannon entropy of a distribution.

        Higher entropy means more even distribution (better for faceting).

        Args:
            counts: List of counts for each value
            total: Total count

        Returns:
            Entropy value (0.0-1.0)
        """
        if not counts or total == 0:
            return 0.0

        # Calculate probabilities
        probs = [count / total for count in counts]

        # Calculate entropy
        entropy = -sum(p * math.log2(p) for p in probs if p > 0)

        # Normalize to 0-1 range (divide by max possible entropy)
        max_entropy = math.log2(len(counts))
        if max_entropy == 0:
            return 0.0

        return entropy / max_entropy

    def _generate_suggestions(
        self,
        facets: list[Facet],
        total_results: int,
    ) -> list[str]:
        """
        Generate natural language suggestions based on facets.

        Args:
            facets: List of facets
            total_results: Total number of results

        Returns:
            List of suggestion strings
        """
        suggestions = []

        # Suggest based on result count
        if total_results > 50:
            suggestions.append(
                f"Your search returned {total_results} results. Consider refining your query.",
            )

        # Generate suggestions from facets
        for facet in facets:
            if not facet.values:
                continue

            # Get the top values
            top_values = facet.values[:3]

            if facet.type == FacetType.FILE_TYPE:
                # Suggest filtering by file type
                if len(top_values) == 1:
                    suggestions.append(
                        f"Filter by {top_values[0].value} files ({top_values[0].count} results)",
                    )
                else:
                    value_list = ", ".join(v.value for v in top_values[:-1])
                    value_list += f" or {top_values[-1].value}"
                    suggestions.append(f"Filter by file type: {value_list}")

            elif facet.type == FacetType.DATE:
                # Suggest filtering by date
                if len(facet.values) > 2:
                    newest = facet.values[0].value
                    suggestions.append(f"Focus on recent documents from {newest}")

            elif facet.type == FacetType.LOCATION:
                # Suggest filtering by location
                if len(top_values) == 1:
                    suggestions.append(
                        f"Look in {top_values[0].value} ({top_values[0].count} results)",
                    )
                else:
                    value_list = ", ".join(v.value for v in top_values[:-1])
                    value_list += f" or {top_values[-1].value}"
                    suggestions.append(f"Filter by location: {value_list}")

            elif facet.type == FacetType.SIZE:
                # Suggest filtering by size
                large_files = [v for v in facet.values if "Large" in v.value]
                if large_files and large_files[0].count > 5:
                    suggestions.append(
                        f"Filter by {large_files[0].value} files ({large_files[0].count} results)",
                    )

            elif facet.type == FacetType.SEMANTIC:
                # Suggest filtering by semantic attribute
                if len(top_values) == 1:
                    suggestions.append(
                        f"Filter by {facet.name}: {top_values[0].value} ({top_values[0].count} results)",
                    )

        return suggestions[:5]  # Limit to top 5 suggestions

    def _generate_conversational_hints(
        self,
        facets: list[Facet],
        total_results: int,
    ) -> list[str]:
        """
        Generate conversational hints for facets.

        Args:
            facets: List of facets
            total_results: Total number of results

        Returns:
            List of conversational hint strings
        """
        hints = []

        # Suggest based on result count
        if total_results > 100:
            hints.append(
                f"I found {total_results} results. Would you like me to help narrow them down?",
            )
        elif total_results > 50:
            hints.append(
                f"I found {total_results} results. Maybe we can refine this further?",
            )

        # Generate hints from facets
        for facet in facets:
            if not facet.values:
                continue

            # Get the top values
            top_values = facet.values[:2]

            if facet.type == FacetType.FILE_TYPE:
                # Conversational hint about file types
                if len(top_values) == 1 and top_values[0].count / total_results > 0.5:
                    hints.append(
                        f"Most of these results ({top_values[0].count}) are {top_values[0].value} files. "
                        f"Would you like to focus on those?",
                    )
                elif len(top_values) > 1:
                    hints.append(
                        f"These results include {top_values[0].count} {top_values[0].value} files and "
                        f"{top_values[1].count} {top_values[1].value} files. "
                        f"Which type are you more interested in?",
                    )

            elif facet.type == FacetType.DATE:
                # Conversational hint about dates
                if len(facet.values) > 2:
                    newest = facet.values[0].value
                    oldest = facet.values[-1].value
                    hints.append(
                        f"These results span from {oldest} to {newest}. Would you prefer more recent documents?",
                    )

            elif facet.type == FacetType.LOCATION:
                # Conversational hint about locations
                if len(top_values) > 1 and top_values[0].count / total_results > 0.3:
                    hints.append(
                        f"Many results ({top_values[0].count}) come from {top_values[0].value}. "
                        f"Should we focus there?",
                    )

            elif facet.type == FacetType.SIZE:
                # Conversational hint about file sizes
                large_files = [v for v in facet.values if "Large" in v.value]
                small_files = [v for v in facet.values if "Small" in v.value]
                if large_files and small_files:
                    hints.append(
                        f"I found {large_files[0].count} large files and {small_files[0].count} small files. "
                        f"Which would you prefer to see?",
                    )

            elif facet.type == FacetType.SEMANTIC:
                # Conversational hint about semantic attributes
                if len(top_values) > 1:
                    hints.append(
                        f"For {facet.name}, I found {top_values[0].count} items with {top_values[0].value} "
                        f"and {top_values[1].count} with {top_values[1].value}. "
                        f"Does either interest you more?",
                    )

        return hints[:3]  # Limit to top 3 conversational hints

    def _generate_facet_statistics(
        self,
        facets: list[Facet],
        file_types: dict[str, int],
        dates: list[datetime],
        sizes: list[int],
        total_results: int,
    ) -> dict[str, Any]:
        """
        Generate statistics about facets for metadata analysis.

        Args:
            facets: List of facets
            file_types: Dictionary of file types and counts
            dates: List of dates
            sizes: List of sizes
            total_results: Total number of results

        Returns:
            Dictionary of statistics
        """
        stats = {}

        # Most common file type
        if file_types:
            most_common = max(file_types.items(), key=lambda x: x[1])
            stats["most_common_file_type"] = most_common[0]
            stats["most_common_file_type_count"] = most_common[1]
            stats["file_type_diversity"] = len(file_types)

        # Date range
        if dates and len(dates) >= 2:
            min_date = min(dates)
            max_date = max(dates)
            stats["oldest_date"] = min_date.isoformat()
            stats["newest_date"] = max_date.isoformat()
            stats["date_range_days"] = (max_date - min_date).days

        # Size statistics
        if sizes:
            stats["min_size"] = min(sizes)
            stats["max_size"] = max(sizes)
            stats["avg_size"] = sum(sizes) / len(sizes)
            stats["total_size"] = sum(sizes)

        # Facet coverage
        stats["facet_coverage"] = {}
        for facet in facets:
            stats["facet_coverage"][facet.name] = facet.coverage

        return stats

    # Legacy compatibility methods
    def _generate_type_facets(self, results: list[dict[str, Any]]) -> list[str]:
        """Legacy method for generating file type facets."""
        file_types = self._extract_file_types(results)
        facet = self._generate_file_type_facet(file_types, len(results))

        suggestions = []
        if facet and facet.values:
            for value in facet.values[:3]:
                suggestions.append(f"Filter by {value.value} files")

        return suggestions

    def _generate_date_facets(self, results: list[dict[str, Any]]) -> list[str]:
        """Legacy method for generating date facets."""
        dates = self._extract_dates(results)
        facet = self._generate_date_facet(dates, len(results))

        suggestions = []
        if facet and facet.values:
            for value in facet.values[:2]:
                suggestions.append(f"Filter by date: {value.value}")

        return suggestions

    def _generate_metadata_facets(self, results: list[dict[str, Any]]) -> list[str]:
        """Legacy method for generating metadata facets."""
        locations = self._extract_locations(results)
        sizes = self._extract_sizes(results)
        semantic_attrs = self._extract_semantic_attributes(results)

        facets = []
        location_facet = self._generate_location_facet(locations, len(results))
        if location_facet:
            facets.append(location_facet)

        size_facet = self._generate_size_facet(sizes, len(results))
        if size_facet:
            facets.append(size_facet)

        semantic_facets = self._generate_semantic_facets(semantic_attrs, len(results))
        facets.extend(semantic_facets)

        suggestions = []
        for facet in facets:
            if facet.values:
                value = facet.values[0]
                suggestions.append(f"Filter by {facet.name}: {value.value}")

        return suggestions
