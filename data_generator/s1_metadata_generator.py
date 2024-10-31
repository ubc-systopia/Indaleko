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

TODO:   1) Create time
        2) Modify time
        3) Last read time

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

from icecream import ic

from pathlib import Path
import yaml
import base64

import datetime
from datetime import timedelta
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
        #                                     "file.modified": {'starttime': '2023-12-10','endtime': '2023-12-23', 'command': 'range'},
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
        #                             } # in the format {file.size:[min, max], file.name:"fake_name", etc.} 
        self.selected_md_attributes = {"Posix":{
                                            "file.name": {'pattern':'hi', 'command':'ends'}, 
                                            "file.directory": {'location': "google_drive"}}, "Semantic": {}, "Activity": {}}

        self.selected_POSIX_md = self.selected_md_attributes["Posix"]
        self.selected_AC_md = self.selected_md_attributes["Activity"]
        self.selected_semantic_md = self.selected_md_attributes["Semantic"]

        self.saved_directory_path = {} 
        self.saved_geo_loc = {}

        self.file_extension = ['.jpg','.txt','.pdf']
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



    # -----------------------------------Generate POSIX metdata-----------------------------------------------------------------
    
    # generate a random number with given number of digits
    def generate_random_number(self, digits):
        rand_digits = ''.join(random.choices('0123456789', k=digits))
        return rand_digits

    # create the UUID for the metadata based on the file_type of metadata they are (filler VS truth metadata)
    def create_UUID(self, number: int, file_type: bool = True) -> str:
        if file_type:
            uuid = f"c{number}" 
        else:
            uuid = f"f{number}"

        digits = 8 - len(uuid)
        space_filler = '0' * digits
        uuid += space_filler + "-" + self.generate_random_number(4) + "-" + self.generate_random_number(4) + "-" + self.generate_random_number(4) + "-" + self.generate_random_number(12)
        return uuid 


    # Helper function to convert query format of date "YYYY-MM-DD" to datetime format
    # used in time generator functions 
    def generate_time(self, time: str) -> datetime:
        splittime = re.split("-", time)

        year = int(splittime[0])
        month = int(splittime[1])
        day = int(splittime[2])

        time = datetime.date(year, month, day)
        return time

    #generate random path to directories within a parent dir based on base_dir, num_direcotries, max_depth and if available, directory_name
    #only runs once 
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
    #TODO: could control for case-sensitivity
    def generate_file_name(self, file_type: bool) -> None:
        n_filler_letters = random.randint(1, 10)
        file_extension = [".pdf", ".doc",".docx", ".txt", ".rtf", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".mov", ".mp4", ".avi", ".mp3", ".wav", ".zip", ".rar"]

        #if the file name is part of the query, extract the appropriate attributes and generate title
        if "file.name" in self.selected_POSIX_md:
            pattern = self.selected_POSIX_md["file.name"]["pattern"]
            command = self.selected_POSIX_md["file.name"]["command"]
            if file_type:
                #if no extension specified, then randomly select a file extension
                if "extension" in self.selected_POSIX_md["file.name"]:
                    true_extension = self.selected_POSIX_md["file.name"]["extension"]
                    file_extension.remove(true_extension)
                else: 
                     true_extension = random.choice(file_extension)
                if command == "starts": # title that starts with a char pattern
                    title = pattern + ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + true_extension 
                elif command == "ends": # title that ends with specific char pattern
                    title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + pattern + true_extension 
                elif command == "contains":  # title that contains a char pattern
                    title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + pattern + ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + true_extension 
            # if a filler metadata, generate random title that excludes all letters specified in the char pattern
            elif not file_type:
                extension = random.choice(file_extension)
                allowed_pattern = list(set(string.ascii_letters) - set(pattern.upper()) - set(pattern.lower()))
                title = ''.join(random.choices(allowed_pattern, k=n_filler_letters)) + extension 
        #if no query specified for title, just randomly create a title 
        else: 
            title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + random.choice(self.file_extension)
        return title 

    #generates path to a remote query 
    def generate_remote_path(self, service_type, file_name: str) -> str:
        alphanum = string.ascii_letters + string.digits
        # Randomly choose characters from the combination and join them to form the key
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

    #generates a directory location for the metadata
    # self.selected_POSIX_md["file.directory"] = [location, directory_name (optional, for remote only)]
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

        #RUN after initialization:
        if file_type and "file.directory" in self.selected_POSIX_md:
            truth_parent_loc = self.selected_POSIX_md["file.directory"]["location"]
            file_locations
            if truth_parent_loc == "local": # if file dir specified, create truth file at that dir
                path = self.saved_directory_path["truth.directory"] + "/" + file_name
                URI = file_locations[truth_parent_loc] + path

            elif file_type and truth_parent_loc in file_locations.keys(): # if remote dir specified, create file at that dir
                path = self.generate_remote_path(truth_parent_loc, file_name)
                ic(truth_parent_loc)
                URI = file_locations[truth_parent_loc] + path

        elif not file_type and  "file.directory" in self.selected_POSIX_md:
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


    # PURPOSE: creates the modified time based on the start time, endtime and command provided
    # self.selected_POSIX_md{file.modified: ["starttime", "endtime", "command"]}
    # CONSTRAINTS:
    #   command: includes "equal", "range", "greater_than", "greater_than_equal", "less_than", less_than_equal"
    #   starttime >= the default_startdate
    #   starttime <= endtime <= starttime.now()
    def generate_file_modified(self, file_type: bool=True) -> datetime:
        fake = Faker()
        #setting a random startdate, can change if needed
        default_startdate = self.generate_time("2019-10-25")

        # if a condition for the modified attribute exists
        if "file.modified" in self.selected_POSIX_md:
            starttime = self.selected_POSIX_md["file.modified"]["starttime"] #this selects the startdate
            endtime = self.selected_POSIX_md["file.modified"]["endtime"] #this selects the enddate
            command = self.selected_POSIX_md["file.modified"]["command"] #this specifies command

            datetime_st = self.generate_time(starttime)
            datetime_et = self.generate_time(endtime)

            # if the starttime is a list and is the same as the endtime choose a random starttime from the list
            if isinstance(starttime, list) and command == "equal":
                if file_type:
                    modified_time = random.choice(starttime)
                else:
                    modified_time = random.choice([fake.date_between(start_date = default_startdate, end_date = self.generate_time(starttime[0])-timedelta(days=1)), 
                    fake.date_between(start_date = self.generate_time(starttime[len(datetime-1)]+timedelta(days=1)))])


            # if the starttime is not a list but is the same as the endtime then just choose that starttime
            elif starttime == endtime and command == "equal":
                if file_type:
                    modified_time = starttime
                else:
                    modified_time = random.choice([fake.date_between(start_date = default_startdate, end_date = datetime_st - timedelta(days=1)), 
                    fake.date_between(start_date = datetime_st+timedelta(days=1))])

            
            #if the starttime and endtime are not equal and are not lists, then choose a date within that range
            elif starttime != endtime and command == "range":
                if file_type:
                    modified_time = fake.date_between(start_date=datetime_st, end_date=datetime_et)
                else:
                    modified_time = random.choice([fake.date_between(start_date = default_startdate, end_date = datetime_st - timedelta(days=1)), fake.date_between(start_date = datetime_et + timedelta(days=1))])

            # if command specifies a date greater than or equal to a time 
            elif isinstance(endtime, string) and starttime == None:  
                if command == "greater_than":
                    delta = 1
                elif command == "greater_than_equal":
                    delta = 0

                if file_type:
                    modified_time = fake.date_between(start_date = datetime_st+timedelta(days=delta))
                else:
                    modified_time = fake.date_between(start_date = default_startdate, end_date = datetime_st-timedelta(days=delta))

            # if command specifies a date less than or equal to a  time
            elif isinstance(starttime, string) and endtime == None:  
                if command == "less_than":
                    delta = 1
                elif command == "less_than_equal":
                    delta = 0

                if file_type:
                    modified_time = fake.date_between(start_date = default_startdate, end_date = datetime_et-timedelta(days=delta))
                else:
                    modified_time = self.calculate_time(start=datetime_et+timedelta(days=delta))

        #if there are no constraints on the modified time, then just gneerate random times
        else:
            modified_time = fake.date_between(start_date=default_startdate)
        return modified_time

    


    # PURPOSE: create random file size based on the presence of a query
    # self.selected_POSIX_md{file.size: ["target_min", "target_max", "command"]}
    # setting the default file size to between 1B - 10GB
    # command includes "equal", "range", "greater_than", "greater_than_equal", "less_than", less_than_equal"
    def generate_file_size(self, min_size: int = 1, max_size: int = 10737418240, file_type: bool=True) -> int:
        if "file.size" in self.selected_POSIX_md:
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
                    size = random.randint(random.randint(min_size, target_min-1), random.randint(target_max+1, max_size))

            # if command specifies a file greater than a certain size
            elif isinstance(target_max, int) and target_min == None:  
                if command == "greater_than":
                    delta = 1
                elif command == "greater_than_equal":
                    delta = 0

                if file_type:
                    size = random.randint(target_max, max_size)
                else:
                    size = random.randint(min_size, target_max-delta)

            # if command specifies a file less than a certain size
            elif isinstance(target_min, int) and target_max == None: 
                if command == "less_than":
                    delta = 1
                elif command == "less_than_equal":
                    delta = 0

                if file_type:
                    size = random.randint(min_size, target_min)
                else:
                    size = random.randint(target_min+delta, max_size)
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
            elif ambient_command == "gt":
                if file_type:
                    ambient_temp = random.randint(ambient_mintemp, overall_maxtemp)
                else:
                    ambient_temp = random.randint(overall_mintemp, ambient_mintemp-1)
            elif ambient_command == "lt":
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
    def generate_semantic_data(self, file_type):
        fake = Faker()
        if "content" in self.selected_semantic_md:
            if file_type:
                semantic = self.selected_semantic_md["content"]
            else: 
                semantic = fake.sentence(nb_words=random.randint(1, 5))
        else:
            semantic = fake.sentence(nb_words=random.randint(1, 5))
        return semantic

    # generate random data; random number of ascii characters
    def generate_random_data(self):
        ascii_chars = string.ascii_letters + string.digits
        random_data = ''.join(random.choices(ascii_chars, k = random.randint(1,500)))
        return random_data


    # GENERATE METADATA based on the data models 
    # create the record data based on record datamodel
    def create_record_data(self, UUID: str, timestamp: str, file_size: int, modified_time: str, file_name: str, path: str) -> dict:
        record_data = {
                "SourceIdentifier": {
                    "Identifier": UUID,
                    "Version": "1.0",
                },
                "Timestamp": timestamp,
                "Attributes": {
                    "Name": file_name,
                    "Path": path,
                    "st_mtime": modified_time,
                    "st_size": file_size
                },
                "Data": self.generate_random_data()
            }
        return record_data

    # create the timestamp data based on timestamp datamodel
    def create_timestamp_data(self, UUID: str, timestamp: str, description: str = "Timestamp") -> dict:
        timestamp_data = {
                "Label": UUID,
                "Value": timestamp,
                "Description": description
            }
        return timestamp_data

    # create the semantic attribute data based on semantic attribute datamodel
    def create_semantic_attribute(self, UUID_data: dict, file_type: bool) -> dict:
        semantic_attribute = {
            "Identifier": UUID_data,
            "Data": self.generate_semantic_data(file_type)
        }
        return semantic_attribute

    # create the UUID data based on the UUID data model
    def create_UUID_data(self, UUID: str, label: str = "IndalekoUUID") -> dict:
        uuid_data = {
            "Identifier": UUID,
            "Label": label
        }
        return uuid_data

    #helper function for setting truth attributes
    def define_truth_attribute(self, attribute, truth_file, truthlike_file, truth_attributes):
        if truth_file or (truthlike_file and attribute in truth_attributes):
            return True
        elif not truth_file or truthlike_file:
            return False


    # generates the filler file with attributes of target metadata:
    def generate_truthlike_metadata(self, current_filenum: int, max_num: int, key: str) -> dict:
        all_metadata = []
       
        for n in range(1, max_num): 
            truth_attributes = list(self.selected_POSIX_md.keys()) + list(self.selected_AC_md.keys()) + list(self.selected_semantic_md.keys())
            total_truth_attributes = len(truth_attributes)
            filler_truth_attributes = random.randint(0, total_truth_attributes-1)
            ic(truth_attributes)
            truth_attributes = random.sample(truth_attributes, k = filler_truth_attributes)

            key_name = f'{key} #{n}, truth-like attributes: {filler_truth_attributes}'

            
            general_time = self.generate_file_modified(file_type=self.define_truth_attribute("file.modified", truth_attributes))
            modified_time = general_time.strftime('%Y-%m-%d %H:%M:%S')
            timestamp = general_time.strftime('%Y-%m-%dT%H:%M:%SZ') # for now stating that timestamp is the same time as modified time
            
            UUID = self.create_UUID(n, file_type = False)
            file_size = self.generate_file_size(file_type= self.define_truth_attribute("file.size", truth_attributes))
            file_name = self.generate_file_name(file_type= self.define_truth_attribute("file.name", truth_attributes))
            path, URI = self.generate_dir_location(file_name, file_type= self.define_truth_attribute("file.directory", truth_attributes)) 
            
            record_data = self.create_record_data(UUID, timestamp, file_size, modified_time, file_name, path)
            timestamp_data = self.create_timestamp_data(UUID, timestamp)
            UUID_data = self.create_UUID_data(UUID)
            semantic_attributes_data = self.create_semantic_attribute(UUID_data, file_type= self.define_truth_attribute("content", truth_attributes))
            
            # Add the new metadata entry to the dictionary
            all_metadata.append({
                "Record": record_data,
                "URI": URI,
                "ObjectIdentifier": UUID,
                "Timestamps": [
                    timestamp_data
                ],
                "Size": file_size,
                "SemanticAttributes": [
                    semantic_attributes_data # could add in more
                ],
                "Label": key_name,
                "LocalIdentifier": current_filenum + n,
                "Volume": UUID,
                "PosixFileAttributes": "S_IFREG", #all are regular files
                "WindowsFileAttributes": "FILE_ATTRIBUTE_ARCHIVE", #setting as default
            })
        return all_metadata

    # generates the target metadata with the specified attributes based on the nubmer of matching queries to generate from config:
    def generate_metadata(self, current_filenum:int, max_num: int, key: str, file_type: bool, truth_like: bool) -> dict:
        all_metadata = []
        truthlike_attributes =[]
        ic(file_type)
        
        for n in range(1, max_num):
            key_name = f'{key} #{n}'

            if truth_like:
                total_truth_attributes = len(self.truth_attributes)
                filler_truth_attributes = random.randint(1, total_truth_attributes-1)
                truthlike_attributes = random.sample(self.truth_attributes, k = filler_truth_attributes)

                key_name += f', truth-like attributes: {truthlike_attributes}'

            general_time = self.generate_file_modified(file_type=self.define_truth_attribute("file.modified", file_type, truth_like, truthlike_attributes))
            modified_time = general_time.strftime('%Y-%m-%d %H:%M:%S')
            timestamp = general_time.strftime('%Y-%m-%dT%H:%M:%SZ') # for now stating that timestamp is the same time as modified time
            
            UUID = self.create_UUID(current_filenum + n, file_type = file_type)
            file_size = self.generate_file_size(file_type= self.define_truth_attribute("file.size", file_type, truth_like, truthlike_attributes))
            file_name = self.generate_file_name(file_type= self.define_truth_attribute("file.name", file_type, truth_like, truthlike_attributes))
            path, URI = self.generate_dir_location(file_name, file_type= self.define_truth_attribute("file.directory", file_type, truth_like, truthlike_attributes))
            
            record_data = self.create_record_data(UUID, timestamp, file_size, modified_time, file_name, path)
            timestamp_data = self.create_timestamp_data(UUID, timestamp)
            UUID_data = self.create_UUID_data(UUID)
            semantic_attributes_data = self.create_semantic_attribute(UUID_data, file_type= self.define_truth_attribute("content", file_type, truth_like, truthlike_attributes))
            
            # Add the new metadata entry to the dictionary
            all_metadata.append({
                "Record": record_data,
                "URI": URI,
                "ObjectIdentifier": UUID,
                "Timestamps": [
                    timestamp_data
                ],
                "Size": file_size,
                "SemanticAttributes": [
                    semantic_attributes_data # could add in more
                ],
                "Label": key_name,
                "LocalIdentifier": str(current_filenum + n),
                "Volume": UUID,
                "PosixFileAttributes": "S_IFREG", #all are regular files
                "WindowsFileAttributes": "FILE_ATTRIBUTE_ARCHIVE", #setting as default
            })
        return all_metadata

    #writes generated metadata in json file
    def write_json(self, target: dict, truth_like_filler: dict, filler: dict, json_path: str) -> None:
        dataset = target + truth_like_filler + filler
        with open(json_path, 'w') as json_file:
            json.dump(dataset, json_file, indent=4)
    
    # main function to run the metadata generator
    def generate_metadata_dataset(self) -> None:
        self.parse_config_json()
        # intiialize the synthetic dir locations
        self.initialize_local_dir()
        ic(self.saved_directory_path)

        self.truth_attributes = list(self.selected_POSIX_md.keys()) + list(self.selected_AC_md.keys()) + list(self.selected_semantic_md.keys())
        target = self.generate_metadata(0, self.n_matching_queries+1, 'Truth File', True, False)

        total_truth_attributes = len(self.truth_attributes) 
        remaining_files = self.n_metadata_records - self.n_matching_queries
        ic(self.n_metadata_records)
        ic(remaining_files)
        # only create truth-like files if the number of attributes is greater than one, otherwise, it becomes a truth file
        if total_truth_attributes > 1:
            truth_like_num = random.randint(0, remaining_files)
        else:
            truth_like_num = 0

        filler_num = remaining_files - truth_like_num
        ic(truth_like_num)
        ic(filler_num)

        truth_like_filler = self.generate_metadata(0, truth_like_num +1, 'Filler Truth-Like File', False, True)
        filler = self.generate_metadata(truth_like_num,  filler_num +1, 'Filler File', False, False)
        result = self.generate_geo_context(True)
        self.write_json(target, truth_like_filler, filler, self.metadata_json)

    #test the data model to see if in the right form
    # test with any of the following variables: target, truth_like_filler, filler
    def test_data_model(self, model):
        try:
            model_test = IndalekoObjecdtDataModel(**model[0])
            print("Valid input passed:", model_test)
        except ValidationError as e:
            print("Validation error for valid input:", e)
    
def main():
    config_path = "data_generator/dg_config.json"
    data_generator = Dataset_Generator(config_path)
    data_generator.generate_metadata_dataset()

if __name__ == '__main__':
    main()


