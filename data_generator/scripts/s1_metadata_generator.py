import os, sys
from icecream import ic
from datetime import datetime
import random
import json
import copy
import re

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from typing import Dict, Any, Tuple, Union
from data_generator.scripts.metadata.posix_metadata import PosixMetadata
from data_generator.scripts.metadata.metadata import Metadata
from data_generator.scripts.metadata.machine_config_metadata import MachineConfigMetadata
from data_generator.scripts.metadata.music_activity_metadata import MusicActivityData
from data_generator.scripts.metadata.temp_activity_metadata import TempActivityData
from data_generator.scripts.metadata.geo_activity_metadata import GeoActivityData
from data_generator.scripts.metadata.semantic_metadata import SemanticMetadata
from collections import namedtuple

# Named tuple for fetching results
DataGeneratorResults = namedtuple('Results', [
    'record', 'semantics', 'geo_activity', 
    'temp_activity', 'music_activity', 'machine_config'
])

class Dataset_Generator():
    """
    Metadata Dataset Generator for given dictionary
    """
    def __init__(self, config: dict, default_lower_timestamp = datetime(2000, 10, 25), default_upper_timestamp = datetime.now(), 
                default_lower_filesize = 1, default_upper_filesize=10737418240):
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

        self.truth_list = []
        self.filler_list = []

        self.selected_AC_md = None
        self.selected_semantic_md = None
        self.selected_POSIX_md = None

        self.posix_generator = None
        self.temp_activity_generator = None
        self.music_activity_generator = None
        self.geo_activity_generator = None
        self.semantic_generator = None
        self.machine_config_generator = None
        self.has_semantic_truth = False
    
    def write_json(self, dataset: dict, json_path: str) -> None:
        """
        Writes the generated metadata to a json file
        """
        with open(json_path, 'w') as json_file:
            json.dump(dataset, json_file, indent=4)

    def initialize_dict(self, selected_md_attributes):
        self.selected_POSIX_md = selected_md_attributes.get("Posix", {})
        self.selected_AC_md = selected_md_attributes.get("Activity", {})
        self.selected_semantic_md = selected_md_attributes.get("Semantic", {})

        self.posix_generator = PosixMetadata(
            self.selected_POSIX_md,
            self.default_lower_filesize,
            self.default_upper_filesize,
            self.default_lower_timestamp,
            self.default_upper_timestamp
        )        
        self.temp_activity_generator = TempActivityData(self.selected_AC_md)
        self.music_activity_generator = MusicActivityData(self.selected_AC_md)
        self.geo_activity_generator = GeoActivityData(self.selected_AC_md)
        self.semantic_generator = SemanticMetadata(self.selected_semantic_md)
        self.machine_config_generator = MachineConfigMetadata()

    
    def generate_metadata_dataset(self, selected_md_attributes: dict[str, Any], save_files: bool, path: str):
        """Main function to generate metadata datasets"""

        # set dictionaries for each metadata:
        self.initialize_dict(selected_md_attributes)
        if self.selected_semantic_md:
            self.has_semantic_truth = True

        # calculate the total number of truth metadata attributes
        self.truth_attributes = (self._return_key_attributes(self.selected_POSIX_md) + 
                                self._return_key_attributes(self.selected_AC_md) + 
                                self._return_key_attributes(self.selected_semantic_md)
                                )

        total_truth_attributes = len(self.truth_attributes)

        # get the total number of truth-like metadata
        # only create truth-like metadata if the number of attributes is greater than one, otherwise, it becomes a truth file
        remaining_files = self.n_metadata_records - self.n_matching_queries
        
        if total_truth_attributes > 1:
            self.truth_like_num = random.randint(0, remaining_files)
        else:
            self.truth_like_num = 0
            
        filler_num = remaining_files - self.truth_like_num
        truth = self._generate_metadata(0, self.n_matching_queries+1, 'Truth File', True, False)
        filler = self._generate_metadata(self.truth_like_num,  filler_num +1, 'Filler File', False, False)
        truth_like_filler = self._generate_metadata(0, self.truth_like_num +1, 'Filler Truth-Like File', False, True)
 
        all_record = truth.record + truth_like_filler.record + filler.record
        all_semantics = truth.semantics + truth_like_filler.semantics + filler.semantics
        all_geo_activity = truth.geo_activity + truth_like_filler.geo_activity + filler.geo_activity
        all_temp_activity = truth.temp_activity + truth_like_filler.temp_activity + filler.temp_activity
        all_music_activity = truth.music_activity + truth_like_filler.music_activity + filler.music_activity
        all_machine_config = truth.machine_config + truth_like_filler.machine_config + filler.machine_config

        metadata_stats = {"truth": self.n_matching_queries, "filler": remaining_files, "truth_like": self.truth_like_num}

        if(save_files):
            # save the resulting dataset to a json file for future reference
            self.write_json(all_record, path + "records.json")
            self.write_json(all_geo_activity, path + "geo_activity.json")
            self.write_json(all_music_activity, path + "music_activity.json")
            self.write_json(all_temp_activity, path + "temp_activity.json")
            self.write_json(all_machine_config, path + "machine_config.json")
            self.write_json(all_semantics, path + "semantics.json")

        return all_record, all_geo_activity, all_temp_activity, all_music_activity,  all_machine_config, all_semantics, metadata_stats

    def _return_key_attributes(self, dictionary: Dict[str, Any]):
        """checks and return the keys of the dictionary as a list"""
        if dictionary == None:
            return []
        else:
            return list(dictionary.keys())
    
    def _add_truth_names(self, file_name: str, is_truth_file: bool):
        if is_truth_file:
            self.truth_list.append(file_name)
        else:
            self.filler_list.append(file_name)


    def _generate_metadata(self, current_filenum: int, max_num: int, key: str, is_truth_file: bool, truth_like: bool) -> DataGeneratorResults:
        """Generates the target metadata with the specified attributes based on the number of matching queries from config:"""
        all_metadata, all_semantics, all_geo_activity, all_temp_activity, all_music_activity, all_machine_configs = [], [], [], [], [], []

        for file_num in range(1, max_num):
            truthlike_attributes = self._get_truthlike_attributes(truth_like)
            
            key_name = self._generate_key_name(key, file_num, truth_like, truthlike_attributes)
            has_semantic_filler = self._has_semantic_attr(truthlike_attributes)
          
            file_size, file_name, path, URI, IO_UUID = self.posix_generator.generate_file_info(current_filenum, 
                                                                                                file_num, 
                                                                                                is_truth_file, 
                                                                                                truth_like, 
                                                                                                truthlike_attributes, 
                                                                                                self.has_semantic_truth, 
                                                                                                has_semantic_filler)
            
            self._add_truth_names(IO_UUID, is_truth_file)

            timestamps = self.posix_generator.generate_timestamps_md(is_truth_file, truth_like, truthlike_attributes)
            ic(timestamps)
            attribute =  self.posix_generator.generate_file_attributes(file_name, path, timestamps, file_size)
            record_data =  self.posix_generator.generate_record_data(IO_UUID, attribute)

            i_object =  self.posix_generator.generate_metadata(record_data, IO_UUID, timestamps, URI, file_size, 
                                                                None, key_name, 
                                                                current_filenum + file_num,
                                                                path)
            name, extension = file_name.split(".")
            semantic = self.semantic_generator.generate_metadata(record_data, IO_UUID, extension, 
                                                                                        timestamps["modified"].strftime("%Y-%m-%dT%H:%M:%S"), 
                                                                                        name,
                                                                                        is_truth_file, truth_like, 
                                                                                        truthlike_attributes, 
                                                                                        has_semantic_filler)
            geo_activity = self.geo_activity_generator.generate_metadata(record_data, timestamps, is_truth_file, truth_like, truthlike_attributes)
            temp_activity = self.temp_activity_generator.generate_metadata(record_data, timestamps, is_truth_file, truth_like, truthlike_attributes)
            music_activity = self.music_activity_generator.generate_metadata(record_data, timestamps, is_truth_file, truth_like, truthlike_attributes)
            machine_config = self.machine_config_generator.generate_metadata(record_data)

            # appending the objects to their lists
            all_metadata.append(Metadata.return_JSON(i_object))
            all_semantics.append(Metadata.return_JSON(semantic))
            all_geo_activity.append(Metadata.return_JSON(geo_activity))
            all_temp_activity.append(Metadata.return_JSON(temp_activity))
            all_music_activity.append(Metadata.return_JSON(music_activity))
            all_machine_configs.append(Metadata.return_JSON(machine_config))

        return DataGeneratorResults(all_metadata, all_semantics, all_geo_activity, all_temp_activity, all_music_activity, all_machine_configs)
    
    def _generate_key_name(self, key: str, n: int, truth_like: bool, truthlike_attributes: list[str]) -> str:
        """generates the key name for the metadata"""
        key_name = f"{key} #{n}"
        if truth_like:
            key_name += f", truth-like attributes: {truthlike_attributes}"
        return key_name

    def _has_semantic_attr(self, truthlike_attributes) -> bool:
        """checks whether there are any semantic attributes populated"""
        return any(attr.startswith("Content_") for attr in truthlike_attributes)


    def _get_truthlike_attributes(self, truth_like: bool) -> list[str]:
        """Returns a list of randomly selected truthlike attributes"""
        if truth_like:
            num_truthlike_attributes = random.randint(1, len(self.truth_attributes) -1)
            selected_truth_like_attr = random.sample(self.truth_attributes, k = num_truthlike_attributes)
            # this is done so that there are no semantic attributes in filler files that aren't text based when the text files are all specified in truth attributes
            return self._check_special_case(selected_truth_like_attr, num_truthlike_attributes);
        return []
    
    def _check_special_case(self, selected_truth_like_attr: list[str], num_truthlike_attributes: int):
        """checks the special case instance when there is semantic data queried but not text file extension"""
        is_all_text = self._check_truth_all_text()
        #If a semantic is not available i.e. file name is not chosen but Content is but file name specifis all text
        if not self._check_semantic_available(selected_truth_like_attr, is_all_text):
            # Case 1: Only posix (file name) and semantic specified in dictionary -> only file name allowed
            if len(self.selected_AC_md) == 0 and len(self.selected_POSIX_md) == 1 and len(self.selected_semantic_md) == 1:
                return ["file.name"]
            # Case 2: Other posix and semantic are availabe
            elif len(self.selected_POSIX_md) >= 1 and len(self.selected_semantic_md) >= 1:
                if num_truthlike_attributes == len(self.truth_attributes) - 1:
                    selected_truth_like_attr = [item for item in selected_truth_like_attr if "Content_" not in item]
                selected_truth_like_attr.append("file.name")
        return selected_truth_like_attr

    def _check_truth_all_text(self):
        """checks whether all metadata queried are all text files"""
        if "file.name" in self.selected_POSIX_md:
            if "extension" in self.selected_POSIX_md["file.name"]:
                true_extension = self.selected_POSIX_md["file.name"]["extension"]
                if set(Metadata.TEXT_FILE_EXTENSIONS) == set(true_extension):
                    return True
        return False
    
    def _check_semantic_available(self, selected_truth_attributes: list[str], is_all_text: bool) -> bool:
        """check if semantic avaiable in the truth like filler metadata"""
        if is_all_text and ("file.name" not in selected_truth_attributes) and any("Content_" in item for item in selected_truth_attributes):
            return False
        return True
    

def main():
    selected_md_attributes = {"Posix": {"file.name": {"extension": [".pdf", ".txt"]}, "timestamps": {"modified": {"starttime": "2025-01-29T00:00:00", "endtime": "2025-01-29T23:59:59", "command": "range"}, 
    "changed": {"starttime": "2025-01-31T00:00:00", "endtime": "2025-01-31T23:59:59", "command": "range"}}},
     "Activity": {
        "geo_location": {"location": {"latitude": 48.8566, "longitude": 2.3522}, "command": "at", "timestamp": "birthtime"}
        }
    }
    config_path = "data_generator/config/dg_config.json"
    with open(config_path, 'r') as file:
        config = json.load(file)
    data_generator = Dataset_Generator(config)
    #selected_md_attributes = data_generator.preprocess_dictionary_timestamps(selected_md_attributes, False)
    all_record, all_geo_activity, all_temp_activity, all_music_activity,  all_machine_config, all_semantics, metadata_stats = data_generator.generate_metadata_dataset(selected_md_attributes)
    converted_selected_md_attributes = copy.deepcopy(selected_md_attributes)
    ic(selected_md_attributes)
    converted_selected_md_attributes["Posix"] = data_generator.posix_generator.preprocess_dictionary_timestamps( True)
    ic(type(converted_selected_md_attributes["Posix"]["timestamps"]['modified']['endtime']))

    data_generator.write_json(all_semantics, "/Users/pearl/Indaleko_updated/Indaleko/data_generator/semantics_test.json")
    data_generator.write_json(all_geo_activity, "/Users/pearl/Indaleko_updated/Indaleko/data_generator/geo_activity.json")

    data_generator.write_json(all_record, "/Users/pearl/Indaleko_updated/Indaleko/data_generator/records_test.json")
if __name__ == '__main__':
    main()
