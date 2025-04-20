"""
Test script to demonstrate session 2 of a multi-session conversation.

This script continues a conversation from session 1, using the 
continuation ID stored by test_session_1.py.
"""

import os
import sys
import uuid
from datetime import datetime, timezone

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.state import ConversationState
from query.memory.archivist_memory import ArchivistMemory
from query.assistants.conversation import ConversationManager


def run_session_2():
    """Run the second conversation session, continuing from session 1."""
    # Create memory
    memory = ArchivistMemory()
    
    # Create conversation manager
    manager = ConversationManager(archivist_memory=memory)
    
    # Get continuation ID from file
    try:
        with open("continuation_id.txt", "r") as f:
            continuation_id = f.read().strip()
    except FileNotFoundError:
        print("Error: continuation_id.txt not found. Please run test_session_1.py first.")
        return
    
    print(f"Found continuation ID: {continuation_id}")
    
    # Get continuation context
    continuation_data = memory.get_continuation_context(continuation_id)
    print("\nContinuation context:")
    for key, value in continuation_data.items():
        if key not in ["created_at", "updated_at", "conversation_id", "continuation_id"]:
            print(f"- {key}: {value}")
    
    # Create new conversation with continuation context
    conversation = manager.create_conversation()
    conversation_id = conversation.conversation_id
    print(f"\nCreated new conversation: {conversation_id}")
    
    # Set continuation pointer
    conversation.set_continuation_pointer(continuation_id)
    
    # Apply context variables from continuation data
    context_variables = continuation_data.get("context_variables", {})
    for key, value in context_variables.items():
        conversation.set_context_variable(key, value)
        
    # Apply key takeaways from continuation data
    for takeaway in continuation_data.get("key_takeaways", []):
        conversation.add_key_takeaway(takeaway)
    
    # Print context variables
    print("\nContext variables from previous session:")
    for key, value in context_variables.items():
        print(f"- {key}: {value}")
    
    # Simulate continuation conversation
    print("\nContinuing conversation...")
    print("User: I'd like to extend my UPI implementation to handle new data sources.")
    manager.add_user_message(conversation_id, "I'd like to extend my UPI implementation to handle new data sources.")
    
    # Create response using the context
    thesis_topic = conversation.get_context_variable("thesis_topic", "your research")
    demo_vehicle = conversation.get_context_variable("demo_vehicle", "your implementation")
    
    response = f"Based on our previous discussion about your {thesis_topic} thesis, " + \
               f"I understand you're using {demo_vehicle} as a demonstration vehicle. " + \
               f"What new data sources are you considering adding to your implementation?"
    
    print(f"Assistant: {response}")
    manager.add_assistant_message(conversation_id, response)
    
    # This demonstrates that the context is preserved
    print("\nVerification of context preservation:")
    print(f"- thesis_topic from previous session: {conversation.get_context_variable('thesis_topic')}")
    print(f"- demo_vehicle from previous session: {conversation.get_context_variable('demo_vehicle')}")
    print(f"- Continuation pointer: {conversation.continuation_pointer}")
    print(f"- Key takeaways preserved: {len(conversation.key_takeaways)} takeaways")
    
    # Update the conversation state in memory
    continuation_id = memory.store_conversation_state(
        conversation_id,
        {
            "summary": "Continued discussion about extending UPI implementation",
            "key_takeaways": conversation.key_takeaways,
            "topics": ["UPI", "thesis", "Archivist", "data sources"],
            "importance_score": 0.9,
            "context_variables": conversation.context_variables
        }
    )
    
    print(f"\nUpdated conversation stored with continuation ID: {continuation_id}")


if __name__ == "__main__":
    run_session_2()