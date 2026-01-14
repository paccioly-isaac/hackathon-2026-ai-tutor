"""State definitions for the AI Tutor LangGraph.

This module defines the shared state types used across all graph nodes.
"""

from typing import Any, Dict, List, Literal, TypedDict


class Message(TypedDict, total=False):
    """Message in the conversation history.
    
    Follows OpenAI-style message format for compatibility.
    """
    content: str
    role: Literal["user", "assistant", "tool"]
    id: str
    tool_call_id: str  # For tool messages - references the assistant's tool_call
    tool_calls: List[dict]  # For assistant messages with tool calls
    name: str  # Tool name for tool messages
    thought_signature: str  # Gemini 3.0 thought signature required for tool calls


class ConversationState(TypedDict):
    """State for conversation tracking."""
    conversation_id: str
    messages: List[Message]


class GraphState(TypedDict):
    """Main graph state shared across all nodes."""
    conversation_state: ConversationState
    llm_tools: List[Dict[str, Any]]
    status: Literal["continue", "waiting_for_input", "complete"]


def get_initial_state(
    conversation_id: str,
    messages: List[Message] | None = None,
) -> GraphState:
    """Create initial state for a new conversation.
    
    Args:
        conversation_id: Unique identifier for the conversation
        messages: Initial messages (optional)
        
    Returns:
        Initial GraphState
    """
    return GraphState(
        conversation_state=ConversationState(
            conversation_id=conversation_id,
            messages=messages or [],
        ),
        llm_tools=[],
        status="continue",
    )
