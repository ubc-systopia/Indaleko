"""
Test script to demonstrate session 1 of a multi-session conversation.

This script creates a conversation with key context variables that
will be used in session 2 to demonstrate conversation continuity.
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


def run_session_1():
    """Run the first conversation session and store it for session 2."""
    # Create memory
    memory = ArchivistMemory()

    # Create conversation manager
    manager = ConversationManager(archivist_memory=memory)

    # Create a conversation
    conversation = manager.create_conversation()
    conversation_id = conversation.conversation_id
    print(f"Created conversation: {conversation_id}")

    # Simulate a conversation
    print("Starting conversation...")
    print("User: I'm working on my thesis about UPI (Unified Personal Index).")
    manager.add_user_message(
        conversation_id, "I'm working on my thesis about UPI (Unified Personal Index).",
    )

    print(
        "Assistant: That's interesting! Can you tell me more about your thesis on UPI?",
    )
    manager.add_assistant_message(
        conversation_id,
        "That's interesting! Can you tell me more about your thesis on UPI?",
    )

    print(
        "User: It's focusing on how to unify data across disparate sources for personal knowledge management.",
    )
    manager.add_user_message(
        conversation_id,
        "It's focusing on how to unify data across disparate sources for personal knowledge management.",
    )

    print(
        "Assistant: That sounds like an important area of research. Are you implementing a prototype?",
    )
    manager.add_assistant_message(
        conversation_id,
        "That sounds like an important area of research. Are you implementing a prototype?",
    )

    print(
        "User: Yes, I'm using Archivist as the demonstration vehicle for my UPI concept.",
    )
    manager.add_user_message(
        conversation_id,
        "Yes, I'm using Archivist as the demonstration vehicle for my UPI concept.",
    )

    # Extract information and update context
    conversation.set_context_variable("thesis_topic", "UPI")
    conversation.set_context_variable(
        "thesis_focus", "unifying data across disparate sources",
    )
    conversation.set_context_variable("demo_vehicle", "Archivist")
    conversation.set_context_variable("domain", "personal knowledge management")

    # Add key takeaways
    conversation.add_key_takeaway(
        "User is working on thesis about Unified Personal Index (UPI)",
    )
    conversation.add_key_takeaway(
        "Thesis focuses on unifying data across disparate sources",
    )
    conversation.add_key_takeaway(
        "Archivist is being used as demonstration vehicle for UPI",
    )
    conversation.add_key_takeaway("Domain is personal knowledge management")

    # Start a topic segment
    conversation.start_topic_segment("UPI thesis")

    # Update importance
    conversation.set_importance_score(0.9)

    # Persist conversation state to memory
    continuation_id = memory.store_conversation_state(
        conversation_id,
        {
            "summary": "Discussion about thesis on UPI with Archivist as demonstration",
            "key_takeaways": conversation.key_takeaways,
            "topics": ["UPI", "thesis", "Archivist", "personal knowledge management"],
            "importance_score": 0.9,
            "context_variables": {
                "thesis_topic": conversation.get_context_variable("thesis_topic"),
                "thesis_focus": conversation.get_context_variable("thesis_focus"),
                "demo_vehicle": conversation.get_context_variable("demo_vehicle"),
                "domain": conversation.get_context_variable("domain"),
            },
        },
    )

    print(f"\nConversation stored with continuation ID: {continuation_id}")
    print("Use this continuation ID in session 2 to continue the conversation.")

    # Save the ID to a file for easy retrieval
    with open("continuation_id.txt", "w") as f:
        f.write(continuation_id)

    print("Continuation ID saved to continuation_id.txt")

    return continuation_id


if __name__ == "__main__":
    continuation_id = run_session_1()
