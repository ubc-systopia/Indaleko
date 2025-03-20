from typing import Dict, Any, Tuple, Union, Callable
import random
import uuid
from faker import Faker
from datetime import datetime
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from semantic.data_models.base_data_model import BaseSemanticDataModel
from data_generator.scripts.metadata.metadata import Metadata


class SemanticMetadata(Metadata):
    """
    Subclass for Semantic Metadata.
    Generates Semantic Metadata based on the given dictionary of queries
    """

    EMPHASIZED_TEXT_TAGS = ["bold", "italic", "underline", "strikethrough", "highlight"]
    TEXT_TAGS = [
        "Title",
        "Subtitle",
        "Header",
        "Footer",
        "Paragraph",
        "BulletPoint",
        "NumberedList",
        "Caption",
        "Quote",
        "Metadata",
        "UncategorizedText",
        "SectionHeader",
        "Footnote",
        "Abstract",
        "FigureDescription",
        "Annotation",
    ]
    LANGUAGES = "English"
    TEXT_BASED_FILES = [
        "pdf",
        "doc",
        "docx",
        "txt",
        "rtf",
        "csv",
        "xls",
        "xlsx",
        "ppt",
        "pptx",
    ]

    def __init__(self, selected_semantic_md):
        super().__init__(selected_semantic_md)

    def generate_metadata(
        self,
        record_data: IndalekoRecordDataModel,
        IO_UUID: str,
        semantic_attributes_data: list[Dict[str, Any]],
    ) -> BaseSemanticDataModel:
        return self._generate_semantic_data(
            record_data, IO_UUID, semantic_attributes_data
        )

    def create_semantic_attribute(
        self,
        extension: str,
        last_modified: str,
        is_truth_file: bool,
        truth_like: bool,
        truthlike_attributes: list[str],
        has_semantic: bool,
    ) -> list[Dict[str, Any]]:
        """Creates the semantic attribute data based on semantic attribute datamodel"""
        # text based files supported by the metadata generator
        list_semantic_attribute = []
        if extension in SemanticMetadata.TEXT_BASED_FILES:
            data = self._generate_semantic_content(
                extension,
                last_modified,
                is_truth_file,
                truth_like,
                truthlike_attributes,
                has_semantic,
            )
        else:
            data = [extension, last_modified]

        for content in data:
            semantic_UUID = uuid.uuid4()
            if isinstance(content, dict):
                for label, context in content.items():
                    semantic_attribute = IndalekoSemanticAttributeDataModel(
                        Identifier=IndalekoUUIDDataModel(
                            Identifier=semantic_UUID, Label=label
                        ),
                        Value=context,
                    )
                    list_semantic_attribute.append(semantic_attribute.dict())
            else:
                semantic_attribute = IndalekoSemanticAttributeDataModel(
                    Identifier=IndalekoUUIDDataModel(
                        Identifier=semantic_UUID, Label=content
                    ),
                    Value=content,
                )
                list_semantic_attribute.append(semantic_attribute.dict())
        return list_semantic_attribute

    def _generate_semantic_data(
        self,
        record_data: IndalekoRecordDataModel,
        IO_UUID: str,
        semantic_attributes_data: list[Dict[str, Any]],
    ) -> BaseSemanticDataModel:
        """Returns the semantic data created from the data model"""
        return BaseSemanticDataModel(
            Record=record_data,
            Timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            RelatedObjects=[IO_UUID],
            SemanticAttributes=semantic_attributes_data,
        )

    def _generate_semantic_content(
        self,
        extension: str,
        last_modified: str,
        is_truth_file: bool,
        truth_like: bool,
        truthlike_attributes: list[str],
        has_semantic: bool,
    ) -> Dict[str, Any]:
        """Generates semantic metadata with given parameters"""
        data_list = []
        all_semantics_attributes = {
            "Languages",
            "PageNumber",
            "Text",
            "Type",
            "EmphasizedTextTags",
            "EmphasizedTextContents",
        }
        # if the selected_semantic_md is queried, and it's a truth metadata
        if self.selected_md is not None and (has_semantic or is_truth_file):
            for content_type, content in self.selected_md.items():
                if self._define_truth_attribute(
                    content_type, is_truth_file, truth_like, truthlike_attributes
                ):
                    semantic_data = self._generate_semantic_content_data(
                        extension, last_modified
                    )
                    # Create a copy of content to avoid mutating the original
                    content_copy = content.copy()
                    remaining_keys = all_semantics_attributes - set(content_copy.keys())
                    for remaining in remaining_keys:
                        content_copy[remaining] = semantic_data[remaining]
                    data_list.append(content_copy)
            data_list.append({"LastModified": last_modified, "FileType": extension})
        else:
            for _ in range(0, random.randint(1, 3)):
                semantic_data = self._generate_semantic_content_data(
                    extension, last_modified
                )
                data_list.append(semantic_data)
        return data_list

    def _generate_semantic_content_data(
        self, extension: str, last_modified: str
    ) -> Dict[str, Any]:
        """
        Generate random semnatic content
        """
        faker = Faker()
        text = faker.sentence(nb_words=random.randint(1, 30))
        type = random.choice(SemanticMetadata.TEXT_TAGS)
        text_tag = random.choice(SemanticMetadata.EMPHASIZED_TEXT_TAGS)
        page_number = random.randint(1, 200)
        emphasized_text_contents = random.choice(text.split(" "))

        return {
            "Languages": SemanticMetadata.LANGUAGES,
            "FileType": extension,
            "PageNumber": page_number,
            "LastModified": last_modified,
            "Text": text,
            "Type": type,
            "EmphasizedTextTags": text_tag,
            "EmphasizedTextContents": emphasized_text_contents,
        }
