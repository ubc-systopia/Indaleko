#!/usr/bin/env python3

from typing import Dict, Any
from icecream import ic
import json
from datetime import datetime

class QueryExtractor():
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
        prompt = self.create_extraction_prompt(query)
        query_result = llm_connector.generate_query(prompt)
        query_statement = query_result.message.content
        assert self.validate_query(query_statement), query_statement
        json_string = query_statement.strip('```json').strip()
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
        return '```json' in dictionary

    def create_extraction_prompt(self, query: str) -> Dict:
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
            The dictionary should look like the following: 
            {“Posix”:{“file.name”: {"pattern":str (word contained in file name), "command":["starts", "ends", "contains", “exactly”], 
            "extension":[".pdf", ".doc",".docx", ".txt", ".rtf", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".mov", ".mp4", ".avi", ".mp3", ".wav", ".zip", ".rar"]}, 
            “timestamps”: {“birthtime”:{"starttime": str or list (lists must be in order latest to most recent),
            "endtime": str or list, "command": ["equal", "range"]}, “modified”:{same as birthtime}, “accessed”:{same as birthtime}, “changed”:{same as birthtime}}, 
            “file.size”: {"target_min": int (in bytes so if in GB, multiply by 1e+9 to get bytes, if necessary), "target_max":int, "command": ["equal", "range", "greater_than", "greater_than_equal", "less_than", less_than_equal"]}, 
            “file.directory”: {“location”: str ["google_drive", "dropbox", "icloud", "local"] (local has to be used when local_dir_name is specified), "local_dir_name": str (provide name for local directories only; create a directory name if none provided)}}, 
            “Semantic”: {“Content_1”: {"Languages": "str" (based on language of Text), "PageNumber": int, "Text": str, "Type": ["Title", "Subtitle", "Header", "Footer", "Paragraph", "BulletPoint", "NumberedList", "Caption", "Quote", "Metadata", "UncategorizedText", "SectionHeader", "Footnote", "Abstract", "FigureDescription", "Annotation"], "EmphasizedTextTags": ["bold", "italic", "underline", "strikethrough", "highlight"], "EmphasizedTextContents": str}}, 
            “Activity”: {"timestamp":"birthtime" or "modified" or "changed" or "accessed"}, “geo_location”: {"location": str, "command": ["at", "within"], "km": int (only when command is "within" convert to km if necessary)}}}. Get rid of keys with null values. “Semantic” can have any number of contents. "command", "Type", and "EmphasizedTextTags" should be a single string not a list. Keep key capitalization as is. 
            
            The dictionary structure is {"Posix": {}, "Semantic":{}, "Activity": {}}; just return this dictionary within a ```json, nothing else. Drop any other keys within these 3 dictionaries with null values. 
            File size: When using commands like "less_than," "greater_than," "equal," "greater_than_equal," and "less_than_equal" in "file.size", the target_min and target_max must both be populated and be equal. For command "range" target_min and target_max should be different where target_min < target_max.
            Order any list of file sizes from least file size to most. File sizes in the form of lists can only use the command 'equal'.
            The semantics is for the content of the file specified by Text and with the Type specifying the type of semantics content.
            If there are no time queries listed, there should be no timestamps ex.) what are the pdf files I created?: Dictionary = {"Posix": {"file.name": {"extension": [".txt"], "command": "contains"}}, "Semantic":{}, "Activity": {}}
            Posix timestamps are for when the file is modified, created, accessed or changed. The activity timestamp is when the activity data was collected at that location, so there should be a timestamp for any populated activity context.
            If the timestamp within Activity should be associated with a type of timestamp from the Posix timestamps. Do not populate the 'timestamp' in Activity if there is not geographical context for longitude and latitude.
            For timestamps for 'Posix' use command "equal" when the starttime and endtime are not the same, otherwise, use command "range" if the starttime and endtime are different ex.) query: What are the files I created 5 days ago? The command in the dictionary should be "range" and not "equal": {"Posix": {"timestamps": {"birthtime: {"starttime": "2025-01-02T00:00:00", "endtime": "2025-01-02T23:59:59", "command": "range"}}}}
            Order any list of timestamps from earliest timestamp to most recent. Timestamps in the form of lists can only use the command 'equal'. Any timestamps should be relevant to today's date. For command "range" starttime and endtime should be different where starttime < endtime.
            Timestamps should use 'YYYY-MM-DDTHH:MM:SS' format and must be relative to the time right now: {curr_date}. 
            Constraints: File size is within 1B-10GB inclusive. The start date for the timestamps is bounded by 2000, 10 25 and the current date inclusive. If any type of timestamp from modified, changed and accessed take on boundaries that are not within the birthtime, raise an error. If any of these constraints are broken, return an error message specifiying the specific error.
            """
        # adding the current date since LLM has difficulties getting today's date
        system_prompt = system_prompt.replace("{curr_date}", str(datetime.now()))

        user_prompt = query
        return {
            'system' : system_prompt,
            'user' : user_prompt
        }
