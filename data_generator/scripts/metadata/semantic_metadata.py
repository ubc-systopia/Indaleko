"""Generate semantic metadata."""

import random

from datetime import UTC, datetime
from typing import Any, Literal

from faker import Faker

from data_generator.scripts.metadata.metadata import Metadata
from data_models.record import IndalekoRecordDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from semantic.data_models.base_data_model import BaseSemanticDataModel


# ruff: noqa: S311, FBT001


class SemanticMetadata(Metadata):
    """
    Subclass for Semantic Metadata.

    Generates Semantic Metadata based on the given dictionary of queries.
    """

    MIN_PAGE = 1
    MAX_PAGE = 200
    MIN_VALUE = -500
    MAX_VALUE = 500

    OPERATORS = ("+", "-", "*", "/")

    AVAIL_TEXT_TAGS = (
        "Title",
        "Text",
        "UncategorizedText",
        "NarrativeText",
        "BulletedText",
        "FormKeysValues",
        "Paragraph",
        "Abstract",
        "Threading",
        "Form",
        "Field-Name",
        "Value",
        "Link",
        "CompositeElement",
        "Image",
        "Picture",
        "FigureCaption",
        "Figure",
        "Caption",
        "List",
        "ListItem",
        "List-item",
        "Checked",
        "Unchecked",
        "CheckBoxChecked",
        "CheckBoxUnchecked",
        "RadioButtonChecked",
        "RadioButtonUnchecked",
        "Address",
        "EmailAddress",
        "PageBreak",
        "Formula",
        "Table",
        "Header",
        "Headline",
        "Subheadline",
        "Page-header",
        "Section-header",
        "Footer",
        "Footnote",
        "Page-footer",
        "PageNumber",
        "CodeSnippet",
    )

    # contains:
    LONG_TAGS = (
        "Text",
        "UncategorizedText",
        "NarrativeText",
        "Paragraph",
        "Abstract",
        "FigureCaption",
        "Caption",
        "CompositeElement",
    )  # truth + faker.paragraph()
    LIST_TAGS = ("List", "ListItem", "List-item")

    # exactly:
    SHORT_TAGS = (
        "Title",
        "Headline",
        "Subtitle",
        "Subheadline",
        "Page-header",
        "Section-header",
        "Header",
        "Field-Name",
        "BulletedText",
        "Page-footer",
        "Footer",
        "Footnote",
        "Threading",
        "Table",
    )  # faker.text(max_nb_chars = 10)
    NUMBER_TAGS = ("PageNumber", "Value")
    KEY_VALUE_TAGS = ("Form", "FormKeysValues")
    BUTTON_TAGS = (
        "Checked",
        "Unchecked",
        "CheckBoxChecked",
        "CheckBoxUnchecked",
        "RadioButtonChecked",
        "RadioButtonUnchecked",
    )  # true

    # random/always there:
    PAGEBREAK = "--- PAGE BREAK ---"
    DEFAULT_LANGUAGE = "English"

    # should be generated:
    IMAGE_TAGS = ("Image", "Picture", "Figure")
    TEXT_BASED_FILES = ("pdf", "doc", "docx", "txt", "rtf", "csv", "xls", "xlsx", "ppt", "pptx")

    faker = Faker()

    def __init__(self, selected_semantic_md: dict) -> None:
        """Initialize the object."""
        super().__init__(selected_semantic_md)
        self.selected_number_values = {key: set() for key in self.NUMBER_TAGS}

    def generate_metadata(self, **kwargs: dict) -> BaseSemanticDataModel:
        """Generate the semantic metadata."""
        _record_data = kwargs["record_data"]
        _io_uuid = kwargs["IO_UUID"]
        extension = kwargs["extension"]
        last_modified = kwargs["last_modified"]
        file_name = kwargs["file_name"]
        is_truth_file = kwargs["is_truth_file"]
        truth_like = kwargs["truth_like"]
        truthlike_attributes = kwargs["truthlike_attributes"]
        has_semantic_filler = kwargs["has_semantic_filler"]
        return self.create_semantic_attribute(
            extension,
            last_modified,
            file_name,
            is_truth_file,
            truth_like,
            truthlike_attributes,
            has_semantic_filler,
        )

    def _generate_semantic_data(
        self,
        record_data: IndalekoRecordDataModel,
        io_uuid: str,
        semantic_attributes_data: list[dict[str, Any]],
    ) -> BaseSemanticDataModel:
        """Returns the semantic data created from the data model."""
        return BaseSemanticDataModel(
            Record=record_data,
            Timestamp=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            ObjectIdentifier=io_uuid,
            RelatedObjects=[io_uuid],
            SemanticAttributes=semantic_attributes_data,
        )

    def create_semantic_attribute(
        self,
        extension: str,
        last_modified: str,
        file_name: str,
        is_truth_file: bool,
        truth_like: bool,
        truthlike_attributes: list[str],
        has_semantic_filler: bool,
    ) -> list[dict[str, Any]]:
        """Creates the semantic attribute data based on semantic attribute datamodel."""
        list_semantic_attribute = []
        data = []

        if extension in SemanticMetadata.TEXT_BASED_FILES:
            semantic_data = self.generate_semantic_attribute(
                is_truth_file,
                truth_like,
                truthlike_attributes,
                has_semantic_filler,
            )
            data = semantic_data
            data.append(("Language", self.DEFAULT_LANGUAGE))

        data.append(("LastModified", last_modified))
        data.append(("filetype", extension))
        data.append(("filename", file_name))

        for element in data:
            label, content = element
            semantic_attribute = IndalekoSemanticAttributeDataModel(Identifier=label, Data=content)
            list_semantic_attribute.append(semantic_attribute.model_dump())

        return list_semantic_attribute

    def generate_semantic_attribute(
        self,
        is_truth_file: bool,
        truth_like: bool,
        truthlike_attributes: list[str],
        has_semantic_filler: bool,
    ) -> list[tuple]:
        """Creates the semantic attributes based on file type (truth/truthlike/filler)."""
        attribute_tuple_list = []
        random_semantic = random.choices(
            self.AVAIL_TEXT_TAGS,
            k=random.randint(1, 25),
        )

        if self.selected_md is not None and (has_semantic_filler or is_truth_file):
            for key, value in self.selected_md.items():
                if self._define_truth_attribute(
                    key,
                    is_truth_file,
                    truth_like,
                    truthlike_attributes,
                ):
                    tag, content = value
                    semantic_attribute = self._generate_semantics(True, tag, content)  # noqa: FBT003
                    attribute_tuple_list.append((tag, semantic_attribute))
        else:  # if no semantics chosen or a filler file
            for item in random_semantic:
                semantic_attribute = self._generate_semantics(
                    False,  # noqa: FBT003
                    item,
                )
                attribute_tuple_list.append((item, semantic_attribute))

        return attribute_tuple_list

    def _generate_semantics(  # noqa: PLR0912
        self,
        is_truth_file: bool,
        tag: str,
        content: str | None = None,
    ) -> str | int | Literal[True]:
        """Creates specfied semantics attribute."""
        if tag in self.LONG_TAGS:
            semantic_attribute = self._generate_long_tags(is_truth_file, content)
        elif tag in self.LIST_TAGS:
            semantic_attribute = self._generate_list(is_truth_file, content)
        elif tag == "Link":
            semantic_attribute = self._generate_link(is_truth_file, content)
        elif tag in self.IMAGE_TAGS:
            semantic_attribute = self._generate_random_image(is_truth_file, content)
        elif tag in self.SHORT_TAGS:
            semantic_attribute = self._pass_generate_short(is_truth_file, content)
        elif tag == "EmailAddress":
            semantic_attribute = self._generate_email(is_truth_file, content)
        elif tag in self.NUMBER_TAGS:
            semantic_attribute = self._generate_random_number(is_truth_file, tag, content)
        elif tag in self.KEY_VALUE_TAGS:
            semantic_attribute = self._generate_key_value(is_truth_file, content)
        elif tag in self.BUTTON_TAGS:
            semantic_attribute = True
        elif tag == "Address":
            semantic_attribute = self._generate_address(is_truth_file, content)
        elif tag == "PageBreak":
            semantic_attribute = self.PAGEBREAK
        elif tag == "Formula":
            semantic_attribute = self._generate_formula(is_truth_file, content)
        elif tag == "CodeSnippet":
            semantic_attribute = self._generate_python_code(is_truth_file, content)
        else:
            raise ValueError("semantic attribute is not available")
        return semantic_attribute

    def _generate_random_image(self, is_truth_file: bool, value: str | None = None) -> str:
        """Creates name for random image."""
        if is_truth_file and self.selected_md:
            if "." in value:
                return value
            return value + "." + self.faker.file_extension(category="image")
        return self.faker.word() + self.faker.file_extension(category="image")

    def _generate_random_number(self, is_truth_file: bool, tag: str, value: str | None = None) -> int:
        """Generates random number for specific semantics attributes."""
        if is_truth_file and self.selected_md:
            self.selected_number_values[tag].add(value)
            return value
        match tag:
            case "PageNumber":
                return self._generate_filler_number(self.MIN_PAGE, self.MAX_PAGE, tag)
            case "Value":
                return self._generate_filler_number(self.MIN_VALUE, self.MAX_VALUE, tag)
            case _:
                raise ValueError(f"Invalid tag {tag} for generating random number")

    def _generate_filler_number(self, min_value: int, max_value: int, tag: str) -> int:
        """Generates random number."""
        avail_num = self.selected_number_values[tag]
        possible_values = set(range(min_value, max_value + 1)) - avail_num
        if possible_values:
            return random.choice(list(possible_values))
        raise ValueError(f"No numbers in the range. Consider broadening the boundary for {tag}")

    def _generate_email(
        self,
        is_truth_file: bool,
        value: str | None = None,
    ) -> str:
        """Generates email address."""
        if is_truth_file and self.selected_md:
            return value
        return self.faker.email()

    def _generate_address(
        self,
        is_truth_file: bool,
        value: str | None = None,
    ) -> str:
        """Generates address."""
        if is_truth_file and self.selected_md:
            return value
        return self.faker.address()

    def _generate_key_value(
        self,
        is_truth_file: bool,
        value: str | None = None,
    ) -> str:
        """Generates key value pair."""
        if is_truth_file and self.selected_md:
            # should be a "key:value"
            return value
        return f"{self.faker.word()} : {self.faker.word()}"

    def _pass_generate_short(
        self,
        is_truth_file: bool,
        value: str | None = None,
    ) -> str:
        """Generates short string."""
        if is_truth_file and self.selected_md:
            return value
        return self.faker.text(max_nb_chars=10).rstrip(".")

    def _generate_long_tags(
        self,
        truth_file: bool,
        content: str | None = None,
    ) -> str:
        """Generates long tags."""
        sentences = self.faker.sentences()
        if not truth_file or not self.selected_md:
            return " ".join(sentences)
        if truth_file and self.selected_md:
            if "." not in content:
                words = self.faker.words(nb=random.randint(2, 8))
                content = self._insert_words_randomly(content, words) + "."
                content = content[0].capitalize() + content[1:]
            return self._insert_words_randomly(content, sentences)
        return None

    def _insert_words_randomly(self, content: str | None, list_sentences: list) -> str:
        """Inserts words randomly given a content and sentences."""
        random_index = random.randint(0, len(list_sentences))
        list_sentences.insert(random_index, content)
        return " ".join(list_sentences)

    def _generate_formula(self, is_truth_file: bool, content: str) -> str:
        """Generates mathematical fomula."""
        if is_truth_file and "Formula" in self.AVAIL_TEXT_TAGS:
            return content
        num1 = random.randint(self.MIN_VALUE, self.MAX_VALUE)
        num2 = random.randint(self.MIN_VALUE, self.MAX_VALUE)
        operator = random.choice(self.OPERATORS)
        return f"{num1} {operator} {num2}"

    def _generate_python_code(self, is_truth_file: bool, content: str) -> str:
        """Generates code snippet."""
        if is_truth_file and "CodeSnippet" in self.AVAIL_TEXT_TAGS:
            return content

        function_name = self.faker.word()
        variable_name = self.faker.word()
        return f"""
            def {function_name}():\n {variable_name} =
                {random.randint(self.MIN_VALUE, self.MAX_VALUE)}\n
            return {variable_name}
        """

    def _generate_link(self, truth_file: bool, content: str | None = None) -> str:
        """Generates link."""
        if truth_file and self.selected_md:
            return "https://" + content + ".com/'"
        return self.faker.url()

    def _generate_list(self, truth_file: bool, content: str | None = None) -> str:
        """Generates list of elements."""
        sentence = self.faker.sentence().rstrip(".")
        if truth_file and self.selected_md:
            sentence = sentence + " " + content
        return "[\n" + ",\n".join(f"'{word}'" for word in sentence.replace("\n", " ").split()) + "\n]"
