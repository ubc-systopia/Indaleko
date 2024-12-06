#!/usr/bin/env python3

from typing import Dict, Any
from icecream import ic
import json

class QueryExtractor():
    """
    Translator for converting parsed queries to populate the self.selected_md_attributes dictionary.
    """
    def __init__(self) -> None:
        pass

    def extract(self, query: str, llm_connector: Any) -> str:
        """
        Translate a parsed query into a dictionary for creating the metadata dataset.

        Args:
            parsed_query (Dict[str, Any]): The parsed query from NLParser
            llm_connector (Any): Connector to the LLM service

        Returns:
            str: The translated user dictionary
        """
        # Use the LLM to help generate the dictionary
        prompt = self.create_extraction_prompt(query)
        query_result = llm_connector.generate_query(prompt)
        query_statement = query_result.message.content
        json_string = query_statement.strip('```json').strip()
        selected_md_attributes = json.loads(json_string)
        ic(selected_md_attributes)
        return selected_md_attributes

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
        The dictionary should look like: 
            {“Posix”:{“file.name”: {"pattern":str (word contained in file name), "command":["starts", "ends", "contains", “exactly”], 
            "extension":[".pdf", ".doc",".docx", ".txt", ".rtf", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".mov", ".mp4", ".avi", ".mp3", ".wav", ".zip", ".rar"]}, 
            “timestamps”: {“general”: {"command":"equal", "between":at least two of ["starttime", "birthtime", “accessed”, "changed"]}, “specific”: {“birthtime”:{"starttime": str or list (lists must be in order latest to most recent),
            "endtime": str or list, "command": ["equal", "range", "greater_than", "greater_than_equal", "less_than", less_than_equal"]}, “modified”:{same as birthtime}, “accessed”:{same as birthtime}, “changed”:{same as birthtime}}, 
            “file.size”: {"target_min": int (in bytes so convert if necessary), "target_max":int, "command": ["equal", "range", "greater_than", "greater_than_equal", "less_than", less_than_equal"]}, 
            “file.directory”: {“location”: str ["google_drive", "dropbox", "icloud", "local"], "local_dir_name": str (provide name for local only; create a directory name if none provided)}}, 
            “Semantic”: {“Content_1”: {"Languages": "str" (based on language of Text), "PageNumber": int, "Text": str, "Type": ["Title", "Subtitle", "Header", "Footer", "Paragraph", "BulletPoint", "NumberedList", "Caption", "Quote", "Metadata", "UncategorizedText", "SectionHeader", "Footnote", "Abstract", "FigureDescription", "Annotation"], "EmphasizedTextTags": ["bold", "italic", "underline", "strikethrough", "highlight"], "EmphasizedTextContents": str}}, 
            “Activity”: {“geo_location”: {"location": str, "command": ["at", "within"], "km": int (only when command is "within" convert to km if necessary)}}}. Get rid of keys with null values. “Semantic” can have any number of contents. "command", "Type", and "EmphasizedTextTags" should be a single string not a list. Keep key capitalization as is. 
            The dictionary structure is {"Posix": {}, "Semantic":{}, "Activity": {}}; drop any other keys within these 3 dictionaries with null values. Timestamps should use 'YYYY-MM-DDTHH:MM:SS' format.
            When using commands like "less_than," "greater_than," "equal," "greater_than_equal," and "less_than_equal" in the "timestamps" section, the starttime and endtime must be equal. 
            Order any list of timestamps from earliest timestamp to most recent. timestamps in Posix is  "specific" or "modified", not both. Any times should be relevant to today's date. For command "range" starttime and endtime should be different where starttime < endtime.
            When using commands like "less_than," "greater_than," "equal," "greater_than_equal," and "less_than_equal" in "file.size", the target_min and target_max must be equal. For command "range" target_min and target_max should be different where target_min < target_max.
            Order any list of timestamps from least file size to most. """
        user_prompt = query
        return {
            'system' : system_prompt,
            'user' : user_prompt
        }
