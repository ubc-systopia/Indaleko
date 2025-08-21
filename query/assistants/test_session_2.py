"""
Test script to demonstrate session 2 of a multi-session conversation.

This script continues a conversation from session 1, using the
continuation ID stored by test_session_1.py.
"""

import os
import sys


if os.environ.get("INDALEKO_ROOT") is None:
    current_path = os.path.dirname(os.path.abspath(__file__))
    while not os.path.exists(os.path.join(current_path, "Indaleko.py")):
        current_path = os.path.dirname(current_path)
    os.environ["INDALEKO_ROOT"] = current_path
    sys.path.append(current_path)

from query.assistants.conversation import ConversationManager
from query.memory.archivist_memory import ArchivistMemory


def run_session_2():
    """Run the second conversation session, continuing from session 1."""
    # Create memory
    memory = ArchivistMemory()

    # Create conversation manager
    manager = ConversationManager(archivist_memory=memory)

    # Get continuation ID from file
    try:
        with open("continuation_id.txt") as f:
            continuation_id = f.read().strip()
    except FileNotFoundError:
        return


    # Get continuation context
    continuation_data = memory.get_continuation_context(continuation_id)
    for key, value in continuation_data.items():
        if key not in [
            "created_at",
            "updated_at",
            "conversation_id",
            "continuation_id",
        ]:
            pass

    # Create new conversation with continuation context
    conversation = manager.create_conversation()
    conversation_id = conversation.conversation_id

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
    for key, value in context_variables.items():
        pass

    # Simulate continuation conversation
    manager.add_user_message(
        conversation_id,
        "I'd like to extend my UPI implementation to handle new data sources.",
    )

    # Create response using the context
    thesis_topic = conversation.get_context_variable("thesis_topic", "your research")
    demo_vehicle = conversation.get_context_variable(
        "demo_vehicle",
        "your implementation",
    )

    response = (
        f"Based on our previous discussion about your {thesis_topic} thesis, "
         f"I understand you're using {demo_vehicle} as a demonstration vehicle. "
         "What new data sources are you considering adding to your implementation?"
    )

    manager.add_assistant_message(conversation_id, response)

    # This demonstrates that the context is preserved

    # Update the conversation state in memory
    continuation_id = memory.store_conversation_state(
        conversation_id,
        {
            "summary": "Continued discussion about extending UPI implementation",
            "key_takeaways": conversation.key_takeaways,
            "topics": ["UPI", "thesis", "Archivist", "data sources"],
            "importance_score": 0.9,
            "context_variables": conversation.context_variables,
        },
    )



if __name__ == "__main__":
    run_session_2()
