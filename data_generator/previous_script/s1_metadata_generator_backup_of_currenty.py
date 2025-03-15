import os, sys
from icecream import ic
from uuid import UUID
from datetime import datetime, timedelta
import random
import string
import json
import copy

import re
import uuid 
from collections import Counter
from faker import Faker
from geopy.distance import geodesic
from geopy.geocoders import Nominatim

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from data_models.i_object import IndalekoObjectDataModel
from data_models.record import IndalekoRecordDataModel
from data_models.timestamp import IndalekoTimestampDataModel
from data_models.semantic_attribute import IndalekoSemanticAttributeDataModel
from data_models.i_uuid import IndalekoUUIDDataModel
from data_models.machine_config import IndalekoMachineConfigDataModel
from data_models.source_identifier import IndalekoSourceIdentifierDataModel
from platforms.data_models.hardware import Hardware
from platforms.data_models.software import Software
from typing import Dict, Any, Tuple, Union, Callable

from activity.collectors.ambient.data_models.ambient_data_model import BaseAmbientConditionDataModel
from activity.collectors.ambient.data_models.smart_thermostat import ThermostatSensorData
from activity.collectors.ambient.music.base import AmbientMusicData
from activity.collectors.ambient.music.spotify import SpotifyAmbientData
from activity.collectors.ambient.smart_thermostat.ecobee import EcobeeAmbientData

from activity.context.data_models.context_data_model import IndalekoActivityContextDataModel
from activity.context.data_models.activity_data import ActivityDataModel
from activity.data_model.activity import IndalekoActivityDataModel
from activity.collectors.location.data_models.windows_gps_location_data_model import WindowsGPSLocationDataModel
from activity.collectors.location.data_models.windows_gps_satellite_data import WindowsGPSLocationSatelliteDataModel
from semantic.data_models.base_data_model import BaseSemanticDataModel

class Dataset_Generator():
    def __init__(self, config: dict, default_lower_timestamp = datetime(2000, 10, 25), default_upper_timestamp = datetime.now(), default_lower_filesize = 1, default_upper_filesize=10737418240):
        """
        A metadata dataset generator for creating synthetic dataset given a query
        Args: 
            config (dict): dictionary of the config attributes 
            default_lower_timestamp (datetime): the datetime specifying the lower bound for timestamp generation
            default_upper_timestamp (datetime): the datetime speciying the upper bound for timestamp generation
        """
        self.n_metadata_records = config["n_metadata_records"]
        self.metadata_json = config["output_json"]
        self.n_matching_queries = config["n_matching_queries"]
        self.default_lower_timestamp = default_lower_timestamp
        self.default_upper_timestamp = default_upper_timestamp
        self.default_lower_filesize = default_lower_filesize
        self.default_upper_filesize = default_upper_filesize
        self.faker = Faker()
        self.earliest_endtime = []
        self.earliest_starttime = []

        self.saved_directory_path = {"truth.directory": {}, "filler.directory": {}}

        self.saved_geo_loc = {}
    
    def write_json(self, dataset: dict, json_path: str) -> None:
        """
        Writes the generated metadata to a json file
        """
        with open(json_path, 'w') as json_file:
            json.dump(dataset, json_file, indent=4)


    def set_selected_md_attributes(self, md_attributes: Dict[str, Any]) -> None:
        """
        Sets the selected metadata attributes given the attribute dictionary
        Args: 
            md_attributes (dict): dictionary of the attributes populated after query extraction
        """
        self.selected_md_attributes = md_attributes
        self.selected_POSIX_md = md_attributes.get("Posix", {})
        self.selected_AC_md = md_attributes.get("Activity", {})
        self.selected_semantic_md = md_attributes.get("Semantic", {})
    
    def convert_dictionary_times(self, selected_md_attributes: Dict[str, Any], to_timestamp: bool) -> Dict[str, Any]:
        """
        Convert time to posix timstamps given a dictionary that the LLM cannot handle properly:
        Args:
            selected_md_attributes (Dict[str, Any]): The dictionary of attributes
        Returns:
            Dict[str, Any]: The converted attributes dictionary
        """
        new_md_attributes = copy.deepcopy(selected_md_attributes)
        if "Posix" in new_md_attributes:        
            posix = new_md_attributes["Posix"]
            if "timestamps" in posix:
                for timestamp_key, timestamp_data in posix["timestamps"].items():
                    starttime, endtime = self._convert_time_timestamp(timestamp_data, to_timestamp)
                    posix["timestamps"][timestamp_key]["starttime"] = starttime
                    posix["timestamps"][timestamp_key]["endtime"] = endtime 
        return new_md_attributes

    # Helper function for convert_dictionary_times()
    def _convert_time_timestamp(self, timestamps: dict, to_timestamp: bool) -> Tuple[Union[Any, datetime], Union[Any, datetime]]:
        """
        Converts the time from string to timestamps
        """

        starttime = timestamps["starttime"]
        endtime = timestamps["endtime"]
        if to_timestamp:
            starttime = starttime.timestamp()
            endtime = endtime.timestamp()
        else: 
            starttime = self._convert_str_datetime(starttime)
            endtime = self._convert_str_datetime(endtime)

            self.earliest_endtime.append(endtime)
            self.earliest_starttime.append(starttime)        
        self.earliest_endtime.sort()
        self.earliest_starttime.sort()
        return starttime, endtime
    
    def generate_metadata_dataset(self):
        """
        Main function to generate metadata datasets
        """
        # initialize the synthetic dir locations
        self._initialize_local_dir()

        # calculate the total number of truth metadata attributes
        self.truth_attributes = self._check_return_dict(self.selected_POSIX_md) + self._check_return_dict(self.selected_AC_md) + self._check_return_dict(self.selected_semantic_md)
        total_truth_attributes = len(self.truth_attributes)

        # get the total number of truth-like metadata
        # only create truth-like metadata if the number of attributes is greater than one, otherwise, it becomes a truth file
        remaining_files = self.n_metadata_records - self.n_matching_queries
        
        if total_truth_attributes > 1:
            self.truth_like_num = random.randint(0, remaining_files)
        else:
            self.truth_like_num = 0

        filler_num = remaining_files - self.truth_like_num

        target_record_md, target_semantics_md, target_geo_activity_md, target_temp_activity_md,target_music_activity_md, target_machine_config = self._generate_metadata(0, self.n_matching_queries+1, 'Truth File', True, False)
        truth_like_filler_record_md, truth_like_filler_semantics_md, truth_like_filler_geo_activity_md, truth_like_filler_temp_activity_md, truth_like_filler_music_activity_md, truth_like_machine_config = self._generate_metadata(0, self.truth_like_num +1, 'Filler Truth-Like File', False, True)
        filler_record_md, filler_semantics_md, filler_geo_activity_md, filler_temp_activity_md, filler_music_activity_md, filler_machine_config = self._generate_metadata(self.truth_like_num,  filler_num +1, 'Filler File', False, False)
        
        all_record_md = target_record_md + truth_like_filler_record_md + filler_record_md
        all_semantics_md = target_semantics_md + truth_like_filler_semantics_md + filler_semantics_md
        all_geo_activity_md = target_geo_activity_md + truth_like_filler_geo_activity_md + filler_geo_activity_md
        all_temp_activity_md = target_temp_activity_md + truth_like_filler_temp_activity_md + filler_temp_activity_md
        all_music_activity_md = target_music_activity_md + truth_like_filler_music_activity_md + filler_music_activity_md

        all_machine_config_md = target_machine_config + truth_like_machine_config + filler_machine_config

        metadata_stats = {"truth": self.n_matching_queries, "filler": remaining_files, "truth-like":self.truth_like_num}
        return all_record_md, all_geo_activity_md, all_temp_activity_md, all_music_activity_md,  all_machine_config_md, metadata_stats

    def _check_return_dict(self, dictionary: Dict[str, Any]):
        """
        checks and return the keys of the dictionary as a list
        """
        if dictionary == None:
            return []
        else:
            return list(dictionary.keys())

    def _initialize_local_dir(self):
        """
        Initializes and saves the local directories to self.saved_directory_path; run only once
        Populates the self.saved_directory_path = {"truth.directory": {"path": str, "files": Counter(str)}, "filler.directory" {"path":, "files": Counter(str)}: list}}
        """
        num_directories = random.randint(3, 8)
        max_depth = random.randint(3,5)
        parent_dir = "/home/user"
        truth_parent_loc = ""
        # if the there is a query related to the directory and the pathing has not been initialized create the directories
        if "file.directory" in self.selected_POSIX_md:
            truth_parent_loc = self.selected_POSIX_md["file.directory"]["location"]
            if truth_parent_loc == "local":
                truth_path_name = self.selected_POSIX_md["file.directory"]["local_dir_name"]
                # if the is_truth_file is a truth file, create path for truth file directories
                self._generate_local_path(parent_dir, num_directories, max_depth, directory_name = truth_path_name)
            else: # if remote  just generate random directory
                self._generate_local_path(parent_dir, num_directories, max_depth)
        else: # no queries related to file directories; generate random directory
            self._generate_local_path(parent_dir, num_directories, max_depth)
    
    # helper for initialize_local_dir():
    def _generate_local_path(self, base_dir: str, num_directories: int, max_depth: int, directory_name: str = None) -> None:
        """
        Generate random path to directories within a parent dir based on base_dir, num_directories, max_depth and if available, directory_name recursively
        Only runs once during initialization
        Adapted from Tony's code from metadata.py
        """
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
                    # Generate a random subdirectory name or choose truth file path name
                    subdir_name = ''.join(random.choices(string.ascii_lowercase, k = random.randint(1,8)))
                    subdir_path = os.path.join(current_dir, subdir_name)
                    generated_paths.append(subdir_path)
                    create_dir_recursive(subdir_path, current_depth + 1)

        create_dir_recursive(base_dir, 1)

        if directory_name != None:
            self.saved_directory_path["truth.directory"]["path"] = random.choice(generated_paths) + "/" + directory_name
            self.saved_directory_path["truth.directory"]["files"] = Counter()
        self.saved_directory_path["filler.directory"]["path"] = generated_paths
        self.saved_directory_path["filler.directory"]["files"] = Counter()
    

    def _generate_file_name(self, is_truth_file: bool, has_semantic_attr: bool) -> str:
        """
        Generates a file_name for given file
        Args: is_truth_file (bool): the type of file it is
            self.selected_POSIX_md{file.name: {"pattern":str, "command":str, "extension":str}}
            commands include: "starts", "ends", "contains"
        Return (str): returns the file name 
        """
        command, pattern = "", ""
        true_extension = None
        n_filler_letters = random.randint(1, 10)
        file_extension = [".pdf", ".doc",".docx", ".txt", ".rtf", ".xls", ".xlsx", ".csv", ".ppt", ".pptx", ".jpg", ".jpeg", ".png", ".gif", ".tif", ".mov", ".mp4", ".avi", ".mp3", ".wav", ".zip", ".rar"]
        text_file_extension = [".pdf", ".doc", ".docx", ".txt", ".rtf", ".csv", ".xls", ".xlsx", ".ppt", ".pptx"]
        #if the file name is part of the query, extract the appropriate attributes and generate title
        if "file.name" in self.selected_POSIX_md:
            if "pattern" in self.selected_POSIX_md["file.name"]:
                pattern = self.selected_POSIX_md["file.name"]["pattern"]
                command = self.selected_POSIX_md["file.name"]["command"]
                avail_text_file_extension = text_file_extension

            if "extension" in self.selected_POSIX_md["file.name"]:
                true_extension = self.selected_POSIX_md["file.name"]["extension"]
                if isinstance(true_extension, list):
                    file_extension = list(set(file_extension) - set(true_extension))
                    avail_text_file_extension = list(set(text_file_extension) - set(true_extension))
                else: 
                    file_extension.remove(true_extension)
                    if true_extension in text_file_extension:
                        avail_text_file_extension.remove(true_extension)


            if is_truth_file: 
                # choose file extension
                if "extension" in self.selected_POSIX_md["file.name"]:# if no extension specified, then randomly select a file extension
                    if isinstance(true_extension, list):
                        true_extension = random.choice(true_extension)
                elif self.selected_semantic_md: # if semantic content exists, then should be a text file
                    true_extension = random.choice(text_file_extension)
                else:
                    true_extension = random.choice(file_extension)
                     
                # create file name based on commands
                if command == "exactly":
                    return pattern + true_extension
                elif command == "starts":
                    return pattern + ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + true_extension
                elif command == "ends":
                    return ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + pattern + true_extension
                elif command == "contains":
                    return ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + pattern + ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + true_extension
                else:
                    return ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + true_extension
                
            else: # if a filler metadata, generate random title that excludes all letters specified in the char pattern
                extension = random.choice(file_extension)
            
            allowed_pattern = list(set(string.ascii_letters) - set(pattern.upper()) - set(pattern.lower()))
            return ''.join(random.choices(allowed_pattern, k=n_filler_letters)) + extension

        else: #if no query specified for title, but semantic context exists, choose a text file extension
            if has_semantic_attr or (is_truth_file and self.selected_semantic_md):
                extension = random.choice(text_file_extension)
            else: # randomly create a title with any extension
                extension = random.choice(file_extension)
            title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + extension
            return title

    def _generate_dir_location(self, file_name: str, is_truth_file: bool=True) -> Tuple[str, str, str]:
        """
        Generates a directory location for the metadata
        self.selected_POSIX_md["file.directory"] = [location, directory_name (optional, for local only)]
        location: where it is stored; local or remote (google drive, drop box, icloud, local)
        RETURN: list consisting of path and URI and updated file name to remote or local storage
   
        """
        # URIs/URLs to local computer or cloud storage services
        file_locations = {
           "google_drive": "https://drive.google.com",
           "dropbox": "https://www.dropbox.com",
           "icloud": "https://www.icloud.com",
           "local": "file:/"
        }
        # RUN after initialization:
        if "file.directory" in self.selected_POSIX_md and is_truth_file:
            truth_parent_loc = self.selected_POSIX_md["file.directory"]["location"]
            file_counter = self.saved_directory_path["truth.directory"]["files"]

            if truth_parent_loc == "local": # if file dir specified, create truth file at that dir
                path = self.saved_directory_path["truth.directory"]["path"] + "/"
                counter_key = path+file_name
                if counter_key in file_counter:
                    file_counter[counter_key] += 1
                    updated_file_name = self._change_name(file_name= file_name, count = file_counter[counter_key])
                    path += updated_file_name
                    URI = file_locations[truth_parent_loc] + path
                    return [path, URI, updated_file_name]
                else:
                    file_counter.update({counter_key: 0})
                    path += file_name
                    URI = file_locations[truth_parent_loc] + path
                    return [path, URI, file_name]

            elif is_truth_file and truth_parent_loc in file_locations.keys(): # if remote dir specified, create file at that dir
                path = self._generate_remote_path(truth_parent_loc, file_name)
                URI = file_locations[truth_parent_loc] + path
            return [path, URI, file_name]

        #for filler files or truth files with no file attributes specified
        elif not is_truth_file and "file.directory" in self.selected_POSIX_md:
            truth_parent_loc = self.selected_POSIX_md["file.directory"]["location"]
            del file_locations[truth_parent_loc]

        # not queried at this point and file type doesn't matter; generate any file path (local or remote)
        random_location = random.choice(list(file_locations.keys()))
        if random_location == "local":
            file_counter = self.saved_directory_path["filler.directory"]["files"]
            path = random.choice(self.saved_directory_path["filler.directory"]["path"]) + "/"
            counter_key = path+file_name
            if counter_key in file_counter:
                file_counter[counter_key] += 1
                updated_file_name = self._change_name(file_name= file_name, count = file_counter[counter_key])
                path += updated_file_name
                URI = file_locations[random_location] + path
                return [path, URI, updated_file_name]
            else:
                file_counter.update({counter_key: 0})
                path += file_name
                URI = file_locations[random_location] + path
                return [path, URI, file_name]
        else:
            path = self._generate_remote_path(random_location, file_name)
            URI = file_locations[random_location] + path

        return path, URI, file_name

        
    def _change_name(self, file_name:str, count:int) -> str:
        """changes name to avoid duplicate files in the same path"""
        base_name, ext = os.path.splitext(file_name)
        return f'{base_name}({count}){ext}'

    # helper functions for generate_dir_location
    def _generate_remote_path(self, service_type: str, file_name: str) -> str:
        """
        Generates path to a remote file location e.g., google drive, dropbox, icloud
        """
        list_alphanum = string.ascii_letters + string.digits
        # Randomly choose characters to form the id
        file_id = ''.join(random.choices(list_alphanum, k=random.randint(3,6)))
        local_file_locations = {
           "google_drive": "/file/d/{file_id}/view/view?name={file_name}",
           "dropbox": "/s/{file_id}/{file_name}?dl=0",
           "icloud": "/iclouddrive/{file_id}/{file_name}"
        }
        remote_path = local_file_locations[service_type].format(file_id = file_id, file_name = file_name)
        return remote_path

    def _generate_timestamps(self, is_truth_file: bool=True) -> Dict[str, datetime]:
        """
        Generates birthtime, modifiedtime, accessedtime, and changedtime for the specified file:
        Args: is_truth_file (bool): file type 
        Returns (Dict[str, datetime]): {birthtime: datetime, modifiedtime: datetime, accessedtime: datetime, changedtime: datetime}
        """
        stamp_labels = {"modified", "accessed", "changed"}
        birthtime = None
        latest_timestamp_of_three = None
        timestamps = {}
        # check whether the query is pertaining to specific timestamp queries
        if "timestamps" in self.selected_POSIX_md:
            query = self.selected_POSIX_md["timestamps"]
            selected_timestamps = set(query.keys())
            non_selected_timestamps = stamp_labels - selected_timestamps
            if "birthtime" in query: # specifically checks for birthtime since other timestamps shouldn't be earlier than the birthtime
                birthtime_query = query["birthtime"]
                birthtime = self._generate_queried_timestamp(birthtime_query["starttime"], birthtime_query["endtime"], birthtime_query["command"], default_startdate=self.default_lower_timestamp, is_truth_file = is_truth_file, is_birthtime=True)
                timestamps["birthtime"] = birthtime
                # if there queries other than the birthtime, iterate over each of the timestamps
                for timestamp in stamp_labels: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                    if timestamp in selected_timestamps:
                        timestamps[timestamp] = self._generate_queried_timestamp(query[timestamp]["starttime"], query[timestamp]["endtime"], query[timestamp]["command"], default_startdate = birthtime, is_truth_file=is_truth_file)
                    else: # if type of timestamp not chosen, either generate a random timestamp within bounds or choose an existing timestamp
                        timestamps[timestamp] = self._choose_existing_or_random(timestamps, birthtime, self.default_upper_timestamp)
            else:
                for timestamp in selected_timestamps: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                    timestamps[timestamp] = self._generate_queried_timestamp(query[timestamp]["starttime"], query[timestamp]["endtime"], query[timestamp]["command"], default_startdate = self.default_lower_timestamp, is_truth_file=is_truth_file)
                for timestamp in non_selected_timestamps:
                    timestamps[timestamp] = self._choose_existing_or_random(timestamps, self.default_lower_timestamp, self.default_upper_timestamp)

                #birthtime has to be <= to the other populated timestamps
                latest_timestamp_of_three = min(timestamps.values())
                birthtime = self._generate_random_timestamp(lower_bound = self.default_lower_timestamp, upper_bound = latest_timestamp_of_three) 
                timestamps["birthtime"] = birthtime

        else:
            birthtime = self._generate_random_timestamp(lower_bound = self.default_lower_timestamp, upper_bound=self.default_upper_timestamp)
            timestamps["birthtime"] = birthtime
            for timestamp in stamp_labels: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                timestamps[timestamp] = self._choose_existing_or_random(timestamps, birthtime, self.default_upper_timestamp)
        return timestamps

    # helper for _generate_timestamps:
    def _choose_existing_or_random(self, timestamps, lower_bound, upperbound) -> datetime:
        """chooses an existing timstamp that is in the dict or creates a random timestamp within bounds"""
        randomtime = self._generate_random_timestamp(lower_bound = lower_bound, upper_bound = upperbound)
        existing_timestamp = random.choice(list(timestamps.values()))
        return random.choice([existing_timestamp, randomtime])

    # helper functions for generate_timestamps():
    def _generate_random_timestamp(self, lower_bound:datetime, upper_bound:datetime) -> datetime:
        """
        Generates a random timestamp within the bounds specified
        Args:
            lower_bound (datetime) birth time for m/a/c timestamps or default "2000-10-25" for birthtime
            upper_bound (datetime) latest timestamp for birthtime or current datetime for m/a/c timestamps
        Returns:
            (datetime): a randomly generated timestamp
        """
        
        random_time = self.faker.date_time_between(start_date = lower_bound, end_date = upper_bound)
        return random_time

    def _generate_queried_timestamp(self, starttime:datetime, endtime:datetime, command:str, default_startdate:datetime, is_truth_file:bool = True, is_birthtime: bool = False) -> datetime:
        """Generates timestamp based on file type; default_truth_startdate is either the self.default_lower_timestamp or the birthtime (if birthtime already set)"""
        filler_delta = 2
        time_delta = timedelta(hours = filler_delta)
        timestamp = None
        # check errors that can arise for str parameters
        if starttime > datetime.now() or endtime > datetime.now():
            raise ValueError("The timestamp you have queried is in the future, please check again.")
        elif starttime > endtime:
            raise ValueError("The starttime cannot be more recent than the endtime")
        elif is_truth_file and default_startdate > endtime:
            raise ValueError("The default_startdate cannot be more recent than the endtime")
        elif self.default_lower_timestamp == self.default_upper_timestamp:
            raise ValueError("The absolute lower bound date cannot be the same time as the date right now")
        elif self.default_lower_timestamp == starttime and self.default_upper_timestamp == endtime:
            raise ValueError("Invalid range, please increase the bounds or decrease the range to within the bounds")
        elif is_birthtime and starttime > self.earliest_endtime[0]:
            raise ValueError("The earliest starttime cannot be earlier than the birthtime starttime")
        elif self.default_lower_timestamp > starttime:
            raise ValueError("The absolute lower bound cannot be greater than the starttime")
         
        elif starttime == endtime and command == "equal":
            if starttime < default_startdate: 
                raise ValueError("The starttime for the timestamps cannot be earlier than the birthtime/default")
            if is_truth_file and default_startdate <= starttime:
                timestamp = starttime
            if not is_truth_file:
                # for birthtime timestamps (choose the lowest/most earliest possible time to not have time earlier than the other timestamps)
                lower = self.faker.date_time_between(start_date = self.default_lower_timestamp, end_date=starttime-time_delta)
                upper = self.faker.date_time_between(start_date = starttime+time_delta)
                # the earliest starttime is within the bounds:
                if is_birthtime and self.default_lower_timestamp + time_delta <= self.earliest_starttime[0] <= starttime:
                    timestamp = self.faker.date_time_between(start_date=self.default_lower_timestamp, end_date=self.earliest_starttime[0]-time_delta)
                # case 2: the earliest starttime is not within the bounds 
                elif is_birthtime and self.default_lower_timestamp + time_delta <= self.earliest_starttime[0]:
                    timestamp = self.faker.date_time_between(start_date=starttime+time_delta, end_date = self._find_next_earliest_endtime(starttime)-time_delta) # can overwrite endtime
                elif is_birthtime:
                    raise ValueError("Cannot generate birthtime timestamp for truth file")
                #for timestamps other than birthtime:
                if not is_birthtime and default_startdate == starttime: #if birthtime is greater than the equal
                    timestamp = self.faker.date_time_between(start_date = default_startdate + timedelta(hours = filler_delta))
                elif not is_birthtime and default_startdate > starttime: #if birthtime is greater than the equal
                    timestamp = self.faker.date_time_between(start_date = default_startdate)
                elif not is_birthtime and default_startdate < starttime:
                    lower = self.faker.date_time_between(start_date = default_startdate, end_date = starttime-time_delta)
                    if starttime+time_delta < self.default_upper_timestamp:
                        upper = self.faker.date_time_between(start_date = starttime+time_delta)
                        timestamp = random.choice([upper, lower])
                    elif starttime+time_delta >= self.default_upper_timestamp:
                        timestamp = lower
                elif not is_birthtime:
                    raise ValueError("cannot form timestamp for filler file")
        #if the starttime and endtime are not equal and are not lists, then choose a date within that range
        # under the assumption that starttime < endtime
        elif starttime != endtime and command == "range": # if is a birthtime, should take on values that are 
            # if it is a birthtime and a truth file, find the earliest time possible
            if is_truth_file and is_birthtime and default_startdate <= starttime and starttime <= self.earliest_starttime[0] <= endtime: # only for the birthtime to make birthtime earlier 
                timestamp = self.faker.date_time_between(start_date=starttime, end_date=self.earliest_starttime[0])
            elif is_truth_file and is_birthtime and default_startdate <= starttime and self.earliest_starttime[0] < starttime:
                timestamp = self.faker.date_time_between(start_date=starttime, end_date=self._find_next_earliest_endtime(starttime))
            elif is_truth_file and is_birthtime:
                raise ValueError("cannot generate truthfile timestamp.")

            if is_truth_file and not is_birthtime and starttime <= default_startdate <= endtime: 
                timestamp = self.faker.date_time_between(start_date=default_startdate, end_date=endtime)     
            elif is_truth_file and not is_birthtime and starttime > default_startdate: 
                timestamp = self.faker.date_time_between(start_date=starttime, end_date=endtime)
            # elif is_truth_file and not is_birthtime and endtime < default_startdate: 
            #     raise ValueError("The birthtime cannot be greater than the other timestamps")
            elif is_truth_file and not is_birthtime:
                raise ValueError("Absolute lower bound date cannot be more recent than the endtime")
            
            if not is_truth_file: 
                # for filler file birhttime timestamps:
                if is_birthtime and self.default_lower_timestamp <= starttime-time_delta and self.default_lower_timestamp + time_delta <= self.earliest_starttime[0] <= starttime:
                    timestamp = self.faker.date_time_between(start_date = self.default_lower_timestamp, end_date=self.earliest_starttime[0]-time_delta)
                elif is_birthtime and self.default_upper_timestamp >= endtime + time_delta:
                    timestamp = self.faker.date_time_between(start_date=endtime + time_delta, end_date=self._find_next_earliest_endtime(starttime)-time_delta)
                elif is_birthtime and not is_truth_file:
                    raise ValueError("cannot generate birthtime timestamp for filler files")
                
                lower = self.faker.date_time_between(start_date = default_startdate, end_date=starttime-time_delta)
                upper = self.faker.date_time_between(start_date = endtime + time_delta)
                # for none birthtime timestamps
                if not is_birthtime and endtime < default_startdate <= self.default_upper_timestamp:
                    timestamp = self.faker.date_time_between(start_date = endtime)
                elif not is_birthtime and starttime <= default_startdate <= endtime:
                    timestamp = upper
                elif not is_birthtime and self.default_lower_timestamp <= default_startdate <= starttime:
                    timestamp = random.choice([lower, upper])
                elif not is_birthtime and not is_truth_file:
                    raise ValueError("Cannot generate timestamps for filler files")
        else:
            raise ValueError("Error in parameters or command: Please check the query once more.")
        return timestamp.replace(microsecond=0)
        
    def _find_next_earliest_endtime(self, starttime) -> datetime:
        for date in self.earliest_endtime:
            if starttime <= date:
                return date
            else:
                raise ValueError("there are no times that work")
        
    # general helper function for _generate_queried_timestamp() and _convert_time_timestamp():
    def _convert_str_datetime(self, time: str) -> datetime:
        """
        Converts a str date from "YYYY-MM-DD" to datetime; used within time generator functions
        """
        splittime = re.split("[-T:]", time)
        year = int(splittime[0])
        month = int(splittime[1])
        day = int(splittime[2])

        hour = int(splittime[3])
        minute = int(splittime[4])
        second = int(splittime[5])

        time = datetime(year, month, day, hour, minute, second)

        # if requested time is sooner than today's day, set it to the time to now
        if time > datetime.now():
            time = datetime.now()
        return time

    def generate_file_size(self, is_truth_file: bool=True) -> int:
        """
        Creates random file size given the is_truth_file
        self.selected_POSIX_md{file.size: ["target_min", "target_max", "command"]}
        setting the default file size to between 1B - 10GB
        command includes "equal", "range", "greater_than", "greater_than_equal", "less_than", less_than_equal
        """
        if "file.size" in self.selected_POSIX_md:
            filler_delta = 1
            delta = 0
            target_min = self.selected_POSIX_md["file.size"]["target_min"] 
            target_max = self.selected_POSIX_md["file.size"]["target_max"]
            command = self.selected_POSIX_md["file.size"]["command"]

            if target_max == self.default_upper_filesize and target_min == self.default_lower_filesize:
                raise ValueError("The range cannot be the whole boundary from ", target_min, " to ", target_max)
            elif target_min > target_max:
                raise ValueError(f"The target max {target_min} cannot be greater than the target max {target_max}")

            # if the target_min/max is a list and is the same as the target_max choose a random size from the list
            if isinstance(target_min, list) and isinstance(target_max, list) and command == "equal":
                if is_truth_file:
                    return random.choice(target_min)
                else:
                    return self._check_return_value_within_range(self.default_lower_filesize, self.default_upper_filesize, target_min[0], target_min[-1], random.randint, 1)

            # if the target_min/max is not a list but is the same as the target_max then just choose that file size
            elif target_min == target_max and command == "equal":
                if is_truth_file:
                    return target_min
                else:
                    return self._check_return_value_within_range(self.default_lower_filesize, self.default_upper_filesize, target_min, target_min, random.randint, 1)

            #if command specifies getting the range between two values
            elif target_min != target_max and command == "range":
                if is_truth_file:
                    return random.randint(target_min, target_max)
                else:
                    return self._check_return_value_within_range(self.default_lower_filesize, self.default_upper_filesize, target_min, target_max,  random.randint, 1)

            # if command specifies a file greater than a certain size
            elif isinstance(target_max, int) and "greater" in command:
                if command == "greater_than":
                    delta = 1
                    filler_delta = 0

                if is_truth_file:
                    return random.randint(target_max+delta, self.default_upper_filesize)
                else:
                    return random.randint(self.default_lower_filesize, target_max-filler_delta)

            # if command specifies a file less than a certain size
            elif isinstance(target_max, int) and "less" in command:
                if command == "less_than":
                    delta = 1
                    filler_delta = 0

                if is_truth_file:
                    return random.randint(self.default_lower_filesize, target_max-delta)
                else:
                    return random.randint(target_max+filler_delta, self.default_upper_filesize)
        # if there are no specified queries, create a random file size
        else:
            return random.randint(self.default_lower_filesize, self.default_upper_filesize)
   
    def _generate_metadata(self, current_filenum: int, max_num: int, key: str, is_truth_file: bool, truth_like: bool) -> Tuple[list[Dict[str,Any]], list[Dict[str,Any]], list[Dict[str,Any]], list[Dict[str,Any]], list[Dict[str,Any]], list[Dict[str,Any]]]:
        """Generates the target metadata with the specified attributes based on the nubmer of matching queries to generate based on config:"""
        all_metadata, all_semantics, all_geo_activity, all_temp_activity, all_music_activity, all_machine_configs = [], [], [], [], [], []

        for n in range(1, max_num):
            truthlike_attributes = self._get_truthlike_attributes(truth_like)
            if(truth_like):
                ic(truthlike_attributes)
            # if there are no truth like attributes chosen, set truth_like to False and decrement
            # if not truthlike_attributes and not is_truth_file:
            #     truth_like = False
            #     self.truth_like_num -= 1
            key_name = self._generate_key_name(key, n, truth_like, truthlike_attributes)
            has_semantic = self._has_semantic_attr(truthlike_attributes)

            file_size, file_name, path, URI, IO_UUID = self._generate_file_info(current_filenum, n, is_truth_file, truth_like, truthlike_attributes, has_semantic)
            timestamps = self._generate_timestamps(is_truth_file=self._define_truth_attribute("timestamps", is_truth_file, truth_like, truthlike_attributes))
            attribute = self._generate_file_attributes(file_name, path, timestamps, file_size)
            semantic_attributes_data = self._create_semantic_attribute(file_name.split(".")[-1], timestamps["modified"].strftime("%Y-%m-%dT%H:%M:%S"), is_truth_file, truth_like, truthlike_attributes, has_semantic)
            record_data = self._generate_record_data(IO_UUID, attribute)

            i_object_data = self._generate_i_object_data(record_data, IO_UUID, timestamps, URI, file_size, semantic_attributes_data, key_name, current_filenum + n)
            semantics_md = self._generate_semantic_data(record_data, IO_UUID, semantic_attributes_data)
            geo_activity_context, temp_activity_context, music_activity_context = self._generate_activity_contexts(record_data, is_truth_file, truth_like, truthlike_attributes, timestamps)
            machine_config = self._generate_machine_config(record_data)

            # appending the objects to their lists
            all_metadata.append(json.loads(i_object_data.json()))
            all_semantics.append(json.loads(semantics_md.json()))
            all_geo_activity.append(json.loads(geo_activity_context.json()))
            all_temp_activity.append(json.loads(temp_activity_context.json()))
            all_music_activity.append(json.loads(music_activity_context.json()))
            all_machine_configs.append(json.loads(machine_config.json()))

        return all_metadata, all_semantics, all_geo_activity, all_temp_activity, all_music_activity, all_machine_configs
    
    # Helper functions for creating ambient music activity context:
    def _generate_ambient_music_context(self, record_kwargs: IndalekoRecordDataModel, timestamps: Dict[str, datetime], is_truth_file: bool) -> Union[AmbientMusicData, SpotifyAmbientData]:
        music_md = self._generate_general_music_data(record_kwargs, is_truth_file, timestamps)
        if (music_md.source == "spotify") or ("ambient_music" in self.selected_AC_md and "spotify" in self.selected_AC_md["ambient_music"]):
            return self._generate_spotify_music_data(music_md, is_truth_file)    
        
        return music_md

    def _generate_spotify_music_data(self, base_md: AmbientMusicData, is_truth_file: bool) -> SpotifyAmbientData:
        """generates spotify music data"""
        devices = ["Computer","Smartphone","Speaker","TV","Game_Console","Automobile","Unknown"]
        artist_id = self._create_spotify_id(False, "artist")
        track_id = self._create_spotify_id(False, "track")
        device_type = random.choice(devices)

        if "ambient_music" in self.selected_AC_md:
            music_dict = self.selected_AC_md["ambient_music"]
            if "track_name" in music_dict:
                track_id = self._create_spotify_id(is_truth_file, "track", music_dict["track_name"])
            if "artist_name" in music_dict:
                artist_id = self._create_spotify_id(is_truth_file, "artist", music_dict["artist_name"])
            if "device_type" in music_dict and is_truth_file:
                device_type = self._choose_random_element(is_truth_file, music_dict["device_type"], devices)
         
        return SpotifyAmbientData(
                                    **base_md.dict(), 
                                    track_id = track_id, 
                                    artist_id = artist_id, 
                                    device_name= "My " + device_type, 
                                    device_type= device_type, 
                                    shuffle_state= random.choice([True, False]), 
                                    repeat_state = random.choice(["track", "context", "off"]), 
                                    danceability= self._generate_spotify_score(), 
                                    energy=self._generate_spotify_score(), 
                                    valence=self._generate_spotify_score(), 
                                    instrumentalness=self._generate_spotify_score(), 
                                    acousticness=self._generate_spotify_score())
    
    def _create_spotify_id(self, is_truth_file, prefix:str, name:str = None):
        """Generates the spotify artist or track id"""
        heading = "spotify:" + prefix + ":"
        if is_truth_file:
            changed_name = name.replace(" ", "")
            digits = 22 - len(changed_name)
            space_filler = '0' * digits
            return heading + changed_name + space_filler
        else:
            return heading + ''.join(random.choices(string.ascii_letters + string.digits, k=22))
        
    def _generate_spotify_score(self, lower:float = 0.000, upper: float = 1.000) -> float:
        """generate a random spotify score for the given track"""
        return round(random.uniform(lower, upper), 3)

    def _generate_general_music_data(self, record_kwargs: IndalekoRecordDataModel, is_truth_file: bool, timestamps: Dict[str, datetime]) -> AmbientMusicData:
        """generates the general music activity context data"""

        music_sources = ['spotify', 'youtube music', "apple music"]

        timestamp = self._generate_ac_timestamp(is_truth_file, timestamps, "ambient_music")
        track_name = self.faker.first_name()
        album_name = self.faker.name()
        artist_name = self.faker.name()
        # can make specfiic, although, tdon't think necessary
        track_duration_ms = random.randint(10000, 300000)
        playback_position_ms = random.randint(0, track_duration_ms)
        source = random.choice(music_sources)
        is_currently_playing = random.choice([True, False])

        if "ambient_music" in self.selected_AC_md:
            music_dict = self.selected_AC_md["ambient_music"]
            if "source" in music_dict:
                source = self._choose_random_element(is_truth_file, music_dict["source"], music_sources)
            if "track_name" in music_dict and is_truth_file:
                track_name = music_dict["track_name"]
            if "artist_name" in music_dict and is_truth_file:
                artist_name = music_dict["artist_name"]
            if "album_name" in music_dict and is_truth_file:
                album_name = music_dict["album_name"]
            if "playback_position_ms" in music_dict and is_truth_file:
                playback_position_ms = music_dict["playback_position_ms"]
            if "track_duration_ms" in music_dict and is_truth_file:
                track_duration_ms = music_dict["track_duration_ms"]
            if "is_currently_playing" in music_dict and is_truth_file:
                is_currently_playing = self._choose_random_element(is_truth_file, music_dict["is_currently_playing"], [True, False]) 
       
        track_name_identifier = IndalekoUUIDDataModel(Identifier=uuid.uuid4(), Label="track_name")
        artist_name_identifier = IndalekoUUIDDataModel(Identifier=uuid.uuid4(), Label="artist_name")
        semantic_attributes = [
                IndalekoSemanticAttributeDataModel(Identifier=track_name_identifier, Data=track_name),
                IndalekoSemanticAttributeDataModel(Identifier=artist_name_identifier, Data=artist_name)
                ]

        return AmbientMusicData(Record=record_kwargs,
                                Timestamp=timestamp,
                                SemanticAttributes=semantic_attributes, 
                                source=source,
                                track_name=track_name,
                                artist_name=artist_name,
                                album_name = album_name,
                                is_playing=is_currently_playing,
                                playback_position_ms=playback_position_ms,
                                track_duration_ms=track_duration_ms,                                
                                )

    # Helper functions for creating ambient temperature activity context within generate_metadata():
    def _generate_smart_thermostat_data(self, record_kwargs: IndalekoRecordDataModel, timestamps: Dict[str, datetime], is_truth_file: bool) -> EcobeeAmbientData:
        allowed_chars = string.ascii_letters + string.digits
        device_id = ''.join(random.choices(allowed_chars, k=12))
        current_state = ['home','away','sleep', 'custom']
        smart_thermostat_data = self._generate_thermostat_sensor_data(is_truth_file, record_kwargs, timestamps)
        ecobee_ac_md = EcobeeAmbientData(
            **smart_thermostat_data.dict(),
            device_id= device_id,
            device_name= "ecobee",
            current_climate=random.choice(current_state),
            connected_sensors=random.randint(0,5)
        )
        return ecobee_ac_md
    
    def _generate_thermostat_sensor_data(self, is_truth_file: bool, record_kwargs: IndalekoRecordDataModel, timestamps: Dict[str, datetime]) -> ThermostatSensorData:
        """returns the thermostat sensor data"""
        temp_lower_bound, temp_upper_bound = -50.0, 100.0
        humidity_lower_bound, humidity_upper_bound = 0.0, 100.0
        hvac_modes = ["heat", "cool", "auto", "off"]
        hvac_states = ["heating", "cooling", "fan", "idle"]
        fan_modes = ["auto", "on", "scheduled"]
        timestamp = self._generate_ac_timestamp(is_truth_file, timestamps, "ecobee_temp")
    
        temperature = round(random.uniform(temp_lower_bound,temp_upper_bound), 1)
        humidity = round(random.uniform(humidity_lower_bound, humidity_upper_bound), 1)
        target_temp = round(random.uniform(temp_lower_bound,temp_upper_bound), 1)
        hvac_mode = random.choice(hvac_modes)
        hvac_state = random.choice(hvac_states)
        fan_mode = random.choice(fan_modes)
        
        if "ecobee_temp" in self.selected_AC_md:
            ecobee_dict = self.selected_AC_md["ecobee_temp"] 
            if "temperature" in ecobee_dict:
                temperature = self._generate_number(is_truth_file, ecobee_dict["temperature"], temp_lower_bound, temp_upper_bound)
            if "humidity" in ecobee_dict:
                humidity = self._generate_number(is_truth_file, ecobee_dict["humidity"], humidity_lower_bound, humidity_upper_bound)
            if "target_temperature" in ecobee_dict:
                target_temp = self._generate_number(is_truth_file, ecobee_dict["target_temperature"], temp_lower_bound, temp_upper_bound)
            if "hvac_mode" in ecobee_dict:
                hvac_mode = self._choose_random_element(is_truth_file, ecobee_dict["hvac_mode"], hvac_modes)
            if "hvac_state" in ecobee_dict:
                hvac_state = self._choose_random_element(is_truth_file, ecobee_dict["hvac_state"], hvac_states)
            if "fan_mode" in ecobee_dict:
                fan_mode = self._choose_random_element(is_truth_file, ecobee_dict["fan_mode"], fan_modes)
        
        temperature_identifier = IndalekoUUIDDataModel(Identifier=uuid.uuid4(), Label="temperature")
        humidity_identifier = IndalekoUUIDDataModel(Identifier=uuid.uuid4(), Label="humidity")
        semantic_attributes = [
                IndalekoSemanticAttributeDataModel(Identifier=temperature_identifier, Data=temperature),
                IndalekoSemanticAttributeDataModel(Identifier=humidity_identifier, Data=humidity)
                ]

        return ThermostatSensorData(
            Record=record_kwargs,
            Timestamp= timestamp,
            source = "ecobee",
            SemanticAttributes= semantic_attributes,
            temperature= round(temperature, 1), 
            humidity= round(humidity, 1), 
            hvac_mode= hvac_mode, 
            fan_mode= fan_mode, 
            hvac_state=hvac_state, 
            target_temperature=round(target_temp,1)
        )
    
    def _choose_random_element(self, is_truth_file: bool, truth_attribute: str, attribute_lists: list[str]) -> str:
        """based on whether the file is a truth or filler file, returns the appropriate value"""
        if is_truth_file:
            return truth_attribute
        else:
            attribute_lists.remove(truth_attribute)
            return random.choice(attribute_lists)

    def _check_return_value_within_range(self, default_min: Union[int, float], default_max: Union[int, float], target_min: Union[int, float], target_max: Union[int, float], 
    random_func: Callable[[Union[int, float], Union[int, float]], Union[int, float]], delta: Union[int, float] = 0) -> Union[int, float]:
        """
        Genearal function to check and return a value (int or float) that is not within the specified target range.
        """

        if target_min - delta >= default_min and target_max + delta <= default_max:
            return random.choice([
                random_func(default_min, target_min - delta),
                random_func(target_max + delta, default_max)
            ])
        elif target_min - delta < default_min and target_max + delta <= default_max:
            return random_func(target_max + delta, default_max)
        elif target_min - delta >= default_min and target_max + delta > default_max:
            return random_func(default_min, target_min - delta)
        else:
            raise ValueError("Invalid query")
            
    def _generate_number(self, is_truth_file:bool, general_dict: dict[str], lower_bound: float, upper_bound:float) -> float:
        """
        generates number based on general dict given in the format:
        {start: float, end: float, command: one of [“range”, “equals”], lower_bound, upper_bound}
        """
        target_min = general_dict["start"]
        target_max = general_dict["end"]
        command = general_dict["command"]
        delta = 0.5

        if target_max == upper_bound and target_min == lower_bound:
                raise ValueError("The range cannot be the whole boundary from ", target_min, " to ", target_max)
        elif target_min > target_max:
            raise ValueError(f"The target min {target_min} cannot be greater than the target max {target_max}")


        # if the size is the same as the target_max then just choose that file size
        if target_min == target_max and command == "equal":
            if is_truth_file:
                return target_min
            else:
                return self._check_return_value_within_range(lower_bound, upper_bound, target_min,  target_max, random.uniform, delta)

        #if command specifies getting the range between two values
        elif target_min != target_max and command == "range":
            if is_truth_file:
                return random.uniform(target_min, target_max)
            else:
                return self._check_return_value_within_range(lower_bound, upper_bound, target_min,  target_max, random.uniform, delta)
        else:
            raise ValueError("Invalid parameter or command, please check your query again.")

    def _generate_activity_contexts(self, record_data: IndalekoRecordDataModel, is_truth_file: bool, truth_like: bool, truthlike_attributes:list[str], timestamps: Dict[str, datetime]) -> Tuple[IndalekoActivityDataModel, EcobeeAmbientData, Union[SpotifyAmbientData, AmbientMusicData]]:
        geo_activity_provider, geo_activity_context = self._generate_geo_semantics(record_data, timestamps, is_truth_file=self._define_truth_attribute("geo_location", is_truth_file, truth_like, truthlike_attributes))
        ambient_temperature_context = self._generate_smart_thermostat_data(record_data, timestamps, is_truth_file=self._define_truth_attribute("ecobee_temp", is_truth_file, truth_like, truthlike_attributes))
        ambient_music_context = self._generate_ambient_music_context(record_data, timestamps, is_truth_file=self._define_truth_attribute("ambient_music", is_truth_file, truth_like, truthlike_attributes))

        return geo_activity_context, ambient_temperature_context, ambient_music_context
    # Helper functions for creating geo activity context within generate_metadata():
    def _generate_geo_semantics(self, record_kwargs: IndalekoRecordDataModel, timestamps: Dict[str, datetime], is_truth_file: bool) -> Tuple[IndalekoActivityContextDataModel, IndalekoActivityDataModel]:
        """
        Creates the geographical semantic data
        """
        geo_timestamp = self._generate_ac_timestamp(is_truth_file, timestamps, "geo_location")
        activity_geo_loc = self._generate_geo_context(is_truth_file)
        activity_geo_md = self._generate_WindowsGPSLocation(activity_geo_loc, geo_timestamp)
            
        UUID_longitude = uuid.uuid4()
        UUID_latitude = uuid.uuid4()
        UUID_accuracy = uuid.uuid4()

        longitude = IndalekoUUIDDataModel(Identifier=UUID_longitude, Label="Longitude")
        latitude = IndalekoUUIDDataModel(Identifier=UUID_latitude, Label="Latitude")
        accuracy = IndalekoUUIDDataModel(Identifier=UUID_accuracy, Label="Accuracy")

        semantic_attributes = [
            IndalekoSemanticAttributeDataModel(Identifier=longitude, Data = activity_geo_md.longitude),
            IndalekoSemanticAttributeDataModel(Identifier=latitude, Data = activity_geo_md.latitude),
            IndalekoSemanticAttributeDataModel(Identifier=accuracy, Data = activity_geo_md.accuracy)
        ]

        #timestamp is set to when the activity data is collected
        geo_activity_context = IndalekoActivityDataModel(Record = record_kwargs, Timestamp=geo_timestamp, SemanticAttributes=semantic_attributes)

        longitude_data_provider = ActivityDataModel(Provider = uuid.uuid4(), ProviderReference=UUID_longitude)
        latitude_data_provider = ActivityDataModel(Provider = uuid.uuid4(), ProviderReference=UUID_latitude)
        accuracy_data_provider = ActivityDataModel(Provider = uuid.uuid4(), ProviderReference=UUID_accuracy)

        geo_activity_service = IndalekoActivityContextDataModel(Handle=uuid.uuid4(), Timestamp=geo_timestamp, Cursors=[longitude_data_provider, latitude_data_provider,accuracy_data_provider])
        return geo_activity_service, geo_activity_context
    
    # helper functions for activity timestamps:
    def _generate_ac_timestamp(self, is_truth_file:bool, timestamps: Dict[str, str], activity_type: str) -> str:
        """
        Generate the activity context timestamp
        """
        timestamp_types = ["birthtime", "modified", "accessed", "changed"]
        if activity_type in self.selected_AC_md and "timestamp" in self.selected_AC_md[activity_type]:
            time_query = self.selected_AC_md[activity_type]["timestamp"]
            if is_truth_file:
                return timestamps[time_query].strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                timestamp_types.remove(time_query)
                return timestamps[random.choice(timestamp_types)].strftime("%Y-%m-%dT%H:%M:%SZ")
        else: 
            return timestamps[random.choice(timestamp_types)].strftime("%Y-%m-%dT%H:%M:%SZ")

    def _generate_geo_context(self, is_truth_file: bool = True) -> Dict[str, Any]:
        """
        Generates a geographical activity context based on the location given:
        self.selected_AC_md["geo_location"] = {'location': str, 'command': str}
        """
        location_dict = {}
        delta = 5
        default_min_alt = -10
        default_max_alt = 1000
        default_min_lat = -90
        default_max_lat = 90
        default_min_long = -180
        default_max_long = 180
        
        if "geo_location" in self.selected_AC_md:
            geo_location = self.selected_AC_md["geo_location"]["location"]
            geo_command = self.selected_AC_md["geo_location"]["command"]
            # run only once to initialize the saved location
            if not self.saved_geo_loc:
                self.saved_geo_loc = self._save_location(geo_location, geo_command)
            if geo_command == "at":
                if is_truth_file:
                    #geo location generator that given a city, generates longitude and latitude
                    latitude = self.saved_geo_loc["latitude"]
                    longitude = self.saved_geo_loc["longitude"]
                    altitude = self.saved_geo_loc["altitude"]

                else:
                    truth_latitude = self.saved_geo_loc["latitude"]
                    truth_longitude = self.saved_geo_loc["longitude"]
                    truth_altitude = self.saved_geo_loc["altitude"]

                    max_lat = min(default_max_lat, truth_latitude + delta)
                    min_lat = max(default_min_lat, truth_latitude - delta)
                    max_long = min(default_max_long, truth_longitude + delta)
                    min_long = max(default_min_long, truth_longitude - delta)
                    min_alt = max(default_min_alt, truth_altitude - delta)
                    max_alt = min(default_max_alt, truth_altitude + delta)

                    latitude = self._check_return_value_within_range(default_min_lat, default_max_lat, min_lat, max_lat, random.uniform)
                    longitude = self._check_return_value_within_range(default_min_long, default_max_long, min_long, max_long, random.uniform)
                    altitude = self._check_return_value_within_range(default_min_alt, default_max_alt, min_alt, max_alt, random.uniform)

            elif geo_command == "within":
                north_bound = self.saved_geo_loc['latitude'][0]
                south_bound = self.saved_geo_loc['latitude'][1]
                east_bound = self.saved_geo_loc['longitude'][0]
                west_bound = self.saved_geo_loc['longitude'][1]
                altitude = self.saved_geo_loc['altitude']

                if is_truth_file:
                    latitude = random.uniform(north_bound,south_bound)
                    longitude = random.uniform(east_bound,west_bound)

                else:
                    max_lat = min(default_max_lat, north_bound + delta)
                    min_lat = max(default_min_lat, south_bound - delta)
                    max_long = min(default_max_long, east_bound + delta)
                    min_long = max(default_min_long, west_bound - delta)
                    min_alt = max(default_min_alt, altitude - delta)
                    max_alt = min(default_max_alt, altitude + delta)

                    latitude = self._check_return_value_within_range(default_min_lat, default_max_lat, min_lat, max_lat, random.uniform)
                    longitude = self._check_return_value_within_range(default_min_long, default_max_long, min_long, max_long, random.uniform)
                    altitude = self._check_return_value_within_range(default_min_alt, default_max_alt, min_alt, max_alt, random.uniform)

        else:
            latitude = random.uniform(default_min_lat, default_max_lat)
            longitude = random.uniform(default_min_long, default_max_long)
            altitude = random.uniform(default_min_alt, default_max_alt)

        location_dict["latitude"] = latitude
        location_dict["longitude"] = longitude
        location_dict["altitude"] = altitude
        return location_dict

    # helper for _generate_geo_context()
    def _save_location(self, geo_location: str, geo_command: str) -> Dict[str, float]:
        """
        Saves the geographical location specified in the selected_md_attributes; run once
        """
        geo_py = Nominatim(user_agent="Geo Location Metadata Generator")
        location = geo_py.geocode(geo_location, timeout=1000)

        latitude = location.latitude
        longitude = location.longitude
        altitude = location.altitude

        # save a list of longitude and latitude values if command is within
        if geo_command == 'within':
            kilometer_range = self.selected_AC_md["geo_location"]["km"]
            north_bound = geodesic(kilometers = kilometer_range).destination((latitude, longitude), bearing=0).latitude
            south_bound = geodesic(kilometers = kilometer_range).destination((latitude, longitude), bearing=180).latitude
            east_bound = geodesic(kilometers = kilometer_range).destination((latitude, longitude), bearing=90).longitude
            west_bound = geodesic(kilometers = kilometer_range).destination((latitude, longitude), bearing=270).longitude
            latitude = [south_bound, north_bound]
            longitude = [west_bound, east_bound]
        
        return {"latitude": latitude, "longitude": longitude, "altitude": altitude}
        
    def _generate_WindowsGPSLocation(self, geo_activity_context: Dict[str, float], timestamp: datetime) -> Dict[str, Any]:
        """
        Generate the Windows GPS location in the form of a dictionary
        """
        latitude = geo_activity_context["latitude"]
        longitude = geo_activity_context["longitude"]
        altitude = geo_activity_context["altitude"]

        windowsGPS_satellite_location = WindowsGPSLocationSatelliteDataModel(geometric_dilution_of_precision=random.uniform(1, 10), horizontal_dilution_of_precision=random.uniform(1, 10), position_dilution_of_precision=random.uniform(1, 10), time_dilution_of_precision=random.uniform(1, 10), vertical_dilution_of_precision=random.uniform(1, 10))
        no_windowsGPS_satellite_location = WindowsGPSLocationSatelliteDataModel(geometric_dilution_of_precision=None, horizontal_dilution_of_precision=None, position_dilution_of_precision=None, time_dilution_of_precision=None, vertical_dilution_of_precision=None)

        GPS_location_dict = WindowsGPSLocationDataModel(latitude =latitude,
                                                        longitude=longitude,
                                                        altitude=altitude,
                                                        accuracy=random.uniform(1, 10),
                                                        altitude_accuracy=random.uniform(0, 10),
                                                        heading= random.randint(0, 360),
                                                        speed= random.uniform(0, 20),
                                                        source= "GPS",
                                                        timestamp= timestamp,
                                                        is_remote_source= False,
                                                        point= f"POINT({longitude} {latitude})",
                                                        position_source= "GPS",
                                                        position_source_timestamp= timestamp,
                                                        satellite_data= random.choice([windowsGPS_satellite_location, no_windowsGPS_satellite_location]),
                                                        civic_address = None,
                                                        venue_data= None)


        return GPS_location_dict
    
    def _create_semantic_attribute(self, extension: str, last_modified: str, is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str], has_semantic:bool) -> list[Dict[str, Any]]:
        """Creates the semantic attribute data based on semantic attribute datamodel"""
        # text based files supported by the metadata generator
        text_based_files = ["pdf", "doc", "docx", "txt", "rtf", "csv", "xls", "xlsx", "ppt", "pptx"] 
        list_semantic_attribute = []
        if extension in text_based_files:
            data = self._generate_semantic_content(extension, last_modified, is_truth_file, truth_like, truthlike_attributes, has_semantic)
        else:
            data = [extension, last_modified]
        
        for content in data:
            semantic_UUID = uuid.uuid4()
            if isinstance(content, dict):
                for label, context in content.items(): 
                    semantic_attribute = IndalekoSemanticAttributeDataModel(Identifier= IndalekoUUIDDataModel(Identifier=semantic_UUID, Label=label), Data=context)
                    list_semantic_attribute.append(semantic_attribute.dict())
            else:
                semantic_attribute = IndalekoSemanticAttributeDataModel(Identifier= IndalekoUUIDDataModel(Identifier=semantic_UUID, Label=content), Data=content)
                list_semantic_attribute.append(semantic_attribute.dict())
        return list_semantic_attribute
    
    #helper for _create_semantic_attribute():
    def _generate_semantic_content(self, extension: str, last_modified: str, is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str], has_semantic: bool) -> Dict[str, Any]:
        """Generates semantic metadata with given parameters"""
        data_list = []
        all_semantics_attributes = {"Languages", "PageNumber", "Text", "Type", "EmphasizedTextTags", "EmphasizedTextContents"}
        # if the selected_semantic_md is queried, and it's a truth metadata
        if self.selected_semantic_md is not None and (has_semantic or is_truth_file):
            for content_type, content in self.selected_semantic_md.items():
                if self._define_truth_attribute(content_type, is_truth_file, truth_like, truthlike_attributes):
                    semantic_data = self._generate_semantic_content_data(extension, last_modified)
                    # Create a copy of content to avoid mutating the original
                    content_copy = content.copy()
                    remaining_keys = all_semantics_attributes - set(content_copy.keys())
                    for remaining in remaining_keys:
                        content_copy[remaining] = semantic_data[remaining]
                    data_list.append(content_copy)
            data_list.append({"LastModified": last_modified, "FileType": extension})
        else:
            for _ in range(0, random.randint(1, 3)):
                semantic_data = self._generate_semantic_content_data(extension, last_modified)
                data_list.append(semantic_data)
        return data_list

    def _generate_semantic_content_data(self, extension: str, last_modified: str) -> Dict[str, Any]:
        """
        Generate random semnatic content
        """
        emphasized_text_tags = ["bold", "italic", "underline", "strikethrough", "highlight"]
        text_tags = ["Title", "Subtitle", "Header", "Footer", "Paragraph", "BulletPoint", "NumberedList", "Caption", "Quote", "Metadata", "UncategorizedText", "SectionHeader", "Footnote", "Abstract", "FigureDescription", "Annotation"]
        languages = "English"
        text = self.faker.sentence(nb_words=random.randint(1, 30))
        type = random.choice(text_tags)
        text_tag = random.choice(emphasized_text_tags)
        page_number = random.randint(1, 200)
        emphasized_text_contents = random.choice(text.split(" "))

        return {
            "Languages": languages,
            "FileType": extension,
            "PageNumber": page_number,
            "LastModified": last_modified,
            "Text": text,
            "Type": type,
            "EmphasizedTextTags": text_tag,
            "EmphasizedTextContents": emphasized_text_contents
        }

    def _generate_machine_config(self, record: IndalekoRecordDataModel) -> IndalekoMachineConfigDataModel:
        """
        Generate the machine configuration for the given Indaleko record using the example hardware and software information
        """
        timestamp = IndalekoTimestampDataModel(Label=uuid.uuid4(), Value=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"), Description="Captured Timestamp")
        hardware = Hardware.Config.json_schema_extra['example']
        software = Software.Config.json_schema_extra['example']
        machine_config = IndalekoMachineConfigDataModel(Record=record, Captured=timestamp, Hardware=hardware, Software=software)
        return machine_config

    def _define_truth_attribute(self, attribute: str, truth_file: bool, truthlike_file: bool, truth_attributes: list[str]) -> bool:
        """Returns true if the file is a truth file or the attribute is contained in the truthlike attribute list"""
        return truth_file or (truthlike_file and attribute in truth_attributes)

    def _generate_semantic_data(self, record_data: IndalekoRecordDataModel, IO_UUID: str, semantic_attributes_data: list[Dict[str, Any]]) -> BaseSemanticDataModel:
        """Returns the semantic data created from the data model"""
        return BaseSemanticDataModel(
                Record=record_data,
                Timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                RelatedObjects=[IO_UUID],
                SemanticAttributes=semantic_attributes_data)

    def _generate_i_object_data(self, record_data: IndalekoRecordDataModel, IO_UUID: str, timestamps: Dict[str, str], URI: str, file_size: int, semantic_attributes_data: list[Dict[str, Any]], key_name: str, local_identifier: str) -> IndalekoObjectDataModel:
        """Returns the Indaleko object created form the data model"""
        timestamp_data = self._create_timestamp_data(IO_UUID, timestamps)
        return IndalekoObjectDataModel(
                Record=record_data, 
                URI = URI, 
                ObjectIdentifier=uuid.uuid4(), 
                Timestamps=timestamp_data,
                Size = file_size, 
                SemanticAttributes=semantic_attributes_data,
                Label = key_name, 
                LocalIdentifier=str(local_identifier),
                Volume=uuid.uuid4(),
                PosixFileAttributes="S_IFREG",
                WindowsFileAttributes="FILE_ATTRIBUTE_ARCHIVE")

    # helper for _generate_i_object_data
    def _create_timestamp_data(self, UUID: str, timestamps: Dict[str, datetime]) -> list[IndalekoTimestampDataModel]:
        """
        Creates the timestamp data based on timestamp datamodel (in UTC time)
        """
        timestamp_data = []
        # sort the timestamp by most earliest to latest
        for timestamp in sorted(timestamps.items(), key=lambda time: time[1]):
            timestamp_data.append(IndalekoTimestampDataModel(Label=UUID, Value=timestamp[1].strftime("%Y-%m-%dT%H:%M:%SZ"), Description=timestamp[0]))
        return timestamp_data

    def _generate_record_data(self, IO_UUID: str, attribute: Dict[str, Any]) -> IndalekoRecordDataModel:
        """generates the record data"""
        id_source_identifier = IndalekoSourceIdentifierDataModel(
                Identifier = IO_UUID, 
                Version = "1.0",
                Description ="Record UUID")

        return IndalekoRecordDataModel(
                SourceIdentifier = id_source_identifier, 
                Timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"), 
                Attributes=attribute, 
                Data = self.generate_random_data())
    
    #helper for _generate_record_data():
    def generate_random_data(self) -> str:
        """Generates a string of random number of ascii characters as data"""
        ascii_chars = string.ascii_letters + string.digits
        random_data = ''.join(random.choices(ascii_chars, k = random.randint(1,500)))
        return random_data

    def _generate_file_info(self, current_filenum: int, n: int, is_truth_file: bool, truth_like: bool, truthlike_attributes: list[str], has_semantic: bool) -> Tuple[int, str, str, str, str]:
        file_size = self.generate_file_size(is_truth_file=self._define_truth_attribute("file.size", is_truth_file, truth_like, truthlike_attributes))
        file_name = self._generate_file_name(is_truth_file=self._define_truth_attribute("file.name", is_truth_file, truth_like, truthlike_attributes), has_semantic_attr=has_semantic)
        path, URI, updated_filename = self._generate_dir_location(file_name, is_truth_file=self._define_truth_attribute("file.directory", is_truth_file, truth_like, truthlike_attributes))
        IO_UUID = self._create_metadata_UUID(current_filenum + n, is_truth_file=is_truth_file)
        return file_size, updated_filename, path, URI, IO_UUID

    #helper function for _generate_file_info()
    def _create_metadata_UUID(self, number: int, is_truth_file: bool = True) -> str:
        """
        Creates UUID for the metadata based on the is_truth_file (filler VS truth metadata) of metadata
        Truth files are given prefix c, Filler or truth like filler files prefix f
        """
        if is_truth_file:
            starter_uuid = f"c{number}" 
        else:
            starter_uuid = f"f{number}" 

        digits = 8 - len(starter_uuid)
        space_filler = '0' * digits
        starter_uuid += space_filler
        uuid = starter_uuid + "-" + ''.join(random.choices('0123456789', k=4)) + "-" + ''.join(random.choices('0123456789', k=4)) + "-" + ''.join(random.choices('0123456789', k=4)) + "-" + ''.join(random.choices('0123456789', k=12))
        return uuid

    def _has_semantic_attr(self, truthlike_attributes) -> bool:
        """checks whether there are any semantic attributes populated"""
        return any(attr.startswith("Content_") for attr in truthlike_attributes)


    def _generate_key_name(self, key: str, n: int, truth_like: bool, truthlike_attributes: list[str]) -> str:
        """generates the key name for the file"""
        key_name = f"{key} #{n}"
        if truth_like:
            key_name += f", truth-like attributes: {truthlike_attributes}"
        return key_name

    def _get_truthlike_attributes(self, truth_like: bool) -> list[str]:
        """Returns a list of randomly selected truthlike attributes"""
        
        if truth_like:
            num_truthlike_attributes = random.randint(1, len(self.truth_attributes) -1)
            selected_truth_like_attr = random.sample(self.truth_attributes, k = num_truthlike_attributes)
            # this is done so that there are no semantic attributes in filler files that aren't text based when the text files are all specified in truth attributes
            return self._check_special_case(selected_truth_like_attr, num_truthlike_attributes);
        return []
    
    def _check_special_case(self, selected_truth_like_attr: list[str], num_truthlike_attributes: int):
        is_all_text = self._check_truth_all_text()
        
        if not self._check_semantic_available(selected_truth_like_attr, is_all_text):
            # semantic_count = sum(1 for item in selected_truth_like_attr if "Content" in item)
            if len(self.selected_AC_md) == 0 and len(self.selected_POSIX_md) == 1 and len(self.selected_semantic_md) == 1:
                return ["file.name"]
            elif len(self.selected_POSIX_md) >= 1 and len(self.selected_semantic_md) >= 1:
                if num_truthlike_attributes == len(self.truth_attributes) - 1:
                    selected_truth_like_attr = [item for item in selected_truth_like_attr if "Content_" not in item]
                selected_truth_like_attr.append("file.name")
        return selected_truth_like_attr

    def _check_truth_all_text(self):
        text_file_extension = [".pdf", ".doc", ".docx", ".txt", ".rtf", ".csv", ".xls", ".xlsx", ".ppt", ".pptx"]
        if "file.name" in self.selected_POSIX_md:
            if "extension" in self.selected_POSIX_md["file.name"]:
                true_extension = self.selected_POSIX_md["file.name"]["extension"]
                if set(text_file_extension) == set(true_extension):
                    return True
        return False
                
    
    def _check_semantic_available(self, selected_truth_attributes: list[str], is_all_text: bool) -> bool:
        if is_all_text and ("file.name" not in selected_truth_attributes) and any("Content_" in item for item in selected_truth_attributes):
            return False
        return True
    
            
    def _generate_file_attributes(self, file_name: str, path: str, timestamps: Dict[str, datetime], file_size: int) -> Dict[str, Any]:
        """Generates the dictionary of file attributes"""

        birthtime = timestamps["birthtime"].timestamp()
        modified_time = timestamps["modified"].timestamp()
        access_time = timestamps["accessed"].timestamp()
        changed_time = timestamps["changed"].timestamp()
        return {
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
        }


def main():
    #selected_md_attributes = {'Posix': {'file.name': {'extension': ['.pdf']}, 'timestamps': {'birthtime': {'starttime': "2025-01-10T00:00:00", 'endtime': "2025-01-10T00:00:00", 'command': 'equal'}}}, 'Semantic': {'Content_1': {'Text': 'essay 1', 'Type': 'Subtitle', 'PageNumber':10}, 'Content_2': {'Text': 'essay 2', 'Type': 'Title', 'PageNumber':20}}, 'Activity': {'ambient_music': {'track_name': 'Happy', 'timestamp': 'birthtime'}}}
    selected_md_attributes ={"Posix": {}, "Semantic": {"Content_1": {"Text": "readd", "Type": "Paragraph", "EmphasizedTextTags": "bold"}, "Content_2": {"Text": "sss", "Type": "Subtitle", "EmphasizedTextTags": "bold"}}, "Activity": {}}
    config_path = "data_generator/dg_config.json"
    with open(config_path, 'r') as file:
        config = json.load(file)
    data_generator = Dataset_Generator(config)
    selected_md_attributes = data_generator.convert_dictionary_times(selected_md_attributes, False)

    data_generator.set_selected_md_attributes(selected_md_attributes)
    all_record_md, all_geo_activity_md, all_temp_activity_md, all_music_activity_md,  all_machine_config_md, metadata_stats = data_generator.generate_metadata_dataset()
    data_generator.write_json(all_record_md, "/Users/pearl/Indaleko_updated/Indaleko/data_generator/results/test_object_records.json")
    data_generator.write_json(all_temp_activity_md, "/Users/pearl/Indaleko_updated/Indaleko/data_generator/results/test_temp_records.json")
    ic(selected_md_attributes)

    converted_dict = data_generator.convert_dictionary_times(selected_md_attributes, True)


if __name__ == '__main__':
    main()
