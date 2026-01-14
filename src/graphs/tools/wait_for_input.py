"""Wait for input tool for the AI Tutor agent.

This tool allows the agent to explicitly pause execution and wait for
user input, triggering a LangGraph interrupt.
"""

from typing import Any, Dict


def build_wait_for_input_tool() -> Dict[str, Any]:
    """Build the waitForInput tool definition for Gemini.
    
    Returns:
        Tool definition dict for LLM
    """
    return {
        "name": "waitForInput",
        "description": (
            "Pause execution and wait for user input. Use when: "
            "you've asked the user a question and need their response, "
            "you need clarification before proceeding, "
            "the user needs to make a choice or decision."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {
                    "type": "string",
                    "description": "Brief explanation of why you're waiting for input"
                }
            },
            "required": ["reason"]
        }
    }
