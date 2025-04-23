#!/usr/bin/env python3

import json
from datetime import datetime
from typing import Any


class QueryExtractor:
    """
    Translator for converting parsed queries to populate the self.selected_md_attributes dictionary.
    """

    def __init__(self) -> None:
        """
        Initializes the Query Extractor.
        """

    def extract(self, query: str, llm_connector: Any) -> str:
        """
        Translates a parsed query into a dictionary for creating the metadata dataset.

        Args:
            parsed_query (Dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service
        Returns:
            str: The translated user dictionary
        """
        schema = self._get_schema()
        prompt = self._create_extraction_prompt(query, schema)
        query_result = llm_connector.generate_query(prompt)
        query_statement = query_result.message.content
        assert self.validate_query(query_statement), query_statement
        json_string = query_statement.strip("```json").strip()
        selected_md_attributes = json.loads(json_string)
        return selected_md_attributes

    def validate_query(self, dictionary: str) -> bool:
        """
        Validate the results of the query before passing
        Args:
            dictionary (str): The dictionary to validate
        Returns:
            bool: True if the dictionary is valid, False otherwise
        """
        return "```json" in dictionary and "error" not in dictionary

    def _get_schema(self) -> str:
        """
        Returns a schema of the dictionary that the LLM is supposed to return
        Args: None
        Returns:
            str: The dictionary of the selected metadata
        """
        return """
            {"Posix": {"file.name": {"pattern": "str (word contained in file name)", "command": "starts, ends, contains, exactly",
                "extension": [".pdf", ".doc", ".docx", ".txt", ".rtf", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".mov", ".mp4",
                ".avi", ".mp3", ".wav", ".zip", ".rar"]}, "timestamps": {"birthtime": {"starttime": "str or list (lists must be in order latest to most recent)",
                "endtime": "str or list"}, "modified": "same as birthtime", "accessed": "same as birthtime", "changed": "same as birthtime"},
                "file.size": {"target_min": "int (in bytes so if in GB, multiply by 1e+9 to get bytes, if necessary)", "target_max": "int", "command": "equal, range,
                greater_than, greater_than_equal, less_than, less_than_equal"}, "file.directory": {"location": "str (google_drive, dropbox, icloud, local; must be stated
                local if local_dir_name specified)", "local_dir_name": "str (provide name for local directories only; create a directory name if none provided)"}},
            "Semantic": {"Content_1": {"Languages": "str (based on language of Text)", "PageNumber": "int", "Text": "str", "Type": one of "Title, Subtitle, Header,
                Footer, Paragraph, BulletPoint, NumberedList, Caption, Quote, Metadata, UncategorizedText, SectionHeader, Footnote, Abstract, FigureDescription, Annotation",
                "EmphasizedTextTags": "bold, italic, underline, strikethrough, highlight", "EmphasizedTextContents": "str"}, "Content_2":{...}, ...},
            "Activity": {"geo_location": {"location": "str", "command": "at, within", "km": "int (only when command is 'within' convert to km if necessary)", "timestamp":
                "str (one of 'birthtime', 'modified', 'changed', or 'accessed')"}, "ecobee_temp": {"temperature": {"start": "float within [-50.0, 100.0]", "end": "float within
                [-50.0, 100.0]", "command": "range, equal"}, "humidity": {"start": "float within [0.0, 100.0]", "end": "float within [0.0, 100.0]", "command": "range, equal"},
                "target_temperature": {"start": "float within [-50.0, 100.0]", "end": "float", "command": "range, equal"}, "hvac_mode": "str (heat, cool, auto, off)",
                "hvac_state": "str (heating, cooling, fan, idle)", "timestamp": "str one of ['birthtime', 'modified', 'changed', 'accessed']"},
                "ambient_music": {"track_name": "str", “album_name”:str, "artist_name": "str", "playback_position_ms": "int (ms [0, track_duration_ms])",
                "track_duration_ms": "int (in milliseconds bound by [10000, 300000])", “is_currently_playing”:bool, "source": "str (one of 'spotify', 'youtube music',
                'apple music'; if 'spotify' can specify device_type)", "device_type": "str (device the music was streamed)one of
                (Computer|Smartphone|Speaker|TV|Game_Console|Automobile|Unknown)", "timestamp": "str one of ['birthtime',
                'modified', 'changed', 'accessed']"}}}
            """

    def _create_extraction_prompt(self, query: str, selected_md_schema: dict) -> dict:
        """
        Create a prompt for the LLM to generate an  query.

        Args:
            query: str the query
        Returns:
            str: The prompt for the LLM
        """
        system_prompt = """
            You are an assistant that generates a dictionary of attributes requested by the user for a Unified Personal Index (UPI) system,
            which stores metadata about digital objects. Given a user query, extract information for record, semantics, and activity context.
            The dictionary should look like the following: {selected_md_schema}

            File name: The 'command' can only exist in the presence of the 'pattern' key, otherwise, ignore. The 'extension' is separate from the
            command and pattern.

            File size: When using commands like "less_than," "greater_than," "equal," "greater_than_equal," and "less_than_equal" in "file.size", the
            target_min and target_max must both be populated and be equal. For command "range", target_min and target_max should be different where
            target_min < target_max. File sizes can be 1B-10GB inclusive. Order any list of file sizes from least file size to most. File sizes in the
            form of lists can only use the command 'equal'.

            The 'semantics' is for the content of the file specified by Text and with the Type specifying the type of semantics content. There can be
            many semantic attributes starting with Content_1, onwards. The 'ecobee_temp' is only for queries that implicitly or explicitly imply for
            settings taken at the user's home. If the user specifically implies a location elsewhere, then do not create a query related to this. The
            'ambient_music' is for queries related to music listening activities related to the file.

            Posix timestamps are for when the file is modified, created, accessed, or changed. For timestamps for 'Posix' the starttime can only be the
            same as the endtime or earlier than the endtime. Otherwise, raise error.
            If there are no specific time queries listed, timestamps shouldn't be populated. For example, query: what are the pdf files I
            created/modified/changed/accessed?: there should be no 'created' in the Posix dictionary), should return
            {"Posix": {"file.name": {"extension": [".txt"], "command": "contains"}}, "Semantic":{}, "Activity": {}}.

            starttime and endtime in Posix timestamps should use 'YYYY-MM-DDTHH:MM:SS' format and must be relative to the time right now: {curr_date}.
            There starttime and endtime are between October 25, 2000 and {curr_date} inclusive. So if the time is October 25, 2000 or {curr_date}
            exactly, it's fine. If any type of timestamp from modified, changed, and accessed specify a starttime / endttime pair not within the birthtime, raise an error.

            If there is a query that uses keywords for location e.g., home or work, then replace that keyword with a reasonable location within BC
            e.g., file I created at home -> 'Activity': {'geo_location': {'location': 'Vancouver, BC', 'command': 'at', 'timestamp': 'birthtime'}.
            where what's specified in the location can be an actual location or a random one within BC. The timestamp within the geo_location is when the
            activity data was collected at that location, so there should be a timestamp for any geo_location populated. This goes for the ecobee_temp and
            ambient_music. For example, what is the photo I took yesterday when I was in Vancouver?:
            "Activity": {"geo_location": {"location": "Vancouver", "command": "at", "timestamp": "birthtime"}}.

            The dictionary structure is {"Posix": {}, "Semantic":{}, "Activity": {}}; just return this dictionary within a JSON (containing '```json'), nothing else. Drop any other keys
            within these 3 dictionaries with null or empty values. The given query should not be blank and should consist of at least one attributes specified above.
            If any of the above constraints are broken, return an error message as a string "error:..." specifying the specific error.
            """
        # adding the current date since LLM has difficulties getting today's date
        system_prompt = system_prompt.replace(
            "{curr_date}", str(datetime.now()),
        ).replace("{selected_md_schema}", selected_md_schema)

        user_prompt = query
        return {"system": system_prompt, "user": user_prompt}
