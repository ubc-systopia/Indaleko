"""
This module provides a CLI based interface for querying Indaleko.

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

import argparse
import configparser
from datetime import datetime, timezone
import os
import sys

from icecream import ic
from typing import Union, Any

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from data_models.collection_metadata_data_model import (
    IndalekoCollectionMetadataDataModel,
)
from data_models.db_index import IndalekoCollectionIndexDataModel
from data_models.named_entity import NamedEntityCollection, IndalekoNamedEntityDataModel
from db import IndalekoDBConfig, IndalekoDBCollections
from db.db_collection_metadata import IndalekoDBCollectionsMetadata
from query.history.data_models.query_history import QueryHistoryData
from query.query_processing.data_models.query_input import StructuredQuery
from query.query_processing.nl_parser import NLParser
from query.query_processing.query_translator.aql_translator import AQLTranslator
from query.query_processing.query_history import QueryHistory
from query.query_processing.data_models.parser_data import ParserResults
from query.query_processing.data_models.translator_input import TranslatorInput
from query.result_analysis.facet_generator import FacetGenerator
from query.result_analysis.metadata_analyzer import MetadataAnalyzer
from query.result_analysis.result_ranker import ResultRanker
from query.search_execution.query_executor.aql_executor import AQLExecutor
from query.utils.llm_connector.openai_connector import OpenAIConnector
from utils.cli.base import IndalekoBaseCLI
from utils.cli.data_models.cli_data import IndalekoBaseCliDataModel

# pylint: enable=wrong-import-position


class IndalekoQueryCLI(IndalekoBaseCLI):
    """This class represents the base class for Indaleko Queries."""

    service_name = "IndalekoQueryCLI"

    def __init__(self):
        """Create an instance of the IndalekoQueryCLI class."""
        cli_data = IndalekoBaseCliDataModel(
            RegistrationServiceName=IndalekoQueryCLI.service_name,
            FileServiceName=IndalekoQueryCLI.service_name,
        )
        handler_mixin = IndalekoQueryCLI.query_handler_mixin
        features = IndalekoBaseCLI.cli_features(
            machine_config=False,
            input=False,
            output=False,
            offline=False,
            logging=False,
            performance=False,
            platform=False,
        )
        super().__init__(
            cli_data=cli_data, handler_mixin=handler_mixin, features=features
        )
        config_data = self.get_config_data()
        config_file_path = os.path.join(
            config_data["ConfigDirectory"], config_data["DBConfigFile"]
        )
        self.db_config = IndalekoDBConfig(config_file=config_file_path)
        self.collections_metadata = IndalekoDBCollectionsMetadata(self.db_config)
        self.openai_key = self.get_api_key()
        self.llm_connector = OpenAIConnector(api_key=self.openai_key)
        self.nl_parser = NLParser(
            llm_connector=self.llm_connector,
            collections_metadata=self.collections_metadata,
        )
        self.query_translator = AQLTranslator(self.collections_metadata)
        self.query_history = QueryHistory()
        self.query_executor = AQLExecutor()
        self.metadata_analyzer = MetadataAnalyzer()
        self.facet_generator = FacetGenerator()
        self.result_ranker = ResultRanker()
        self.prompt = "Indaleko Search> "
        self.schema = self.build_schema_table()

    class query_handler_mixin(IndalekoBaseCLI.default_handler_mixin):
        """Handler mixin for the CLI"""

        @staticmethod
        def get_pre_parser() -> Union[argparse.Namespace, None]:
            """
            This method is used to get the pre-parser.  Callers can
            set up switches/parameters before we add the common ones.

            Note the default implementation here does not add any additional parameters.
            """
            parser = argparse.ArgumentParser(add_help=False)
            subparsers = parser.add_subparsers(
                dest="command",
                help="The mode in which to run the script (batch or interactive).",
            )
            subparsers.add_parser(
                "interactive", help="Run the query tool in interactive mode."
            )
            batch_parser = subparsers.add_parser(
                "batch", help="Run the query tool in batch mode."
            )
            batch_parser.add_argument(
                "batch_input_file", help="The file containing the batch input queries."
            )
            parser.set_defaults(command="interactive")
            return parser

    query_cli_handler_mixin = query_handler_mixin

    def get_api_key(self, api_key_file: Union[str, None] = None) -> str:
        """Get the API key from the config file"""
        if api_key_file is None:
            api_key_file = os.path.join(
                self.config_data["ConfigDirectory"], "openai-key.ini"
            )
        assert os.path.exists(api_key_file), f"API key file ({api_key_file}) not found"
        config = configparser.ConfigParser()
        config.read(api_key_file, encoding="utf-8-sig")
        openai_key = config["openai"]["api_key"]
        if openai_key is None:
            raise ValueError("OpenAI API key not found in config file")
        if openai_key[0] == '"' or openai_key[0] == "'":
            openai_key = openai_key[1:]
        if openai_key[-1] == '"' or openai_key[-1] == "'":
            openai_key = openai_key[:-1]
        return openai_key

    def run(self):
        batch = False
        if self.args is None:
            self.args = self.pre_parser.parse_args()
        ic(self.args)
        if self.args.command == "batch":
            with open(self.args.batch_input_file, "rt") as batch_file:
                batch_queries = batch_file.readlines()
            batch = True

        while True:
            # Need UPI information about the database
            #

            # Get query from user
            if batch:
                if len(batch_queries) == 0:
                    break
                user_query = batch_queries.pop(0).strip()
            else:
                user_query = self.get_query()

            if user_query.lower() in ["exit", "quit", "bye", "leave"]:
                return

            # Log the query
            # self.logging_service.log_query(user_query)
            start_time = datetime.now(timezone.utc)

            # Process the query
            ic(f"Parsing query: {user_query}")
            parsed_query = self.nl_parser.parse(query=user_query)
            ParserResults.model_validate(parsed_query)

            # Only support search for now.
            if parsed_query.Intent.intent != "search":
                print(f"Only search queries are supported. Intent inferred is {parsed_query.Intent.intent}")
                print('Defaulting to "search" for now.')
            ic(f"Query Type: {parsed_query.Intent.intent}")

            # Map entities to database attributes
            entity_mappings = self.map_entities(parsed_query.Entities)

            # Use the categories to obtain the metadata attributes
            # of the corresponding collection
            collection_categories = [
                entity.collection for entity in parsed_query.Categories.category_map
            ]
            collection_metadata = self.get_collection_metadata(collection_categories)

            # Let's get the index data
            indices = {}
            for category in collection_categories:
                collection_indices = self.db_config.db.collection(category).indexes()
                for index in collection_indices:
                    if category not in indices:
                        indices[category] = []
                    if index["type"] != "primary":
                        kwargs = {
                            "Name": index["name"],
                            "Type": index["type"],
                            "Fields": index["fields"],
                        }
                        if "unique" in index:
                            kwargs["Unique"] = index["unique"]
                        if "sparse" in index:
                            kwargs["Sparse"] = index["sparse"]
                        if "deduplicate" in index:
                            kwargs["Deduplicate"] = index["deduplicate"]
                        indices[category].append(
                            IndalekoCollectionIndexDataModel(**kwargs)
                        )

            # Obtain information about the database based upon
            # the parsed results
            # self.logging_service.log_query_results(parsed_query)

            # this is the original query translation that I am
            # going to replace with the new query translation
            # translated_query = self.query_translator.translate(
            #     parsed_query,
            #     selected_md_attributes=None,
            #     additional_notes=None,
            #     n_truth=1,dir
            #     llm_connector=self.llm_connector,
            # )
            structured_query = StructuredQuery(
                original_query=user_query,
                intent=parsed_query.Intent.intent,
                entities=entity_mappings,
                db_info=collection_metadata,
                db_indices=indices,
            )
            query_data = TranslatorInput(
                Query=structured_query,
                Connector=self.llm_connector,
            )

            translated_query = self.query_translator.translate(query_data)
            print(translated_query.model_dump_json(indent=2))

            # Execute the query
            raw_results = self.query_executor.execute(
                translated_query.aql_query, self.db_config
            )

            # Analyze and refine results
            analyzed_results = self.metadata_analyzer.analyze(raw_results)
            facets = self.facet_generator.generate(analyzed_results)
            ranked_results = self.result_ranker.rank(analyzed_results)

            # Display results to user
            self.display_results(ranked_results, facets)

            # Update query history
            end_time = datetime.now(timezone.utc)
            time_diference = end_time - start_time
            query_history = QueryHistoryData(
                OriginalQuery=user_query,
                ParsedResults=parsed_query,
                LLMName=self.llm_connector.get_llm_name(),
                LLMQuery=structured_query,
                TranslatedOutput=translated_query,
                RawResults=raw_results,
                AnalyzedResults=analyzed_results,
                Facets=facets,
                RankedResults=ranked_results,
                StartTimestamp=start_time,
                EndTimestamp=end_time,
                ElapsedTime=time_diference.total_seconds(),
            )
            self.query_history.add(query_history)

            # Check if user wants to continue
            if not self.continue_session():
                break

        # self.logging_service.log_session_end()

    def map_entities(
        self, entity_list: NamedEntityCollection
    ) -> list[NamedEntityCollection]:
        """
        Construct a new list that maps the entities into values from the NER collection.

        Args:
            entities (List[NamedEntityCollection]): The list of named entities to try mapping.

        Returns:
            List[NamedEntityCollection]: The list of named entities with mapped values.

        If a named entity cannot be mapped, it is omitted from the returned list.  If it
        can be mapped, the entry is replaced with the mapped value from the NER collection.
        """
        mapped_entities = []
        collection = self.db_config.db.collection(
            IndalekoDBCollections.Indaleko_Named_Entity_Collection
        )
        if collection is None:
            return NamedEntityCollection(entities=mapped_entities)
        for entity in entity_list.entities:
            if entity.name is None:
                continue
            docs = [doc for doc in collection.find({"name": entity.name})]
            if docs is None or len(docs) == 0:
                ic(f"NER mapping: Could not find entity: {entity.name}")
                continue
            if len(docs) > 1:
                ic(f"NER mapping: Multiple entities found for: {entity.name}")
                raise NotImplementedError("Multiple entities found, not handled yet")
            doc = docs[0]
            mapped_entities.append(
                IndalekoNamedEntityDataModel(
                    name=entity.name,
                    uuid=doc.uuid,
                    category=doc.category,
                    description=doc.description,
                    gis_location=doc.gis_location,
                    device_id=doc.device_id,
                )
            )
        return NamedEntityCollection(entities=mapped_entities)

    def get_collection_metadata(
        self, categories: list[str]
    ) -> list[IndalekoCollectionMetadataDataModel]:
        """Get the metadata for the collections based upon the selected categories."""
        if self.collections_metadata is None:
            return []
        collection_metadata = []
        for category in categories:
            metadata = self.collections_metadata.get_collection_metadata(category)
            if metadata is None:
                ic(f"Failed to get metadata for category: {category}")
            collection_metadata.append(metadata)
        return collection_metadata

    def get_query(self) -> str:
        """Get a query from the user."""
        return input(self.prompt).strip()

    def display_results(self, results: list[dict[str, Any]], facets: list[str]) -> None:
        """
        Displays the search results and suggested facets to the user.

        Args:
            results (List[Dict[str, Any]]): The ranked search results
            facets (List[str]): Suggested facets for query refinement
        """
        if not results:
            print("No results found.")
            return

        print("\nSearch Results:")
        ic(len(results))
        if len(results) < 10:
            for i, result in enumerate(results, 1):
                doc = result["original"]["result"]
                ic(doc["Record"]["Attributes"]["Path"])

        if facets:
            print("Suggested refinements:")
            for facet in facets:
                print(f"- {facet}")

    def continue_session(self) -> bool:
        """Check if the user wants to continue the session."""
        return input("Do you want to continue? [Y/N] ").strip().lower() in ["y", "yes"]

    def build_schema_table(self):
        """Build the schema table."""
        schema = {}
        for collection in self.db_config.db.collections():
            name = collection["name"]
            if name.startswith("_"):
                continue
            doc = self.db_config.db.collection(name)
            properties = doc.properties()
            schema[name] = properties["schema"]
        return schema


def main():
    """A CLI based query tool for Indaleko."""
    ic("Starting Indaleko Query CLI")
    IndalekoQueryCLI().run()
    print("Thank you for using Indaleko Query CLI")
    print("Have a lovely day!")


if __name__ == "__main__":
    main()
