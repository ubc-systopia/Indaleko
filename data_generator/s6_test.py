import unittest
from datetime import datetime
import random
from data_generator.scripts.metadata.activity_metadata import ActivityMetadata

class TestGenerateAcTimestamp(unittest.TestCase):
    def setUp(self):
        self.instance = ActivityMetadata({  # Instantiate the actual class
            "login": {"timestamp": "birthtime"},
            "logout": {"timestamp": "modified"}
        })
        self.timestamps = {
            "birthtime": datetime(2024, 3, 10, 12, 0, 0),
            "modified": datetime(2024, 3, 10, 13, 0, 0),
            "accessed": datetime(2024, 3, 10, 14, 0, 0),
            "changed": datetime(2024, 3, 10, 15, 0, 0)
        }

    def test_truth_file_with_valid_activity_type(self):
        result = self.instance._generate_ac_timestamp(True, self.timestamps, "login")
        self.assertEqual(result, "2024-03-10T12:00:00Z")
    
    def test_non_truth_file_with_valid_activity_type(self):
        random.seed(0)  # Ensure deterministic choice
        result = self.instance._generate_ac_timestamp(False, self.timestamps, "login")
        self.assertIn(result, ["2024-03-10T13:00:00Z", "2024-03-10T14:00:00Z", "2024-03-10T15:00:00Z"])  # birthtime should be removed
    
    def test_truth_file_with_invalid_activity_type(self):
        random.seed(0)  # Ensure deterministic choice
        result = self.instance._generate_ac_timestamp(True, self.timestamps, "unknown_activity")
        self.assertIn(result, ["2024-03-10T12:00:00Z", "2024-03-10T13:00:00Z", "2024-03-10T14:00:00Z", "2024-03-10T15:00:00Z"]) 
    
    def test_non_truth_file_with_invalid_activity_type(self):
        random.seed(1)  # Ensure deterministic choice
        result = self.instance._generate_ac_timestamp(False, self.timestamps, "unknown_activity")
        self.assertIn(result, ["2024-03-10T12:00:00Z", "2024-03-10T13:00:00Z", "2024-03-10T14:00:00Z", "2024-03-10T15:00:00Z"]) 
    
    def test_missing_timestamp_key_in_truth_file(self):
        self.instance.selected_md = {"login": {}}  # No "timestamp" key
        random.seed(0)
        result = self.instance._generate_ac_timestamp(True, self.timestamps, "login")
        self.assertIn(result, ["2024-03-10T12:00:00Z", "2024-03-10T13:00:00Z", "2024-03-10T14:00:00Z", "2024-03-10T15:00:00Z"]) 

    def test_missing_timestamp_key_in_non_truth_file(self):
        self.instance.selected_md = {"login": {}}  # No "timestamp" key
        random.seed(0)
        result = self.instance._generate_ac_timestamp(False, self.timestamps, "login")
        self.assertIn(result, ["2024-03-10T12:00:00Z", "2024-03-10T13:00:00Z", "2024-03-10T14:00:00Z", "2024-03-10T15:00:00Z"]) 

if __name__ == "__main__":
    unittest.main()
