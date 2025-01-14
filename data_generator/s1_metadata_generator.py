import os, sys
from icecream import ic
from uuid import UUID
from datetime import datetime, timedelta
import random
import string
import json
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
from typing import Dict, Any

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

        self.saved_directory_path = {"truth.directory": {}, "filler.directory": {}}

        self.saved_geo_loc = {}
    
    def write_json(self, dataset: dict, json_path: str) -> None:
        """
        Writes the generated metadata to a json file
        """
        with open(json_path, 'w') as json_file:
            json.dump(dataset, json_file, indent=4)


    def set_selected_md_attributes(self, md_attributes) -> None:
        """
        Sets the selected metadata attributes given the attribute dictionary
        Args: 
            md_attributes (dict): dictionary of the attributes populated after query extraction
        """
        self.selected_md_attributes = md_attributes
        self.selected_POSIX_md = md_attributes.get("Posix", {})
        self.selected_AC_md = md_attributes.get("Activity", {})
        self.selected_semantic_md = md_attributes.get("Semantic", {})
    
    def convert_dictionary_times(self, selected_md_attributes: dict[str, Any], to_timestamp: bool) -> dict[str, Any]:
        """
        Convert time to posix timstamps given a dictionary that the LLM cannot handle properly:
        Args:
            selected_md_attributes (dict[str, Any]): The dictionary of attributes
        Returns:
            Dict[str, Any]: The converted attributes dictionary
        """
        if "Posix" in selected_md_attributes:        
            posix = selected_md_attributes["Posix"]
            if "timestamps" in posix:
                for timestamp_key, timestamp_data in posix["timestamps"].items():
                    starttime, endtime = self._convert_time_timestamp(timestamp_data, to_timestamp)
                    posix["timestamps"][timestamp_key]["starttime"] = starttime
                    posix["timestamps"][timestamp_key]["endtime"] = endtime 
        
        # if "Activity" in selected_md_attributes:
        #     activity = selected_md_attributes["Activity"]
        #     if "timestamp" in activity:
        #         starttime, endtime = self._convert_time_timestamp(activity["timestamp"], to_timestamp)
        #         activity["timestamp"]["starttime"] = starttime
        #         activity["timestamp"]["endtime"] = endtime 
        return selected_md_attributes

    # Helper function for convert_dictionary_times()
    def _convert_time_timestamp(self, timestamps: dict, to_timestamp: bool) -> tuple:
        """
        Converts the time from string to timestamps
        """
        self.earliest_endtime = None
        self.earliest_starttime = None

        starttime = timestamps["starttime"]
        endtime = timestamps["endtime"]
        if to_timestamp:
            starttime = starttime.timestamp()
            endtime = endtime.timestamp()
        else: 
            starttime = self._convert_str_datetime(starttime)
            endtime = self._convert_str_datetime(endtime)

        if self.earliest_endtime is None:
            self.earliest_endtime = endtime
            self.earliest_starttime = starttime
        else:
            self.earliest_endtime = min(self.earliest_endtime, endtime)
            self.earliest_starttime = min(self.earliest_starttime, starttime)
        return starttime, endtime
    
    def generate_metadata_dataset(self) -> dict:
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
        if total_truth_attributes > 1 and self.n_matching_queries > 0:
            truth_like_num = random.randint(0, remaining_files)
        else:
            truth_like_num = 0
        filler_num = remaining_files - truth_like_num

        target_record_md, target_semantics_md, target_activity_md, target_machine_config = self._generate_metadata(0, self.n_matching_queries+1, 'Truth File', True, False)
        truth_like_filler_record_md, truth_like_filler_semantics_md, truth_like_filler_activity_md, truth_like_machine_config = self._generate_metadata(0, truth_like_num +1, 'Filler Truth-Like File', False, True)
        filler_record_md, filler_semantics_md, filler_activity_md, filler_machine_config = self._generate_metadata(truth_like_num,  filler_num +1, 'Filler File', False, False)
        
        all_record_md = target_record_md + truth_like_filler_record_md + filler_record_md
        all_semantics_md = target_semantics_md + truth_like_filler_semantics_md + filler_semantics_md
        all_activity_md = target_activity_md + truth_like_filler_activity_md + filler_activity_md
        all_machine_config_md = target_machine_config + truth_like_machine_config + filler_machine_config

        metadata_stats = {"truth": self.n_matching_queries, "filler": remaining_files, "truth-like":truth_like_num}
        return all_record_md, all_activity_md, all_machine_config_md, metadata_stats

    def _check_return_dict(self, dictionary: dict):
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
    

    def _generate_file_name(self, is_truth_file: bool) -> str:
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

            if "extension" in self.selected_POSIX_md["file.name"]:
                true_extension = self.selected_POSIX_md["file.name"]["extension"]
                if isinstance(true_extension, list):
                    file_extension = list(set(file_extension) - set(true_extension))
                else: 
                    file_extension.remove(true_extension)

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

            else:  # if a filler metadata, generate random title that excludes all letters specified in the char pattern
                extension = random.choice(file_extension)
                allowed_pattern = list(set(string.ascii_letters) - set(pattern.upper()) - set(pattern.lower()))
                return ''.join(random.choices(allowed_pattern, k=n_filler_letters)) + extension

        else: #if no query specified for title, but semantic context exists, choose a text file extension
            if is_truth_file and self.selected_semantic_md:
                extension = random.choice(text_file_extension)
            else: # randomly create a title with any extension
                extension = random.choice(file_extension)
            title = ''.join(random.choices(string.ascii_letters, k=n_filler_letters)) + extension
            return title

    def _generate_dir_location(self, file_name: str, is_truth_file: bool=True) -> list:
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
                    ic(updated_file_name)
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

        return [path, URI, file_name]

        
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

    def _generate_timestamps(self, is_truth_file: bool=True) -> dict[datetime]:
        """
        Generates birthtime, modifiedtime, accessedtime, and changedtime for the specified file:
        Args: is_truth_file (bool): file type 
        Returns (dict[datetime]): {birthtime: datetime, modifiedtime: datetime, accessedtime: datetime, changedtime: datetime}
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
                birthtime = self._generate_queried_timestamp(birthtime_query["starttime"], birthtime_query["endtime"], birthtime_query["command"], default_truth_startdate=self.default_lower_timestamp, is_truth_file = is_truth_file, is_birthtime=True)
                timestamps["birthtime"] = birthtime

                # if there queries other than the birthtime, iterate over each of the timestamps
                for timestamp in stamp_labels: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                    if timestamp in selected_timestamps:
                        timestamps[timestamp] = self._generate_queried_timestamp(query[timestamp]["starttime"], query[timestamp]["endtime"], query[timestamp]["command"], default_truth_startdate = birthtime, is_truth_file=is_truth_file)
                    else: # if type of timestamp not chosen, either generate a random timestamp within bounds or choose an existing timestamp
                        timestamps[timestamp] = self._choose_existing_or_random(timestamps, birthtime, self.default_upper_timestamp)
            else:
                for timestamp in selected_timestamps: # for each of the other timestamps, set the timestamp based on whether it has been selected in the query or not
                    timestamps[timestamp] = self._generate_queried_timestamp(query[timestamp]["starttime"], query[timestamp]["endtime"], query[timestamp]["command"], default_truth_startdate = self.default_lower_timestamp, is_truth_file=is_truth_file)
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
        #lowest_datetime_key = min(timestamps, key=timestamps.get)
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
        fake = Faker()
        random_time = fake.date_time_between(start_date = lower_bound, end_date = upper_bound)
        return random_time

    def _generate_queried_timestamp(self, starttime:datetime, endtime:datetime, command:str, default_truth_startdate:datetime, is_truth_file:bool = True, is_birthtime: bool = False) -> datetime:
        """Generates timestamp based on file type"""
        fake = Faker()
        filler_delta = 2
        timestamp = None
            
        # check errors that can arise for str parameters
        if starttime > datetime.now() or endtime > datetime.now():
            raise ValueError("The timestamp you have queried is in the future, please check again.")
        elif starttime > endtime:
            raise ValueError("The starttime cannot be more recent than the endtime")
        elif is_truth_file and default_truth_startdate > endtime:
            raise ValueError("The default_startdate cannot be more recent than the endtime")
        elif self.default_lower_timestamp == self.default_upper_timestamp:
            raise ValueError("The absolute lower bound date cannot be the same time as the date right now")
        elif self.default_lower_timestamp > starttime:
            raise ValueError("The absolute lower bound cannot be greater than the starttime")

        elif starttime == endtime and command == "equal":
            if is_truth_file and default_truth_startdate <= starttime:
                timestamp = starttime
            elif is_truth_file and default_truth_startdate > starttime:
                raise ValueError("the starttime cannot be greater than the default, either change the default starttime or the timestamp boundaries")
    
            if not is_truth_file:
                # for birthtime timestamps (choose the lowest/most latest possible time to not have time earlier than the other timestamps)
                lower = fake.date_time_between(start_date = self.default_lower_timestamp, end_date=starttime-timedelta(hours=filler_delta)).replace(microsecond=0)
                upper = fake.date_time_between(start_date = starttime+timedelta(hours=filler_delta)).replace(microsecond=0)
                
                if is_birthtime and starttime-timedelta(hours=filler_delta) < self.default_lower_timestamp:
                    raise ValueError("birthtime for filler cannot be more earlier than the absolute default")
                elif is_birthtime and self.default_lower_timestamp <= self.earliest_starttime-timedelta(hours=filler_delta) <= starttime-timedelta(hours=filler_delta):
                    timestamp = fake.date_time_between(start_date=self.default_lower_timestamp, end_date=self.earliest_starttime-timedelta(hours=filler_delta)).replace(microsecond=0) # check if this is okay
                elif is_birthtime:
                    raise ValueError("Cannot generate birthtime timestamp for truth file")
                #if not a birthtime timestamp
                if not is_birthtime and default_truth_startdate == starttime: #if birthtime is greater than the equal
                    timestamp = fake.date_time_between(start_date = default_truth_startdate + timedelta(hours = filler_delta)).replace(microsecond=0)
                elif not is_birthtime and default_truth_startdate > starttime: #if birthtime is greater than the equal
                    timestamp = fake.date_time_between(start_date = default_truth_startdate).replace(microsecond=0)
                elif not is_birthtime and default_truth_startdate < starttime:
                    lower = fake.date_time_between(start_date = default_truth_startdate, end_date = starttime-timedelta(hours=filler_delta)).replace(microsecond=0)
                    if starttime+timedelta(hours=filler_delta) < self.default_upper_timestamp:
                        upper = fake.date_time_between(start_date = starttime+timedelta(hours=filler_delta)).replace(microsecond=0)
                        timestamp = random.choice([upper, lower])
                    elif starttime+timedelta(hours=filler_delta) >= self.default_upper_timestamp:
                        timestamp = lower
                elif not is_birthtime:
                    raise ValueError("cannot form timestamp for filler file")

        #if the starttime and endtime are not equal and are not lists, then choose a date within that range
        elif starttime != endtime and command == "range": # if is a birthtime, should take on values that are 
            # if it is a birthtime and a truth file, find the earliest time possible
            if is_truth_file and is_birthtime and default_truth_startdate <= starttime and starttime <= self.earliest_starttime <= endtime: # only for the birthtime to make birthtime earlier 
                timestamp = fake.date_time_between(start_date=starttime, end_date=self.earliest_starttime).replace(microsecond=0)
            elif is_truth_file and is_birthtime and default_truth_startdate <= starttime:
                timestamp = fake.date_time_between(start_date=starttime, end_date=endtime).replace(microsecond=0)
            elif is_truth_file and is_birthtime:
                raise ValueError("cannot generate truthfile timestamp.")

            if is_truth_file and not is_birthtime and starttime <= default_truth_startdate <= endtime: 
                timestamp = fake.date_time_between(start_date=default_truth_startdate, end_date=endtime).replace(microsecond=0)     
            elif is_truth_file and not is_birthtime and starttime >= default_truth_startdate: 
                timestamp = fake.date_time_between(start_date=starttime, end_date=endtime).replace(microsecond=0)
            elif is_truth_file and not is_birthtime and endtime < default_truth_startdate: 
                raise ValueError("The birthtime cannot be greater than the other timestamps")
            elif is_truth_file and not is_birthtime:
                raise ValueError("Absolute lower bound date cannot be more recent than the endtime")
            
            if not is_truth_file: 
                # for filler file birhttime timestamps:
                lower = fake.date_time_between(start_date = default_truth_startdate, end_date=starttime-timedelta(hours=filler_delta)).replace(microsecond=0)
                upper = fake.date_time_between(start_date = endtime + timedelta(hours=filler_delta)).replace(microsecond=0)
                if endtime == self.default_upper_timestamp and starttime == self.default_lower_timestamp:
                    raise ValueError("There are no choice of filler timestamps that are within bounds. Please narrow the bounds or change the default startdate")
                elif is_birthtime and self.default_lower_timestamp < starttime-timedelta(hours=filler_delta):
                    timestamp = lower 
                elif is_birthtime and self.default_lower_timestamp < starttime-timedelta(hours=filler_delta) and  self.default_lower_timestamp < self.earliest_starttime < starttime:
                    timestamp = fake.date_time_between(start_date = default_truth_startdate, end_date=self.earliest_starttime-timedelta(hours=filler_delta)).replace(microsecond=0)
                elif is_birthtime and not is_truth_file:
                    raise ValueError("cannot generate birthtime timestamp for filler files")
                # for none birthtime timestamps
                if not is_birthtime and endtime < default_truth_startdate <= self.default_upper_timestamp:
                    timestamp = fake.date_time_between(start_date = default_truth_startdate).replace(microsecond=0)
                elif not is_birthtime and starttime <= default_truth_startdate <= endtime:
                    timestamp = fake.date_time_between(start_date = endtime+timedelta(hours=filler_delta)).replace(microsecond=0)
                elif not is_birthtime and self.default_lower_timestamp <= default_truth_startdate <= starttime:
                    timestamp = random.choice([lower, upper])
                elif not is_birthtime and not is_truth_file:
                    raise ValueError("Cannot generate timestamps for filler files")
        else:
            raise ValueError("Error in parameters or command: Please check the query once more.")
        return timestamp
    
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

            # if the target_min/max is a list and is the same as the target_max choose a random size from the list
            if isinstance(target_min, list) and isinstance(target_max, list) and command == "equal":
                if is_truth_file:
                    return random.choice(target_min)
                else:
                    return self._check_return_size_within_range(self.default_lower_filesize, self.default_upper_filesize, target_min[0], target_min[-1])

            # if the target_min/max is not a list but is the same as the target_max then just choose that file size
            elif target_min == target_max and command == "equal":
                if is_truth_file:
                    return target_min
                else:
                    return self._check_return_size_within_range(self.default_lower_filesize, self.default_upper_filesize, target_min, target_min)

            #if command specifies getting the range between two values
            elif target_min != target_max and command == "range":
                if is_truth_file:
                    return random.randint(target_min, target_max)
                else:
                    return self._check_return_size_within_range(self.default_lower_filesize, self.default_upper_filesize, target_min, target_max)

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
   
    # helper function for generate_file_size():
    def _check_return_size_within_range(self, min_size: int, max_size: int, target_min: int, target_max: int) -> int:
        """
        Checks and returns a file size that is not within the range of the truth files; helper for generate_file_size function
        """
        if target_min - 1 <= min_size and target_max + 1 <= max_size:
            return random.choice([random.randint(min_size, target_min - 1), random.randint(target_max + 1, max_size)])
        elif target_min - 1 < min_size and target_max + 1 <= max_size:
            return random.randint(target_max + 1, max_size)
        elif target_min - 1 <= min_size and target_max + 1 > max_size:
            return random.randint(min_size, target_min - 1)
        return 0
    

    def _generate_metadata(self, current_filenum:int, max_num: int, key: str, is_truth_file: bool, truth_like: bool) -> dict:
        """Generates the target metadata with the specified attributes based on the nubmer of matching queries to generate based on config:"""
        all_metadata, all_semantics, all_activity, all_machine_configs = [], [], [], []

        for n in range(1, max_num):
            truthlike_attributes = self._get_truthlike_attributes(truth_like)
            key_name = self._generate_key_name(key, n, truth_like, truthlike_attributes)
            file_size, file_name, path, URI, IO_UUID = self._generate_file_info(current_filenum, n, is_truth_file, truth_like, truthlike_attributes)
            timestamps = self._generate_timestamps(is_truth_file=self._define_truth_attribute("timestamps", is_truth_file, truth_like, truthlike_attributes))
            attribute = self._generate_file_attributes(file_name, path, timestamps, file_size)
            semantic_attributes_data = self._create_semantic_attribute(extension=file_name.split(".")[-1], last_modified=timestamps["modified"].strftime("%Y-%m-%dT%H:%M:%S"), is_truth_file= self._define_truth_attribute("semantic_1", is_truth_file, truth_like, truthlike_attributes))
            record_data = self._generate_record_data(IO_UUID, attribute)

            i_object_data = self._generate_i_object_data(record_data, IO_UUID, timestamps, URI, file_size, semantic_attributes_data, key_name, current_filenum + n)
            semantics_md = self._generate_semantic_data(record_data, IO_UUID, semantic_attributes_data)
            activity_provider, activity_context = self._generate_geo_semantics(record_data, is_truth_file, timestamps)
            machine_config = self._generate_machine_config(record_data)

            # appending the objects to their lists
            all_metadata.append(json.loads(i_object_data.json()))
            all_semantics.append(json.loads(semantics_md.json()))
            all_activity.append(json.loads(activity_context.json()))
            all_machine_configs.append(json.loads(machine_config.json()))


        return all_metadata, all_semantics, all_activity, all_machine_configs
    
    # Helper functions for generate_metadata():
    def _generate_geo_semantics(self, record_kwargs: IndalekoRecordDataModel, is_truth_file: bool, timestamps: dict[str]) -> list:
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
        activity_context = IndalekoActivityDataModel(Record = record_kwargs, Timestamp=geo_timestamp, SemanticAttributes=semantic_attributes)

        longitude_data_provider = ActivityDataModel(Provider = uuid.uuid4(), ProviderReference=UUID_longitude)
        latitude_data_provider = ActivityDataModel(Provider = uuid.uuid4(), ProviderReference=UUID_latitude)
        accuracy_data_provider = ActivityDataModel(Provider = uuid.uuid4(), ProviderReference=UUID_accuracy)

        activity_service = IndalekoActivityContextDataModel(Handle=uuid.uuid4(), Timestamp=geo_timestamp, Cursors=[longitude_data_provider, latitude_data_provider,accuracy_data_provider])
        return activity_service, activity_context
    
    # helper functions for generate_geo_semantics:
    def _generate_ac_timestamp(self, is_truth_file:bool, timestamps: dict[str], activity_type: str) -> str:
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

    def _generate_geo_context(self, is_truth_file: bool = True) -> dict:
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

                    latitude = self._check_return_within_range_geo(min_lat, max_lat, default_min_lat, default_max_lat)
                    longitude = self._check_return_within_range_geo(min_long, max_long, default_min_long, default_max_long)
                    altitude = self._check_return_within_range_geo(min_alt, max_alt, default_min_alt, default_max_alt)

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

                    latitude = self._check_return_within_range_geo(min_lat, max_lat, default_min_lat, default_max_lat)
                    longitude = self._check_return_within_range_geo(min_long, max_long, default_min_long, default_max_long)
                    altitude = self._check_return_within_range_geo(min_alt, max_alt, default_min_alt, default_max_alt)

        else:
            latitude = random.uniform(default_min_lat, default_max_lat)
            longitude = random.uniform(default_min_long, default_max_long)
            altitude = random.uniform(default_min_alt, default_max_alt)

        location_dict["latitude"] = latitude
        location_dict["longitude"] = longitude
        location_dict["altitude"] = altitude
        return location_dict

    # helper for _generate_geo_context()
    def _save_location(self, geo_location: str, geo_command: str) -> dict:
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

    def _check_return_within_range_geo(self, min_coord, max_coord, target_min, target_max):
        """
        Checks and returns a random geographical coordinate within the bounds specified 
        """
        coord = 0
        if min_coord > target_min and max_coord < target_max:
            coord = random.choice([random.uniform(target_min, min_coord), random.uniform(max_coord, target_max)])
        elif min_coord > target_min and max_coord == target_max:
            coord = random.uniform(target_min, min_coord)
        elif min_coord == target_min and max_coord < target_max:
            coord = random.uniform(max_coord, target_max)
        else: 
            raise RuntimeError("Invalid coordinates; choose smaller range")
        return coord
        
    def _generate_WindowsGPSLocation(self, geo_activity_context: dict, timestamp: datetime) -> dict:
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
    
    def _create_semantic_attribute(self, extension, last_modified, is_truth_file: bool) -> list:
        """Creates the semantic attribute data based on semantic attribute datamodel"""
        # text based files supported by the metadata generator
        text_based_files = ["pdf", "doc", "docx", "txt", "rtf", "csv", "xls", "xlsx", "ppt", "pptx"] 
        list_semantic_attribute = []
        if extension in text_based_files:
            data = self._generate_semantic_content(extension, last_modified, is_truth_file)
        else:
            data = [extension, last_modified]

        for content in data:
            semantic_UUID = uuid.uuid4()
            if isinstance(content, dict):
                for label, context in content.items(): 
                    semantic_attribute = IndalekoSemanticAttributeDataModel(Identifier= IndalekoUUIDDataModel(Identifier=semantic_UUID, Label=label), Data=str(context))
                    list_semantic_attribute.append(semantic_attribute.dict())
            else:
                semantic_attribute = IndalekoSemanticAttributeDataModel(Identifier= IndalekoUUIDDataModel(Identifier=semantic_UUID, Label=content), Data=str(content))
                list_semantic_attribute.append(semantic_attribute.dict())

        return list_semantic_attribute
    
    #helper for _create_semantic_attribute():
    def _generate_semantic_content(self, extension, last_modified, is_truth_file) -> dict:
        """Generates semantic metadata with given parameters"""
        fake = Faker()
        emphasized_text_tags = ["bold", "italic", "underline", "strikethrough", "highlight"]
        text_tags = ["Title", "Subtitle", "Header", "Footer", "Paragraph", "BulletPoint", "NumberedList", "Caption", "Quote", "Metadata", "UncategorizedText", "SectionHeader", "Footnote", "Abstract", "FigureDescription", "Annotation"]
        data_list = []
        #if the selected_semantic_md is queried, and it's a truth metadata
        if self.selected_semantic_md != None and is_truth_file:
            for content in self.selected_semantic_md.values():
                data_list.append(content)
            data_list.append({"LastModified": last_modified, "FileType": extension})
        else:
            languages = "English"
            text = fake.sentence(nb_words=random.randint(1, 30))
            type = random.choice(text_tags)
            text_tag =random.choice(emphasized_text_tags)
            page_number = random.randint(1, 200)
            emphasized_text_contents = random.choice(text.split(" "))

            data_list = [{
                "Languages": languages,
                "FileType": extension,
                "PageNumber": page_number,
                "LastModified": last_modified,
                "Text": text,
                "Type": type,
                "EmphasizedTextTags": text_tag,
                "EmphasizedTextContents": emphasized_text_contents
            }]
        return data_list

    def _generate_machine_config(self, record) -> IndalekoMachineConfigDataModel:
        """
        Generate the machine configuration for the given Indaleko record using the example hardware and software information
        """
        timestamp = IndalekoTimestampDataModel(Label=uuid.uuid4(), Value=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"), Description="Captured Timestamp")
        hardware = Hardware.Config.json_schema_extra['example']
        software = Software.Config.json_schema_extra['example']
        machine_config = IndalekoMachineConfigDataModel(Record=record, Captured=timestamp, Hardware=hardware, Software=software)
        return machine_config

    def _define_truth_attribute(self, attribute, truth_file, truthlike_file, truth_attributes):
        """Returns true if the file is a truth file or the attribute is contained in the truthlike attribute list"""
        return truth_file or (truthlike_file and attribute in truth_attributes)

    def _generate_semantic_data(self, record_data, IO_UUID, semantic_attributes_data):
        return BaseSemanticDataModel(
                Record=record_data,
                Timestamp=datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                RelatedObjects=[IO_UUID],
                SemanticAttributes=semantic_attributes_data)

    def _generate_i_object_data(self, record_data, IO_UUID, timestamps, URI, file_size, semantic_attributes_data, key_name, local_identifier):
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
    def _create_timestamp_data(self, UUID: str, timestamps: dict) -> dict:
        """
        Creates the timestamp data based on timestamp datamodel (in UTC time)
        """
        timestamp_data = []
        # sort the timestamp by most earliest to latest
        for timestamp in sorted(timestamps.items(), key=lambda time: time[1]):
            timestamp_data.append(IndalekoTimestampDataModel(Label=UUID, Value=timestamp[1].strftime("%Y-%m-%dT%H:%M:%SZ"), Description=timestamp[0]))
        return timestamp_data

    def _generate_record_data(self, IO_UUID, attribute):
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
    def generate_random_data(self):
        """Generates random number of ascii characters as data"""
        ascii_chars = string.ascii_letters + string.digits
        random_data = ''.join(random.choices(ascii_chars, k = random.randint(1,500)))
        return random_data

    def _generate_file_info(self, current_filenum, n, is_truth_file, truth_like, truthlike_attributes):
        file_size = self.generate_file_size(is_truth_file=self._define_truth_attribute("file.size", is_truth_file, truth_like, truthlike_attributes))
        file_name = self._generate_file_name(is_truth_file=self._define_truth_attribute("file.name", is_truth_file, truth_like, truthlike_attributes))
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

    def _generate_key_name(self, key: str, n: int, truth_like: bool, truthlike_attributes: list) -> str:
        key_name = f"{key} #{n}"
        if truth_like:
            key_name += f", truth-like attributes: {truthlike_attributes}"
        return key_name

    def _get_truthlike_attributes(self, truth_like: bool):
        if truth_like:
            num_truthlike_attributes = random.randint(1, len(self.truth_attributes) -1)
            return random.sample(self.truth_attributes, k = num_truthlike_attributes)
        return []
            
    def _generate_file_attributes(self, file_name, path, timestamps, file_size):
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
    selected_md_attributes = {"Posix": {"file.name": {"pattern": "essay", "command": "exactly", "extension": [".pdf"]}, "file.directory": {"location": "local", "local_dir_name": "essays"}}, "Semantic": {}, "Activity": {}}
    config_path = "data_generator/dg_config.json"
    with open(config_path, 'r') as file:
        print("here")
        config = json.load(file)
    data_generator = Dataset_Generator(config)
    original_dict = data_generator.convert_dictionary_times(selected_md_attributes, False)
    ic(original_dict)

    data_generator.set_selected_md_attributes(selected_md_attributes)
    all_record_md, all_activity_md, all_machine_config_md, metadata_stats = data_generator.generate_metadata_dataset()
    data_generator.write_json(all_record_md, "/Users/pearl/Indaleko_updated/Indaleko/data_generator/results/test_records.json")

    converted_dict = data_generator.convert_dictionary_times(selected_md_attributes, True)


if __name__ == '__main__':
    main()
