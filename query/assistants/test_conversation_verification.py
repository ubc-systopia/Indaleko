"""
Simple verification script for conversation continuity features.

This script tests the basic functionality of conversation continuity
without relying on the full assistant infrastructure.
"""

import os
import sys

if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.state import ConversationState
from query.memory.archivist_memory import ArchivistMemory


def test_basic_context_flow():
    """Test basic context flow between sessions without using assistants."""
    # Create memory
    memory = ArchivistMemory()

    # Create first conversation state
    conversation1 = ConversationState()
    conversation_id1 = conversation1.conversation_id
    print(f"Created first conversation: {conversation_id1}")

    # Add context variables
    conversation1.set_context_variable("thesis_topic", "UPI")
    conversation1.set_context_variable("demo_vehicle", "Archivist")
    print(
        f"Set context variables: thesis_topic={conversation1.get_context_variable('thesis_topic')}, "
        f"demo_vehicle={conversation1.get_context_variable('demo_vehicle')}",
    )

    # Add key takeaways
    conversation1.add_key_takeaway("Thesis focus is on UPI capabilities")
    conversation1.add_key_takeaway("Archivist is a demonstration vehicle for UPI")
    print(f"Added key takeaways: {conversation1.key_takeaways}")

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
                "demo_vehicle": conversation1.get_context_variable("demo_vehicle"),
            },
        },
    )

    print(f"Stored first conversation with continuation ID: {continuation_id}")

    # Retrieve continuation context from memory
    continuation_data = memory.get_continuation_context(continuation_id)
    print(f"Retrieved continuation context: {continuation_data}")

    # Apply continuation context to new conversation
    conversation2 = ConversationState()
    conversation_id2 = conversation2.conversation_id
    print(f"Created second conversation: {conversation_id2}")

    # Set continuation pointer
    conversation2.set_continuation_pointer(continuation_id)
    print(f"Set continuation pointer: {conversation2.continuation_pointer}")

    # Apply context variables from continuation data
    if "context_variables" in continuation_data:
        for key, value in continuation_data["context_variables"].items():
            conversation2.set_context_variable(key, value)

    # Apply key takeaways from continuation data
    if "key_takeaways" in continuation_data:
        for takeaway in continuation_data["key_takeaways"]:
            conversation2.add_key_takeaway(takeaway)

    # Verify context carried forward
    print("Second conversation context variables:")
    print(f"- thesis_topic: {conversation2.get_context_variable('thesis_topic')}")
    print(f"- demo_vehicle: {conversation2.get_context_variable('demo_vehicle')}")
    print(f"Second conversation key takeaways: {conversation2.key_takeaways}")

    # Verify continuation information
    print(f"Continuation pointer: {conversation2.continuation_pointer}")


if __name__ == "__main__":
    test_basic_context_flow()
