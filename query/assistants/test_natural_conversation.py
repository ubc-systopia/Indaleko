"""
Test script for the Natural Conversation Capabilities in Indaleko.

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

import os
import sys
import json
import uuid
import argparse
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from icecream import ic

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

# pylint: disable=wrong-import-position
from db import IndalekoDBConfig
from query.assistants.conversation import ConversationManager
from query.assistants.state import ConversationState, Message, TopicSegment
from query.memory.archivist_memory import ArchivistMemory
# pylint: enable=wrong-import-position


def test_conversation_basics():
    """Test basic conversation functionality."""
    # Create conversation manager
    manager = ConversationManager()
    
    # Create conversation
    conversation = manager.create_conversation()
    conversation_id = conversation.conversation_id
    
    print(f"Created conversation: {conversation_id}")
    
    # Exchange messages
    messages = [
        "Hello, can you help me find some documents?",
        "I'm looking for files about the Indaleko project.",
        "Can you search for documents related to UPI?",
        "Let's talk about the Archivist component.",
        "How does memory consolidation work?"
    ]
    
    for message in messages:
        response = manager.process_message(conversation_id, message)
        print(f"\nUser: {message}")
        print(f"Assistant: {response['response']}")
    
    # Check conversation state
    print("\nConversation Summary:")
    print(f"Topic segments: {len(conversation.topic_segments)}")
    for i, segment in enumerate(conversation.topic_segments):
        print(f"  Segment {i+1}: {segment.topic}")
    
    print(f"Total messages: {len(conversation.messages)}")
    if conversation.conversation_summary:
        print(f"Summary: {conversation.conversation_summary}")
    
    print(f"Importance score: {conversation.importance_score}")
    
    return conversation


def test_topic_segmentation():
    """Test topic segmentation capabilities."""
    # Create conversation state
    conversation = ConversationState()
    
    # Start with general topic
    general_segment = conversation.start_topic_segment("general")
    print(f"Started general segment: {general_segment.segment_id}")
    
    # Add messages
    conversation.add_message("user", "Hello, I need help with my files.")
    conversation.add_message("assistant", "I can help you with that. What kind of files?")
    
    # Switch to file organization topic
    conversation.end_topic_segment("Initial greeting and request for help.")
    files_segment = conversation.start_topic_segment("file organization", 
                                                 entities=["files", "organization"])
    print(f"Started file organization segment: {files_segment.segment_id}")
    
    # Add messages
    conversation.add_message("user", "I have many PDF documents I need to organize.")
    conversation.add_message("assistant", "Sure, how would you like to organize them?")
    conversation.add_message("user", "I'd like to group them by project.")
    
    # Switch to UPI topic
    conversation.end_topic_segment("Discussion about organizing PDF files by project.")
    upi_segment = conversation.start_topic_segment("UPI", 
                                             entities=["UPI", "Unified Personal Index"])
    print(f"Started UPI segment: {upi_segment.segment_id}")
    
    # Add messages
    conversation.add_message("user", "Tell me about the UPI architecture.")
    conversation.add_message("assistant", "UPI stands for Unified Personal Index...")
    
    # End final segment
    conversation.end_topic_segment("Introduction to UPI architecture.")
    
    # Print segment summaries
    print("\nTopic Segments:")
    for segment in conversation.topic_segments:
        print(f"- {segment.topic}: {segment.summary}")
        segment_messages = conversation.get_segment_messages(segment.segment_id)
        print(f"  Messages: {len(segment_messages)}")
    
    return conversation


def test_memory_integration():
    """Test integration with archivist memory."""
    # Create memory
    memory = ArchivistMemory()
    
    # Add some test data
    memory.add_long_term_goal("File Organization", "Organize PDF documents by project and year")
    memory.add_insight("organization", "User frequently searches for PDF documents", 0.8)
    memory.add_insight("retrieval", "Project name is a key search criterion", 0.7)
    
    # Create conversation manager with memory
    manager = ConversationManager(archivist_memory=memory)
    
    # Create conversation
    conversation = manager.create_conversation()
    conversation_id = conversation.conversation_id
    
    print(f"Created conversation with memory integration: {conversation_id}")
    
    # Exchange messages with memory references
    messages = [
        "Do I have any PDF documents?",
        "I'm working on a project called Indaleko.",
        "Can you help me organize my files?",
        "Remember this conversation for next time."
    ]
    
    for message in messages:
        response = manager.process_message(conversation_id, message)
        print(f"\nUser: {message}")
        print(f"Assistant: {response['response']}")
        
        # Check if memory was referenced
        if response.get("referenced_memories"):
            print(f"Referenced memories: {response['referenced_memories']}")
    
    # Store conversation state
    if hasattr(memory, "store_conversation_state"):
        continuation_id = memory.store_conversation_state(
            conversation_id,
            {
                "summary": "Conversation about PDF documents and Indaleko project",
                "key_takeaways": ["User is working on Indaleko project", 
                                 "User needs to organize PDF documents"],
                "topics": ["PDF documents", "Indaleko", "file organization"],
                "importance_score": 0.8
            }
        )
        
        print(f"\nStored conversation state with continuation ID: {continuation_id}")
        
        # Retrieve continuation context
        context = memory.get_continuation_context(continuation_id)
        print(f"Retrieved continuation context: {context}")
    
    return conversation


class EnhancedConversationManager(ConversationManager):
    """Enhanced conversation manager for testing that demonstrates memory features."""
    
    def _generate_contextual_response(self, conversation, message, referenced_memories):
        """Generate a contextual response that demonstrates memory usage."""
        # Topic-based response
        topic = self._get_active_topic(conversation)
        
        # Check for continuation context explicitly for testing
        continuation_context = None
        if conversation.continuation_pointer:
            thesis_topic = conversation.get_context_variable("thesis_topic")
            demo_vehicle = conversation.get_context_variable("demo_vehicle")
            
            if thesis_topic and demo_vehicle:
                # Explicitly check for continuation info in execution context
                continuation_info = conversation.execution_context.get("continuation_info", {})
                continuation_summary = continuation_info.get("summary", "")
                takeaways = continuation_info.get("key_takeaways", [])
                
                # Create a response that shows we know about previous conversation
                if "remind" in message.lower() or "previous" in message.lower() or "before" in message.lower():
                    return (f"Based on our previous conversation, I know you're working on a thesis "
                           f"about {thesis_topic} and using {demo_vehicle} as a demonstration vehicle. "
                           f"Key takeaways: {', '.join(takeaways)}. "
                           f"Summary: {continuation_summary}")
                
                # Show that we recognize this is a continuation
                if "continue" in message.lower():
                    return (f"I remember our previous discussion about your thesis on {thesis_topic}. "
                           f"We were discussing how {demo_vehicle} demonstrates the capabilities. "
                           f"Let's continue where we left off.")
                
                # Add continuation context to all responses
                continuation_context = f"[Context from previous conversation about {thesis_topic} using {demo_vehicle}] "
        
        # Check referenced memories for relevant context
        if referenced_memories:
            memory = referenced_memories[0]
            memory_type = getattr(memory, "memory_type", "unknown")
            summary = getattr(memory, "summary", "this information")
            
            prefix = continuation_context or ""
            
            if memory_type == "insight":
                return f"{prefix}Based on what I've learned, {summary}"
            elif memory_type == "goal":
                return f"{prefix}I remember your goal about {summary}"
        
        # Topic-specific responses
        prefix = continuation_context or ""
        
        if topic == "UPI":
            return f"{prefix}UPI (Unified Personal Index) is a core architecture that enables cross-source data integration. What specific aspect would you like to discuss?"
        elif topic == "Archivist":
            return f"{prefix}Archivist serves as a demonstration vehicle for UPI capabilities, providing persistent memory and context management across sessions."
        elif "thesis" in topic.lower():
            return f"{prefix}Your thesis work focuses on demonstrating how UPI provides the foundation for intelligent data management tools like Archivist."
        
        # Default contextual response
        return f"{prefix}I understand we're discussing {topic}. How can I help you further with this topic?"


def test_conversation_continuity():
    """Test conversation continuity across sessions."""
    # Create memory
    memory = ArchivistMemory()
    
    # Create first conversation with enhanced manager
    manager1 = EnhancedConversationManager(archivist_memory=memory)
    conversation1 = manager1.create_conversation()
    conversation_id1 = conversation1.conversation_id
    
    print(f"Created first conversation: {conversation_id1}")
    
    # Start a topic about the thesis
    conversation1.start_topic_segment("thesis")
    
    # Exchange messages in first conversation
    messages1 = [
        "I'm working on my thesis about UPI.",
        "The main focus is on demonstrating UPI capabilities.",
        "I'm using Archivist as a demonstration vehicle."
    ]
    
    for message in messages1:
        response = manager1.process_message(conversation_id1, message)
        print(f"\nUser: {message}")
        print(f"Assistant: {response['response']}")
    
    # Add key takeaways
    conversation1.add_key_takeaway("Thesis focus is on UPI capabilities")
    conversation1.add_key_takeaway("Archivist is a demonstration vehicle for UPI")
    
    # Add context variables
    conversation1.set_context_variable("thesis_topic", "UPI")
    conversation1.set_context_variable("demo_vehicle", "Archivist")
    
    # End topic segment
    conversation1.end_topic_segment("Initial discussion about thesis focus")
    
    # Store conversation state
    continuation_id = memory.store_conversation_state(
        conversation_id1,
        {
            "summary": "Discussion about thesis on UPI with Archivist as demonstration",
            "key_takeaways": conversation1.key_takeaways,
            "topics": ["UPI", "thesis", "Archivist"],
            "importance_score": 0.9,
            "context_variables": {
                "thesis_topic": conversation1.get_context_variable("thesis_topic"),
                "demo_vehicle": conversation1.get_context_variable("demo_vehicle")
            }
        }
    )
    
    print(f"\nStored first conversation with continuation ID: {continuation_id}")
    
    # Create second conversation with continuation
    manager2 = EnhancedConversationManager(archivist_memory=memory)
    conversation2 = manager2.create_conversation()
    conversation_id2 = conversation2.conversation_id
    
    print(f"\nCreated second conversation: {conversation_id2}")
    
    # Continue from previous conversation
    context = {"continuation_pointer": continuation_id}
    
    # Exchange messages in second conversation
    messages2 = [
        "Let's continue our discussion from before.",
        "I've made progress on the implementation.",
        "Can you remind me what we were focused on?"
    ]
    
    for i, message in enumerate(messages2):
        # Special handling for first message to ensure context is applied
        if i == 0:
            response = manager2.process_message(conversation_id2, message, context)
        else:
            response = manager2.process_message(conversation_id2, message)
            
        print(f"\nUser: {message}")
        print(f"Assistant: {response['response']}")
    
    # Check for continuation info
    if conversation2.continuation_pointer:
        print(f"\nContinuation recognized: {conversation2.continuation_pointer}")
    
    # Check for context variables from previous conversation
    thesis_topic = conversation2.get_context_variable("thesis_topic")
    demo_vehicle = conversation2.get_context_variable("demo_vehicle")
    
    if thesis_topic:
        print(f"Recovered thesis topic: {thesis_topic}")
    if demo_vehicle:
        print(f"Recovered demo vehicle: {demo_vehicle}")
    
    return conversation2


def main():
    """Run the tests based on command line arguments."""
    parser = argparse.ArgumentParser(description="Test Natural Conversation Capabilities")
    parser.add_argument("--basics", action="store_true", help="Test basic conversation functionality")
    parser.add_argument("--topics", action="store_true", help="Test topic segmentation")
    parser.add_argument("--memory", action="store_true", help="Test memory integration")
    parser.add_argument("--continuity", action="store_true", help="Test conversation continuity")
    parser.add_argument("--all", action="store_true", help="Run all tests")
    
    args = parser.parse_args()
    
    # Default to all tests if none specified
    if not (args.basics or args.topics or args.memory or args.continuity or args.all):
        args.all = True
    
    # Run tests
    if args.all or args.basics:
        print("\n===== Testing Basic Conversation Functionality =====")
        test_conversation_basics()
    
    if args.all or args.topics:
        print("\n===== Testing Topic Segmentation =====")
        test_topic_segmentation()
    
    if args.all or args.memory:
        print("\n===== Testing Memory Integration =====")
        test_memory_integration()
    
    if args.all or args.continuity:
        print("\n===== Testing Conversation Continuity =====")
        test_conversation_continuity()


if __name__ == "__main__":
    main()