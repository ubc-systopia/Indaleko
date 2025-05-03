#!/usr/bin/env python3
"""
Tests for the domain-specific generator agents.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open
from pathlib import Path

# Bootstrap project root so imports work
current_path = Path(__file__).parent.resolve()
while not (current_path / "Indaleko.py").exists() and current_path != current_path.parent:
    current_path = current_path.parent
sys.path.insert(0, str(current_path))

from tools.data_generator_enhanced.agents.data_gen.agents.storage import StorageGeneratorAgent
from tools.data_generator_enhanced.agents.data_gen.agents.semantic import SemanticGeneratorAgent
from tools.data_generator_enhanced.agents.data_gen.agents.activity import ActivityGeneratorAgent
from tools.data_generator_enhanced.agents.data_gen.agents.relationship import RelationshipGeneratorAgent
from tools.data_generator_enhanced.agents.data_gen.agents.machine_config import MachineConfigGeneratorAgent


class TestStorageGeneratorAgent(unittest.TestCase):
    """Test case for the StorageGeneratorAgent."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock OpenAI API key
        self.openai_env_patch = patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
        self.openai_env_patch.start()
        
        self.tool_registry = MagicMock()
        self.llm_provider = MagicMock()
        
        # Mock tools that would be used by the agent
        self.file_metadata_tool = MagicMock()
        self.file_metadata_tool.execute.return_value = {"records": [
            {"path": "/test/file1.txt", "size": 1024, "created": "2023-01-01T00:00:00Z"}
        ]}
        
        self.db_tool = MagicMock()
        self.db_tool.execute.return_value = {"inserted": 1}
        
        # Set up tool registry mock
        self.tool_registry.get_tool.side_effect = lambda name: {
            "file_metadata_generator": self.file_metadata_tool,
            "database_bulk_insert": self.db_tool
        }.get(name)
        
        # Create agent
        self.agent = StorageGeneratorAgent(
            tool_registry=self.tool_registry, 
            llm_provider=self.llm_provider,
            config={"store_directly": True, "direct_generation": True}
        )
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.openai_env_patch.stop()

    def test_direct_generation(self):
        """Test direct generation of storage records."""
        count = 5
        records = self.agent.generate(count=count)
        
        # Assert file metadata tool was called
        self.file_metadata_tool.execute.assert_called_once()
        self.assertEqual(len(records), 1)  # Our mock returns 1 record
        
        # Test batch generation
        self.agent.generate(count=20)
        # Should have called the tool 4 more times (5 total)
        self.assertEqual(self.file_metadata_tool.execute.call_count, 5)
    
    def test_llm_generation(self):
        """Test LLM-assisted generation of storage records."""
        # Mock the run method instead since direct LLM generation is handled differently
        with patch.object(self.agent, 'run') as mock_run:
            mock_run.return_value = {
                "content": "",
                "actions": [{
                    "tool": "file_metadata_generator", 
                    "result": {
                        "records": [{"path": "/llm/generated.txt", "size": 2048}]
                    }
                }]
            }
            
            # Override the direct generation flag to use LLM
            with patch.dict(self.agent.config, {"direct_generation": False}):
                records = self.agent.generate(count=1)
                
                mock_run.assert_called_once()
                self.assertEqual(len(records), 1)
    
    def test_truth_record_generation(self):
        """Test generation of truth records with specific criteria."""
        criteria = {"contains_text": "important", "file_type": "document"}
        
        # Since truth generation uses the same generate method but with criteria, we'll mock the tool
        self.file_metadata_tool.execute.return_value = {"records": [
            {"path": "/truth/doc.pdf", "size": 5000, "truth_marker": True}
        ]}
        
        records = self.agent.generate_truth(
            count=1, 
            criteria=criteria
        )
        
        self.file_metadata_tool.execute.assert_called_with({
            "count": 1, 
            "criteria": criteria
        })
        self.assertEqual(len(records), 1)


class TestSemanticGeneratorAgent(unittest.TestCase):
    """Test case for the SemanticGeneratorAgent."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock OpenAI API key
        self.openai_env_patch = patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
        self.openai_env_patch.start()
        
        self.tool_registry = MagicMock()
        self.llm_provider = MagicMock()
        
        # Mock tools
        self.semantic_tool = MagicMock()
        self.semantic_tool.execute.return_value = {"records": [
            {"ObjectIdentifier": "123", "MIMEType": "text/plain", "Checksum": "abc123"}
        ]}
        
        self.db_tool = MagicMock()
        self.db_tool.execute.return_value = {"inserted": 1}
        
        # Set up tool registry mock
        self.tool_registry.get_tool.side_effect = lambda name: {
            "semantic_metadata_generator": self.semantic_tool,
            "database_bulk_insert": self.db_tool
        }.get(name)
        
        # Create agent
        self.agent = SemanticGeneratorAgent(
            tool_registry=self.tool_registry, 
            llm_provider=self.llm_provider,
            config={"store_directly": True, "direct_generation": True}
        )
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.openai_env_patch.stop()

    def test_semantic_generation_from_storage(self):
        """Test generation of semantic records from storage objects."""
        storage_objects = [
            {"ObjectIdentifier": "123", "Path": "/test/doc.pdf", "Extension": ".pdf"}
        ]
        
        # Update the mock criteria to include storage objects
        with patch.dict(self.agent.config, {"criteria": {"storage_objects": storage_objects}}):
            records = self.agent.generate(count=1)
            
            self.semantic_tool.execute.assert_called_once()
            self.assertEqual(len(records), 1)
    
    def test_content_extraction_generation(self):
        """Test generation of content extracts for documents."""
        # Since the internal methods may vary, we'll test the high-level behavior
        # Mock the tool with content extraction
        self.semantic_tool.execute.return_value = {"records": [
            {
                "ObjectIdentifier": "123", 
                "MIMEType": "application/pdf",
                "Content": {
                    "extract": "This is a test document content.",
                    "type": "document"
                }
            }
        ]}
        
        storage_obj = {"ObjectIdentifier": "123", "Path": "/test/doc.pdf", "Extension": ".pdf"}
        
        # Test document content generation through the generate method
        with patch.dict(self.agent.config, {"criteria": {"storage_objects": [storage_obj]}}):
            records = self.agent.generate(count=1)
            
            self.semantic_tool.execute.assert_called_once()
            self.assertEqual(len(records), 1)
            self.assertTrue("Content" in records[0])
            self.assertTrue("extract" in records[0]["Content"])


class TestActivityGeneratorAgent(unittest.TestCase):
    """Test case for the ActivityGeneratorAgent."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock OpenAI API key
        self.openai_env_patch = patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
        self.openai_env_patch.start()
        
        self.tool_registry = MagicMock()
        self.llm_provider = MagicMock()
        
        # Mock tools
        self.activity_tool = MagicMock()
        self.activity_tool.execute.return_value = {"records": [
            {"ObjectIdentifier": "123", "ActivityType": "FILE_READ", "Timestamp": "2023-01-01T00:00:00Z"}
        ]}
        
        self.db_tool = MagicMock()
        self.db_tool.execute.return_value = {"inserted": 1}
        
        # Set up tool registry mock
        self.tool_registry.get_tool.side_effect = lambda name: {
            "activity_generator": self.activity_tool,
            "database_bulk_insert": self.db_tool
        }.get(name)
        
        # Create agent
        self.agent = ActivityGeneratorAgent(
            tool_registry=self.tool_registry, 
            llm_provider=self.llm_provider,
            config={"store_directly": True, "direct_generation": True}
        )
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.openai_env_patch.stop()

    def test_activity_sequence_generation(self):
        """Test generation of activity sequences."""
        # Setup the activity tool to return a sequence
        self.activity_tool.execute.return_value = {"records": [
            {"ActivityType": "FILE_CREATE", "Timestamp": "2023-01-01T00:00:00Z"},
            {"ActivityType": "FILE_MODIFY", "Timestamp": "2023-01-01T00:01:00Z"},
            {"ActivityType": "FILE_READ", "Timestamp": "2023-01-01T00:02:00Z"}
        ]}
        
        # Configure for sequence generation
        criteria = {
            "sequence_type": "file_workflow",
            "storage_objects": [{"ObjectIdentifier": "123"}],
            "create_sequences": True
        }
        
        with patch.dict(self.agent.config, {"criteria": criteria}):
            records = self.agent.generate(count=3)
            
            self.activity_tool.execute.assert_called_once()
            self.assertEqual(len(records), 3)
            # Check that we received the first record from our mock
            self.assertEqual(records[0]["ActivityType"], "FILE_CREATE")


class TestRelationshipGeneratorAgent(unittest.TestCase):
    """Test case for the RelationshipGeneratorAgent."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock OpenAI API key
        self.openai_env_patch = patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
        self.openai_env_patch.start()
        
        self.tool_registry = MagicMock()
        self.llm_provider = MagicMock()
        
        # Mock tools
        self.relationship_tool = MagicMock()
        self.relationship_tool.execute.return_value = {"records": [
            {"_from": "Objects/123", "_to": "Objects/456", "relationship": "CONTAINS"}
        ]}
        
        self.db_tool = MagicMock()
        self.db_tool.execute.return_value = {"inserted": 1}
        
        # Set up tool registry mock
        self.tool_registry.get_tool.side_effect = lambda name: {
            "relationship_generator": self.relationship_tool,
            "database_bulk_insert": self.db_tool
        }.get(name)
        
        # Create agent
        self.agent = RelationshipGeneratorAgent(
            tool_registry=self.tool_registry, 
            llm_provider=self.llm_provider,
            config={"store_directly": True, "direct_generation": True}
        )
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.openai_env_patch.stop()

    def test_relationship_generation(self):
        """Test generation of relationships between objects."""
        storage_objects = [
            {"_id": "Objects/123", "ObjectIdentifier": "123", "Path": "/folder/"},
            {"_id": "Objects/456", "ObjectIdentifier": "456", "Path": "/folder/file.txt"}
        ]
        
        semantic_objects = [
            {"_id": "SemanticData/789", "ObjectIdentifier": "456"}
        ]
        
        # Configure with objects to relate
        criteria = {
            "storage_objects": storage_objects,
            "semantic_objects": semantic_objects
        }
        
        with patch.dict(self.agent.config, {"criteria": criteria}):
            records = self.agent.generate(count=1)
            
            self.relationship_tool.execute.assert_called_once()
            self.assertEqual(len(records), 1)


class TestMachineConfigGeneratorAgent(unittest.TestCase):
    """Test case for the MachineConfigGeneratorAgent."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock OpenAI API key
        self.openai_env_patch = patch.dict(os.environ, {"OPENAI_API_KEY": "test_api_key"})
        self.openai_env_patch.start()
        
        self.tool_registry = MagicMock()
        self.llm_provider = MagicMock()
        
        # Mock tools
        self.machine_config_tool = MagicMock()
        self.machine_config_tool.execute.return_value = {"records": [
            {"MachineID": "machine1", "DeviceType": "desktop", "OS": "Windows"}
        ]}
        
        self.db_tool = MagicMock()
        self.db_tool.execute.return_value = {"inserted": 1}
        
        # Set up tool registry mock
        self.tool_registry.get_tool.side_effect = lambda name: {
            "machine_config_generator": self.machine_config_tool,
            "database_bulk_insert": self.db_tool
        }.get(name)
        
        # Create agent
        self.agent = MachineConfigGeneratorAgent(
            tool_registry=self.tool_registry, 
            llm_provider=self.llm_provider,
            config={"store_directly": True, "direct_generation": True}
        )
        
    def tearDown(self):
        """Tear down test fixtures."""
        self.openai_env_patch.stop()

    def test_machine_config_generation(self):
        """Test generation of machine configurations."""
        # Set up the machine config tool to return a specific device type
        self.machine_config_tool.execute.return_value = {"records": [
            {"MachineID": "machine1", "DeviceType": "desktop", "OS": "Windows"}
        ]}
        
        # Configure with device types
        criteria = {
            "device_types": ["desktop"]
        }
        
        with patch.dict(self.agent.config, {"criteria": criteria}):
            records = self.agent.generate(count=1)
            
            self.machine_config_tool.execute.assert_called_once()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["DeviceType"], "desktop")


if __name__ == '__main__':
    unittest.main()