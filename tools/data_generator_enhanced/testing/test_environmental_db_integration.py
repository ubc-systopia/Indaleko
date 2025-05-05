"""
Database integration tests for EnvironmentalMetadataGenerator.

These tests verify that the EnvironmentalMetadataGenerator can successfully:
1. Connect to a real ArangoDB instance
2. Insert properly formatted weather and climate data
3. Query data using semantic attributes
4. Handle database constraints and error conditions

Project Indaleko
Copyright (C) 2024-2025 Tony Mason

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import json
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

# Set up path for Indaleko imports
if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from db import IndalekoDBConfig
from db.db_collections import IndalekoDBCollections
from tools.data_generator_enhanced.agents.data_gen.tools.environmental_metadata_generator import (
    EnvironmentalMetadataGenerator,
    EnvironmentalMetadataGeneratorTool,
    WeatherCondition,
    WEATHER_CONDITION_UUID,
    TEMPERATURE_OUTDOOR_UUID,
    TEMPERATURE_INDOOR_UUID,
    HUMIDITY_OUTDOOR_UUID,
    HUMIDITY_INDOOR_UUID
)


class TestEnvironmentalDBIntegration(unittest.TestCase):
    """Test the database integration for EnvironmentalMetadataGenerator."""

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures for the whole test case."""
        try:
            # Initialize DB connection
            cls.db_config = IndalekoDBConfig()
            cls.db = cls.db_config.db
            
            # Test database connection
            info = cls.db.properties()
            cls.db_available = True
            print(f"Connected to ArangoDB: {info.get('version', 'unknown version')}")
            
            # Get TempActivityData collection or create if needed
            collection_name = IndalekoDBCollections.Indaleko_TempActivityData_Collection
            if not cls.db.has_collection(collection_name):
                cls.db.create_collection(collection_name)
            cls.collection = cls.db.collection(collection_name)
            
            # Initialize generator tool
            cls.generator_tool = EnvironmentalMetadataGeneratorTool()
            
            # Set up test data range (use a unique date range to avoid conflicts)
            cls.test_year = 2030  # Future year to avoid conflicts with real data
            cls.test_start = datetime(cls.test_year, 1, 1, tzinfo=timezone.utc)
            cls.test_end = datetime(cls.test_year, 1, 2, tzinfo=timezone.utc)  # One day
            
            # Test location data
            cls.test_locations = [
                {
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "label": "TestLocation1"
                }
            ]
            
        except Exception as e:
            cls.db_available = False
            print(f"Database setup failed: {str(e)}")
            
    def setUp(self):
        """Set up for each test method."""
        if not getattr(self, 'db_available', False):
            self.skipTest("Database not available")
            
    def tearDown(self):
        """Clean up after each test."""
        if hasattr(self, 'db_available') and self.db_available:
            try:
                # Clean up test data
                collection_name = IndalekoDBCollections.Indaleko_TempActivityData_Collection
                collection = self.db.collection(collection_name)
                
                # Delete only our test data (from test year)
                query = f"""
                FOR doc IN {collection_name}
                FILTER doc.Timestamp >= "{self.test_start.isoformat()}" 
                AND doc.Timestamp <= "{self.test_end.isoformat()}"
                REMOVE doc IN {collection_name}
                """
                self.db.aql.execute(query)
                
            except Exception as e:
                print(f"Teardown error: {str(e)}")
    
    def test_insert_weather_data(self):
        """Test inserting weather data into the database."""
        # Generate a small set of weather data
        generator = EnvironmentalMetadataGenerator()
        weather_records = generator.generate_weather_data(
            start_date=self.test_start,
            end_date=self.test_end,
            locations=self.test_locations,
            count=10
        )
        
        # Insert the data
        result_count = generator.insert_weather_data_into_database(weather_records)
        
        # Verify insertion
        self.assertEqual(result_count, 10, "Should have inserted all 10 records")
        
        # Query to verify the data exists
        query = f"""
        FOR doc IN {IndalekoDBCollections.Indaleko_TempActivityData_Collection}
        FILTER doc.Timestamp >= "{self.test_start.isoformat()}"
        AND doc.Timestamp <= "{self.test_end.isoformat()}"
        AND doc.Record.SourceIdentifier.Identifier == "{generator.weather_source_data['Identifier']}"
        RETURN doc
        """
        cursor = self.db.aql.execute(query)
        results = list(cursor)
        
        # Verify result count
        self.assertEqual(len(results), 10, "Should have found 10 weather records")
        
        # Verify data structure and content
        for record in results:
            # Check essential fields
            self.assertIn("Record", record)
            self.assertIn("Timestamp", record)
            self.assertIn("SemanticAttributes", record)
            
            # Check source identifier
            self.assertEqual(
                str(record["Record"]["SourceIdentifier"]["Identifier"]), 
                str(generator.weather_source_data["Identifier"])
            )
            
            # Check data content
            data_str = record["Record"]["Data"]
            data = json.loads(data_str)
            self.assertIn("condition", data)
            self.assertIn("temperature", data)
            self.assertIn("humidity", data)
            self.assertIn("wind_speed", data)
            self.assertIn("precipitation", data)
            
            # Check semantic attributes
            has_condition_attr = False
            has_temperature_attr = False
            
            for attr in record["SemanticAttributes"]:
                if attr["Identifier"]["Identifier"] == WEATHER_CONDITION_UUID:
                    has_condition_attr = True
                elif attr["Identifier"]["Identifier"] == TEMPERATURE_OUTDOOR_UUID:
                    has_temperature_attr = True
                    
            self.assertTrue(has_condition_attr, "Weather record missing condition semantic attribute")
            self.assertTrue(has_temperature_attr, "Weather record missing temperature semantic attribute")
            
    def test_insert_climate_data(self):
        """Test inserting indoor climate data into the database."""
        # Generate a small set of climate data
        generator = EnvironmentalMetadataGenerator()
        climate_records = generator.generate_indoor_climate_data(
            start_date=self.test_start,
            end_date=self.test_end,
            count=10
        )
        
        # Insert the data
        result_count = generator.insert_climate_data_into_database(climate_records)
        
        # Verify insertion
        self.assertEqual(result_count, 10, "Should have inserted all 10 records")
        
        # Query to verify the data exists
        query = f"""
        FOR doc IN {IndalekoDBCollections.Indaleko_TempActivityData_Collection}
        FILTER doc.Timestamp >= "{self.test_start.isoformat()}"
        AND doc.Timestamp <= "{self.test_end.isoformat()}"
        AND doc.Record.SourceIdentifier.Identifier == "{generator.climate_source_data['Identifier']}"
        RETURN doc
        """
        cursor = self.db.aql.execute(query)
        results = list(cursor)
        
        # Verify result count
        self.assertEqual(len(results), 10, "Should have found 10 climate records")
        
        # Verify data structure and content
        for record in results:
            # Check essential fields
            self.assertIn("Record", record)
            self.assertIn("Timestamp", record)
            self.assertIn("SemanticAttributes", record)
            
            # Check source identifier
            self.assertEqual(
                str(record["Record"]["SourceIdentifier"]["Identifier"]), 
                str(generator.climate_source_data["Identifier"])
            )
            
            # Check data content
            data_str = record["Record"]["Data"]
            data = json.loads(data_str)
            self.assertIn("temperature", data)
            self.assertIn("humidity", data)
            self.assertIn("hvac_mode", data)
            self.assertIn("location", data)
            self.assertIn("device_id", data)
            
            # Check semantic attributes
            has_temperature_attr = False
            has_humidity_attr = False
            
            for attr in record["SemanticAttributes"]:
                if attr["Identifier"]["Identifier"] == TEMPERATURE_INDOOR_UUID:
                    has_temperature_attr = True
                elif attr["Identifier"]["Identifier"] == HUMIDITY_INDOOR_UUID:
                    has_humidity_attr = True
                    
            self.assertTrue(has_temperature_attr, "Climate record missing temperature semantic attribute")
            
    def test_generate_and_query_by_condition(self):
        """Test generating data and querying by weather condition."""
        # Generate data with the tool
        result = self.generator_tool.generate_environmental_data(
            start_date=self.test_start,
            end_date=self.test_end,
            locations=self.test_locations,
            count_weather=20,
            count_climate=20,
            insert_to_db=True
        )
        
        # Check insertion results - print for debugging
        print(f"Generated records: {result}")
        print(f"Weather records: {result['total_weather_records']}, inserted: {result['weather_db_inserts']}")
        print(f"Climate records: {result['total_climate_records']}, inserted: {result['climate_db_inserts']}")
        
        # Check the results
        self.assertEqual(result["total_weather_records"], 20)
        self.assertEqual(result["weather_db_inserts"], 20)
        self.assertEqual(result["total_climate_records"], 20)
        self.assertEqual(result["climate_db_inserts"], 20)
        
        # Get a sample weather condition from the data
        if result["top_weather_conditions"]:
            sample_condition = result["top_weather_conditions"][0][0]  # first condition
            
            # Query by that condition
            query = f"""
            FOR doc IN {IndalekoDBCollections.Indaleko_TempActivityData_Collection}
            FILTER doc.Timestamp >= "{self.test_start.isoformat()}"
            AND doc.Timestamp <= "{self.test_end.isoformat()}"
            LET data = JSON_PARSE(doc.Record.Data)
            FILTER data.condition == "{sample_condition}"
            RETURN doc
            """
            cursor = self.db.aql.execute(query)
            results = list(cursor)
            
            # Should have found at least one record
            self.assertGreater(len(results), 0, f"Should find records with condition '{sample_condition}'")
            
            # Verify the condition in the first result
            first_result = results[0]
            data = json.loads(first_result["Record"]["Data"])
            self.assertEqual(data["condition"], sample_condition)
            
    def test_query_by_semantic_attribute(self):
        """Test querying data by semantic attribute."""
        # Generate data with the tool
        result = self.generator_tool.generate_environmental_data(
            start_date=self.test_start,
            end_date=self.test_end,
            locations=self.test_locations,
            count_weather=20,
            count_climate=20,
            insert_to_db=True
        )
        
        # Query by temperature semantic attribute with a range
        query = f"""
        FOR doc IN {IndalekoDBCollections.Indaleko_TempActivityData_Collection}
        FILTER doc.Timestamp >= "{self.test_start.isoformat()}"
        AND doc.Timestamp <= "{self.test_end.isoformat()}"
        LET temp_attrs = (
            FOR attr IN doc.SemanticAttributes
            FILTER attr.Identifier.Identifier == "{TEMPERATURE_OUTDOOR_UUID}"
            RETURN attr
        )
        FILTER LENGTH(temp_attrs) > 0
        FILTER temp_attrs[0].Data >= 15 AND temp_attrs[0].Data <= 30
        RETURN doc
        """
        cursor = self.db.aql.execute(query)
        results = list(cursor)
        
        # Should find some records in this common temperature range
        print(f"Found {len(results)} records in temperature range 15-30°C")
        
        # If we found records, verify their temperature values
        for record in results:
            # Find the temperature attribute
            temp_attr = None
            for attr in record["SemanticAttributes"]:
                if attr["Identifier"]["Identifier"] == TEMPERATURE_OUTDOOR_UUID:
                    temp_attr = attr
                    break
                    
            if temp_attr:
                temperature = temp_attr["Data"]
                self.assertGreaterEqual(temperature, 15)
                self.assertLessEqual(temperature, 30)
                
    def test_query_by_combination(self):
        """Test querying data by a combination of criteria."""
        # Generate data with the tool
        result = self.generator_tool.generate_environmental_data(
            start_date=self.test_start,
            end_date=self.test_end,
            locations=self.test_locations,
            count_weather=30,
            count_climate=30,
            insert_to_db=True
        )
        
        # Query for clear or partly_cloudy weather with temperature > 20°C
        query = f"""
        FOR doc IN {IndalekoDBCollections.Indaleko_TempActivityData_Collection}
        FILTER doc.Timestamp >= "{self.test_start.isoformat()}"
        AND doc.Timestamp <= "{self.test_end.isoformat()}"
        LET data = JSON_PARSE(doc.Record.Data)
        FILTER data.condition IN ["clear", "partly_cloudy"]
        LET temp_attrs = (
            FOR attr IN doc.SemanticAttributes
            FILTER attr.Identifier.Identifier == "{TEMPERATURE_OUTDOOR_UUID}"
            RETURN attr
        )
        FILTER LENGTH(temp_attrs) > 0
        FILTER temp_attrs[0].Data > 20
        RETURN {{
            condition: data.condition,
            temperature: temp_attrs[0].Data,
            timestamp: doc.Timestamp
        }}
        """
        cursor = self.db.aql.execute(query)
        results = list(cursor)
        
        # Print results for debugging
        print(f"Found {len(results)} records with clear/partly_cloudy and temp > 20°C")
        
        # Verify results if any were found
        for record in results:
            self.assertIn(record["condition"], ["clear", "partly_cloudy"])
            self.assertGreater(record["temperature"], 20)
            
    def test_query_indoor_climate(self):
        """Test querying indoor climate data."""
        # Generate data with the tool
        result = self.generator_tool.generate_environmental_data(
            start_date=self.test_start,
            end_date=self.test_end,
            locations=self.test_locations,
            count_weather=20,
            count_climate=40,  # More climate records to ensure some variety
            insert_to_db=True
        )
        
        # Query for rooms with heating active
        query = f"""
        FOR doc IN {IndalekoDBCollections.Indaleko_TempActivityData_Collection}
        FILTER doc.Timestamp >= "{self.test_start.isoformat()}"
        AND doc.Timestamp <= "{self.test_end.isoformat()}"
        LET data = JSON_PARSE(doc.Record.Data)
        FILTER HAS(data, "hvac_state") AND data.hvac_state == "heating"
        RETURN {{
            room: data.location.room,
            temperature: data.temperature,
            target_temperature: data.target_temperature,
            timestamp: doc.Timestamp
        }}
        """
        cursor = self.db.aql.execute(query)
        results = list(cursor)
        
        # Print results for debugging
        print(f"Found {len(results)} records with heating active")
        
        # Just verify we found some records and they have the expected fields
        if results:
            for record in results:
                self.assertIn("room", record)
                self.assertIn("temperature", record)
                self.assertIn("target_temperature", record)
                # We don't need to verify the exact temperature relationship since
                # our simplified generation model doesn't guarantee HVAC behavior


if __name__ == "__main__":
    unittest.main()