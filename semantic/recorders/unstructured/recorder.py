"""
This module handles processing and recording data from the Unstructured
Semantic data collector.

Indaleko Windows Local Recorder
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

import datetime
import json
import os
import sys
from uuid import UUID

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)


import semantic.collectors.semantic_attributes as known_semantic_attributes
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from Indaleko import Indaleko
from semantic.data_models.base_data_model import BaseSemanticDataModel
from utils.misc.data_management import encode_binary_data


class UnstructuredRecorder:
    """
    This class handles the recording of semantic data produced by
    the Unstructured collector stored in a jsonl file.
    """

    semantic_recorder_uuid = "31764240-1397-4cd2-9c74-b332a0ff1b72"

    input_file = os.path.join(
        Indaleko.default_data_dir,
        "semantic\\unstructured_outputs.jsonl",
    )
    output_file = os.path.join(
        Indaleko.default_data_dir,
        "semantic\\unstructured_recorder.jsonl",
    )
    semantic_recording_date = datetime.datetime.now(datetime.UTC).isoformat()

    attributes_by_uuid = {}
    attributes_by_label = {}

    def __init__(self) -> None:

        for label, value in known_semantic_attributes.__dict__.items():
            if label.startswith(known_semantic_attributes.PREFIX):
                self.attributes_by_uuid[value] = label
                self.attributes_by_label[label] = value

    def create_semantic_record(self, unstructured_obj_line) -> IndalekoRecordDataModel:
        """
        Creates a Record for the current
        """
        return IndalekoRecordDataModel(
            SourceIdentifier={
                "Identifier": self.semantic_recorder_uuid,
                "Version": "1.1",
            },
            Data=encode_binary_data(unstructured_obj_line.encode("utf-8")),
        )

    def create_semantic_related_objects(self, unstructured_obj) -> list[UUID]:
        """
        Extracts the ObjectIdentifier of the original source file that was
        processed by Unstructured.

        May need to add the UUIDs of other files that contain similar
        semantic contents
        """
        return [unstructured_obj["ObjectIdentifier"]]

    def extract_filetype_attribute(
        self,
        elements,
    ) -> IndalekoSemanticAttributeDataModel:
        """
        Extracts the filetype attribute from the first Element's metadata
        """
        first_element = elements[0]
        filetype = first_element["metadata"]["filetype"]

        return IndalekoSemanticAttributeDataModel(
            Identifier=self.get_attribute_identifier("filetype"),
            Value=filetype,
        )

    def extract_filename_attribute(
        self,
        elements,
    ) -> IndalekoSemanticAttributeDataModel:
        """
        Extracts the filename attribute from the first Element's metadata
        """
        first_element = elements[0]
        filename = first_element["metadata"]["filename"]

        return IndalekoSemanticAttributeDataModel(
            Identifier=self.get_attribute_identifier("filename"),
            Value=filename,
        )

    def extract_language_attribute_list(
        self,
        languages: set,
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """
        Takes in a Set of all languages detected in the file.
        Returns a list of SemanticAttributes where one object
        references one language only
        """
        language_list = []
        for language in languages:
            language_list.append(
                IndalekoSemanticAttributeDataModel(
                    Identifier=self.get_attribute_identifier("language"),
                    Value=language,
                ),
            )

        return language_list

    def normalize_semantic_attributes(
        self,
        unstructured_obj,
    ) -> list[IndalekoSemanticAttributeDataModel]:
        """
        Given an entry, representing the unstructured elements of one file,
        normalize the elements in the entry by doing the following:

            1. Extract the filename and filetype then store it as a SemanticAttribute
            2. Identify the unique languages contained in the file, and store
                each language as one SemanticAttribute
            3. Convert each element into a SemanticAttribute where the Identifier
                is one of the Element types specified by Unstructured, and the
                Data is the "text" field in each Element, which is guarenteed to be present

        This returns a list of IndalekoSemanticAttributes.
        """
        elements = unstructured_obj["Unstructured"]
        attributes = []
        languages = set()

        attributes.append(self.extract_filename_attribute(elements))
        attributes.append(self.extract_filetype_attribute(elements))

        for element in elements:
            semantic_attribute = IndalekoSemanticAttributeDataModel(
                Identifier=self.get_attribute_identifier(element["type"]),
                Value=element["text"],
                # Data = {
                #     "text": element['text'],
                #     # "metadata": element["metadata"] #May be redundant
                # }
            )

            languages.update(element["metadata"]["languages"])
            attributes.append(semantic_attribute)

        attributes.extend(self.extract_language_attribute_list(languages))

        return attributes

    def get_attribute_identifier(self, label: str):

        return label

        # prefix = known_semantic_attributes.PREFIX
        # id = prefix + '_'+label.upper()
        # return IndalekoUUIDDataModel(
        #             Identifier = self.attributes_by_label[id],
        #             Label=label
        #         )

    def map_attributes(
        self,
        attributes: list[IndalekoSemanticAttributeDataModel],
    ) -> None:
        """
        Given a list of SemanticAttributes, iterate through each attribute and
        replace the Identifier (originally an Unstructured Label) with the UUID
        that maps to it. Essentially, this function separates the meaning of the label
        from the data storage.

        See semantic.collectors.semantic_attributes for the list of labels
        """
        prefix = known_semantic_attributes.PREFIX
        for attr in attributes:
            id = prefix + "_" + attr.Identifier.upper()
            attr.Identifier = self.attributes_by_label[id]

    def record(self) -> None:
        """
        Main function that reads the output JSONL file from unstructured and normalizes
        the elements of all the files.

        The output of this function is written into another JSONL file and is ready
        for upload onto the ArangoDB instance
        """
        # Read the JSONL file and convert to JSON
        with open(self.output_file, "w", encoding="utf-8") as jsonl_output:
            with open(self.input_file, encoding="utf-8") as jsonl_file:
                for line in jsonl_file:
                    unstructured_obj = json.loads(line)

                    semantic_record = self.create_semantic_record(line)
                    timestamp = self.semantic_recording_date
                    related_objects = self.create_semantic_related_objects(
                        unstructured_obj,
                    )
                    # map_attributes(attributes) # Comment this line out if you want to see meaning of labels
                    attributes = self.normalize_semantic_attributes(unstructured_obj)

                    i_semantic_attribute = BaseSemanticDataModel(
                        Record=semantic_record,
                        Timestamp=timestamp,
                        ObjectIdentifier=related_objects[0],
                        RelatedObjects=related_objects,
                        SemanticAttributes=attributes,
                    )

                    jsonl_output.write(i_semantic_attribute.model_dump_json() + "\n")


def main():
    ic("Unstructured Data Recorder")
    unstructured_recorder = UnstructuredRecorder()
    ic("Normalizing Unstructured metadata")
    unstructured_recorder.record()
    ic("Extracted file located at: ", unstructured_recorder.output_file)

    # parser = argparse.ArgumentParser(description='Indaleko Unstructured Data Recorder')

    # command_subparser = parser.add_subparsers(dest='command', help='Command to execute')

    # ## Subparser to normalize the unstructured outputs
    # parser_lookup = command_subparser.add_parser('record',
    #                                             help='Creates a jsonl file that contains the normalized Unstructured outputs')
    # parser_lookup.set_defaults(func = unstructured_recorder.record)

    # parser.set_defaults(func = None)


if __name__ == "__main__":
    main()
