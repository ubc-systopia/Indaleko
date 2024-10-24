"""
Script to generate metadata based on db_config.json to test Indaleko
Author: Pearl Park

File metadata generator for:
    A) POSIX metadata
    B) semantic metada
    C) activity context

Pipeline workflow:
    - Query processor takes in a json config consisting of parameters for:
           
        0) output_json_file: the output json file to store the metadata
        1) n_metadata_records: The total number of metadata 
        2) total_storage_size: the total dataset size in terms of file size
        3) n_queries: number of queries; started with one for now
        4) n_matching_queries: N
        5) query: query itself in aql or text 

    - query is processed by NLP to generate an aql query 
    - components of query will have to be extracted to specifiy selected_md_attributes for the metadata generator: 

    selected_md_attributes{  file.size: ["target_min", "target_max", "command"], 
                             file.modified: ["starttime", "endtime", "command"],
                             file.name: ["pattern", "command", "extension"], ... }  # extension is optional

    - The resulting metadata is then stored within the Indaleko DB
    - the aql query is run with Indaleko
    - the resulting metadata are compared with what was intended to be found
    - the precision and recall are calculated and outputted in a txt format


TODO: finish creating metadata for directory that the file is found in and generation of data for the activity context and semantics
TODO: figure out how to process the queries to generate the intended input for the metadata generator 
TODO: feed metadata into the Indaleko DB and run against query 
TODO: create the recall/precision tool 


"""
from icecream import ic

import os, shutil
from pathlib import Path
import yaml
import sys

import datetime
from datetime import timedelta
import time

import random
import string
import json
import re
from faker import Faker

# from Indaleko.query.query_processing.nl_parser import NLParser
# from Indaleko.query.query_processing.query_tranlsator.aql_translator import AQLTranslator


#the class for the data generator that creates metadata dataset based on the query given 
class Dataset_Generator:
    def __init__(self, config_path):
        self.config_path = config_path

        self.aql_queries_commands = ["FILTER", "LIKE"]
        self.query_ops = [">=", "<=", "==", "<>",">", "<"]
        self.metadata_json = ""
        # self.metadata_attributes = ["dir_location", "file.modified", "file.size", "file.name"]

        self.selected_md_attributes = {"file.name": ["hi", "ends", ".pdf"], "file.modified": ['2023-12-10', '2023-12-23', "range"], "file.size":[10, 10000, "range"], "file.directory": ["photo", "find"]} # in the format {file.size:[min, max], file.name:"fake_name", etc.} 
        self.saved_directory_path = {} 

        self.file_type = ['.jpg','.txt','.pdf']
        self.total_storage = 0
        self.total_metadata = 0 
        self.aql_query = ""
        

    #parse the json config file and extract appropriate parameters 
    def parse_config_json(self):
        print("e")
        with open(self.config_path, 'r') as file:
            print("here")
            config = json.load(file)
            self.n_metadata_records = config["n_metadata_records"]
            self.total_storage_size = config["total_storage_size"]
            self.query = config["query"]
            self.metadata_json = config["output_json_file"]
            self.n_matching_queries = config["n_matching_queries"]

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

    #TODO: working on...
    def get_selected_md_attributes(self, extracted_attributes):
        # split multiple attribute finding queries in two 
        # TODO: what about ORs?
        if "AND" in extracted_attributes:
            attribute_list = extracted_attributes.split("AND")
            regex_ops = "|".join(self.query_ops)
            for attributes in attribute_list:
                result = re.split(f"({regex_ops})", attributes)
                self.selected_md_attributes
        elif "OR" in extracted_attributes:
            None
    
    # generate a random number with given number of digits
    def generate_random_number(self, digits):
        rand_digits = ''.join(random.choices('0123456789', k=digits - 1))
        return rand_digits

    #create the UUID for the metadata based on the type of metadata they are (filler VS truth metadata)
    def create_UUID(self, number, query_number, type=True):
        if type:
            uuid = f"q{query_number}t{number}" 
        else:
            uuid = f"f{number}"

        digits = 8 - len(uuid)
        space_filler = 'z' * digits
        uuid += space_filler + "-" + self.generate_random_number(4) + "-" + self.generate_random_number(4) + "-" + self.generate_random_number(4) + "-" + self.generate_random_number(12)
        return uuid 


    #convert query format of date "YYYY-MM-DD" to datetime format
    def generate_time(self, time):
        splittime = re.split("-", time)

        year = int(splittime[0])
        month = int(splittime[1])
        day = int(splittime[2])

        time = datetime.date(year, month, day)
        return time

    #generate random path to directories within a parent dir based on base_dir, num_direcotries, max_depth and if available, directory_name
    def generate_random_path(self, base_dir, num_directories, max_depth, directory_name = None):
        directory_count = 0  
        # List to store generated paths
        generated_paths = [] 
        
        def create_dir_recursive(current_dir, current_depth):
            nonlocal directory_count
            if current_depth > max_depth or directory_count >= num_directories:
                return  

            if num_directories - directory_count > 0:
                max_subdirs = max(1, (num_directories - directory_count) // (max_depth - current_depth + 1))
                subdirs = random.randint(1, max_subdirs)

                for _ in range(subdirs):
                    directory_count += 1
                    if directory_count >= num_directories:
                        break
                    # Generate a random subdirectory name or choose truth path name
                    subdir_name = ''.join(random.choices(string.ascii_lowercase, k = random.randint(1,8)))
                    subdir_path = os.path.join(current_dir, subdir_name)
                    generated_paths.append(subdir_path)
                    create_dir_recursive(subdir_path, current_depth + 1)

        create_dir_recursive(base_dir, 1)
        if directory_name != None:
            self.saved_directory_path["truth.directory"] = random.choice(generated_paths) + "/" + directory_name
        self.saved_directory_path["filler.directory"] = generated_paths

        ic(generated_paths)
        

        

    

    #generates a directory location for the metadata
    # self.selected_md_attributes["file.directory"] = [directory_name, command]
    # self.saved_md_attributes["file.directory"] saves the pathing to files created
    def generate_dir_location(self, file_name, type=True):
        parent_dir = "/home"
        num_directories = random.randint(3, 8)
        max_depth = random.randint(3,5)

        # if the there is a query related to the directory and the pathing has not been initialized create the directories 
        if "file.directory" in self.selected_md_attributes and "truth.directory" not in self.saved_directory_path:
            truth_path_name = self.selected_md_attributes["file.directory"][0]
            truth_path_command = self.selected_md_attributes["file.directory"][1]
            if truth_path_command == "find":
                self.generate_random_path(parent_dir, num_directories, max_depth, directory_name = truth_path_name)
        #else if not instantiated
        elif "filler.directory" not in self.saved_directory_path: 
            self.generate_random_path(parent_dir, num_directories, max_depth)


        #if the directory has been instantiated and there is a path to the truth directory
        if "truth.directory" in self.saved_directory_path:
            if type:
                path = self.saved_directory_path["truth.directory"] + "/" + file_name
            else:
                path = random.choice(self.saved_directory_path["filler.directory"]) + "/" + file_name
        else: 
            path = random.choice(self.saved_directory_path["filler.directory"]) + "/" + file_name
        return path


    # PURPOSE: creates the modified time based on the start time, endtime and command provided
    # self.selected_md_attributes{file.modified: ["starttime", "endtime", "command"]}
    # CONSTRAINTS:
    #   command: includes "equal", "range", "greater_than", "greater_than_equal", "less_than", less_than_equal"
    #   starttime >= the default_startdate
    #   starttime <= endtime <= starttime.now()
    def generate_file_modified(self, type=True):
        fake = Faker()
        #setting a random startdate, can change if needed
        default_startdate = self.generate_time("2019-10-25")

        # if a condition for the modified attribute exists
        if "file.modified" in self.selected_md_attributes:
            starttime = self.selected_md_attributes["file.modified"][0] #this selects the startdate
            endtime = self.selected_md_attributes["file.modified"][1] #this selects the enddate
            command = self.selected_md_attributes["file.modified"][2] #this specifies command

            datetime_st = self.generate_time(starttime)
            datetime_et = self.generate_time(endtime)

            # if the starttime is a list and is the same as the endtime choose a random starttime from the list
            if isinstance(starttime, list) and command == "equal":
                if type:
                    modified_time = random.choice(starttime)
                else:
                    modified_time = random.choice([fake.date_between(start_date = default_startdate, end_date = self.generate_time(starttime[0])-timedelta(days=1)), 
                    fake.date_between(start_date = self.generate_time(starttime[len(datetime-1)]+timedelta(days=1)))])


            # if the starttime is not a list but is the same as the endtime then just choose that starttime
            elif starttime == endtime and command == "equal":
                if type:
                    modified_time = starttime
                else:
                    modified_time = random.choice([fake.date_between(start_date = default_startdate, end_date = datetime_st - timedelta(days=1)), 
                    fake.date_between(start_date = datetime_st+timedelta(days=1))])

            
            #if the starttime and endtime are not equal and are not lists, then choose a date within that range
            elif starttime != endtime and command == "range":
                if type:
                    modified_time = fake.date_between(start_date=datetime_st, end_date=datetime_et)
                else:
                    modified_time = random.choice([fake.date_between(start_date = default_startdate, end_date = datetime_st - timedelta(days=1)), fake.date_between(start_date = datetime_et + timedelta(days=1))])

            # if command specifies a date greater than or equal to a time 
            elif isinstance(endtime, string) and starttime == None:  
                if command == "greater_than":
                    delta = 1
                elif command == "greater_than_equal":
                    delta = 0

                if type:
                    modified_time = fake.date_between(start_date = datetime_st+timedelta(days=delta))
                else:
                    modified_time = fake.date_between(start_date = default_startdate, end_date = datetime_st-timedelta(days=delta))

            # if command specifies a date less than or equal to a  time
            elif isinstance(starttime, string) and endtime == None:  
                if command == "less_than":
                    delta = 1
                elif command == "less_than_equal":
                    delta = 0

                if type:
                    modified_time = fake.date_between(start_date = default_startdate, end_date = datetime_et-timedelta(days=delta))
                else:
                    modified_time = self.calculate_time(start=datetime_et+timedelta(days=delta))

        #if there are no constraints on the modified time, then just gneerate random times
        else:
            modified_time = fake.date_between(start_date=default_startdate)
        return str(modified_time)


    # PURPOSE: create random file size based on the presence of a query
    # self.selected_md_attributes{file.size: ["target_min", "target_max", "command"]}
    # setting the default file size to between 1B - 10GB
    def generate_file_size(self, min_size = 1, max_size =10737418240, type=True):
        if "file.size" in self.selected_md_attributes:
            target_min = self.selected_md_attributes["file.size"][0] #this selects the min size (list or number)
            target_max = self.selected_md_attributes["file.size"][1] #this selects the max size (list or number)
            command = self.selected_md_attributes["file.size"][2] #this selects the command
            # if the target_min/max is a list and is the same as the target_max choose a random size from the list
            if isinstance(target_min, list) and isinstance(target_max, list) and command == "equal":
                if type:
                    size = random.choice(target_min)
                else:
                    size = random.randint(random.randint(min_size, target_min[0]-1), random.randint(target_min[len(target_min)-1]+1, max_size))

            # if the target_min/max is not a list but is the same as the target_max then just choose that file size
            elif target_min == target_max and command == "equal":
                if type:
                    size = target_min
                else:
                    size = random.randint(random.randint(min_size, target_min-1), random.randint(target_min+1, max_size))
            
            #if command specifies getting the range between two values
            elif target_min != target_max and command == "range":
                if type:
                    size = random.randint(target_min, target_max)
                else:
                    size = random.randint(random.randint(min_size, target_min-1), random.randint(target_max+1, max_size))

            # if command specifies a file greater than a certain size
            elif isinstance(target_max, int) and target_min == None:  
                if command == "greater_than":
                    delta = 1
                elif command == "greater_than_equal":
                    delta = 0

                if type:
                    size = random.randint(target_max, max_size)
                else:
                    size = random.randint(min_size, target_max-delta)

            # if command specifies a file less than a certain size
            elif isinstance(target_min, int) and target_max == None: 
                if command == "less_than":
                    delta = 1
                elif command == "less_than_equal":
                    delta = 0

                if type:
                    size = random.randint(min_size, target_min)
                else:
                    size = random.randint(target_min+delta, max_size)
        #if there are no specified queries, create a random file size
        else:
            size = random.randint(min_size, max_size)
        return size

    # PURPOSE: generate a file_name based on query or randomly
    # self.selected_md_attributes{file.name: ["pattern", "command", "extension"]}
    def generate_file_name(self, type=True):
        n_filler_letters = random.randint(1, 10)

        #if the file name is part of the query, extract the appropriate attributes and generate title
        if "file.name" in self.selected_md_attributes:
            pattern = self.selected_md_attributes["file.name"][0]
            command = self.selected_md_attributes["file.name"][1]
            extension = self.selected_md_attributes["file.name"][2]

            #if no extension specified, then randomly select a file extension
            if extension == "":
                extension = random.choice(self.file_type)
            if type:
                if command == "starts": # title that starts with a char pattern
                    title = pattern + ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + extension 
                elif command == "ends": # title that ends with specific char pattern
                    title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + pattern + extension 
                elif command == "contains":  # title that contains a char pattern
                    title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + pattern + ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + extension 
            
            # if a filler metadata, generate random title that excludes all letters specified in the char pattern
            else:
                allowed_pattern = list(set(string.ascii_letters) - set(pattern.upper()) - set(pattern.lower()))
                title = ''.join(random.choices(allowed_pattern, k=n_filler_letters)) + extension 
        #if no query specified for title, just randomly create a title 
        else: 
            title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + random.choice(self.file_type)
        return title 

    # PURPOSE: generates the target metadata with the specified attributes based on the nubmer of matchiing queries to generate from config:
    def generate_target_metadata(self, query_number):
        all_metadata = {}
        for n in range(self.n_matching_queries):
            key = f'Truth File #{n}'
            file_name = self.generate_file_name()
            # Add the new metadata entry to the dictionary
            all_metadata[key] = {
                "UUID": self.create_UUID(n, query_number),
                "dir_location": self.generate_dir_location(file_name),
                "file.modified": self.generate_file_modified(),
                "file.size": self.generate_file_size(),
                "file.name": file_name
            }
        return all_metadata

        
    # generates the filler metadata with the specified attributes based on the number of filler files required after generating truth metadata:
    def generate_filler_metadata(self, query_number):
        all_metadata = {}
        for n in range(self.n_metadata_records - self.n_matching_queries):
            key = f'Filler File #{n}'
            file_name = self.generate_file_name(type = False)
            # Add the new metadata entry to the dictionary
            all_metadata[key] = {
                "UUID": self.create_UUID(n, query_number, type = False),
                "dir_location": self.generate_dir_location(file_name, type = False),
                "file.modified": self.generate_file_modified(type = False),
                "file.size": self.generate_file_size(type = False),
                "file.name": file_name
            }
        return all_metadata

    #writes generated metadata in json file
    def write_json(self, target, filler):
        target.update(filler)
        with open(self.metadata_json, 'w') as self.json_file:
            json.dump(target, self.json_file, indent=4)

    # main function to run the metadata generator
    def generate_metadata_dataset(self):
        self.parse_config_json()
        target = self.generate_target_metadata(1)
        filler = self.generate_filler_metadata(1)
        self.write_json(target, filler)

def main():
    sys.path.append('/Users/pearl/Indaleko_updated/Indaleko')
    config_path = "/Users/pearl/Indaleko_updated/Indaleko/data_generator/0_Input/dg_config.json"
    data_generator = Dataset_Generator(config_path)
    data_generator.generate_metadata_dataset()



if __name__ == '__main__':
    main()


