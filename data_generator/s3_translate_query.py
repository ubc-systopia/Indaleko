
#TODO: translate the query 
def translate_query(self):
    #parser = NLParser()
    #aqltranslator = AQLTranslator()

    parsed_query = parser.parse(self.query)
    self.aql_query = aqltranslator.translate(parsed_query)

#TODO: process and extract the attributes required for the metadata creation
def process_query(self):
    #test with one query first
    query = self.query
    for command in self.aql_queries_commands:
        if command in query:
            regex = rf"(?<={command}\s)(.*?)(?=\sRETURN)"
            extracted_attributes = re.search(regex, query).group()
            self.get_selected_md_attributes(extracted_attributes)
    print("here")

#TODO: working on... generates dictionary of the selected md attributes to queried for
def get_selected_md_attributes(self, extracted_attributes):
    # split multiple attribute finding queries in two 
    # TODO: what about ORs?
    if "AND" in extracted_attributes:
        attribute_list = extracted_attributes.split("AND")
        regex_ops = "|".join(self.query_ops)
        for attributes in attribute_list:
            result = re.split(f"({regex_ops})", attributes)
            self.selected_POSIX_md
    elif "OR" in extracted_attributes:
        None