"""Message utilities for LangGraph nodes.

Provides helper functions for creating and processing messages
in the conversation state.
"""

import json
import uuid
from typing import Any, Dict, List, Tuple

from src.graphs.state import Message


def create_tool_message(
    content: str = "",
    role: str = "assistant",
    tool_calls: List[dict] | None = None,
    tool_call_id: str | None = None,
    name: str | None = None,
) -> Message:
    """Create a message dict for the conversation state.
    
    Args:
        content: Message content
        role: Message role (user, assistant, tool)
        tool_calls: List of tool calls (for assistant messages)
        tool_call_id: Tool call ID (for tool response messages)
        name: Tool name (for tool response messages)
        
    Returns:
        Message dict
    """
    message: Message = {
        "id": f"msg_{uuid.uuid4().hex[:16]}",
        "role": role,
        "content": content,
    }
    
    if tool_calls:
        message["tool_calls"] = tool_calls
    if tool_call_id:
        message["tool_call_id"] = tool_call_id
    if name:
        message["name"] = name
        
    return message


def format_message_to_gemini(msg: Message) -> Dict[str, Any]:
    """Format a Message for Gemini API.
    
    Converts our internal message format to Gemini's expected format.
    
    Args:
        msg: Internal Message dict
        
    Returns:
        Gemini-compatible message dict
    """
    role = msg.get("role", "user")
    
    # Map roles to Gemini format
    if role == "assistant":
        gemini_role = "model"
    elif role == "tool":
        gemini_role = "function"
    else:
        gemini_role = "user"
    
    result: Dict[str, Any] = {
        "role": gemini_role,
    }
    
    # Handle content
    if msg.get("content"):
        result["parts"] = [{"text": msg["content"]}]
    elif msg.get("tool_calls"):
        # Assistant message with tool calls
        tool_call = msg["tool_calls"][0]
        result["parts"] = [{
            "functionCall": {
                "name": tool_call["function"]["name"],
                "args": json.loads(tool_call["function"]["arguments"])
            }
        }]
    
    # Handle tool response
    if role == "tool" and msg.get("name"):
        result["parts"] = [{
            "functionResponse": {
                "name": msg["name"],
                "response": {"result": msg.get("content", "")}
            }
        }]
    
    return result


def get_last_message(messages: List[Message], role: str) -> Message | None:
    """Get the last message with a specific role.
    
    Args:
        messages: List of messages
        role: Role to filter by
        
    Returns:
        Last message with that role, or None
    """
    for msg in reversed(messages):
        if msg.get("role") == role:
            return msg
    return None


def parse_tool_call_from_messages(
    messages: List[Message]
) -> Tuple[str, str, dict]:
    """Parse the latest tool call from messages.
    
    Args:
        messages: List of messages
        
    Returns:
        Tuple of (tool_call_id, tool_name, arguments)
        
    Raises:
        ValueError: If no tool call found
    """
    assistant_msg = get_last_message(messages, "assistant")
    
    if not assistant_msg or not assistant_msg.get("tool_calls"):
        raise ValueError("No tool call found in messages")
    
    tool_call = assistant_msg["tool_calls"][0]
    tool_call_id = tool_call["id"]
    tool_name = tool_call["function"]["name"]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    return tool_call_id, tool_name, arguments
