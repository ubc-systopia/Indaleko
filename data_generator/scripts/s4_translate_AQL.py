#!/usr/bin/env python3

from typing import Dict, Any
from query.query_processing.query_translator.translator_base import TranslatorBase
from data_generator.scripts.metadata.semantic_metadata import SemanticMetadata
from icecream import ic
from db.db_collection_metadata import IndalekoDBCollectionsMetadata


class AQLQueryConverter(TranslatorBase):
    """
    Translator for converting parsed queries to AQL (ArangoDB Query Language).
    """
    STATIC_COLLECTIONS = ["Objects", "Semantic"]
    def __init__(self, db_schema: dict, collections_metadata: IndalekoDBCollectionsMetadata = None):
        """
        Initialize the AQL translator.

        Args:
            collections_metadata: Metadata for the collections in the database.
        """
        self.db_schema = db_schema
        self.db_collections_metadata = collections_metadata
        self.db_config = self.db_collections_metadata.db_config
        self.dynamic_db_schema = self.db_collections_metadata.get_all_collections_metadata()

    def translate(self, selected_md_attributes: Dict[str, Any], collections:dict[str], 
    geo_coordinates: str, n_truth: int, llm_connector: Any) -> str:
        """
        Translate a parsed query into an AQL query.

        Args:
            parsed_query (Dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service

        Returns:
            str: The translated AQL query
        """
        dynamic_prompt = self._create_translation(selected_md_attributes, collections, geo_coordinates, n_truth)
        ic(self.dynamic_db_schema)
        aql_query = llm_connector.generate_query(dynamic_prompt)
        aql_statement = aql_query.aql_query
        assert self.validate_query(aql_statement), "Generated AQL query is invalid"
        aql_statement = aql_statement[aql_statement.index('FOR'):] # trim preamble

        return aql_statement
        
    def validate_query(self, query: str) -> bool:
        """
        Validate the translated AQL query.

        Args:
            query (str): The translated AQL query

        Returns:
            bool: True if the query is valid, False otherwise
        """
        all_valid = (
            "FOR" in query and "RETURN" in query and 
            any(keyword in query for keyword in [
                ".Record", ".SemanticAttributes", ".Timestamp", ".Data", ".URI"
            ])
        )  
        
        return all_valid

    def optimize_query(self, query: str) -> str:
        """
        Optimize the translated AQL query.

        Args:
            query (str): The translated AQL query

        Returns:
            str: The optimized AQL query
        """
        # Implement query optimization logic
        # This is a placeholder implementation
        return query

    def _create_translation(self, selected_md_attributes:Dict[str, Any], collections: Dict[str, str], 
    geo_coordinates: str, n_truth: int) -> str:
        """
        Create a prompt for the LLM to generate an AQL query.

        Args:
            selected_md_attributes (Dict[str, Any]): The dictionary created for dataset generation,
            collections (Dict[str, str]): the collections that are used to create the metadata
            geo_coordinates (str): geo coordinate specifying longitude/latitude of truth metadata (if any)
            n_truth (int): number of truth metadata 

        Returns:
            str: The prompt for the LLM
        """
        system_prompt = """
        You are an assistant that generates ArangoDB queries for a Unified Personal Index 
        (UPI) system. The UPI stores metadata about digital objects (e.g., files, directories) 
        in an ArangoDB database. Given a dictionary called selected_md_attributes, generate the 
        corresponding AQL query that retrieves matching information.

        The schema includes 4 main collections:
        1) {GeoActivity}: Stores metadata related to the geographical context of activities, 
        including the location field.
        2) {MusicActivity}: Stores music-related activity context.
        3) {TempActivity}: Stores temperature-related activity context.
        4) Objects: Stores Posix metadata ("Posix" of the dictionary). Do not search for 
        semantics within Objects.
        5) SemanticData: Stores information about the semantic data of the file ("Semantic" 
        of the dictionary).

        The collections you should search for are listed in {dynamic_activity_providers}. 
        First, identify the collection (Semantic, GeoActivity, MusicActivity, TempActivity, 
        Objects) via its Record.SourceIdentifier.Identifier. Properly quote the ActivityDataProvider 
        collection names with `` (e.g., `{GeoActivity}`) and ensure that their identifiers match. 
        For example:
        FILTER musicActivity.Record.SourceIdentifier.Identifier == semantic.Record.SourceIdentifier.Identifier
        FILTER semantic.Record.SourceIdentifier.Identifier == Objects.Record.SourceIdentifier.Identifier

        If 'geo_location' is specified in selected_md_attributes, search within the 
        {GeoActivity} collection that has the corresponding SourceIdentifier.Identifier. 
        Ignore collections in the list that don’t have the identifier, and compare longitude 
        and latitude with the {geo_coords}. 

        If 'ambient_music' is specified in selected_md_attributes, search within the 
        {MusicActivity} collection that has the corresponding SourceIdentifier.Identifier. 

        If 'ecobee_temp' is specified in selected_md_attributes, search within the 
        {TempActivity} collection that has the corresponding SourceIdentifier.Identifier. 
        The item is uniquely identified by its Identifier, stored in the SourceIdentifier 
        field of Records in each collection. 

        You don't necessarily have to check the Objects collection for Posix metadata, as all 
        activity collections should have a Record attribute. For {MusicActivity} or {TempActivity}, 
        access the attributes directly (e.g., musicActivity.track_name or tempActivity.temperature) 
        instead of using the SemanticAttributes, as for geo_location.

        Important Instructions:
        - Use TO_NUMBER when comparing numbers or floats (e.g., timestamp, temperature, humidity, 
        track_duration_ms, playback_position_ms, PageNumber, etc.)
        - In selected_md_attributes['Posix']:
        - If "file.name" is specified, include it in the query as object.Record.Attributes.Name.
        - If "file.size" is specified, use object.Record.Attributes.st_size.
        - If "file.directory" is specified, use the Path in object.Record.Attributes.Path.
        - If "location" is specified, filter paths based on: "google_drive": /file/d/, 
            "dropbox": /s/...?dl=0, "icloud": /iclouddrive/, "local": paths containing 
            the local_dir_name specified.

        Do not include path filters in the query unless explicitly specified in selected_md_attributes.

        When comparing timestamps, ensure that timestamps with a prefix of "st_" are converted 
        to numbers (use TO_NUMBER).

        The timestamp in Objects correspond to the time  within Record.Attributes.st_birthtime, st_mtime, etc.

        But for timestamps in geo_location, ambient_music, and ecobee_temp, Semantics corresponds to the time 
        the activity context was collected. The timestamp in Posix corresponds to when the file 
        was modified, changed, accessed, or created. You don't have to convert timestamps; just 
        use the Posix timestamp as-is. For example:
        - {'Posix': {'timestamps': {'birthtime': {'starttime': 1736064000.0, 
            'endtime': 1736064000.0, 'command': 'equal'}}}, 
        - Activity': {geo_location: {'location': 'Victoria', 'command': 'at', 
        'timestamp': 'birthtime'}}} should produce the query:
        - FILTER TO_NUMBER(object.Record.Attributes.st_birthtime) == 1736064000.0 AND FILTER TO_NUMBER(activity.Timestamp) == 1736064000.0

        To match coordinates, find SemanticAttributes with an Identifier.Label of "Longitude" 
        and ensure the Data matches the given longitude, and similarly for latitude.

        For geo_location with the "within" command, check if the coordinates are within 
        the specified distance in "km" relative to the given longitude and latitude. 
        Example query:
        - FOR record IN `ActivityProviderData_...` 
        LET longitude = FIRST(FOR attr IN object.SemanticAttributes \n
        FILTER attr.Identifier.Label == 'Longitude' RETURN attr.Data) \n
        LET latitude = FIRST(FOR attr IN object.SemanticAttributes \n
        FILTER attr.Identifier.Label == 'Latitude' RETURN attr.Data) \n
        FILTER longitude >= -123.400 AND longitude <= -123.113952 \n
        FILTER latitude >= 49.000 AND latitude <= 49.2608724 \n
        RETURN record

        Always check the extension if specified in file.name.
        If there are multiple truth attributes in the dictionary and the file name command 
        is 'exactly' with a local directory specified, make sure to add `%` to the command 
        for files with duplicate names in the same directory:
        - {'Posix': {'file.name': {'pattern': 'photo', 'command': 'exactly', 
        'extension': ['.jpg']}, 'file.directory': {'location': 'local', 
        'local_dir_name': 'vacation'}}} should produce:
        - record.Record.Attributes.Name LIKE 'photo%.pdf' OR 'photo(%).pdf'

        If the number of attributes is one, use:
        - record.Record.Attributes.Name LIKE 'photo.pdf'

        The file.name specifies the file extension. If none is specified, assume any 
        extension is acceptable. For example:
        - {'Posix': {'file.name': {'pattern': 'photo', 'command': 'exactly'}}}
        should produce:
        - record.Record.Attributes.Name LIKE 'photo%'

        For semantic attributes, access the attributes in object.SemanticAttributes, 
        where attr.Identifier is the key of the dictionary (e.g., "Content_1", "Content_2") 
        and attr.Data is the value.

        For {BUTTON_TAGS}, the associated data can only be true (as a boolean value). 
        Use LIKE '%data%' for semantic attributes such as {LONG_TAG}, {LIST_TAGS}, 
        "CodeSnippet", "Formula", "EmailAddress", "Link", and for {IMAGE_TAGS}, use LIKE 
        'data%' (check both capitalized and uncapitalized). 

        For PageBreaks, the value should always be "--- PAGE BREAK ---".

        For example:
        - "Semantic": {"Content_1": ["PageNumber", 20], "Content_2": ["Subtitle", "jogging"]}
        should produce:
        - FOR object IN SemanticData \n
            LET text1Attr = FIRST(FOR attr IN object.SemanticAttributes \n
            FILTER attr.Identifier == 'PageNumber' AND TO_NUMBER(attr.Data) == 20 
            RETURN 1) \n
            LET type2Attr = FIRST(FOR attr IN object.SemanticAttributes \n
            FILTER attr.Identifier == 'Paragraph' AND (attr.Data LIKE '%jogging%' OR \n
            attr.Data LIKE '%Jogging%') RETURN 1) \n
            FILTER text1Attr != NULL AND type2Attr != NULL \n
            RETURN object

        Return only one of the whole object (tempActivity, object, geoActivity, musicActivity). 
        Do not return the same object multiple times.

        Incorporate all attributes from the given dictionary into the AQL statement. Escape any 
        single quotes with a backslash (e.g., if searching for a name containing "1990's news", 
        use: FILTER object.Record.Attributes.Name LIKE '%1990\'s news%.pdf').

        The query should include only the AQL code in a single line, with no additional explanations 
        or comments. Return the code in a single block wrapped with "json```" at the start and 
        '```' at the end and add \n for better readability where appropriate within the code.
        """ +  "\n Number of truth attributes: " + str(n_truth) \
            + "\n Schema: " + str(self.dynamic_db_schema)

        system_prompt = system_prompt.replace("{geo_coords}", geo_coordinates).\
            replace("{BUTTON_TAGS}", str(SemanticMetadata.BUTTON_TAGS)).\
                replace("{LONG_TAG}", str(SemanticMetadata.LONG_TAGS)).\
                    replace("{LIST_TAGS}", str(SemanticMetadata.LIST_TAGS)).\
                        replace("{IMAGE_TAGS}", str(SemanticMetadata.IMAGE_TAGS)).\
                            replace("{dynamic_activity_providers}", str(collections))

        user_prompt = "Dictionary: " + str(selected_md_attributes)

        return {
            'system' : system_prompt,
            'user' : user_prompt
        }

    # UNUSED: for use with static schema
    def _create_translation_prompt_statically(self, selected_md_attributes:Dict[str, Any], collections: Dict[str, str], 
    geo_coordinates: str, n_truth: int) -> str:
        """
        Create a prompt for the LLM to generate an AQL query.

        Args:
            selected_md_attributes (Dict[str, Any]): The dictionary created for dataset generation,
            collections (Dict[str]): the collections that are used to create the metadata
            geo_coordinates (str): geo coordinate specifying longitude/latitude of truth metadata (if any)
            n_truth (int): number of truth metadata 

        Returns:
            str: The prompt for the LLM
        """
        # Implement prompt creation logic
        system_prompt = """
        You are an assistant that generates ArangoDB queries for a Unified Personal Index 
        (UPI) system. The UPI stores metadata about digital objects (e.g., files, directories) 
        in an ArangoDB database. Given a dictionary called selected_md_attributes, generate the 
        corresponding AQL query that retrieves matching information.

        The schema includes 4 main collections:
        1) {GeoActivity}: Stores metadata related to the geographical context of activities, 
        including the location field.
        2) {MusicActivity}: Stores music-related activity context.
        3) {TempActivity}: Stores temperature-related activity context.
        4) Objects: Stores Posix metadata ("Posix" of the dictionary). Do not search for 
        semantics within Objects.
        5) SemanticData: Stores information about the semantic data of the file ("Semantic" 
        of the dictionary).

        The collections you should search for are listed in {dynamic_activity_providers}.
        You should only use the collections that are needed for the AQL search. 
        FIRST start off by identifying the collection for the current object via its 
        Record.SourceIdentifier.Identifier. Properly quote the ActivityDataProvider 
        collection names with `` (e.g., `{GeoActivity}`) and ensure that their identifiers match. 
        For example:
        - FILTER musicActivity.Record.SourceIdentifier.Identifier == 
        semantic.Record.SourceIdentifier.Identifier
        - FILTER semantic.Record.SourceIdentifier.Identifier == 
        Objects.Record.SourceIdentifier.Identifier

        If 'geo_location' is specified in selected_md_attributes, search within the 
        {GeoActivity} collection that has the corresponding SourceIdentifier.Identifier. 
        Ignore collections in the list that don’t have the identifier, and compare longitude 
        and latitude with the {geo_coords}. 

        If 'ambient_music' is specified in selected_md_attributes, search within the 
        {MusicActivity} collection that has the corresponding SourceIdentifier.Identifier. 

        If 'ecobee_temp' is specified in selected_md_attributes, search within the 
        {TempActivity} collection that has the corresponding SourceIdentifier.Identifier. 
        The item is uniquely identified by its Identifier, stored in the SourceIdentifier 
        field of Records in each collection. 

        You don't necessarily have to check the Objects collection for Posix metadata, as all 
        activity collections should have a Record attribute. For {MusicActivity} or {TempActivity}, 
        access the attributes directly (e.g., musicActivity.track_name or tempActivity.temperature) 
        instead of using the SemanticAttributes, as for geo_location.

        Important Instructions:
        - Use TO_NUMBER when comparing numbers or floats (e.g., temperature, humidity, 
        track_duration_ms, playback_position_ms, PageNumber, etc.)
        - In selected_md_attributes['Posix']:
        - If "file.name" is specified, include it in the query as object.Record.Attributes.Name.
        - If "file.size" is specified, use object.Record.Attributes.st_size.
        - If "file.directory" is specified, use the Path in object.Record.Attributes.Path.
        - If "location" is specified, filter paths based on: "google_drive": /file/d/, 
            "dropbox": /s/...?dl=0, "icloud": /iclouddrive/, "local": paths containing 
            the local_dir_name specified (use LIKE "/{path}/")

        Do not include path filters in the query unless explicitly specified in selected_md_attributes. 

        The timestamp in geo_location, ambient_music, and ecobee_temp corresponds to the time 
        the activity context was collected. The timestamp in Posix corresponds to when the file 
        was modified, changed, accessed, or created. You don't have to convert timestamps; just 
        use the Posix timestamp as-is. For example:
        - {'Posix': {'timestamps': {'birthtime': {'starttime': 1736064000.0, 
            'endtime': 1736064000.0, 'command': 'equal'}}}, 
        - Activity': {geo_location: {'location': 'Victoria', 'command': 'at', 
        'timestamp': 'birthtime'}}} should produce the query:
        - FILTER TO_NUMBER(activity.Timestamp) == 1736064000.0

        To match coordinates, find SemanticAttributes with an Identifier.Label of "Longitude" 
        and ensure the Data matches the given longitude, and similarly for latitude.

        For geo_location with the "within" command, check if the coordinates are within 
        the specified distance in "km" relative to the given longitude and latitude. Example query:
        - FOR record IN `ActivityProviderData_da...` 
        LET longitude = FIRST(FOR attr IN object.SemanticAttributes 
        FILTER attr.Identifier.Label == 'Longitude' RETURN attr.Data) 
        LET latitude = FIRST(FOR attr IN object.SemanticAttributes 
        FILTER attr.Identifier.Label == 'Latitude' RETURN attr.Data) 
        FILTER longitude >= -123.400 AND longitude <= -123.113952 
        FILTER latitude >= 49.000 AND latitude <= 49.2608724 
        RETURN record

        Always check the extension if specified in file.name.

        If there are multiple truth attributes in the dictionary and the file name command 
        is 'exactly' with a local directory specified, make sure to add `%` to the command 
        for files with duplicate names in the same directory:
        - {'Posix': {'file.name': {'pattern': 'photo', 'command': 'exactly', 
        'extension': ['.jpg']}, 'file.directory': {'location': 'local', 
        'local_dir_name': 'vacation'}}} should produce:
        - record.Record.Attributes.Name LIKE 'photo%.pdf' OR 'photo(%).pdf'

        If the number of attributes is one, use:
        - record.Record.Attributes.Name LIKE 'photo.pdf'

        The file.name specifies the file extension. If none is specified, assume any 
        extension is acceptable. For example:
        - {'Posix': {'file.name': {'pattern': 'photo', 'command': 'exactly'}}}
        should produce:
        - record.Record.Attributes.Name LIKE 'photo%'

        For semantic attributes, access the attributes in object.SemanticAttributes, 
        where attr.Identifier is the key of the dictionary (e.g., "Content_1", "Content_2") 
        and attr.Data is the value.

        For {BUTTON_TAGS}, the associated data can only be true (as a boolean value). 
        Use LIKE '%data%' for semantic attributes such as {LONG_TAG}, {LIST_TAGS}, 
        "CodeSnippet", "Formula", "EmailAddress", "Link", and for {IMAGE_TAGS}, use LIKE 
        'data%' (check both capitalized and uncapitalized). 

        For PageBreaks, the value should always be "--- PAGE BREAK ---".

        For example:
        - "Semantic": {"Content_1": ["PageNumber", 20], "Content_2": ["Subtitle", "jogging"]}
        should produce:
        - FOR object IN SemanticData
            LET text1Attr = FIRST(FOR attr IN object.SemanticAttributes 
            FILTER attr.Identifier == 'PageNumber' AND TO_NUMBER(attr.Data) == 20 
            RETURN 1)
            LET type2Attr = FIRST(FOR attr IN object.SemanticAttributes 
            FILTER attr.Identifier == 'Paragraph' AND (attr.Data LIKE '%jogging%' OR 
            attr.Data LIKE '%Jogging%') RETURN 1)
            FILTER text1Attr != NULL AND type2Attr != NULL
            RETURN object

        When comparing timestamps, ensure that timestamps with a prefix of "st_" are converted 
        to numbers (use TO_NUMBER). When matching file names, use the 'LIKE' command instead of '=='.

        Return only one of the whole object (tempActivity, object, geoActivity, musicActivity). 
        Do not return the same object multiple times.

        Incorporate all attributes from the given dictionary into the AQL statement. Escape any 
        single quotes with a backslash (e.g., if searching for a name containing "1990's news", 
        use: FILTER object.Record.Attributes.Name LIKE '%1990\'s news%.pdf').

        The query should include only the AQL code in a single line, with no additional explanations 
        or comments. Return the code in a single block wrapped with "json```" at the start and 
        '```' at the end and add \n for newlines.
        """ +  "\n Number of truth attributes: " + str(n_truth) \
            + "\n Schema: " + str(self.db_schema)

        system_prompt = system_prompt.replace("{geo_coords}", geo_coordinates).\
            replace("{BUTTON_TAGS}", str(SemanticMetadata.BUTTON_TAGS)).\
                replace("{LONG_TAG}", str(SemanticMetadata.LONG_TAGS)).\
                    replace("{LIST_TAGS}", str(SemanticMetadata.LIST_TAGS)).\
                        replace("{IMAGE_TAGS}", str(SemanticMetadata.IMAGE_TAGS)).\
                            replace("{dynamic_activity_providers}", str(collections))

        user_prompt = "Dictionary: " + str(selected_md_attributes)

        return {
            'system' : system_prompt,
            'user' : user_prompt
        }
