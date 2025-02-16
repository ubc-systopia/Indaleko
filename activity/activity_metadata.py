'''
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
'''
import os
import sys
import json
from textwrap import dedent

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from activity.data_model.activity import IndalekoActivityDataModel
from activity.collectors.known_semantic_attributes import KnownSemanticAttributes
from data_models.collection_metadata_data_model import IndalekoCollectionMetadataDataModel
from utils import IndalekoSingleton


class ActivityMetadata(IndalekoSingleton):
    '''Provides structured metadata guidance for activity data collections.'''

    @staticmethod
    def build_semantic_attribute_description() -> str:
        attributes = []
        for category, value in KnownSemanticAttributes.get_all_attributes().items():
            for key, detail in value.items():
                attributes.append({
                    "SemanticLabel": key,
                    "UUID": detail,
                    "Category": category
                })
        return json.dumps(attributes, indent=4)

    default_metadata = IndalekoCollectionMetadataDataModel(
        key='ActivityData',
        Description=dedent(
            """
            ## Activity Data Collection Overview
            This description serves as a **template** for activity data collections. Unlike other descriptions,
            it does not refer to a specific collection but defines the **common format** applicable to all.

            ### Purpose
            - Activity data collections are **dynamic**, with additional fields tailored to specific data types.
            - Indaleko allows rapid development of **new data collection agents**, even when descriptions and
              schemas are incomplete.
            - The **Archivist** can use this description to infer what metadata might be useful for a new provider.

            ### System Context
            - Indaleko is a **cross-platform unified personal indexing system** using an **ArangoDB** database.
            - Activity data represents **human-experiential information**, linking **episodic memory** with
              **system events and stored objects**.
            - This structure enhances Indaleko's ability to help users **locate specific files** efficiently.

            ### Semantic Attributes
            The following attributes describe key data points collected from activity providers:
            """
        ) + '\n' + build_semantic_attribute_description(),

        QueryGuidelines=[
            dedent(
                """
                ## Query Guidelines
                The **primary field** for queries is `SemanticAttributes`, which stores activity data as
                **key-value pairs**:

                - **Key**: A **UUID** identifying the semantic attribute.
                - **Value**: The actual data associated with that attribute.

                ### Handling Queries
                1. **Known Mappings**: If a UUID has a predefined label, retrieve and use it.
                2. **Unknown Mappings**: If a UUID is **not recognized**:
                   - Check related documents for context.
                   - Infer possible categories based on semantic similarity.
                   - Flag as an unknown attribute if no match is found.
                3. **Overlapping Attributes**: Some attributes have **synonyms** (e.g., `filename` vs. `document_name`).
                   Consider alternative labels.
                4. **Query Optimization**: Structure AQL queries to accommodate **flexible and evolving schemas**.
                """
            )
        ],

        Schema=IndalekoActivityDataModel.get_json_schema()
    )


def main():
    '''Main entry point for the module.'''
    metadata = ActivityMetadata()
    print(metadata.default_metadata.model_dump_json(indent=4))


if __name__ == '__main__':
    main()
