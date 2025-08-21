#!/usr/bin/env python3
"""Translate Query to Metadata Dictionary."""
import json
import re

from datetime import UTC, datetime
from textwrap import dedent

from icecream import ic

from data_generator.scripts.metadata.semantic_metadata import SemanticMetadata
from data_models.named_entity import NamedEntityCollection
from query.utils.llm_connector.llm_base import LLMBase


# ruff: noqa: S101


class QueryExtractor:
    """Translator for converting parsed queries."""

    def __init__(self) -> None:
        """Initializes the Query Extractor."""

    def extract(
        self,
        query: str,
        named_entities: NamedEntityCollection,
        llm_connector: LLMBase,
    ) -> str:
        """
        Translates a parsed query into a dictionary for creating the metadata dataset.

        Args:
            query (str): The query
            named_entities (NamedEntityCollection): The named entities
            llm_connector (Any): Connector to the LLM service
        Returns:
            str: The translated user dictionary
        """
        schema = self._get_schema()
        prompt = self._create_extraction_prompt(query, schema, named_entities)
        query_result = self.generate_query_str(prompt, llm_connector)
        assert self.validate_query(query_result), query_result
        json_string = re.sub(r"```json|```", "", query_result).strip()
        return json.loads(json_string)

    def generate_query_str(
        self,
        prompt: str,
        llm_connector: LLMBase,
        temperature: int = 0,
    ) -> str:
        """
        Generate a query string from the LLM.

        Args:
            prompt (str): The prompt to generate the query from
            llm_connector (LLMBase): The LLM connector
            temperature (int): The temperature for the LLM
        Returns:
            str: The generated query string
        """
        completion = llm_connector.client.beta.chat.completions.parse(
            model=llm_connector.model,
            messages=[
                {
                    "role": "system",
                    "content": prompt["system"],
                },
                {
                    "role": "user",
                    "content": prompt["user"],
                },
            ],
            temperature=temperature,
        )
        ic("Received response from OpenAI")
        return completion.choices[0].message.content

    def validate_query(self, dictionary: str) -> bool:
        """
        Validate the results of the query before passing.

        Args:
            dictionary (str): The dictionary to validate
        Returns:
            bool: True if the dictionary is valid, False otherwise.
        """
        return "```json" in dictionary and "error" not in dictionary

    def _get_schema(self) -> str:
        """
        Returns a schema of the dictionary that the LLM is supposed to return.

        Args: None
        Returns:
            str: The dictionary of the selected metadata.
        """
        dictionary = dedent(
            """{
            "Posix": {
                "file.name": {
                    "pattern": str (word contained in file name),
                    "command": one of ["starts", "ends", "contains", "exactly"]
                        (must be populated if pattern exists),
                    "extension": [
                        ".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".csv",
                        ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".mov",
                        ".mp4", ".avi", ".mp3", ".wav", ".zip", ".rar"
                    ]
                },
                "timestamps": {
                    "birthtime": {"starttime": str,"endtime": str},
                    "modified": {"starttime": str,"endtime": str},
                    "accessed": {"starttime": str,"endtime": str},
                    "changed": {"starttime": str,"endtime": str}
                },
                "file.size": {
                    "target_min": int (in bytes so if in GB, multiply by 1e+9 to get bytes,
                        if necessary),
                    "target_max": int,
                    "command": one of [
                        "equal", "range", "greater_than", "greater_than_equal", "less_than",
                        "less_than_equal"
                    ]
                },
                "file.directory": {
                    "location": str ("google_drive", "dropbox", "icloud", "local"
                                    must be stated local if local_dir_name specified),
                    "local_dir_name": str (provide name for local directories only;
                                            create a directory name if none provided)
                }
            },
            "Semantic": {
                "Content_1": ["label": "data"],
                "Content_2": ["label": "data"],
                ...
            },
            "Activity": {
                "geo_location": {
                    "location": "str" or {longitude: int, latitude: int},
                    "command": "at, within",
                    "km": "int (only when command is 'within' convert to km if necessary)",
                    "timestamp": "str (one of 'birthtime', 'modified', 'changed', or 'accessed')"
                },
                "ecobee_temp": {
                    "temperature": {
                        "start": "float within [-50.0, 100.0]",
                        "end": "float within [-50.0, 100.0]",
                        "command": "range, equal"
                    },
                    "humidity": {
                        "start": "float within [0.0, 100.0]",
                        "end": "float within [0.0, 100.0]",
                        "command": "range, equal"
                    },
                    "target_temperature": {
                        "start": "float within [-50.0, 100.0]",
                        "end": "float",
                        "command": "range, equal"
                    },
                    "hvac_mode": "str (heat, cool, auto, off)",
                    "hvac_state": "str (heating, cooling, fan, idle)",
                    "timestamp": "str one of ['birthtime', 'modified', 'changed', 'accessed']"
                },
                "ambient_music": {
                    "track_name": str,
                    "album_name": str,
                    "artist_name": str,
                    "playback_position_ms": int (ms [0, track_duration_ms]),
                    "track_duration_ms": int (in milliseconds bound by [10000, 300000]),
                    "is_playing": bool,
                    "source": str (one of 'spotify', 'youtube music', 'apple music';
                                    'spotify' can specify device_type),
                    "device_type": str only populated when source is 'spotify'
                        (device the music was streamed)
                    one of ("Computer"|"Smartphone"|"Speaker"|"TV"|"Game_Console"|
                    "Automobile"|"Unknown"),
                    "timestamp": str one of ['birthtime', 'modified', 'changed', 'accessed']
                }
            }
        }
        """,
        )
        return dictionary.replace("{TEXT_TAGS}", str(SemanticMetadata.AVAIL_TEXT_TAGS))

    def _create_extraction_prompt(
        self,
        query: str,
        selected_md_schema: str,
        named_entities: NamedEntityCollection,
    ) -> dict:
        """
        Create a prompt for the LLM to generate an  query.

        Args:
            query: str the query
            selected_md_schema: str the metadata schema
            named_entities: NamedEntityCollection the named entities
        Returns:
            str: The prompt for the LLM
        """
        system_prompt = """
        You are an assistant that generates a dictionary of attributes requested
        by the user for a Unified Personal Index (UPI) system, which stores
        metadata about digital objects. Given a user query, extract information
        for record, semantics, and activity context. The dictionary should look
        like the following: {selected_md_schema}

        File name: If file name is not specifically stated, assume it's a title
        in the semantics. The 'command' can only exist in the presence of the
        'pattern' key, otherwise, ignore. The 'extension' is separate from the
        command and pattern, it specifies what type the file created is e.g.,
        the presentation with an image of a rabbit, the presentation is the file
        type not the image another ex.) find me the images I took, the type is
        images. Remove spaces from file name patterns and use '_' instead or
        camel casing.

        File size: When using commands like "less_than," "greater_than,"
        "equal," "greater_than_equal," and "less_than_equal" in "file.size",
        the target_min and target_max must both be populated and be equal. For
        command "range", target_min and target_max should be different where
        target_min < target_max. File sizes can be 1B-10GB inclusive. Order
        any list of file sizes from least file size to most. File sizes in the
        form of lists can only use the command 'equal'.

        The 'semantics' is for the semantic content of the file represented in a
        2 element list with ['label', data]. 'label' is any one of {AVAIL_TEXT_TAGS}
        Make sure that the syntax is exactly the same as in the list above.
        The data is the label of that particular semantic attribute. There can be many
        semantic attributes starting with Content_1, onwards. There can be multiple
        duplicate labels. For attributes like "CodeSnippet" or "Formula" just make a code
        or math formula/equation based on the arbitrary code or equation given by the user.
        For any {BUTTON_TAGS}, the value should only be True. For any {IMAGE_TAGS}, if the
        extension of the image, and the name is specified return the full name and extension
        e.g., the file with a png image of a dog --> "Content_1": ["Image", "dog.png"]
        ex.) This is how you should convert a paragraph that has the word "hi" and
        title 'bye' --> {"Semantic": {"Content_1": ["Paragraph", "hi"],
        "Content_2": ["Title", "bye"]}},

        The 'ecobee_temp' is only for queries that implicitly or explicitly
        imply for settings taken at the user's home. If the user specifically
        implies a location elsewhere, then do not create a query related to this.
        The 'ambient_music' is for queries related to music listening activities
        related to the file. device_type can only exist when "source" is "spotify"
        so add "source": "spotify" when device_type is specified, or don't specify
        device_type when source is not "spotify" so "what is the file I created
        when listening to youtube music on my phone? => don't include device_type
        so "ambient_music": {"source": "youtube music", "timestamp": "birthtime"}.

        Posix timestamps are for when the file is modified, created, accessed,
        or changed. For timestamps for 'Posix' the starttime can only be the
        same as the endtime or earlier than the endtime. Otherwise, raise error.
        If there are no specific time queries listed, timestamps shouldn't be
        populated. For example, query: what are the pdf files I created/modified/
        changed/accessed?: there should be no 'created' in the Posix dictionary),
        should return {"Posix": {"file.name": {"extension": [".txt"]}},
        "Semantic":{}, "Activity": {}}.

        starttime and endtime in Posix timestamps should use 'YYYY-MM-DDTHH:MM:SS'
        format and must be relative to the time right now: {curr_date}. There
        starttime and endtime are between October 25, 2000 and {curr_date} inclusive.
        So if the time is October 25, 2000 or {curr_date} exactly, it's fine.
        If any type of timestamp from modified, changed, and accessed specify a
        starttime / endtime pair not within the birthtime, raise an error.

        The 'geo_location' is for any geographical location key word. Convert
        any of these keyword to format "City, Country or Province/State"
        and put as a value of geographical activity's location key.
        If there is a query that uses keywords for location e.g., home, work,
        someone's place, then replace that keyword with a reasonable location
        within BC if not in the {named_entities} e.g., file I created at home ->
        'Activity': {'geo_location': {'location': 'Vancouver, BC', 'command':
        'at', 'timestamp': 'birthtime'}. Else, if the location is specified in
        gis_location, return the latitude and longitude within gis_location (e.g.,
        gis_location=BaseLocationDataModel(source='defined', timestamp=datetime.now(timezone.utc),
        latitude=48.8566, longitude=2.3522)) as "geo_location": {"location":
        {"latitude": 48.8566, "longitude": 2.3522}, command: "at", "timestamp": "birthtime"},
        where what's specified in the location can be an actual location or a random
        one within BC. The timestamp within the geo_location is when the activity data
        was collected at that location, so there should be a timestamp for any geo_location
        populated. This goes for the ecobee_temp and ambient_music. For example, what is
        the photo I took yesterday when I was in Vancouver?: "Activity": {"geo_location":
        {"location": "Vancouver, BC", "command": "at", "timestamp": "birthtime"}}.

        Return this dictionary as a JSON object inside `LLMTranslateQueryResponse.message.content`,
        using the format:
        ```json
        {"Posix": {}, "Semantic": {}, "Activity": {}}
        within these 3 dictionaries. The given query should not be blank and should consist of at
        least one attribute specified above. If any of the above constraints are broken, return an
        error message as a string "error:..." specifying the specific error.
        """

        # adding the current date since LLM has difficulties getting today's date
        system_prompt = (
            system_prompt.replace("{curr_date}", str(datetime.now(UTC)))
            .replace("{selected_md_schema}", selected_md_schema)
            .replace(
                "{BUTTON_TAGS}",
                str(SemanticMetadata.BUTTON_TAGS),
            )
            .replace("{IMAGE_TAGS}", str(SemanticMetadata.IMAGE_TAGS))
            .replace(
                "{AVAIL_TEXT_TAGS}",
                str(SemanticMetadata.AVAIL_TEXT_TAGS),
            )
            .replace("{named_entities}", str(named_entities))
        )

        user_prompt = query
        return {"system": system_prompt, "user": user_prompt}
