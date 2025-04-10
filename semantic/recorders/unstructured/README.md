# Semantic metadata support in Indaleko

While semantic indexing support is not a "critical" part of the research aspects of Indaleko, it is important when constructing a "full featured" search facility, since some aspects of search will benefit from semantic analysis.   In addition, the strength of Indaleko is in demonstrating how integrating various sources of information can be beneficial in terms of improving search outcomes (_finding_).

There is no real reason to limit the tools we enable to implement semantic extraction.  In looking at options, I wanted to find something that would be viable for extracting something from a broad range of files.  There are, in fact, many tools for doing this, including at least two we've considered: [Apache Tika](https://tika.apache.org/), and [Unstructured](https://unstructured.io).

After some consideration, we've chosen to use Unstructured initially. Our use of it is a bit different than Unstructured's core purpose (e.g., preparing large datasets for use in training AI models, such as LLMs) but it is sufficiently close, that we can utilize its broad support for a variety of different file types.

**Note:** Nothing here is intended to suggest that other tools might not be useful.  [Hugging Face](https://huggingface.co/) has a vast array of tools, some of which can be used to build additional semantic data extraction mechanisms.  [LM Studio](https://lmstudio.ai/) makes it easy to take a number of models and run them locally on the machine (an essential part of providing privacy with respect to the data we're collecting and using for inference.)

## Unstructured

We took a sample of files, across a range of file types, and extracted metadata from them.  Our emphasis was on identifying the metadata elements that we think will be beneficial in augmenting the search abilities of Indaleko.

Here is a "prototype" of a pydantic schema definition of the common metadata elements that look to be useful:

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class ExtractedElement(BaseModel):
    element_id: str = Field(..., description="Unique identifier for each extracted metadata element.")
    filename_uuid: str = Field(..., description="UUID representing the original file's identity in ArangoDB.")
    filetype: str = Field(..., description="Type of the file, e.g., PDF, DOCX, etc.")
    last_modified: datetime = Field(..., description="Last modification timestamp of the source file.")
    page_number: Optional[int] = Field(None, description="Page number from which the text was extracted, if applicable.")
    languages: List[str] = Field(..., description="Languages detected in the text.")
    emphasized_text_contents: Optional[List[str]] = Field(None, description="List of text strings that are emphasized in the source document.")
    emphasized_text_tags: Optional[List[str]] = Field(None, description="Corresponding tags (e.g., bold, italic) for emphasized text.")
    text: str = Field(..., description="The extracted text content.")
    type: str = Field(..., description="Type of the extracted text, such as 'Title' or 'UncategorizedText'.")

    class Config:
        schema_extra = {
            "example": {
                "element_id": "964ed20182745c596e23dd371e368df3",
                "filename_uuid": "f1a2b3c4-d5e6-7f89-0abc-def123456789",
                "filetype": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "last_modified": "2024-09-06T19:59:50",
                "page_number": 1,
                "languages": ["eng"],
                "emphasized_text_contents": ["IN THE UNITED STATES DISTRICT COURT"],
                "emphasized_text_tags": ["b"],
                "text": "IN THE UNITED STATES DISTRICT COURT",
                "type": "Title"
            }
        }
```

Note that this was generated via a [conversation](https://chatgpt.com/share/67029bde-8640-800e-8cba-cbf8c09eecd0) via ChatGPT-4o-with-canvas.

This is not a useful representation of the general direction for Indaleko data, but it is useful in understanding the metadata that is available.  In addition, the same conversation includes a discussion about the "mapping" between the JSONL input data and that data schema:

```python
from datetime import datetime
from typing import Dict, Any

def map_unstructured_to_schema(raw_data: Dict[str, Any]) -> ExtractedElement:
    try:
        # Convert last_modified to a datetime object
        last_modified = datetime.fromisoformat(raw_data['metadata']['last_modified'])

        # Create ExtractedElement instance
        return ExtractedElement(
            element_id=raw_data['element_id'],
            filename_uuid=raw_data['metadata'].get('filename', 'Unknown_UUID'),  # Placeholder if UUID is not yet assigned
            filetype=raw_data['metadata']['filetype'],
            last_modified=last_modified,
            page_number=raw_data['metadata'].get('page_number'),
            languages=raw_data['metadata']['languages'],
            emphasized_text_contents=raw_data['metadata'].get('emphasized_text_contents'),
            emphasized_text_tags=raw_data['metadata'].get('emphasized_text_tags'),
            text=raw_data['text'],
            type=raw_data['type']
        )
    except KeyError as e:
        print(f"Missing expected field: {e}")
        raise

# Example usage
mapped_data = map_unstructured_to_schema(data[0])
print(mapped_data.json())
```

One challenge we need to address when using Unstructured with Indaleko is how to map the file that Unstructured processed back to the file in the Indaleko system. If we think of Unstructured as being an "ingester" (or the new term I'm tentatively using a "recorder") it becomes simple: the file name we present to Unstructured either contains or is replaced by the UUID of the file object in the database.  Since the indexers now generate those UUIDs, this can be drive just from local indexing files, though it could also be driven by using data extracted from ArangoDB as well (or in addition to).

Another challenge is in doing semantic extraction from remote files.  By default, I am assuming we will not do semantic analysis of remote files, at least for now, since it is not necessary for the prototype.  A more extensive/robust solution might add that functionality in, perhaps by doing some limited amount of such analysis.  That is a more complex process.

An important cost minimization step would be to see if a given file has already been extracted by verifying that either: (1) the metadata is not present in the collection where this data is; or (2) the metadata in the database is stale (e.g., the document has changed since last analyzed.)  Only then is it worth re-analyzing the files in Unstructured.

This is also likely to be a "batch process", where some number of files are prepared for analysis, the analysis is performed using Unstructured, and then the resulting data is used to build an Indaleko-compatible set of definitions for the extracted fields.  It is this last step that is the bulk of the work needed to incorporate it into Indaleko for purposes of completing the prototype.


### Semantic Attributes Model

With activity context, I have used a "semantic attributes" model.  In this model, the semantic data is extracted and presented as a list of semantic elements:

```python
class IndalekoSemanticAttributeDataModel(IndalekoBaseModel):
    '''
    This class defines the UUID data model for Indaleko.

    A "semantic attribute" is a top level concept of something that has a
    semantic meaning within the Indaleko system.  For example, this might be the
    name of the file, or the user that created the file, or notable elements
    from contents of the file.

    The UUID should be unique to the type of semantic attribute, so that records
    with the same UUID can infer the relationship based upon that semantic
    attribute.  For example, if the semantic attribute is the name of the file,
    then all records with the same UUID give the same meaning to that field.  In
    this way, we allow Indaleko to index these values without understanding the
    meaning of them.
    '''
    Identifier : IndalekoUUIDDataModel = Field(...,
                                   title='Identifier',
                                   description='The UUID specific to this type of semantic attribute.',
                                    example='12345678-1234-5678-1234-567812345678')
    Data : Any = Field(...,
                       title='Data',
                       description='The data associated with this semantic attribute.')

    class Config:
        '''Sample configuration data for the data model'''
        json_schema_extra = {
            "example": {
                "Identifier": IndalekoUUIDDataModel.get_json_example(),
                "Data": "foo.lua"
            }
        }
```

[Source](../data_models/semantic_attribute.py)

The idea behind this is that we can construct an index of these elements, which will make it efficient to search for them (or so goes the theory, as it hasn't been formally verified yet.)  Whether this works "in reality" or not, remains to be seen.

Thus, we can define a set of semantic attributes for the metadata 