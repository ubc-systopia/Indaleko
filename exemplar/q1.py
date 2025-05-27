"""Exemplar Query 1 - Documents with 'report' in their titles."""

import os
import sys

from typing import Self
from pathlib import Path

from icecream import ic


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = Path(__file__).parent.resolve()
    while not (Path(current_path) / "Indaleko.py").exists():
        current_path = Path(current_path).parent
    os.environ["INDALEKO_ROOT"] = str(current_path)
    sys.path.insert(0, str(current_path))

# pylint: disable=wrong-import-position
from db.db_collections import IndalekoDBCollections
from exemplar.qbase import ExemplarQueryBase, exemplar_main
# pylint: enable=wrong-import-position


class ExemplarQuery1(ExemplarQueryBase):
    """Exemplar Query 1 - Search for documents with 'report' in titles."""

    def _get_user_query(self: Self) -> str:
        """Return the natural language query string."""
        return 'Show me documents with "report" in their titles.'

    def _get_base_aql(self: Self) -> str:
        """Return the base AQL query without LIMIT or RETURN."""
        return """
            FOR doc IN @@collection
                SEARCH
                ANALYZER(LIKE(doc.Label, @name), "text_en") OR
                ANALYZER(LIKE(doc.Label, @name), "Indaleko::indaleko_snake_case")
            """

    def _get_base_bind_variables(self: Self) -> dict[str, object]:
        """Return the base bind variables including @collection."""
        return {
            "@collection": IndalekoDBCollections.Indaleko_Objects_Text_View,
            "name": "%report%",
        }


def main():
    """Main function for testing functionality."""
    exemplar_main(ExemplarQuery1)


if __name__ == "__main__":
    main()
