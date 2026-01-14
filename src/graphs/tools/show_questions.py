"""Show questions tool for the AI Tutor agent.

This tool allows the agent to display multiple choice questions to the student.
The frontend will render these as an interactive question component.
"""

from typing import Any, Dict


def build_show_questions_tool() -> Dict[str, Any]:
    """Build the showQuestions tool definition for Gemini.
    
    Returns:
        Tool definition dict for LLM
    """
    return {
        "name": "showQuestions",
        "description": (
            "Display multiple choice questions to the student for practice. "
            "Use this after retrieving questions with routeToQuestions. "
            "Pass the question IDs you want to show. The student can answer "
            "some or all questions at their own pace. Reference past questions "
            "using [q1], [q2] etc format in your messages."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "questionIds": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of question IDs to display to the student (e.g., ['q1', 'q2'])"
                },
                "title": {
                    "type": "string",
                    "description": "A short, engaging title for the question set (e.g., 'Physics Challenge', 'Test Your Knowledge')"
                },
                "message": {
                    "type": "string",
                    "description": "Optional message to accompany the questions"
                }
            },
            "required": ["questionIds", "title"]
        }
    }
