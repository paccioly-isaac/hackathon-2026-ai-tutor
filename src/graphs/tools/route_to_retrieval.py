"""Route to retrieval tools for the AI Tutor agent.

These tools route the conversation to specialized retrieval sub-agents
for fetching questions or knowledge articles.
"""

from typing import Any, Dict


def build_route_to_questions_tool() -> Dict[str, Any]:
    """Build the routeToQuestions tool definition for Gemini.
    
    Returns:
        Tool definition dict for LLM
    """
    return {
        "name": "routeToQuestions",
        "description": (
            "Route to the Questions Agent to retrieve practice questions. "
            "Use when the student wants to practice or test their knowledge on a topic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant practice questions"
                }
            },
            "required": ["query"]
        }
    }


def build_route_to_articles_tool() -> Dict[str, Any]:
    """Build the routeToArticles tool definition for Gemini.
    
    Returns:
        Tool definition dict for LLM
    """
    return {
        "name": "routeToArticles",
        "description": (
            "Route to the Knowledge Agent to retrieve educational articles. "
            "Use when the student wants to learn about or study a topic."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query to find relevant knowledge articles"
                }
            },
            "required": ["query"]
        }
    }
