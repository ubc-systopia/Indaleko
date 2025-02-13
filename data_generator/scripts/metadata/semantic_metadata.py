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
from icecream import ic
# from semantic.recorders.unstructured.recorder import get_attribute_identifier
# from pillow import Image


class SemanticMetadata(Metadata):
    faker = Faker()
    """
    Subclass for Semantic Metadata.
    Generates Semantic Metadata based on the given dictionary of queries
    """
    # EMPHASIZED_TEXT_TAGS = ["bold", "italic", "underline", "strikethrough", "highlight"]
    AVAIL_TEXT_TAGS = ['Title', 'Text', 'UncategorizedText', 'NarrativeText', 'BulletedText', 'FormKeysValues',
                            'Paragraph', 'Abstract', 'Threading', 'Form', 'Field-Name', 'Value', 'Link', 'CompositeElement', 
                            'Image', 'Picture', 'FigureCaption', 'Figure', 'Caption', 'List', 'ListItem', 'List-item', 'Checked', 
                            'Unchecked', 'CheckBoxChecked', 'CheckBoxUnchecked', 'RadioButtonChecked', 'RadioButtonUnchecked', 
                            'Address', 'EmailAddress', 'PageBreak', 'Formula', 'Table', 'Header', 'Headline', 'Subheadline', 
                            'Page-header', 'Section-header', 'Footer', 'Footnote', 'Page-footer', 'PageNumber', 'CodeSnippet', 
                            ]

    #key value pairs should exist "tag": value of tag
    #contains
    LONG_TAGS = ['Text', 'UncategorizedText', 'NarrativeText', 'Paragraph', 'Abstract', 'FigureCaption', 'Caption', 'CompositeElement'] #truth + faker.paragraph()
    LIST_TAGS = ['List','ListItem', 'List-item'] 

    #exactly
    SHORT_TAGS = ['Title', 'Headline', 'Subtitle', 'Subheadline', 'Page-header', 'Section-header', 'Header', 'Field-Name', 'BulletedText', 'Page-footer', 'Footer', 'Footnote', 'Threading', 'Table'] #faker.text(max_nb_chars = 10)
    NUMBER_TAGS = ['PageNumber', 'Value']
    KEY_VALUE_TAGS = ['Form', 'FormKeysValues']
    BUTTON_TAGS = ['Checked', 'Unchecked', 'CheckBoxChecked', 'CheckBoxUnchecked', 'RadioButtonChecked', 'RadioButtonUnchecked'] #true

    #random/always there:
    PAGEBREAK = "--- PAGE BREAK ---"
    DEFAULT_LANGUAGE = "English"
    #should be generated
    IMAGE_TAGS = ['Image', 'Picture', 'Figure'] 
    TEXT_BASED_FILES = ["pdf", "doc", "docx", "txt", "rtf", "csv", "xls", "xlsx", "ppt", "pptx"] 

    def __init__(self, selected_semantic_md):
        super().__init__(selected_semantic_md)
        self.selected_number_values = {key: set() for key in self.NUMBER_TAGS}

    def generate_metadata(self, record_data: IndalekoRecordDataModel, IO_UUID: str, extension: str, 
                    last_modified: str, file_name:str, is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str], has_semantic_filler: bool)  -> BaseSemanticDataModel:
        semantic_attributes_data = self.create_semantic_attribute(extension, last_modified, file_name, is_truth_file, truth_like, truthlike_attributes, has_semantic_filler)
        return self._generate_semantic_data(record_data, IO_UUID, semantic_attributes_data)


    def _generate_semantic_data(self, record_data: IndalekoRecordDataModel, IO_UUID: str, semantic_attributes_data: list[Dict[str, Any]]) -> BaseSemanticDataModel:
        """Returns the semantic data created from the data model"""
        return BaseSemanticDataModel(
                Record=record_data,
                Timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                ObjectIdentifier= IO_UUID, 
                RelatedObjects=[IO_UUID],
                SemanticAttributes=semantic_attributes_data)


    def create_semantic_attribute(self, extension: str, last_modified: str, file_name:str, is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str], has_semantic_filler:bool) -> list[Dict[str, Any]]:
        """Creates the semantic attribute data based on semantic attribute datamodel"""
        # text based files supported by the metadata generator
        list_semantic_attribute = []
        data = []
        if extension in SemanticMetadata.TEXT_BASED_FILES:
            semantic_data = self.generate_semantic_attribute(is_truth_file, truth_like, truthlike_attributes, has_semantic_filler)
            data = semantic_data
            data.append(("Language", self.DEFAULT_LANGUAGE))

        data.append(("LastModified", last_modified))
        data.append(("filetype", extension))
        data.append(("filename", file_name))
        
        for tuple in data: 
            label, content = tuple
            semantic_attribute = IndalekoSemanticAttributeDataModel(Identifier=label, Data=content)
            list_semantic_attribute.append(semantic_attribute.dict())
        return list_semantic_attribute

    def generate_semantic_attribute(self, is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str], has_semantic_filler: bool):
        random_semantic = random.choices(self.AVAIL_TEXT_TAGS, k = random.randint(1, 25))
        attribute_tuple_list = []   
        if self.selected_md is not None and (has_semantic_filler or is_truth_file):
            for key, value in self.selected_md.items():
                if self._define_truth_attribute(key, is_truth_file, truth_like, truthlike_attributes):
                    tag, content = value     
                    semantic_attribute = self._generate_semantics(True, tag, content)
                    attribute_tuple_list.append((tag, semantic_attribute))
        else: # if no semantics chosen or a filler file
            for item in random_semantic:
                semantic_attribute = self._generate_semantics(False, item)
                attribute_tuple_list.append((item, semantic_attribute))

        return attribute_tuple_list

    def _generate_semantics(self, is_truth_file, tag, content: str = None):
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

    def _generate_random_image(self, is_truth_file: bool, value = None) -> int:
        if is_truth_file and self.selected_md:
            if "." in value:
                return value
            else:
                return value + "." + self.faker.file_extension(category='image')
        else: 
            return self.faker.word() + self.faker.file_extension(category='image')

    def _generate_random_number(self, is_truth_file: bool, tag: str, value = None) -> int:
        min_page = 1
        max_page = 200
        min_value = -500
        max_value = 500
        if is_truth_file and self.selected_md:
            self.selected_number_values[tag].add(value)
            return value
        else:
            if tag == "PageNumber":
                return self._generate_filler_number(min_page, max_page, tag)
            elif tag == "Value":
                return self._generate_filler_number(min_value, max_value, tag)
            return self._generate_filler_number(tag)

    def _generate_filler_number(self, min: int, max:int, tag:str) -> int:
        avail_num = self.selected_number_values[tag]
        possible_values = set(range(min, max + 1)) - avail_num 
        if possible_values:
            return random.choice(list(possible_values))
        else:
            raise ValueError(f"No numbers in the range. Consider broadening the boundary for {tag}")

    def _generate_email(self, is_truth_file, value = None) -> str:
        if is_truth_file and self.selected_md: 
            return value
        else:
            return self.faker.email()

    def _generate_address(self, is_truth_file, value = None) -> str:
        if is_truth_file and self.selected_md: 
            return value
        else:
            return self.faker.address()

    def _generate_key_value(self, is_truth_file, value= None) -> str:
        if is_truth_file and self.selected_md:
            # should be a "key:value"
            return value
        else:
            return f"{self.faker.word()} : {self.faker.word()}"


    def _pass_generate_short(self, is_truth_file, value= None) -> str:
        if is_truth_file and self.selected_md:
            return value
        else:
            return self.faker.text(max_nb_chars = 10).rstrip('.')

    def _generate_long_tags(self, truth_file: bool, content = None) -> str:
        sentences = self.faker.sentences()
        if not truth_file or not self.selected_md:
            return " ".join(sentences)
        if truth_file and self.selected_md:
            if "." not in content:
                words = self.faker.words(nb = random.randint(2, 8))
                content = self._insert_words_randomly(content, words) + "."
                content = content.capitalize()
            return self._insert_words_randomly(content, sentences)
            
    def _insert_words_randomly(self, content, list_sentences) -> str:
        random_index = random.randint(0, len(list_sentences))
        list_sentences.insert(random_index, content)
        resulting_words = " ".join(list_sentences)
        return resulting_words

            
    def _generate_formula(self, is_truth_file: bool, content: str) -> str:
        if is_truth_file and "Formula" in self.AVAIL_TEXT_TAGS:
            return content
        operators = ['+', '-', '*', '/']
        num1 = random.randint(1, 100)
        num2 = random.randint(1, 100)
        operator = random.choice(operators)
        return f"{num1} {operator} {num2}"

    def _generate_python_code(self, is_truth_file: bool, content: str) -> str:
        if is_truth_file and "CodeSnippet" in self.AVAIL_TEXT_TAGS:
            return content
        function_name = self.faker.word()
        variable_name = self.faker.word()
        code = f"def {function_name}():\n    {variable_name} = {random.randint(1, 100)}\n    return {variable_name}"
        return code

    def _generate_link(self, truth_file, content= None) -> str:
        if truth_file and self.selected_md:
            return "https://" + content + ".com/'"
        else: 
            return self.faker.url()

    def _generate_list(self, truth_file, content= None) -> str:
        sentence = self.faker.sentence().rstrip('.')
        if truth_file and self.selected_md:
            sentence = sentence + " " + content
        word_list_string = "[\n" + ",\n".join(f"'{word}'" for word in sentence.replace("\n", " ").split()) + "\n]"
        return word_list_string