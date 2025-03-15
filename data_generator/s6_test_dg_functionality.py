import os, shutil, sys
from icecream import ic

if os.environ.get('INDALEKO_ROOT') is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, 'Indaleko.py')):
        current_path = os.path.dirname(current_path)
    os.environ['INDALEKO_ROOT'] = current_path
    sys.path.append(current_path)

from data_generator.scripts.metadata.posix_metadata import PosixMetadata
from data_generator.scripts.metadata.semantic_metadata import SemanticMetadata
from data_generator.scripts.metadata.geo_activity_metadata import GeoActivityData
from data_generator.scripts.metadata.music_activity_metadata import MusicActivityData
from data_generator.scripts.metadata.temp_activity_metadata import TempActivityData
from data_generator.scripts.metadata.activity_metadata import ActivityMetadata

from data_generator.scripts.s1_metadata_generator import Dataset_Generator
import unittest
from datetime import datetime
import re
from data_models.record import IndalekoRecordDataModel


class TestRandomDateGeneration(unittest.TestCase):
    def setUp(self):
        self.AC = ActivityMetadata({})
        self.default_lower_timestamp = datetime(2000, 10, 25)
        self.default_upper_timestamp = datetime.now()
        self.default_lower_filesize = 10
        self.default_upper_filesize = 100000
        self.record = IndalekoRecordDataModel.Config.json_schema_extra["example"]
    
    # def test_generate_random_date_filler_equal(self):
    #     starttime = "2025-01-02T12:00:00"
    #     endtime = "2025-01-02T12:00:00"
    #     command = "equal"

    #     selected_md_attributes = {"Posix": {"timestamps": {"birthtime": {"starttime": starttime, "endtime":endtime, "command": command}}}}
    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)

    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)

    #     for _ in range(100):  # Generate multiple random dates
    #         random_date = self.dg._generate_queried_timestamp(starttime, endtime, command, self.default_lower_timestamp, is_truth_file=False, is_birthtime = True)
            
    #         # The date must be within the range
    #         assert (starttime < random_date <= self.default_upper_timestamp) or (self.default_lower_timestamp <= random_date < starttime), f"Date {random_date} equal to truth!"

    # def test_generate_random_date_filler_range(self):
    #     starttime = "2025-01-02T12:00:00"
    #     endtime = "2025-01-02T13:30:00"
    #     command = "range"

    #     selected_md_attributes = {"Posix": {"timestamps": {"birthtime": {"starttime": starttime, "endtime":endtime, "command": command}}}}
    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)

    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)

    #     for _ in range(100):  # Generate multiple random dates
    #         random_date = self.dg._generate_queried_timestamp(starttime, endtime, command, self.default_lower_timestamp, is_truth_file=False, is_birthtime = True)
            
    #         # The date must be within the range
    #         assert (endtime < random_date <= self.default_upper_timestamp) or (self.default_lower_timestamp <= random_date < starttime), f"Date {random_date} equal to truth!"


    # def test_generate_random_date_truth_range(self):
    #     starttime = "2025-01-02T12:00:00"
    #     endtime = "2025-01-02T13:30:00"
    #     command = "range"

    #     selected_md_attributes = {"Posix": {"timestamps": {"birthtime": {"starttime": starttime, "endtime":endtime, "command": command}}}}
    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)

    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)

    #     for _ in range(100):  # Generate multiple random dates
    #         random_date = self.dg._generate_queried_timestamp(starttime, endtime, command, self.default_lower_timestamp, is_truth_file=True, is_birthtime = True)
            
    #         # The date must be within the range
    #         assert (starttime == random_date), f"Date {random_date} equal to truth!"

    # def test_generate_random_date_truth_equal(self):
    #     starttime = "2025-01-02T12:00:00"
    #     endtime = "2025-01-02T12:00:00"
    #     command = "equal"

    #     selected_md_attributes = {"Posix": {"timestamps": {"birthtime": {"starttime": starttime, "endtime":endtime, "command": command}}}}
    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)

    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)

    #     for _ in range(100):  # Generate multiple random dates
    #         random_date = self.dg._generate_queried_timestamp(starttime, endtime, command, self.default_lower_timestamp, is_truth_file=True, is_birthtime = True)
            
    #         # The date must be within the range
    #         assert (starttime <= random_date <= endtime), f"Date {random_date} equal to truth!"

    # def test_generate_random_date_filler_start_changed(self):
    #     starttime = "2025-01-02T12:00:00"
    #     endtime = "2025-01-02T12:00:00"
    #     command = "equal"

    #     changed_stime = "2025-01-01T12:00:00"
    #     changed_etime = "2025-01-03T12:00:00"
    #     changed_command = "range"

    #     selected_md_attributes = {"Posix": {"timestamps": {"birthtime": {"starttime": starttime, "endtime": endtime, "command": command}, 
    #     "changed": {"starttime": changed_stime, "endtime": changed_etime, "command": changed_command}}}}

    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)

    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)
    #     changed_stime = self.dg._convert_str_datetime(changed_stime)
    #     changed_etime = self.dg._convert_str_datetime(changed_etime)

    #     for _ in range(100):  # Generate multiple random dates
    #         random_birthdate = self.dg._generate_queried_timestamp(starttime, endtime, command, self.default_lower_timestamp, is_truth_file=False, is_birthtime = True)
    #         random_changedate = self.dg._generate_queried_timestamp(changed_stime, changed_etime, changed_command, random_birthdate, is_truth_file=False, is_birthtime = False)

    #         # The date must be within the range
    #         assert (starttime < random_birthdate <= self.default_upper_timestamp) or (self.default_lower_timestamp <= random_birthdate < starttime), f"Date {random_birthdate} equal to truth!"
    #         assert (changed_etime < random_changedate <= self.default_upper_timestamp) or (random_birthdate <= random_changedate < changed_stime), f"Date {random_changedate} equal to truth!"
    #         assert (random_birthdate <= random_changedate <= self.default_upper_timestamp), f"Date {random_changedate} is before {random_birthdate}!"
    
    # def test_generate_random_date_filler_start_lowerbound(self):
    #     starttime = "2000-10-25T00:00:00"
    #     endtime = "2000-10-25T00:00:00"
    #     command = "equal"


    #     selected_md_attributes = {"Posix": {"timestamps": {"birthtime": {"starttime": starttime, "endtime": endtime, "command": command}}}}

    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)

    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)

    #     for _ in range(1000):  # Generate multiple random dates
    #         random_birthdate = self.dg._generate_queried_timestamp(starttime, endtime, command, self.default_lower_timestamp, is_truth_file=False, is_birthtime = True)

    #         # The date must be within the range
    #         ic(random_birthdate)
    #         assert (starttime < random_birthdate <= self.default_upper_timestamp) or (self.default_lower_timestamp < random_birthdate < starttime), f"Date {random_birthdate} equal to truth!"
    
    # def test_generate_random_date_filler_start_lowerbound(self):
    #     starttime = "2020-10-25T00:00:00"
    #     endtime = "2020-10-25T00:00:00"
    #     command = "equal"


    #     selected_md_attributes = {"Posix": {"timestamps": {"birthtime": {"starttime": starttime, "endtime": endtime, "command": command}}}}

    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)

    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)

    #     for _ in range(1000):  # Generate multiple random dates
    #         random_birthdate = self.dg._generate_queried_timestamp(starttime, endtime, command, self.default_lower_timestamp, is_truth_file=False, is_birthtime = True)

    #         # The date must be within the range
    #         ic(random_birthdate)
    #         assert (endtime < random_birthdate <= self.default_upper_timestamp) or (self.default_lower_timestamp < random_birthdate < starttime), f"Date {random_birthdate} equal to truth!"
    
    # def test_fail_when_non_birthtime_timestamp_earlier(self):
    #     starttime = "2025-01-02T12:00:00"
    #     endtime = "2025-01-02T12:00:00"
    #     command = "equal"

    #     changed_stime = "2025-01-01T12:00:00"
    #     changed_etime = "2025-01-01T14:00:00"
    #     changed_command = "range"

    #     selected_md_attributes = {"Posix": {"timestamps": {"birthtime": {"starttime": starttime, "endtime": endtime, "command": command}, 
    #     "changed": {"starttime": changed_stime, "endtime": changed_etime, "command": changed_command}}}}

    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)

    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)
    #     changed_stime = self.dg._convert_str_datetime(changed_stime)
    #     changed_etime = self.dg._convert_str_datetime(changed_etime)


    #     try:
    #         birth = self.dg._generate_queried_timestamp(starttime, endtime, command, self.default_lower_timestamp, is_truth_file=False, is_birthtime = True)
    #         random_changedate = self.dg._generate_queried_timestamp(changed_stime, changed_etime, changed_command, birth, is_truth_file=False, is_birthtime = False)

    #         ic(birth)
    #         ic(random_changedate)
    #     except Exception as e:
    #         ic("here")
    #         print(f"Error: {e}")

    # def test_for_overlapping_timestamp(self):
    #     starttime = "2025-01-02T12:00:00"
    #     endtime = "2025-01-03T12:00:00"
    #     command = "range"

    #     changed_stime = "2025-01-01T12:00:00"
    #     changed_etime = "2025-01-02T14:00:00"
    #     changed_command = "range"

    #     modified_stime = "2025-01-01T10:00:00"
    #     modified_etime = "2025-01-02T16:00:00"
    #     modified_command = "range"
        


    #     selected_md_attributes = {"Posix": {"timestamps": {"birthtime": {"starttime": starttime, "endtime": endtime, "command": command}, 
    #     "changed": {"starttime": changed_stime, "endtime": changed_etime, "command": changed_command},  "modified": {"starttime": modified_stime, "endtime": modified_etime, "command": modified_command}}}}

    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)


    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)
    #     changed_stime = self.dg._convert_str_datetime(changed_stime)
    #     changed_etime = self.dg._convert_str_datetime(changed_etime)
    #     modified_stime = self.dg._convert_str_datetime(modified_stime)
    #     modified_etime = self.dg._convert_str_datetime(modified_etime)


    #     for _ in range(1000):  # Generate multiple random dates
    #         timestamps = self.dg._generate_timestamps(False)
    #         random_birthdate = timestamps["birthtime"]
    #         random_changedate = timestamps["changed"]
    #         random_accessed = timestamps["accessed"]
    #         random_modified = timestamps["modified"]


    #         # The date must be within the range
    #         assert (modified_etime < random_modified <= self.default_upper_timestamp) or (random_birthdate <= random_modified < modified_stime), f"Date {random_modified} equal to truth!"
    #         assert (starttime < random_birthdate <= self.default_upper_timestamp) or (self.default_lower_timestamp <= random_birthdate < starttime), f"Date {random_birthdate} equal to truth!"
    #         assert (changed_etime < random_changedate <= self.default_upper_timestamp) or (random_birthdate <= random_changedate < changed_stime), f"Date {random_changedate} equal to truth!"
    #         assert self.default_lower_timestamp <= random_birthdate <= self.default_upper_timestamp, f"Birthdate {random_birthdate} is before the lower timestamp!"
    #         assert random_birthdate <= random_changedate <= self.default_upper_timestamp, f"Change date {random_changedate} is before birthdate {random_birthdate}!"
    #         assert random_birthdate <= random_modified <= self.default_upper_timestamp, f"Modified date {random_modified} is before change date {random_changedate}!"
    #         assert random_birthdate <= random_accessed <= self.default_upper_timestamp, f"Accessed date {random_accessed} is before modified date {random_modified}!"
    @unittest.skip("Skipping test overlapping timestamp filler")

    def test_for_filler_bounds(self):
   
        starttime = "2000-10-25T12:00:00"
        endtime = "2000-10-29T18:00:00"
        command = "range"

        changed_stime = "2025-01-01T12:00:00"
        changed_etime = "2025-01-02T14:00:00"

        modified_stime = "2025-01-01T10:00:00"
        modified_etime = "2025-01-02T16:00:00"

        accessed_stime = "2025-01-02T10:00:00"
        accessed_etime = "2025-01-02T15:00:00"
        selected_md_attributes = {"timestamps": {
                "birthtime": {"starttime": starttime, "endtime": endtime, "command": command}, 
                "changed": {"starttime": changed_stime, "endtime": changed_etime, "command": command},
                "modified": {"starttime": modified_stime, "endtime": modified_etime, "command": command},
                "accessed": {"starttime": accessed_stime, "endtime": accessed_etime, "command": command}
                }
            }
        
        self.posix = PosixMetadata(selected_md_attributes, self.default_lower_filesize, self.default_upper_filesize, self.default_lower_timestamp, self.default_upper_timestamp)
        starttime = self.posix._convert_str_datetime(starttime)
        endtime = self.posix._convert_str_datetime(endtime)
        changed_stime = self.posix._convert_str_datetime(changed_stime)
        changed_etime = self.posix._convert_str_datetime(changed_etime)
        modified_stime = self.posix._convert_str_datetime(modified_stime)
        modified_etime = self.posix._convert_str_datetime(modified_etime)
        accessed_stime = self.posix._convert_str_datetime(accessed_stime)
        accessed_etime = self.posix._convert_str_datetime(accessed_etime)


        timestamps = self.posix._generate_timestamps(False)
        random_birthdate = timestamps["birthtime"]
        random_changedate = timestamps["changed"]
        random_accessed = timestamps["accessed"]
        random_modified = timestamps["modified"]

        for _ in range(100):  # Generate multiple random dates
            timestamps = self.posix._generate_timestamps(False)
            random_birthdate = timestamps["birthtime"]
            random_changedate = timestamps["changed"]
            random_accessed = timestamps["accessed"]
            random_modified = timestamps["modified"]

            # The date must be within the range
            assert (modified_etime < random_modified <= self.default_upper_timestamp) or (random_birthdate <= random_modified < modified_stime), f"Date {random_modified} equal to truth!"
            assert (starttime < random_birthdate <= self.default_upper_timestamp) or (self.default_lower_timestamp <= random_birthdate < starttime), f"Date {random_birthdate} equal to truth!"
            assert (changed_etime < random_changedate <= self.default_upper_timestamp) or (random_birthdate <= random_changedate < changed_stime), f"Date {random_changedate} equal to truth!"
            assert self.default_lower_timestamp <= random_birthdate <= self.default_upper_timestamp, f"Birthdate {random_birthdate} is before the lower timestamp!"
            assert random_birthdate <= random_changedate <= self.default_upper_timestamp, f"Change date {random_changedate} is before birthdate {random_birthdate}!"
            assert random_birthdate <= random_modified <= self.default_upper_timestamp, f"Modified date {random_modified} is before change date {random_changedate}!"
            assert random_birthdate <= random_accessed <= self.default_upper_timestamp, f"Accessed date {random_accessed} is before modified date {random_modified}!"
    
    
    def test_for_overlapping_timestamp_filler(self):
   
        starttime = "2025-01-01T12:00:00"
        endtime = "2025-01-03T12:00:00"
        command = "range"

        changed_stime = "2025-01-01T12:00:00"
        changed_etime = "2025-01-02T14:00:00"

        modified_stime = "2025-01-01T10:00:00"
        modified_etime = "2025-01-02T16:00:00"

        accessed_stime = "2025-01-02T10:00:00"
        accessed_etime = "2025-01-02T15:00:00"
        selected_md_attributes = {"timestamps": {
                "birthtime": {"starttime": starttime, "endtime": endtime, "command": command}, 
                "changed": {"starttime": changed_stime, "endtime": changed_etime, "command": command},
                "modified": {"starttime": modified_stime, "endtime": modified_etime, "command": command},
                "accessed": {"starttime": accessed_stime, "endtime": accessed_etime, "command": command}
                }
            }
        
        self.posix = PosixMetadata(selected_md_attributes, self.default_lower_filesize, self.default_upper_filesize, self.default_lower_timestamp, self.default_upper_timestamp)
        starttime = self.posix._convert_str_datetime(starttime)
        endtime = self.posix._convert_str_datetime(endtime)
        changed_stime = self.posix._convert_str_datetime(changed_stime)
        changed_etime = self.posix._convert_str_datetime(changed_etime)
        modified_stime = self.posix._convert_str_datetime(modified_stime)
        modified_etime = self.posix._convert_str_datetime(modified_etime)
        accessed_stime = self.posix._convert_str_datetime(accessed_stime)
        accessed_etime = self.posix._convert_str_datetime(accessed_etime)


        timestamps = self.posix._generate_timestamps(False)
        random_birthdate = timestamps["birthtime"]
        random_changedate = timestamps["changed"]
        random_accessed = timestamps["accessed"]
        random_modified = timestamps["modified"]

        for _ in range(100):  # Generate multiple random dates
            timestamps = self.posix._generate_timestamps(False)
            random_birthdate = timestamps["birthtime"]
            random_changedate = timestamps["changed"]
            random_accessed = timestamps["accessed"]
            random_modified = timestamps["modified"]

            # The date must be within the range
            assert (modified_etime < random_modified <= self.default_upper_timestamp) or (random_birthdate <= random_modified < modified_stime), f"Date {random_modified} equal to truth!"
            assert (starttime < random_birthdate <= self.default_upper_timestamp) or (self.default_lower_timestamp <= random_birthdate < starttime), f"Date {random_birthdate} equal to truth!"
            assert (changed_etime < random_changedate <= self.default_upper_timestamp) or (random_birthdate <= random_changedate < changed_stime), f"Date {random_changedate} equal to truth!"
            assert self.default_lower_timestamp <= random_birthdate <= self.default_upper_timestamp, f"Birthdate {random_birthdate} is before the lower timestamp!"
            assert random_birthdate <= random_changedate <= self.default_upper_timestamp, f"Change date {random_changedate} is before birthdate {random_birthdate}!"
            assert random_birthdate <= random_modified <= self.default_upper_timestamp, f"Modified date {random_modified} is before change date {random_changedate}!"
            assert random_birthdate <= random_accessed <= self.default_upper_timestamp, f"Accessed date {random_accessed} is before modified date {random_modified}!"
    
    @unittest.skip("Skipping test overlapping timestamp filler")
    def test_for_boundary_timestamp_truth(self):
        starttime = "2000-10-25T12:00:00"
        endtime = "2001-01-03T12:00:00"
        command = "range"

        changed_stime = "2025-01-01T12:00:00"
        changed_etime = "2025-01-02T14:00:00"

        modified_stime = "2025-01-01T10:00:00"
        modified_etime = "2025-01-02T16:00:00"

        accessed_stime = "2025-01-02T10:00:00"
        accessed_etime = "2025-01-02T15:00:00"
        selected_md_attributes = {"timestamps": {
                "birthtime": {"starttime": starttime, "endtime": endtime, "command": command}, 
                "changed": {"starttime": changed_stime, "endtime": changed_etime, "command": command},
                "modified": {"starttime": modified_stime, "endtime": modified_etime, "command": command},
                "accessed": {"starttime": accessed_stime, "endtime": accessed_etime, "command": command}
                }
            }
        
        self.posix = PosixMetadata(selected_md_attributes, self.default_lower_filesize, self.default_upper_filesize, self.default_lower_timestamp, self.default_upper_timestamp)
        starttime = self.posix._convert_str_datetime(starttime)
        endtime = self.posix._convert_str_datetime(endtime)
        changed_stime = self.posix._convert_str_datetime(changed_stime)
        changed_etime = self.posix._convert_str_datetime(changed_etime)
        modified_stime = self.posix._convert_str_datetime(modified_stime)
        modified_etime = self.posix._convert_str_datetime(modified_etime)
        accessed_stime = self.posix._convert_str_datetime(accessed_stime)
        accessed_etime = self.posix._convert_str_datetime(accessed_etime)


        timestamps = self.posix._generate_timestamps(True)
        random_birthdate = timestamps["birthtime"]
        random_changedate = timestamps["changed"]
        random_accessed = timestamps["accessed"]
        random_modified = timestamps["modified"]

        for _ in range(100):  # Generate multiple random dates
            timestamps = self.posix._generate_timestamps(True)
            random_birthdate = timestamps["birthtime"]
            random_changedate = timestamps["changed"]
            random_accessed = timestamps["accessed"]
            random_modified = timestamps["modified"]
            # The date must be within the range
            assert (modified_stime <= random_modified <= modified_etime and random_birthdate <= random_modified), f"modified {random_modified} not within truth!"
            assert (changed_stime <= random_changedate <= changed_etime and random_birthdate <= random_changedate), f"changed {random_changedate} not within truth!"
            assert (accessed_stime <= random_accessed <= accessed_etime and random_birthdate <= random_birthdate), f"accessed {random_accessed} not within truth!"
            assert (starttime <= random_birthdate <= endtime and starttime <= random_birthdate <= endtime), f"birthdate {random_birthdate} not within truth!"
    
    def test_file_size_range(self):
        selected_md_attributes = {
        "file.size": {
            "target_min": 10,
            "target_max": 1000,
            "command": "range"
         }
        }
        
        self.posix = PosixMetadata(selected_md_attributes, self.default_lower_filesize, self.default_upper_filesize, self.default_lower_timestamp, self.default_upper_timestamp)

        for _ in range(100):  # Generate multiple random dates
            truth_size = self.posix._generate_file_size(True)
            assert selected_md_attributes["file.size"]["target_min"] <= truth_size <= selected_md_attributes["file.size"]["target_max"], f"file size {truth_size} not within the range!"
            filler_size = self.posix._generate_file_size(False)
            assert selected_md_attributes["file.size"]["target_min"] > filler_size or filler_size > selected_md_attributes["file.size"]["target_max"] , f"file size {filler_size} not within the range!"

    def test_file_size_exactly(self):
        selected_md_attributes = {
        "file.size": {
            "target_min": 1000,
            "target_max": 1000,
            "command": "equal"
         }
        }
        
        self.posix = PosixMetadata(selected_md_attributes, self.default_lower_filesize, self.default_upper_filesize, self.default_lower_timestamp, self.default_upper_timestamp)

        for _ in range(100):  # Generate multiple random dates
            truth_size = self.posix._generate_file_size(True)
            assert selected_md_attributes["file.size"]["target_min"] == truth_size, f"file size {truth_size} not {selected_md_attributes['file.size']['target_min']}!"
            filler_size = self.posix._generate_file_size(False)
            assert selected_md_attributes["file.size"]["target_min"] > filler_size or filler_size > selected_md_attributes["file.size"]["target_max"] , f"file size {filler_size}  within the range!"


    def test_naming_w_dir(self):
        selected_md_attributes = {
        "file.name": {
            "pattern": "essay",
            "command": "exactly",
            "extension": [
                ".pdf"
            ]
         }, "file.directory" : {
            "location": "local",
            "local_dir_name": "file"
            
         }
        }
        
        self.posix = PosixMetadata(selected_md_attributes, self.default_lower_filesize, self.default_upper_filesize, self.default_lower_timestamp, self.default_upper_timestamp)

        for _ in range(100):  # Generate multiple random dates
            truth_path, URI, truth_name = self.posix._generate_dir_location("essay.pdf", True)
            assert re.search(r"essay(?: \(\d+\))?", truth_name), f"file name {truth_name} doesn't contain 'essay'!"
            assert re.search(r"/file/essay(?: \(\d+\))?", truth_path), f"path {truth_path} doesn't contain 'essay'!"

            filler_name = self.posix._generate_file_name(False, False, False)
            filler_path, URI, filler_name = self.posix._generate_dir_location(filler_name, True)
            assert not re.search(r"essay(?: \(\d+\))?", filler_name), f"file name {filler_name} doesn't contain 'essay'!"
            assert not re.search(r"/file/essay(?: \(\d+\))?", filler_path), f"path {filler_path} doesn't contain 'essay'!"


    def test_naming_exactly(self):
        selected_md_attributes = {
        "file.name": {
            "pattern": "essay",
            "command": "exactly",
            "extension": [
                ".pdf"
            ]
         }
        }
        
        self.posix = PosixMetadata(selected_md_attributes, self.default_lower_filesize, self.default_upper_filesize, self.default_lower_timestamp, self.default_upper_timestamp)

        for _ in range(100):  # Generate multiple random dates
            truth_name = self.posix._generate_file_name(True, False, False)
            assert re.search(r"essay(?: \(\d+\))?", truth_name), f"file name {truth_name} doesn't contain 'essay'!"

            filler_name = self.posix._generate_file_name(False, False, False)
            assert not re.search(r"essay(?: \(\d+\))?", filler_name), f"file name {filler_name} shouldn't contain 'essay'!"

    def test_naming_contains(self):
        selected_md_attributes = {
        "file.name": {
            "pattern": "essay",
            "command": "contains",
            "extension": [
                ".pdf"
            ]
         }
        }
        
        self.posix = PosixMetadata(selected_md_attributes, self.default_lower_filesize, self.default_upper_filesize, self.default_lower_timestamp, self.default_upper_timestamp)

        for _ in range(100):  # Generate multiple random dates
            truth_name = self.posix._generate_file_name(True, False, False)
            assert selected_md_attributes["file.name"]["pattern"] in truth_name, f"file name {truth_name} doesn't contain 'essay'!"

            filler_name = self.posix._generate_file_name(False, False, False)
            assert not selected_md_attributes["file.name"]["pattern"] in filler_name, f"file name {filler_name} shouldn't contain 'essay'!"

    def test_semantics_contains(self):
        selected_md_attributes = {
        "Content_1": [
            "Title",
            "CPSC 300 Essay"
        ],
        "Content_2": [
            "Link",
            "Into"
        ], 
        "Content_3": [
            "EmailAddress",
            "j@gmail.com"
        ],
        "Content_4": [
            "Form",
            "apple: pie"
        ], "Content_5": [
            "PageNumber",
            5
        ], "Content_6": [
            "Checked",
            True
        ], "Content_7": [
            "Image",
            "duck.png"
        ], "Content_8": [
            "Text",
            "I went to the mall yesterday to buy a ......"
        ], "Content_9": [
            "Address",
            "Vancouver, BC"
        ]
        }
        
        self.sem = SemanticMetadata(selected_md_attributes)

        for _ in range(100):  # Generate multiple random dates
            truth_title = self.sem._generate_long_tags(True, selected_md_attributes["Content_1"][0])
            assert selected_md_attributes["Content_1"][0] in truth_title, f"file {truth_title} doesn't contain 'essay'!"

            filler_name = self.sem._generate_long_tags(False, selected_md_attributes["Content_1"][0])
            assert not  selected_md_attributes["Content_1"][0] in filler_name, f"file {filler_name} doesn't contain 'essay'!"

    def test_music_spotify_id(self):
        selected_md_attributes = {
        "Content_1": [
            "Title",
            "CPSC 300 Essay"
        ],
        "Content_2": [
            "Link",
            "Into"
        ], 
        "Content_3": [
            "EmailAddress",
            "j@gmail.com"
        ],
        "Content_4": [
            "Form",
            "apple: pie"
        ], "Content_5": [
            "PageNumber",
            5
        ], "Content_6": [
            "Checked",
            True
        ], "Content_7": [
            "Image",
            "duck.png"
        ], "Content_8": [
            "Text",
            "I went to the mall yesterday to buy a ......"
        ], "Content_9": [
            "Address",
            "Vancouver, BC"
        ]
        }
        
        self.sem = SemanticMetadata(selected_md_attributes)

        for _ in range(100):  # Generate multiple random dates
            truth_title = self.sem._generate_long_tags(True, selected_md_attributes["Content_1"][0])
            assert selected_md_attributes["Content_1"][0] in truth_title, f"file {truth_title} doesn't contain 'essay'!"

            filler_name = self.sem._generate_long_tags(False, selected_md_attributes["Content_1"][0])
            assert not  selected_md_attributes["Content_1"][0] in filler_name, f"file {filler_name} doesn't contain 'essay'!"
    
    def test_spotify_device(self):
        music_dict= {"ambient_music": {
            "track_name": "Happy song",
            "artist_name": "Will",
            "playback_position_ms": 2000,
            "track_duration_ms": 30000,
            "is_currently_playing": True,
            "album_name":"H",
            "source":"youtube music",
            "timestamp": "birthtime"
        }
}
        self.music_ac = MusicActivityData(music_dict)

        truth_id_track = self.music_ac._create_spotify_id(True, "track", music_dict["ambient_music"]["track_name"])
        assert "spotify:track:Happysong" + ("0"* 13) == truth_id_track , f"truth spotify id: {truth_id_track} isn't in the right format!"
        
        filler_id_track = self.music_ac._create_spotify_id(False, "track", music_dict["ambient_music"]["track_name"])
        assert "spotify:track:Happysong" + ("0"* 13) != filler_id_track , f"filler spotify id: {truth_id_track} has attribute of the truth ids!"
        
       
    def test_geo_at(self):
        selected_geo_md ={"geo_location": {
            "location": "Langley, BC",
            "command": "at",
            "timestamp": "birthtime"
         }
        }
        self.geo = GeoActivityData(selected_geo_md)
        truth_loc = self.geo._generate_geo_context(True)

        filler_loc = self.geo._generate_geo_context(False)
        assert  truth_loc["latitude"] < filler_loc["latitude"] <= self.geo.DEFAULT_MAX_LAT or self.geo.DEFAULT_MIN_LAT <= filler_loc["latitude"] < truth_loc["latitude"], f"filler geo lat {filler_loc['latitude']} isn't within bounds!"
        assert  truth_loc['longitude'] < filler_loc['longitude'] <= self.geo.DEFAULT_MAX_LONG or self.geo.DEFAULT_MIN_LONG <= filler_loc['longitude'] < truth_loc['longitude'], f"filler geo long {filler_loc['longitude']} isn't within bounds!"
        assert  truth_loc['altitude'] < filler_loc['altitude'] <= self.geo.DEFAULT_MAX_ALT or self.geo.DEFAULT_MIN_ALT <= filler_loc['altitude'] < truth_loc['altitude'], f"filler geo altitude {filler_loc['altitude']} isn't within bounds!"
    
    def test_geo_within(self):
        selected_geo_md = {"geo_location": {
            "location": "Langley, BC",
            "command": "within",
            "km": 2,
            "timestamp": "birthtime"
            }
        }
        self.geo = GeoActivityData(selected_geo_md)
        self.geo._generate_geo_context(True)
        ic(self.geo.saved_geo_loc)
        truth_loc = self.geo.saved_geo_loc
        for _ in range(1000):  # Generate multiple random dates
            filler_loc = self.geo._generate_geo_context(False)
            assert  truth_loc["latitude"][1] < filler_loc["latitude"] <= self.geo.DEFAULT_MAX_LAT or self.geo.DEFAULT_MIN_LAT <= filler_loc["latitude"] < truth_loc["latitude"][0], f"filler geo lat {filler_loc['latitude']} isn't within bounds!"
            assert  truth_loc['longitude'][1] < filler_loc['longitude'] <= self.geo.DEFAULT_MAX_LONG or self.geo.DEFAULT_MIN_LONG <= filler_loc['longitude'] < truth_loc['longitude'][0], f"filler geo long {filler_loc['longitude']} isn't within bounds!"
            assert  truth_loc['altitude'] < filler_loc['altitude'] <= self.geo.DEFAULT_MAX_ALT or self.geo.DEFAULT_MIN_ALT <= filler_loc['altitude'] < truth_loc['altitude'], f"filler geo altitude {filler_loc['altitude']} isn't within bounds!"


    def test_choose_random_element(self):
        lists = ["happy", "sad" , "angry"]


        for _ in range(100):  # Generate multiple random dates
            truth_element = self.AC._choose_random_element(True, "happy", lists)
            filler_element = self.AC._choose_random_element(False, "happy", lists)
            assert  truth_element == "happy", f"truth element {truth_element} doesn't match!"
            assert  filler_element == "sad" or filler_element == "angry", f"filler element {filler_element} shouldn't match truth!"

    def test_generate_ac_timestamp(self):
        pass 
    def test_generate_number(self):
        lists = ["happy", "sad" , "angry"]


        for _ in range(100):  # Generate multiple random dates
            truth_element = self.AC._choose_random_element(True, "happy", lists)
            filler_element = self.AC._choose_random_element(False, "happy", lists)
            assert  truth_element == "happy", f"truth element {truth_element} doesn't match!"
            assert  filler_element == "sad" or filler_element == "angry", f"filler element {filler_element} shouldn't match truth!"
 

    def test_generate_number(self):
        dict = {
                "start": 15.0,
                "end": 15.0,
                "command": "equal",
            }

        number_eq = self.AC._generate_number(True, dict, -100, 100)
        assert number_eq == dict["start"], f"truth element {number_eq} doesn't match!"

        number_eq_f = self.AC._generate_number(False, dict, -100, 100)
        assert -100 < number_eq_f < dict["start"] or dict["start"] < number_eq_f < 100, f"truth element {number_eq_f} doesn't match!"

        dict2 = {
                "start": -32.1,
                "end": 15.0,
                "command": "range",
            }
        number_range = self.AC._generate_number(True, dict, -100, 100)
        assert dict2["start"] <= number_range <= dict2["end"], f"truth element {number_range} doesn't match!"
        
        number_range_f = self.AC._generate_number(False, dict, -100, 100)
        assert -100 < number_range_f < dict["start"] or dict["end"] < number_range_f < 100, f"truth element {number_range_f} doesn't match!"

    
     


    # def test_for_boundary_timestamp_filler(self):
    #     starttime = "2000-10-25T00:00:00"
    #     endtime = "2000-10-25T12:19:00"
    #     command = "range"

    #     changed_stime = "2025-01-22T05:20:00"
    #     changed_etime = "2025-01-22T05:21:00"
    #     changed_command = "range"

    #     modified_stime = "2025-01-01T10:00:00"
    #     modified_etime = "2025-01-02T16:00:00"
    #     modified_command = "range"

    #     accessed_stime = "2025-01-02T10:00:00"
    #     accessed_etime = "2025-01-02T12:00:00"
    #     accessed_command = "range"
        


    #     selected_md_attributes = {"Posix": 
    #         {"timestamps": {
    #             "birthtime": {"starttime": starttime, "endtime": endtime, "command": command}, 
    #             "changed": {"starttime": changed_stime, "endtime": changed_etime, "command": changed_command},
    #             "modified": {"starttime": modified_stime, "endtime": modified_etime, "command": modified_command},
    #             "accessed": {"starttime": accessed_stime, "endtime": accessed_etime, "command": accessed_command}
    #             }
    #         }
    #     }

    #     self.dg.convert_dictionary_times(selected_md_attributes, False)
    #     self.dg.set_selected_md_attributes(selected_md_attributes)


    #     starttime = self.dg._convert_str_datetime(starttime)
    #     endtime = self.dg._convert_str_datetime(endtime)
    #     changed_stime = self.dg._convert_str_datetime(changed_stime)
    #     changed_etime = self.dg._convert_str_datetime(changed_etime)
    #     modified_stime = self.dg._convert_str_datetime(modified_stime)
    #     modified_etime = self.dg._convert_str_datetime(modified_etime)
    #     accessed_stime = self.dg._convert_str_datetime(accessed_stime)
    #     accessed_etime = self.dg._convert_str_datetime(accessed_etime)


    #     for _ in range(100000):  # Generate multiple random dates
    #         timestamps = self.dg._generate_timestamps(False)
    #         random_birthdate = timestamps["birthtime"]
    #         random_changedate = timestamps["changed"]
    #         random_accessed = timestamps["accessed"]
    #         random_modified = timestamps["modified"]

    #         # The date must be within the range
    #         assert (self.default_lower_timestamp <= random_modified < modified_stime or random_modified > modified_etime and random_birthdate <= random_modified), f"modified {random_modified} not within truth!{random_birthdate}"
    #         assert (self.default_lower_timestamp <= random_changedate < changed_stime or random_changedate > changed_etime and random_birthdate <= random_changedate), f"changed {random_changedate} not within truth! birthdate: {random_birthdate}"
    #         assert (self.default_lower_timestamp <= random_accessed < accessed_stime or random_accessed > accessed_etime and random_birthdate <= random_accessed), f"accessed {random_accessed} not within truth!{random_birthdate}"
    #         assert (self.default_lower_timestamp <= random_birthdate < starttime or random_birthdate > endtime), f"birthtime {random_birthdate} not within truth!"
          
 
    # def test_dates_within_range(self):
    #     # Access variables set in setUp
    #     random_date = self.start_date  # Replace with actual generation logic
    #     self.assertGreaterEqual(random_date, self.start_date)
    #     self.assertLessEqual(random_date, self.end_date)

    # def test_another_property(self):
    #     # Access variables set in setUp
    #     self.assertEqual(self.start_date.year, 2025)

if __name__ == "__main__":
    unittest.main()
