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
        3) n_matching_queries: N
        4) query: query itself in aql or text 

    - query is processed by NLP to generate an aql query 
    - components of query will have to be extracted to specifiy selected_md_attributes for the metadata generator: 

    selected_md_attributes{  file.size: {"target_min":int, "target_max":int, "command":str}, 
                             file.modified: {"starttime":str, "endtime":str, "command":str},
                            ... }  

    - The resulting metadata is then stored within the Indaleko DB
    - the aql query is run with Indaleko
    - the resulting metadata are compared with what was intended to be found
    - the precision and recall are calculated and outputted in a txt format
--------------------------------------------------------------------------------------------------------------
TODOs....
TODO: testing already created functionalities
TODO: NER --> wait for Tony to specify definition of this
Done: make sure that the uri generated can be local, online, etc. 
Done: creating truth like files
Done: add altitude for geo location although altitude seems to be 0 most of the time



"""
import os, shutil, sys
from pydantic import ValidationError
if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from data_models.i_object import IndalekoObjecdtDataModel
from data_models.base import IndalekoBaseModel
from data_models.record import IndalekoRecordDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from activity.context.data_models.context_data_model import IndalekoActivityContextDataModel
from activity.context.data_models.activity_data import ActivityDataModel
from activity.data_model.activity import IndalekoActivityDataModel
from activity.collectors.location.data_models.windows_gps_location_data_model import WindowsGPSLocationDataModel
from data_models.source_identifer import IndalekoSourceIdentifierDataModel
from activity.recorders.location.location_data_collector import BaseLocationDataCollector
import IndalekoActivityDataProviderRegistration
from activity.recorders.registration_service import IndalekoActivityDataRegistrationService

from icecream import ic

from pathlib import Path
import yaml
import base64

from datetime import datetime, timedelta
import time

import random
import string
import json
import re
from faker import Faker
from geopy import geocoders
from geopy.geocoders import Nominatim

#the class for the data generator that creates metadata dataset based on the query given 
class Dataset_Generator:
    def __init__(self, config_path):

        self.config_path = config_path
        self.aql_queries_commands = ["FILTER", "LIKE"]
        self.query_ops = [">=", "<=", "==", "<>",">", "<"]
        self.metadata_json = ""

        # self.selected_md_attributes = {"Posix":{
        #                                     "file.name": {'pattern':'hi', 'command':'ends'}, 
        #                                   "timestamps": {"file.created": {'starttime': '2023-12-10','endtime': '2023-12-10', 'command': 'greater_than'}, 
                                            # "file.modified": {'starttime': '2023-12-10','endtime': '2023-12-10', 'command': 'greater_than'}, 
                                            # "file.accessed": {'starttime': '2024-1-2','endtime': '2024-1-2', 'command': 'greater_than'},
                                            # "file.changed": {'starttime': '2023-12-10','endtime': '2023-12-10', 'command': 'greater_than'}}},
        #                                     "file.size":{'target_min': 10, 'target_max': 10000, 'command':'range'}, 
        #                                     "file.directory": {'location': "google_drive"}},
        #                                 "Semantic":{
        #                                     "content": "Summary about the immune response to infections."
        #                                 }, 
        #                                 "Activity": {
        #                                     "weather": "Sun",
        #                                     "ambient_temp": {'min_temp': 21, 'max_temp':21, 'command':"gt"},
        #                                     "geo_location": {'location': "1600 Amphitheatre Parkway, Mountain View, CA 94043, USA", 'command': "at"}
        #                                 }
        #                             } 
        self.selected_md_attributes = {"Posix":{
                                            "file.name": {'pattern':'hi', 'command':'exactly', 'extension': ".txt"}
                                        #     , 
                                        #     "timestamps": {
                                        #         "specific" : {
                                        #             "birthtime": {'starttime': '2022-12-10','endtime': '2022-12-10', 'command': 'equal'}
                                        # }
                                        },
                                        "Semantic":{
                                            "semantic_1":{"content": "A summary about the immune response to infections.",
                                                "emphasized_text_contexts":["immune", "infections"]}
                                        }, "Activity": {}}

        self.selected_POSIX_md = self.selected_md_attributes["Posix"]
        self.selected_AC_md = self.selected_md_attributes["Activity"]
        self.selected_semantic_md = self.selected_md_attributes["Semantic"]

        self.saved_directory_path = {} 
        self.saved_geo_loc = {}

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
            self.metadata_json = config["output_json"]
            self.n_matching_queries = config["n_matching_queries"]



    # -----------------------------------Generate POSIX metdata-----------------------------------------------------------------

    # FUNCTION: creates  UUID for the metadata based on the file_type (filler VS truth metadata) of metadata
    def create_metadata_UUID(self, number: int, file_type: bool = True) -> str:
        if file_type:
            starter_uuid = f"c{number}" #truth files are named with a c...
        else:
            starter_uuid = f"f{number}" #filler/truth-like filler files with a f...

        digits = 8 - len(starter_uuid)
        space_filler = '0' * digits
        starter_uuid += space_filler
        uuid = self.generate_UUID(starter_uuid)

        return uuid 

    # FUNCTION: generates a random number with given number of digits
    def generate_random_number(self, digits):
        rand_digits = ''.join(random.choices('0123456789', k=digits))
        return rand_digits

    # FUNCTION: generates UUID with a given starter if provided 
    def generate_UUID(self, starter = None):
        if starter:
            first_uuid = starter
        else:
            first_uuid = self.generate_random_number(8)

        uuid = first_uuid + "-" + self.generate_random_number(4) + "-" + self.generate_random_number(4) + "-" + self.generate_random_number(4) + "-" + self.generate_random_number(12)
        return uuid

    # FUNCTION: converts date in "YYYY-MM-DD" to datetime 
    # used in time generator functions 
    def generate_time(self, time: str) -> datetime:
        splittime = re.split("-", time)

        year = int(splittime[0])
        month = int(splittime[1])
        day = int(splittime[2])

        time = datetime(year, month, day)

        # if requested time is sooner than today's day, set it to the time right now
        if time > datetime.now():
            time = datetime.now()
        return time

    # FUNCION: generate random path to directories within a parent dir based on base_dir, num_direcotries, max_depth and if available, directory_name
    # only runs once during intialization
    # adapted from Tony's code from metadata.py
    def generate_local_path(self, base_dir: str, num_directories: int, max_depth: int, directory_name: str = None) -> None:
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

    
    # PURPOSE: generate a file_name based on query or randomly
    # self.selected_POSIX_md{file.name: {"pattern":str, "command":str, "extension":str}}
    # command includes: "starts", "ends", "contains"
    def generate_file_name(self, file_type: bool) -> None:
        n_filler_letters = random.randint(1, 10)
        file_extension = [".pdf", ".doc",".docx", ".txt", ".rtf", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".mov", ".mp4", ".avi", ".mp3", ".wav", ".zip", ".rar"]

        #if the file name is part of the query, extract the appropriate attributes and generate title
        if "file.name" in self.selected_POSIX_md:
            pattern = self.selected_POSIX_md["file.name"]["pattern"]
            command = self.selected_POSIX_md["file.name"]["command"]
            if file_type: # truth file
                # if no extension specified, then randomly select a file extension
                if "extension" in self.selected_POSIX_md["file.name"]:
                    true_extension = self.selected_POSIX_md["file.name"]["extension"]
                    file_extension.remove(true_extension)
                else: 
                     true_extension = random.choice(file_extension)
                # process commands
                if command == "exactly":
                    title = pattern + true_extension
                elif command == "starts": 
                    title = pattern + ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + true_extension 
                elif command == "ends":
                    title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + pattern + true_extension 
                elif command == "contains":  
                    title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + pattern + ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + true_extension 
            elif not file_type:  # if a filler metadata, generate random title that excludes all letters specified in the char pattern
                extension = random.choice(file_extension)
                allowed_pattern = list(set(string.ascii_letters) - set(pattern.upper()) - set(pattern.lower()))
                title = ''.join(random.choices(allowed_pattern, k=n_filler_letters)) + extension 
        else: #if no query specified for title, just randomly create a title for any file_type
            title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + random.choice(self.file_extension)
        return title 

    # FUNCTION: generates path to a remote file location e.g., google drive, dropbox, icloud 
    def generate_remote_path(self, service_type, file_name: str) -> str:
        alphanum = string.ascii_letters + string.digits
        # Randomly choose characters to form the id
        file_id = ''.join(random.choices(alphanum, k=random.randint(3,6)))
        local_file_locations = {
           "google_drive": "/file/d/{file_id}/view/view?name={file_name}",
           "dropbox": "/s/{file_id}/{file_name}?dl=0",
           "icloud": "/iclouddrive/{file_id}/{file_name}"
        }
        remote_path = local_file_locations[service_type].format(file_id = file_id, file_name = file_name)
        return remote_path

    # initializes the fake local directories: 
    # the truth.directory is only populated iff the self.selected_md specifies
    # populates the self.saved_directory_path = {"truth.directory": str, "filler.directory": list, "truth.remote_directory"}}
    def initialize_local_dir(self):
        num_directories = random.randint(3, 8)
        max_depth = random.randint(3,5)
        parent_dir = "/home/user"
        truth_parent_loc = ""
        # if the there is a query related to the directory and the pathing has not been initialized create the directories 
        if "file.directory" in self.selected_POSIX_md:
            truth_parent_loc = self.selected_POSIX_md["file.directory"]["location"]
            if truth_parent_loc == "local":
                truth_path_name = self.selected_POSIX_md["file.directory"]["local_dir_name"]
                # RUN ONCE: if the file_type is a truth file, initialize the truth file directories
                self.generate_local_path(parent_dir, num_directories, max_depth, directory_name = truth_path_name)
            else: # remote so just generate random dir
                self.generate_local_path(parent_dir, num_directories, max_depth)
        else: #no queries related to file dir; generate random dir 
            self.generate_local_path(parent_dir, num_directories, max_depth)

    # FUNCTION: generates a directory location for the metadata
    # self.selected_POSIX_md["file.directory"] = [location, directory_name (optional, for local only)]
    # location: where it is stored; local or remote (google drive, drop box, icloud, local)
    # RETURN: dict consisting of path and URI to remote or local storage
    # CONSTRAINT: file name has to be determined first before creating file location and URI
    # ex) a query that specifies file type but not name: find me a file I created in dropbox two days ago: file.directory populated
    # ex) a query with no  file type and name specified: find me a file that I modified two days ago: (non populated so file name randomly generated and file directory generated randomly remote or local)
    # ex) a query with name specified without specifying file dir: (file extension randomly generated so file dir would also be randomly generated)
    def generate_dir_location(self, file_name: str, file_type: bool=True) -> dict:
        # URIs/URLs to local computer or cloud storage services
        file_locations = {
           "google_drive": "https://drive.google.com",
           "dropbox": "https://www.dropbox.com",
           "icloud": "https://www.icloud.com",
           "local": "file:/"
        }
        # RUN after initialization:
        if file_type and "file.directory" in self.selected_POSIX_md:
            truth_parent_loc = self.selected_POSIX_md["file.directory"]["location"]
            file_locations
            if truth_parent_loc == "local": # if file dir specified, create truth file at that dir
                path = self.saved_directory_path["truth.directory"] + "/" + file_name
                URI = file_locations[truth_parent_loc] + path

            elif file_type and truth_parent_loc in file_locations.keys(): # if remote dir specified, create file at that dir
                path = self.generate_remote_path(truth_parent_loc, file_name)
                URI = file_locations[truth_parent_loc] + path

        elif not file_type and "file.directory" in self.selected_POSIX_md:
            truth_parent_loc = self.selected_POSIX_md["file.directory"]["location"]
            del file_locations[truth_parent_loc]

        # not queried at this point and file type doesn't matter; generate any file path (local or remote)
        random_location = random.choice(list(file_locations.keys()))
        if random_location == "local":
            path = random.choice(self.saved_directory_path["filler.directory"]) + "/" + file_name
            URI = file_locations[random_location] + path
        else:
            path = self.generate_remote_path(random_location, file_name)
            URI = file_locations[random_location] + path

        return [path, URI]

    # Helper function for general time stamp queries in generate_timestamps
    # populates the {birthtime, m_time, a_time and c_time} given list of selected timestamps
    def generate_general_timestamps(self, selected_time: list, default_lowerbound, default_upperbound, file_type: bool) -> dict:
        timestamps = {}
        all_labels = ["birthtime", "modified", "accessed", "changed"] 
        if not file_type: # for filler files
            # generate a random combination of simliar timestamps that is not the same as the queried
            num_filter_out = random.randint(1,len(selected_time))
            filler_num = random.randint(0,len(all_labels))
            selected_time = list(set(random.sample(all_labels, k=filler_num)) - set(random.sample(selected_time, k=num_filter_out)))
        
        #if birthtime is a selected attribute in "between", set the birthtime as a random time and set the random timstamp = birthtime
        if "birthtime" in selected_time:
            birthtime = self.generate_random_timestamp(lower_bound=default_lowerbound, upper_bound=default_upperbound)
            random_similar_timestamp = birthtime
            timestamps["birthtime"] = birthtime # set the birthtime 
            all_labels.remove("birthtime")

            for timestamp in all_labels: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                if timestamp in selected_time:
                    timestamps[timestamp] = random_similar_timestamp
                else: # generates a timestamp that is above the birthtime
                    timestamps[timestamp] = self.generate_queried_timestamp(starttime= birthtime, endtime=birthtime, command="greater_than", file_type= True)
                
        else: # else, set the random time bounded above the birthtime, but not the birthtime
            # subtracting by time delta to make sure that if the upper bound is set to the datetime now, won't enforce all timestamps to be the same
            birthtime = self.generate_random_timestamp(lower_bound = default_lowerbound, upper_bound=datetime.now()-timedelta(days=1))
            # random time is not the birttime but is lower bounded by birthtime
            random_similar_timestamp = self.generate_queried_timestamp(starttime= birthtime, endtime=birthtime, command="greater_than", file_type= True)

            timestamps["birthtime"] = birthtime # set the birthtime 
            all_labels.remove("birthtime") # remove from the label to focus on the remaining timestamps

            for timestamp in all_labels: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                if timestamp in selected_time:
                    timestamps[timestamp] = random_similar_timestamp
                else: # generates a timestamp that is either above or below the random_similar_timestamp and bounded by startdate
                    timestamps[timestamp] = self.generate_queried_timestamp(starttime= random_similar_timestamp, endtime=random_similar_timestamp, default_startdate=birthtime, command="equal", file_type= False)
        return timestamps
    

    def generate_timestamps(self, file_type: bool=True) -> dict:
        stamp_labels = {"modified", "accessed", "changed"}
        birthtime = None
        latest_timestamp_of_three = None
        timestamps = {}
        default_lowerbound = datetime(2019, 10, 25)
        default_upperbound = datetime.now()

        # check whether the query is pertaining to a general relationship between queries or asking for specific timestamp queries
        if "timestamps" in self.selected_POSIX_md:
            query = self.selected_POSIX_md["timestamps"]
            if "general" in query:
                general_query = query["general"]
                if general_query["command"] == "equal":
                    times_stamps = self.generate_general_timestamps(general_query["between"], default_lowerbound, default_upperbound, file_type)
                    return times_stamps

            elif "specific" in query:
                specific_query = query["specific"]
                selected_timestamps = set(specific_query.keys())
                #todo think about implementing list to check the populated values
                if "birthtime" in specific_query:
                    birthtime_query = specific_query["birthtime"]
                    birthtime = self.generate_queried_timestamp(birthtime_query["starttime"], birthtime_query["endtime"], birthtime_query["command"], default_startdate=default_lowerbound, file_type = file_type) # creates filler timestamp, if marked false
                    timestamps["birthtime"] = birthtime

                    # if there queries other than the birthtime, iterate over each of the timestamps 
                    for timestamp in stamp_labels: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                        if timestamp in selected_timestamps:
                            timestamps[timestamp] = self.generate_queried_timestamp(specific_query[timestamp]["starttime"], specific_query[timestamp]["endtime"], specific_query[timestamp]["command"], default_startdate = birthtime, file_type=file_type)
                        else:
                            randomtime = self.generate_random_timestamp(lower_bound = birthtime, upper_bound=default_upperbound)
                            existing_timestamp = random.choice(list(timestamps.values()))
                            timestamps[timestamp] = random.choice([existing_timestamp, randomtime])

                else:
                    for timestamp in stamp_labels: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                        if timestamp in selected_timestamps:
                            timestamps[timestamp] = self.generate_queried_timestamp(specific_query[timestamp]["starttime"], specific_query[timestamp]["endtime"], specific_query[timestamp]["command"], default_startdate = default_lowerbound, file_type=file_type)
                        else:
                            timestamps[timestamp] = self.generate_random_timestamp(lower_bound=default_lowerbound, upper_bound = default_upperbound)
                            existing_timestamp = random.choice(list(timestamps.values()))
                            timestamps[timestamp] = random.choice([existing_timestamp, randomtime])

                    latest_timestamp_of_three = min(timestamps.values())
                    birthtime = self.generate_random_timestamp(lower_bound = default_lowerbound, upper_bound = latest_timestamp_of_three) 
                    timestamps["birthtime"] = birthtime

        else:
            birthtime = self.generate_random_timestamp(lower_bound = default_lowerbound, upper_bound=default_upperbound)
            timestamps["birthtime"] = birthtime
            for timestamp in stamp_labels: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                randomtime = self.generate_random_timestamp(lower_bound = birthtime, upper_bound = default_upperbound)
                existing_timestamp = random.choice(list(timestamps.values()))
                timestamps[timestamp] = random.choice([existing_timestamp, randomtime])

        return timestamps
    
    ''' 
    generate the timestamps for the specified file:
    
    starttime/endtime are in the string format: "YYYY-MM-DD"

    self.selected_POSIX_md{
        timestamps:{
            specific: { CONSTRAINT: the modified, accessed, changed must have a timestamp at least that of the created timestamp date
                file.created:{"starttime": str, "endtime": str, "command": str},
                file.modified:{"starttime": str, "endtime": str, "command": str},
                file.accessed:{"starttime": str, "endtime": str, "command": str},
                file.changed:{"starttime": str, "endtime": str, "command": str}
            }
            general: {"command":str, "between":list[str]}
        }
    }
    CONSTRAINT: a query can only specify one type of timestamp per query either a general or specific not both
    general: where there is a relationship between at least two timestamps e.g. "file where the create time and modified times are the same"
           general commands are for  general relationship queries between timestamps like which files have no change in modified, accessed, changed etc. 
           supported general command: "equal", more specific relationship between timestamps should be in the specific (where the time is specified "file where the create and modified time are specific date...)
    RETURNS: {birthtime: datetime, :, m_time: datetime, a_time: datetime, c_time: datetime}

    '''

    # Generates a random timestamp given:
    #     1) lower_bound (birth time for m/a/c timestamps or default "2019-10-25" for birthtime) 
    #     2) upper_bound (latest timestamp for birthtime or current datetime for m/a/c timestamps)
    def generate_random_timestamp(self, lower_bound, upper_bound) -> datetime:
        fake = Faker()
        random_time = fake.date_time_between(start_date = lower_bound, end_date = upper_bound)
        return random_time

    def generate_queried_timestamp(self, starttime, endtime, command, default_startdate, file_type = True) -> datetime:
        fake = Faker()
        filler_delta = 1

        if isinstance(starttime, str):
            starttime = self.generate_time(starttime)
        if isinstance(endtime, str):
            endtime = self.generate_time(endtime)
        
        if default_startdate > starttime:
            starttime = default_startdate

        # if starttime == None and endtime == None:
        #     timestamp = fake.date_time_between(start_date = default_startdate)

        # if the starttime is a list and is the same as the endtime choose a random starttime from the list
        if isinstance(starttime, list) and command == "equal":
            if file_type:
                timestamp = self.generate_time(random.choice(starttime))
            else:
                reference_time = self.generate_time(starttime[-1])
                timestamp = random.choice([fake.date_time_between(start_date = default_startdate, end_date = self.generate_time(starttime[0])-timedelta(days=filler_delta)), 
                fake.date_time_between(start_date = reference_time+timedelta(days=filler_delta))])

        elif starttime == endtime and command == "equal":
                if file_type:
                    timestamp = starttime
                else:
                    timestamp = random.choice([fake.date_time_between(start_date = default_startdate, end_date = starttime - timedelta(days=filler_delta)), 
                    fake.date_time_between(start_date = starttime+timedelta(days=filler_delta))])

        #if the starttime and endtime are not equal and are not lists, then choose a date within that range
        elif starttime != endtime and command == "range":
            if file_type:
                timestamp = fake.date_time_between(start_date=starttime, end_date=endtime)
            else:
                timestamp = random.choice([fake.date_time_between(start_date = default_startdate, end_date = starttime - timedelta(days=filler_delta)), fake.date_time_between(start_date = endtime + timedelta(days=filler_delta))])

        # if command specifies a date greater than or equal to a time 
        elif "greater_than" in command:  
            if command == "greater_than":
                delta = 1
                filler_delta = 0
            elif command == "greater_than_equal":
                delta = 0
                filler_delta = 1

            if file_type:
                timestamp = fake.date_time_between(start_date = starttime+timedelta(days=delta))
            else:
                timestamp = fake.date_time_between(start_date = default_startdate, end_date = starttime-timedelta(days=filler_delta))

        # if command specifies a date less than or equal to a  time
        elif "less_than" in command:  
            if command == "less_than":
                delta = 1
                filler_delta = 0
            elif command == "less_than_equal":
                delta = 0
                filler_delta = 1
            
            if file_type:
                timestamp = fake.date_time_between(start_date = default_startdate, end_date = endtime-timedelta(days=delta))
            else:
                timestamp = fake.date_time_between(start_date=endtime+timedelta(days=filler_delta))

        #if there are no queries related to the time, then just generate random times
        else:
            timestamp = fake.date_time_between(start_date=default_startdate)
        ic(timestamp)

        return timestamp

    '''
        PURPOSE: create random file size based on the presence of a query
        self.selected_POSIX_md{file.size: ["target_min", "target_max", "command"]}
        setting the default file size to between 1B - 10GB
        command includes "equal", "range", "greater_than", "greater_than_equal", "less_than", less_than_equal"
    '''
    def generate_file_size(self, min_size: int = 1, max_size: int = 10737418240, file_type: bool=True) -> int:
        if "file.size" in self.selected_POSIX_md:
            filler_delta = 1
            delta = 0
            target_min = self.selected_POSIX_md["file.size"]["target_min"] #this selects the min size (list or number)
            target_max = self.selected_POSIX_md["file.size"]["target_max"] #this selects the max size (list or number)
            command = self.selected_POSIX_md["file.size"]["command"] #this selects the command
            # if the target_min/max is a list and is the same as the target_max choose a random size from the list
            if isinstance(target_min, list) and isinstance(target_max, list) and command == "equal":
                if file_type:
                    size = random.choice(target_min)
                else:
                    size = random.randint(random.randint(min_size, target_min[0]-1), random.randint(target_min[len(target_min)-1]+1, max_size))

            # if the target_min/max is not a list but is the same as the target_max then just choose that file size
            elif target_min == target_max and command == "equal":
                if file_type:
                    size = target_min
                else:
                    size = random.randint(random.randint(min_size, target_min-1), random.randint(target_min+1, max_size))
            
            #if command specifies getting the range between two values
            elif target_min != target_max and command == "range":
                if file_type:
                    size = random.randint(target_min, target_max)
                else:
                    size = random.randint(random.randint(min_size, target_min-filler_delta), random.randint(target_max+filler_delta, max_size))

            # if command specifies a file greater than a certain size
            elif isinstance(target_max, int) and target_min == None:  
                if command == "greater_than":
                    delta = 1
                    filler_delta = 0
                elif command == "greater_than_equal":
                    delta = 0
                    filler_delta = 1

                if file_type:
                    size = random.randint(target_max+delta, max_size)
                else:
                    size = random.randint(min_size, target_max-filler_delta)

            # if command specifies a file less than a certain size
            elif isinstance(target_min, int) and target_max == None: 
                if command == "less_than":
                    delta = 1
                    filler_delta = 0
                elif command == "less_than_equal":
                    delta = 0
                    filler_delta = 1

                if file_type:
                    size = random.randint(min_size, target_min-delta)
                else:
                    size = random.randint(target_min+filler_delta, max_size)
        #if there are no specified queries, create a random file size
        else:
            size = random.randint(min_size, max_size)
        return size

   

    # -----------------------------------Generate activity context-----------------------------------------------------------------

    """ include the user's location
        - The music the user was listening to at the time
        - The ambient temperature
        - The weather
        - geo context
    """
    #generates a geographical activity context based on the location given 
    # self.selected_AC_md["geo_location"] = {'location': str, 'command': str}
    def generate_geo_context(self, file_type: bool = True) -> dict:
        location_dict = {}
        delta = 5
        if "geo_location" in self.selected_AC_md:
            geo_location = self.selected_AC_md["geo_location"]["location"]
            geo_command = self.selected_AC_md["geo_location"]["command"]
            if geo_command == "at":
                if file_type:
                    #geo location generator that given a city, generates longitude and latitude
                    geo_py = Nominatim(user_agent="Geo Location Metadata Generator")
                    location = geo_py.geocode(geo_location, timeout=1000)
                    latitude = location.latitude
                    longitude = location.longitude
                    altitude = location.altitude
                    self.saved_geo_loc["latitude"] = latitude
                    self.saved_geo_loc["longitude"] = longitude
                    self.saved_geo_loc["elevation"] = altitude

                else:
                    truth_latitude = self.saved_geo_loc["latitude"]
                    truth_longitude = self.saved_geo_loc["longitude"]
                    truth_altitude = self.saved_geo_loc["altitude"]

                    max_lat = 90 if truth_latitude + delta > 90 else truth_latitude + delta
                    min_lat = -90 if truth_latitude - delta < -90 else truth_latitude - delta
                    max_long = 180 if truth_longitude + delta > 180 else truth_longitude + delta
                    min_long = -180 if truth_longitude - delta < -180 else truth_longitude - delta
                    min_alt = -10 if truth_altitude - delta < -10 else truth_latitude - delta
                    max_alt = 1000 if truth_altitude + delta > 100 else truth_latitude + delta

                    latitude = random.choice([random.uniform(-90, min_lat), random.uniform(max_lat, 90)])
                    longitude = random.choice([random.uniform(-180, min_long), random.uniform(max_long, 180)])
                    altitude = random.choice([random.uniform(-10, min_alt), random.uniform(max_alt, 1000)])

        else:
            latitude = random.uniform(-90, 90)
            longitude = random.uniform(-180, 180)
            altitude = random.uniform(-10, 1000)

        location_dict["latitude"] = latitude
        location_dict["longitude"] = longitude
        location_dict["altitude"] = altitude
        return location_dict

    #generates the ambient temperature activity context
    # self.selected_AC_md["ambient_temp"] = {'min_temp': int, 'max_temp': int, 'command':str},
    #commands: equal, range, gt, lt 
    def generate_ambient_temp_ac(self, file_type: bool = True) -> int:
        overall_maxtemp = 40
        overall_mintemp = -20
        if "ambient_temp" in self.selected_AC_md:
            ambient_mintemp = self.selected_AC_md["ambient_temp"]['min_temp']
            ambient_maxtemp = self.selected_AC_md["ambient_temp"]['max_temp']
            ambient_command = self.selected_AC_md["ambient_temp"]['command']
            if ambient_command == 'equal' or ambient_command == 'range':
                if file_type:
                    ambient_temp = random.randint(ambient_mintemp, ambient_maxtemp)
                else:
                    ambient_temp = random.choice([random.randint(overall_mintemp, ambient_mintemp-1), random.randint(ambient_maxtemp+1, overall_maxtemp)])
            elif ambient_command == "greater_than":
                if file_type:
                    ambient_temp = random.randint(ambient_mintemp, overall_maxtemp)
                else:
                    ambient_temp = random.randint(overall_mintemp, ambient_mintemp-1)
            elif ambient_command == "less_than":
                if file_type:
                    ambient_temp = random.randint(overall_mintemp, ambient_mintemp)
                else:
                    ambient_temp = random.randint(ambient_mintemp+1, overall_maxtemp)
        else:
            ambient_temp = random.randint(overall_mintemp, overall_maxtemp)
        return ambient_temp

    #generates the music activity context metdata
    # self.selected_AC_md["music"] = str (music name)
    def generate_music_ac(self, file_type: bool = True) -> str:
        fake = Faker()
        if "music" in self.selected_AC_md:
            if file_type:
                music = self.selected_AC_md["music"] + ".mp3"
            else:
                music = fake.file_name(category='audio', extension = 'mp3')
        else:
            music = fake.file_name(category='audio', extension = 'mp3')
        return music

    # generates the weather activity context for the metadata 
    # self.selected_AC_md["weather"] = str (explaining the weather),
    def generate_weather_ac(self, file_type: bool = True) -> str:
        weather_dict = {"Precipitation": ["rainy", "drizzling", "showering", "stormy"], "Sun": ["sunny", "scorching", "warm", "bright", "dry"], "Snow": ["icy", "chilly", "frozen"]}
        if "weather" in self.selected_AC_md:
            weather_ac = self.selected_AC_md["weather"]
            if file_type:
                weather = random.choice(weather_dict[weather_ac])
            else:
                weather_choice_exc = list(weather_dict.keys())
                weather_choice_exc.remove(weather_ac)
                random_weather_key = random.choice(weather_choice_exc)
                weather = random.choice(weather_dict[random_weather_key])

        else:
            weather = random.choice(random.choice(weather_dict))
        return weather

    # -----------------------------------Generate semantic data--------------------------------------------------------------------

    # generates semantic data 
    def generate_semantic_content(self, file_type):
        fake = Faker()
        text = ""
        emphasized_text_contents = ""
        if self.selected_semantic_md != None:
            semantic_content = self.selected_semantic_md["semantic_1"]
            if "content" in semantic_content and "emphasized_text_contexts" in semantic_content:
                ic(file_type)
                if file_type:
                    text = semantic_content["content"]
                    emphasized_text_contents = semantic_content["emphasized_text_contexts"]
                    ic(text)
                else: 
                    text = fake.sentence(nb_words=random.randint(1, 30))
                    emphasized_text_contents = random.choice(text.split(" "))
        else:
            text = fake.sentence(nb_words=random.randint(1, 30))
            emphasized_text_contents = random.choice(text.split(" "))
        return [text, emphasized_text_contents]

    # generate random number of ascii characters
    def generate_random_data(self):
        ascii_chars = string.ascii_letters + string.digits
        random_data = ''.join(random.choices(ascii_chars, k = random.randint(1,500)))
        return random_data


    # GENERATE METADATA based on the data models 
    # create the record data based on record datamodel
    def create_record_data(self, source_identifier:dict, UUID: str, timestamp: list, file_size: int, timestamps: list, file_name: str, path: str) -> dict:
        birthtime = timestamps["birthtime"].timestamp()
        modified_time = timestamps["modified"].timestamp()
        changed_time = timestamps["changed"].timestamp()
        access_time = timestamps["accessed"].timestamp()
        record_data = {
                "SourceIdentifier": source_identifier,
                "Timestamp": timestamp,
                "Attributes": {
                    "Name": file_name,
                    "Path": path,
                    "st_birthtime": str(birthtime),
                    "st_birthtime_ns": str(birthtime * 10**9),
                    "st_mtime": str(modified_time),
                    "st_mtime_ns": str(modified_time * 10**9),
                    "st_atime": str(access_time),
                    "st_atime_ns": str(access_time * 10**9),
                    "st_ctime": str(changed_time),
                    "st_ctime_ns": str(changed_time * 10**9),
                    "st_size": file_size
                },
                "Data": self.generate_random_data()
            }
        return record_data

    # create the timestamp data based on timestamp datamodel (in UTC time)
    def create_timestamp_data(self, UUID: str, timestamps: dict) -> dict:
        timestamp_data = []
        #sort the timestamp by most earliest to latest
        for timestamp in sorted(timestamps.items(), key=lambda time: time[1]):
            timestamp_data.append(
                {
                    "Label": UUID,
                    "Value": timestamp[1].strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "Description": timestamp[0]
                }
            )
        return timestamp_data

    # create the semantic attribute data based on semantic attribute datamodel
    def create_semantic_attribute(self, extension, last_modified, file_type: bool) -> list:
        text_based_files = ["pdf", "doc", "docx", "txt", "rtf", "csv", "xls", "xlsx", "ppt", "pptx"] # text based files supported by the metadata generator
        emphasize_text_tags = ["bold", "italic", "underline", "strikethrough", "higlight"] 
        text_tags = ["Title", "Subtitle", "Header", "Footer", "Paragraph", "BulletPoint", "NumberedList", "Caption", "Quote", "Metadata", "UncategorizedText", "SectionHeader", "Footnote", "Abstract", "FigureDescription", "Annotation"]

        if extension in text_based_files:
            #choose language:
            language = "English"
            text, emphasized_text_contents = self.generate_semantic_content(file_type)
            type = random.choice(text_tags)
            text_tag =random.choice(emphasize_text_tags)
            page_number = random.randint(1, 200)
            data = {
                "text_content": [text, type, language, text_tag],
                "filetype": extension,
                "last_modified":last_modified,
                "page_number": str(page_number) + " pages",
            }
        else:
            data = {
                "filetype": extension,
                "last_modified":last_modified,
            }

        list_semantic_attribute = []
        for values in list(data.values()):
            semantic_UUID = self.generate_UUID()
            semantics_metadata_uuid = self.create_UUID_data(semantic_UUID, "semantics_UUID")
            if isinstance(values, list):
                for data in values:
                    ic(data)
                    list_semantic_attribute.append({
                        "Identifier": semantics_metadata_uuid,
                        "Data": data
                    })
            else:
                list_semantic_attribute.append({
                        "Identifier": semantics_metadata_uuid,
                        "Data": values
                    })

        return list_semantic_attribute

    # create the UUID data based on the UUID data model
    def create_UUID_data(self, UUID: str, label: str = "IndalekoUUID") -> dict:
        uuid_data = {
            "Identifier": UUID,
            "Label": label
        }
        return uuid_data

    #helper function for setting truth attributes
    # returns true if the file is a truth file or the attribute is contained int he truthlike attribute list 
    def define_truth_attribute(self, attribute, truth_file, truthlike_file, truth_attributes):
        return truth_file or (truthlike_file and attribute in truth_attributes)

    # generates the target metadata with the specified attributes based on the nubmer of matching queries to generate from config:
    def generate_metadata(self, current_filenum:int, max_num: int, key: str, file_type: bool, truth_like: bool) -> dict:
        all_metadata = []
        truthlike_attributes =[]  
        geo_data_md = []      
        for n in range(1, max_num):
            key_name = f'{key} #{n}'

            if truth_like:
                total_truth_attributes = len(self.truth_attributes)
                filler_truth_attributes = random.randint(1, total_truth_attributes-1)
                truthlike_attributes = random.sample(self.truth_attributes, k = filler_truth_attributes)

                key_name += f', truth-like attributes: {truthlike_attributes}'

            timestamps = self.generate_timestamps(file_type=self.define_truth_attribute("timestamps", file_type, truth_like, truthlike_attributes))
            IO_UUID = self.create_metadata_UUID(current_filenum + n, file_type = file_type)
            source_uuid = self.generate_UUID()
            file_size = self.generate_file_size(file_type= self.define_truth_attribute("file.size", file_type, truth_like, truthlike_attributes))
            file_name = self.generate_file_name(file_type= self.define_truth_attribute("file.name", file_type, truth_like, truthlike_attributes))
            path, URI = self.generate_dir_location(file_name, file_type= self.define_truth_attribute("file.directory", file_type, truth_like, truthlike_attributes))
            record_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

            source_identifier = {
                "Identifier": IO_UUID, # UUID Of the record data
                "Version": "1.0"
            }

            record_data = self.create_record_data(source_identifier, IO_UUID, record_timestamp, file_size, timestamps, file_name, path)
            timestamp_data = self.create_timestamp_data(IO_UUID, timestamps)

            extension = file_name.split(".")[-1]
            ic(truth_like)
            semantic_attributes_data = self.create_semantic_attribute(extension= extension, last_modified=timestamps["modified"].strftime("%Y-%m-%dT%H:%M:%S"), file_type= self.define_truth_attribute("semantic_1", file_type, truth_like, truthlike_attributes))
            record_md = {
                "Record": record_data,
                "URI": URI,
                "ObjectIdentifier": source_uuid,
                "Timestamps": timestamp_data,
                "Size": file_size,
                "SemanticAttributes": semantic_attributes_data,
                "Label": key_name,
                "LocalIdentifier": str(current_filenum + n),
                "Volume": source_uuid,
                "PosixFileAttributes": "S_IFREG", #default set to regular files
                "WindowsFileAttributes": "FILE_ATTRIBUTE_ARCHIVE", #setting as default
            }

            GPS_UUID = self.generate_UUID()
            record_kwargs = {
                'Identifier' : GPS_UUID,
                'Version' : '1.0.0',
                'Description' : key_name,
                'Record' : record_data
            }
            # Add the new metadata entry to the dictionary
            all_metadata.append(record_md)

            activity_geo_loc = self.generate_geo_context(file_type)
            activity_geo_md = self.generate_WindowsGPSLocation(activity_geo_loc)
            geo_data_md.append(self.generate_geo_semantics(record_kwargs, activity_geo_md, GPS_UUID))

        return all_metadata, geo_data_md

    # --------------------------------- GENERATE ACTIVITY CONTEXT METADATA -------------------------------------------------------

    def generate_WindowsGPSLocation(self, geo_activity_context: dict) -> dict:
        latitude = geo_activity_context["latitude"]
        longitude = geo_activity_context["longitude"]
        altitude = geo_activity_context["altitude"]
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
        #WindowsGPSLocationDataModel

        windowsGPS_satellite_location = {
            'geometric_dilution_of_precision': random.uniform(1, 10),
            'horizontal_dilution_of_precision': random.uniform(1, 10),
            'position_dilution_of_precision': random.uniform(1, 10),
            'time_dilution_of_precision': random.uniform(1, 10),
            'vertical_dilution_of_precision': random.uniform(1, 10)
        }

        no_windowsGPS_satellite_location = {
            'geometric_dilution_of_precision': None,
            'horizontal_dilution_of_precision': None,
            'position_dilution_of_precision': None,
            'time_dilution_of_precision': None,
            'vertical_dilution_of_precision': None
        }
        
        GPS_location_dict = {
            "latitude": latitude,
            "longitude": longitude,
            "altitude": altitude,
            "accuracy": random.uniform(1, 10),
            "altitude_accuracy": random.uniform(0, 10),
            "heading": random.randint(0, 360),
            "speed": random.uniform(0, 20),
            "source": "GPS",
            "timestamp": timestamp,
            "is_remote_source": False,
            "point": f"POINT({longitude} {latitude})",
            "position_source": "GPS",
            "position_source_timestamp": timestamp,
            "satellite_data": random.choice([windowsGPS_satellite_location, no_windowsGPS_satellite_location]),
            "civic_address" : None,
            "venue_data": None,
        }

        return GPS_location_dict

    # def generate_activity_data_registration(self, record_data: dict):
    #     activity_data_provider_uuid = self.generate_UUID()
    #     activity_registration_md = {
    #         "Identifier": activity_data_provider_uuid,
    #         "Version": "1.0",
    #         "Description": "Data provider registration",
    #         "Record": record_data
    #     }

    #     return activity_registration_md

    def generate_source_identifier(self, description, UUID= None):
        if UUID == None:
            UUID = self.self.generate_UUID()
        source_identifier = {
            "Identifier": UUID,
            "Version": "1",
            "Description": description
        }
        return source_identifier
    def generate_activity_semantic(self, description, data):
        semantic_md = { 
            "Identifier": self.generate_source_identifier(description),
            "Data": data
        }
        return semantic_md

    def generate_geo_semantics(self, record_md, activity_geo_md, UUID) -> list:
        activity_service = IndalekoActivityDataRegistrationService()
        provider_data, collection = activity_service.register_provider(**record_md)
        ic(provider_data)
        ic(collection)
        source_identifier = self.generate_source_identifier("source_identifier", UUID)

        semantic_attributes = [
            self.generate_activity_semantic("Longitude", activity_geo_md["longitude"]), 
            self.generate_activity_semantic("Latitude", activity_geo_md["latitude"]), 
            self.generate_activity_semantic("Accuracy", activity_geo_md["accuracy"])
        ]

        doc = BaseLocationDataCollector.build_location_activity_document(
            source_data=source_identifier,
            location_data=activity_geo_md,
            semantic_attributes=semantic_attributes
        )
        return json.loads(doc)
    

    #writes generated metadata in json file
    def write_json(self, dataset: dict, json_path: str) -> None:
        with open(json_path, 'w') as json_file:
            json.dump(dataset, json_file, indent=4)
    
    # main function to run the metadata generator
    def generate_metadata_dataset(self) -> None:
        self.parse_config_json()
        # intiialize the synthetic dir locations
        self.initialize_local_dir()

        self.truth_attributes = list(self.selected_POSIX_md.keys()) + list(self.selected_AC_md.keys()) + list(self.selected_semantic_md.keys())
        target_record_md,  target_activity_md = self.generate_metadata(0, self.n_matching_queries+1, 'Truth File', True, False)

        total_truth_attributes = len(self.truth_attributes) 
        remaining_files = self.n_metadata_records - self.n_matching_queries

        # only create truth-like files if the number of attributes is greater than one, otherwise, it becomes a truth file
        if total_truth_attributes > 1 and self.n_matching_queries > 0:
            truth_like_num = random.randint(0, remaining_files)
        else:
            truth_like_num = 0

        filler_num = remaining_files - truth_like_num

        truth_like_filler_record_md,  truth_like_filler_activity_md = self.generate_metadata(0, truth_like_num +1, 'Filler Truth-Like File', False, True)
        filler_record_md, filler_activity_md = self.generate_metadata(truth_like_num,  filler_num +1, 'Filler File', False, False)
        all_record_md = target_record_md + truth_like_filler_record_md + filler_record_md
        all_activity_md = target_activity_md + truth_like_filler_activity_md + filler_activity_md
        self.write_json(all_record_md, self.metadata_json + "all_records.json")
        self.write_json(all_activity_md, self.metadata_json + "all_activity.json")
        # ic(target[0]["Timestamps"][0])
        # self.test_data_model(target[0]["SemanticAttributes"][0], IndalekoSemanticAttributeDataModel)

    #test the data model to see if in the right form
    # test with any of the following variables: target, truth_like_filler, filler
    def test_data_model(self, model, dataModel):
        try:
            model_test = dataModel(**model)
            print("Valid input passed:", model_test)
        except ValidationError as e:
            print("Validation error for valid input:", e)
    
def main():
    config_path = "data_generator/dg_config.json"
    data_generator = Dataset_Generator(config_path)
    data_generator.generate_metadata_dataset()

if __name__ == '__main__':
    main()