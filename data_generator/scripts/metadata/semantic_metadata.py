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
    LIST_TAGS = ['List','ListItem', 'List-item'] #faker.sentence() split by " " and \n line break 

    #exactly
    SHORT_TAGS = ['Title', 'Headline', 'Subtitle', 'Subheadline', 'Page-header', 'Section-header', 'Header', 'Field-Name', 'BulletedText', 'Page-footer', 'Footer', 'Footnote', 'Threading', 'Table'] #faker.text(max_nb_chars = 10)
    NUMBER_TAGS = ['PageNumber', 'Value'] # random.number()
    KEY_VALUE_TAGS = ['Form', 'FormKeysValues'] #"{faker.word()} : {faker.word()}"
    BUTTON_TAGS = ['Checked', 'Unchecked', 'CheckBoxChecked', 'CheckBoxUnchecked', 'RadioButtonChecked', 'RadioButtonUnchecked'] #true

    #random/always there:
    PageBreak = "--- PAGE BREAK ---"
    DEFAULT_LANGUAGE = "English"
    #should be generated
    IMAGE_TAGS = ['Image', 'Picture', 'Figure'] # faker.image()
    TEXT_BASED_FILES = ["pdf", "doc", "docx", "txt", "rtf", "csv", "xls", "xlsx", "ppt", "pptx"] 

    def __init__(self, selected_semantic_md):
        super().__init__(selected_semantic_md)
        self.selected_number_values = {key: set() for key in self.NUMBER_TAGS}


    # def create_semantic_attribute(self, extension: str, last_modified: str, is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str], has_semantic:bool) -> list[Dict[str, Any]]:
    #     """Creates the semantic attribute data based on semantic attribute datamodel"""
    #     # text based files supported by the metadata generator
    #     list_semantic_attribute = []
    #     if extension in SemanticMetadata.TEXT_BASED_FILES:
    #         data = self._generate_semantic_content(extension, last_modified, is_truth_file, truth_like, truthlike_attributes, has_semantic)
    #     else:
    #         data = {"LastModified": last_modified, "FileType": extension}
        
    #     for label, context in data.items(): 
    #         semantic_attribute = IndalekoSemanticAttributeDataModel(Identifier= IndalekoUUIDDataModel(Identifier=label, Label=None), Data=context)
    #         list_semantic_attribute.append(semantic_attribute.dict())
    #     return list_semantic_attribute
    
    # def generate_semantic_data(self, record_data: IndalekoRecordDataModel, IO_UUID: str, semantic_attributes_data: list[Dict[str, Any]]) -> BaseSemanticDataModel:
    #     """Returns the semantic data created from the data model"""

    #     return BaseSemanticDataModel(
    #             Record=record_data,
    #             Timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
    #             ObjectIdentifier= IO_UUID, 
    #             RelatedObjects=[IO_UUID],
    #             SemanticAttributes=semantic_attributes_data)

    # def _generate_semantic_content(self, extension: str, last_modified: str, is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str], has_semantic: bool) -> Dict[str, Any]:
    #     """Generates semantic metadata with given parameters"""
    #     data_list = []
    #     # if the selected_semantic_md is queried, and it's a truth metadata
    #     if self.selected_md is not None and (has_semantic or is_truth_file):
    #         for content_type, content in self.selected_md.items():
    #             if self._define_truth_attribute(content_type, is_truth_file, truth_like, truthlike_attributes):
    #                 semantic_data = self._generate_semantic_content_data(extension, last_modified)
    #                 # Create a copy of content to avoid mutating the original
    #                 content_copy = content.copy()
    #                 remaining_keys = set(SemanticMetadata.AVAIL_TEXT_TAGS) - set(content_copy.keys())
    #                 for remaining in remaining_keys:
    #                     content_copy[remaining] = semantic_data[remaining]
    #                 data_list.append(content_copy)
    #         data_list.append({"LastModified": last_modified, "FileType": extension})
    #     else:
    #         for _ in range(0, random.randint(1, 3)):
    #             semantic_data = self._generate_semantic_content_data(extension, last_modified)
    #             data_list.append(semantic_data)
    #     return data_list
    

    # def _generate_semantic_content_data(self, extension: str, last_modified: str) -> Dict[str, Any]:
    #     """
    #     Generate random semnatic content
    #     """
    #     faker = Faker()
    #     text = faker.sentence(nb_words=random.randint(1, 30))
    #     type = random.choice(SemanticMetadata.AVAIL_TEXT_TAGS)
    #     text_tag = random.choice(SemanticMetadata.EMPHASIZED_TEXT_TAGS)
    #     page_number = random.randint(1, 200)
    #     # for now, excluding emphasized text contents
    #     # emphasized_text_contents = random.choice(text.split(" "))

    #     return {
    #         "Languages": SemanticMetadata.LANGUAGES,
    #         "FileType": extension,
    #         "PageNumber": page_number,
    #         "LastModified": last_modified,
    #         "Text": text,
    #         "Type": type,
    #         "EmphasizedTextTags": text_tag
    #         # "EmphasizedTextContents": emphasized_text_contents
    #     }
    


    # --------------------------------------------------------------------------

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

        data.append(("LastModified", last_modified))
        data.append(("filetype", extension))
        data.append(("filename", file_name))
        data.append(("language", self.DEFAULT_LANGUAGE))
        
        for tuple in data: 
            label, content = tuple
            semantic_attribute = {
                "Identifier": label,
                "Data": {
                    "Text":content
                    }
            }
        
            # semantic_attribute = IndalekoSemanticAttributeDataModel(Identifier= get_attribute_identifier(label), Data=content)
            # list_semantic_attribute.append(semantic_attribute.dict())
            list_semantic_attribute.append(semantic_attribute)
        ic(list_semantic_attribute)
        return list_semantic_attribute

    
    # if this is a text file, if not just generate the last mod and ...
    #TODO: i don't think has_semantic_filler needed...
    def generate_semantic_attribute(self, is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str], has_semantic_filler: bool):
        random_semantic = random.choices(self.AVAIL_TEXT_TAGS, k = random.randint(1, 25))
        attribute_tuple_list = []
        if self.selected_md:
            for key, value in self.selected_md.items():
                is_truth_file = self._define_truth_attribute(key, is_truth_file, truth_like, truthlike_attributes)
                ic(is_truth_file)
                if is_truth_file: # for truth and truth like metadata
                    tag, content = value     
                    ic(content)               
                    semantic_attribute = self._generate_semantics(True, tag, content)
                    attribute_tuple_list.append((tag, semantic_attribute))
                    ic(attribute_tuple_list)
                else: 
                    for item in random_semantic:
                        semantic_attribute = self._generate_semantics(False, item)
                        attribute_tuple_list.append((item, semantic_attribute))
        else:
            for item in random_semantic:
                semantic_attribute = self._generate_semantics(is_truth_file, item)
                attribute_tuple_list.append((item, semantic_attribute))

        return attribute_tuple_list

    def _generate_semantics(self, is_truth_file, tag, content: str = None):
        ic(tag)
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
        elif tag == "Languages":
            semantic_attribute = "English"
        elif tag == "PageBreak":
            semantic_attribute = "--- PAGE BREAK ---"
        elif tag == "Formula":
            semantic_attribute = self._generate_formula(is_truth_file)
        elif tag == "CodeSnippet":
            semantic_attribute = self._generate_python_code(is_truth_file)
        else:
            raise ValueError("semantic attribute is not available")
        return semantic_attribute

    def _generate_random_image(self, is_truth_file: bool, value = None) -> int:
        if is_truth_file and self.selected_md:
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
            return self.faker.text(max_nb_chars = 10)

    def _generate_long_tags(self, truth_file: bool, content = None) -> str:
        sentences = self.faker.sentences()
        concatenated_sentences = " ".join(sentences)
        if truth_file and self.selected_md:
            ic(truth_file)
            ic(content)
            concatenated_sentences = content + concatenated_sentences
        
        
        return concatenated_sentences
            
    def _generate_formula(self, is_truth_file) -> str:
        if is_truth_file and "Formula" in self.AVAIL_TEXT_TAGS:
            self.AVAIL_TEXT_TAGS.remove("Formula")
        operators = ['+', '-', '*', '/']
        num1 = random.randint(1, 100)
        num2 = random.randint(1, 100)
        operator = random.choice(operators)
        return f"{num1} {operator} {num2}"

    def _generate_python_code(self, is_truth_file) -> str:
        if is_truth_file and "CodeSnippet" in self.AVAIL_TEXT_TAGS:
            self.AVAIL_TEXT_TAGS.remove("CodeSnippet")
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
        sentence = self.faker.sentence() 
        if truth_file and self.selected_md:
            sentence = sentence + " " + content
        word_list_string = "[\n" + ",\n".join(f"'{word}'" for word in sentence.replace("\n", " ").split()) + "\n]"
        return word_list_string

    # "Semantic": {
    #     "Content_1": ("PageNumber", 20),
    #     "Content_2" : ("SUBTITLE", "jogging"),
    #     "Content_3" : ("TITLE", "EXERCISE"),
    # }
