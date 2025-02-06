#!/usr/bin/env python3

from typing import Dict, Any
from query.query_processing.query_translator.translator_base import TranslatorBase

class AQLQueryConverter(TranslatorBase):
    """
    Translator for converting parsed queries to AQL (ArangoDB Query Language).
    """

    def translate(self, parsed_query: Dict[str, Any], selected_md_attributes: Dict[str, Any], dynamic_activity_providers:dict[str], additional_notes: str, n_truth: int, llm_connector: Any) -> str:
        """
        Translate a parsed query into an AQL query.

        Args:
            parsed_query (Dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service

        Returns:
            str: The translated AQL query
        """
        # Use the LLM to help generate the AQL query
        prompt = self._create_translation_prompt(parsed_query, selected_md_attributes, dynamic_activity_providers, additional_notes, n_truth)
        aql_query = llm_connector.generate_query(prompt)
        aql_statement = aql_query.message.content
        assert self.validate_query(aql_statement), "Generated AQL query is invalid"
        aql_statement = aql_statement[aql_statement.index('FOR'):] # trim preamble
        assert aql_statement.endswith('```'), "Code block not found at the end of the generated AQL query"
        aql_statement = aql_statement[:aql_statement.rindex('```')-1] # trim postamble
        return self.optimize_query(aql_statement)

    def validate_query(self, query: str) -> bool:
        """
        Validate the translated AQL query.

        Args:
            query (str): The translated AQL query

        Returns:
            bool: True if the query is valid, False otherwise
        """
        all_valid = ("FOR" in query and "RETURN" in query) and (".Record" in query or ".SemanticAttributes" in query or ".Timestamp" in query or ".Size" in query or ".URI" in query)
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

    def _create_translation_prompt(self, parsed_query: Dict[str, Any], selected_md_attributes:Dict[str, Any],dynamic_activity_providers: dict[str], additional_notes: str, n_truth_md: int) -> str:
        """
        Create a prompt for the LLM to generate an AQL query.

        Args:
            parsed_query (Dict[str, Any]): The parsed query

        Returns:
            str: The prompt for the LLM
        """
        # Implement prompt creation logic
        system_prompt = """
            You are an assistant that generates ArangoDB queries for a Unified Personal Index (UPI) system. The UPI stores metadata about digital objects 
            (e.g., files, directories) in an ArangoDB database. Given a dictionary called selected_md_attributes, generate the corresponding 
            AQL query that retrieves matching information.
            The schema includes 4 main collections:
             1) {GeoActivity}: the GeoActivity that stores metadata related to the geographical context of activities. It includes the location field.
             2) {MusicActivity} : the MusicActivity that stores music related activity context.
             3) {TempActivity} : the TempActivity that stores temperature related activity context.
             4) Objects: Stores information about posix information
             5) SemanticData: Stores information about the semantic data
             
            You need to search through all five collections (GeoActivity, MusicActivity, TempActivity, Objects, Semantics) to verify if an item satisfies the necessary 
            conditions across these different contexts. First, identify the GeoActivity, MusicActivity, TempActivity, Objects data via its Record.SourceIdentifier.Identifier. 
            If 'geo_location' is specified in selected_md_attributes, search within the {GeoActivity} and compare longitude and latitude with the {geo_coords} . 
            If 'ambient_music' is specified in selected_md_attributes, search within the {MusicActivity}. 
            If 'ecobee_temp' is specified in selected_md_attributes, search within {TempActivity}. The item is uniquely identified by its Identifier, which is stored within the SourceIdentifier field of the Records in each collection. 
            When looking through multiple collections at once, properly quote these long collection names with `` like `{GeoActivity}` and make sure to check that 
            their identifiers are the same e.g., FILTER musicActivity.Record.SourceIdentifier.Identifier == geoActivity.Record.SourceIdentifier.Identifier.
            You don't necessarily have to check the Objects collection to check the Posix metadata, since all activity collections should have a Record attribute. 
            For the {MusicActivity} or the {TempActivity}, you can access the attributes directly by doing: musicActivity.attribute_specified or tempActivity.attribute_specified 
            instead of the SemanticAttributes like for geo_location. Ex.) tempActivity.temperature to access temperature for temperature activity or musicActivity.track_name 
            to access the track name. 

            Important Instructions:
            Use TO_NUMBER when doing any comparisons with numbers or floats like temperature, humidity, track_duration_ms, playback_position_ms, PageNumber, etc.
            In selected_md_attributes['Posix']:
                If "file.name" is specified, include it in the query as object.Record.Attributes.Name.
                If "file.size" is specified, use object.Record.Attributes.st_size.
                If "file.directory" is specified, use the Path in object.Record.Attributes.Path.
                If "location" is specified in selected_md_attributes, include logic to filter paths based on: "google_drive": /file/d/, "dropbox": /s/...?dl=0, 
                "icloud": /iclouddrive/, "local": paths that contain the local_dir_name specified in selected_md_attributes.

            Do not include path filters in the query unless they are explicitly specified in the selected_md_attributes dictionary.
            You don't have to check for whether an identifier doesn't contain data in a specific collection, all identifiers should have an associated data within all
            collections. The timestamp in geo_location, ambient_music and ecobee_temp is the time when the activity context was collected. 
            The timestamp in the Posix is when the file was modified, changed, accessed or created; you don't have to convert the timestamps, just use the posix 
            timestamp as is e.g.)  when given {'Posix': {'timestamps': {'birthtime': {'starttime': 1736064000.0 , 'endtime': 1736064000.0 , 'command': 'equal'}}}, 
            Activity': {geo_location: {'location': 'Victoria', 'command': 'at', 'timestamp': 'birthtime'}} aql query is: FILTER TO_NUMBER(activity.Timestamp) == 1736064000.0 
            To match coordinates, find SemanticAttributes with an Identifier.Label of "Longitude" and ensure the Data matches the given longitude, and similarly for latitude.
            For geo_location, when command is "within", check that the coordinates are within the value specified in "km" relative to the given longitude and latitude coordinates. 
            Given coordinates {"latitude": [-123.40000, -123.113952], "longitude": [49.000,49.2608724], "altitude":0} 
            translated_query = "FOR record IN `ActivityProviderData_da...` LET longitude = FIRST(FOR attr IN object.SemanticAttributes 
            FILTER attr.Identifier.Label == 'Longitude' RETURN attr.Data) LET latitude = FIRST(FOR attr IN object.SemanticAttributes FILTER attr.Identifier.Label == 'Latitude' RETURN attr.Data) 
            FILTER longitude >= -123.400 AND longitude <= -123.113952 FILTER latitude >= 49.000 AND latitude <= 49.2608724 RETURN record"

            If the number of truth attributes is greater than one and in the dictionary and the file name command is 'exactly' with a local directory specified, make sure
            to add % in command as there could be files with duplicate names in the same directory: {'Posix': {'file.name': {'pattern': 'photo', 'command': 'exactly', 
            'extension': ['.jpg']}, 'file.directory': {'location': 'local', 'local_dir_name': 'photo'}}} should give aql: record.Record.Attributes.Name LIKE 'photo%.pdf' 
            OR 'photo(%).pdf'; instead of record.Record.Attributes.Name LIKE 'photo.pdf'. If number of attributes is one, just use record.Record.Attributes.Name LIKE 'photo.pdf.
            The file.name also specifies the extenstion of the file, if none specified assume that any can be used e.g., {'Posix': {'file.name': {'pattern': 'photo', 'command': 'exactly'}}
            use record.Record.Attributes.Name LIKE 'photo%'

            For the semantics, attribute, the attr.Identifier NOT attr.Identifier label for semantics should be the key of what's in Content_# of the dictionary and the attr.Data.Text is the value of that key. 
            Make sure to access the semantic.SemanticAttributes to access the list of semantic attributes and all of these attributes should be in the semantic attributes list.
            Ex.) "Semantic": {"Content_1": ["PageNumber", 20], "Content_2": ["Subtitle", "jogging"], "Content_3":["Subtitle", "EXERCISE"]} is equal to: 
            FOR object IN SemanticData
            LET text1Attr = FIRST(
                FOR attr IN object.SemanticAttributes
                FILTER attr.Identifier == 'PageNumber' AND TO_NUMBER(attr.Data.Text) == 20 (notice how it's attr.Identifier not attr.Indeitifer.Label)
                RETURN 1
            )
            LET type1Attr = FIRST(
                FOR attr IN object.SemanticAttributes
                FILTER attr.Identifier == 'Subtitle' AND attr.Data.Text LIKE 'jogging'
                RETURN 1
            )
            LET textAttr = FIRST(
                FOR attr IN object.SemanticAttributes
                FILTER attr.Identifier == 'Subtitle' AND attr.Data.Text LIKE 'EXERCISE'
                RETURN 1
            )
            FILTER text1Attr != NULL AND type1Attr != NULL AND textAttr != NULL
            RETURN object 
            For queries involving title of a file, you can either search within any collection's record.Record.Attributes.Name or search in object.SemanticAttributes.Identifier.Label where object is from Objects.  
            Ex.) {'Posix': {'file.name': {'pattern': 'presentation', 'command': 'equal'}}, 'Semantic': {}, 'Activity': {'ecobee_temp': {'temperature': {'start': 20.0,
            'end': 20.0, 'command': 'equal'}, 'timestamp': 'birthtime'}}} then to get the file name, we would just search within the tempActivity.Record.Attributes.Name.
            
            When comparing timestamps in the Record table, ensure that timestamps with a prefix of st_ are converted to number (use TO_NUMBER) 
            When matching file names, names should have an extension at the end, so use 'LIKE' command not ==.
            Make sure to return just one of the whole object tempActivity, object, geoActivity, musicActivity; don't use object.any_attribute. Do not return the same 
            object multiple times, just once. Make sure to incorporate all attributes from the given dictionary into the aql statement. Escape any ' with a backslash
            ex.) if we want to find a Name containing "1990's news" -> FILTER object.Record.Attributes.Name LIKE '%1990\'s news%.pdf'. The query should only include 
            the AQL code in a single line, with no additional explanations or comments. You must return one single code block that with '``` at the start and '``` at the end and that contains a FOR and
            a RETURN ... statement. Do not create additional attributes not found in the dictionary. \n""" + \
            "\n Number of truth attributes:" + str(n_truth_md) + "\n Schema:" + str(parsed_query['schema'])

        system_prompt = system_prompt.replace("{GeoActivity}", dynamic_activity_providers["GeoActivity"]).replace("{TempActivity}", dynamic_activity_providers["TempActivity"]).replace("{MusicActivity}", dynamic_activity_providers["MusicActivity"]).replace("{geo_coords}", additional_notes)
        # user_prompt = parsed_query['original_query']
        user_prompt = "Dictionary: " + str(selected_md_attributes)

        return {
            'system' : system_prompt,
            'user' : user_prompt
        }