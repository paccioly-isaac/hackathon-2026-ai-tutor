"""Send message tool for the AI Tutor agent.

This tool allows the agent to send messages to the student with optional
cited paragraphs from retrieved documents.
"""

from typing import Any, Dict


def build_send_message_tool() -> Dict[str, Any]:
    """Build the sendMessage tool definition for Gemini.
    
    Returns:
        Tool definition dict for LLM
    """
    return {
        "name": "sendMessage",
        "description": (
            "Send a message to the student. Use for: "
            "answering questions, providing explanations, "
            "asking clarifying questions, sharing retrieved information with citations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The message content to send to the student"
                },
                "citedParagraphs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of cited paragraphs from retrieved documents."
                },
                "interrupt": {
                    "type": "boolean",
                    "description": "Whether to interrupt the graph flow to wait for user input (default: true). Set to true when expecting a reply or action from the student."
                }
            },
            "required": ["message"]
        }
    }
