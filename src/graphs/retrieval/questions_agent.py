"""Questions retrieval sub-agent.

This sub-agent retrieves practice questions from the knowledge base.
Currently mocked for hackathon P0.
"""

import json
from typing import Any, Dict, List

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt

from src.graphs.state import GraphState, Message
from src.graphs.utils.messages import create_tool_message


# Mock questions data for P0
MOCK_QUESTIONS = [
    {
        "id": "q1",
        "topic": "physics",
        "question": "What is Newton's First Law of Motion?",
        "alternatives": [
            "A) Force equals mass times acceleration",
            "B) An object at rest stays at rest unless acted upon by an external force",
            "C) For every action there is an equal and opposite reaction",
            "D) Energy cannot be created or destroyed"
        ],
        "correct_answer": "B",
        "explanation": "Newton's First Law states that an object at rest stays at rest and an object in motion stays in motion unless acted upon by an external force."
    },
    {
        "id": "q2", 
        "topic": "physics",
        "question": "What is the formula for kinetic energy?",
        "alternatives": [
            "A) E = mc²",
            "B) KE = ½mv²",
            "C) F = ma",
            "D) P = mv"
        ],
        "correct_answer": "B",
        "explanation": "Kinetic energy is calculated as one-half times mass times velocity squared."
    },
    {
        "id": "q3",
        "topic": "programming",
        "question": "What is the time complexity of binary search?",
        "alternatives": [
            "A) O(n)",
            "B) O(n²)",
            "C) O(log n)",
            "D) O(1)"
        ],
        "correct_answer": "C",
        "explanation": "Binary search divides the search space in half each iteration, resulting in logarithmic time complexity."
    }
]


def _mock_retrieve(query: str) -> List[Dict[str, Any]]:
    """Mock retrieve function for questions.
    
    In production, this would query MongoDB/vector search.
    
    Args:
        query: Search query
        
    Returns:
        List of matching questions as JSON
    """
    query_lower = query.lower()
    
    # Simple keyword matching for mock
    results = []
    for q in MOCK_QUESTIONS:
        if (query_lower in q["topic"].lower() or 
            query_lower in q["question"].lower()):
            results.append(q)
    
    # If no matches, return first question as fallback
    if not results:
        results = [MOCK_QUESTIONS[0]]
    
    return results


async def retrieve_questions_node(state: GraphState) -> GraphState:
    """Node that retrieves questions based on the query.
    
    This is the core retrieval logic. It:
    1. Parses the query from the tool call
    2. Calls the (mocked) retrieve function
    3. Returns the results as a tool message
    
    The intermediate retrieve calls stay local - only the final
    output is written to global messages.
    """
    messages = state["conversation_state"]["messages"]
    
    # Get the tool call that routed here
    assistant_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            assistant_msg = msg
            break
    
    if not assistant_msg:
        # No tool call found, create error response
        error_msg = create_tool_message(
            content=json.dumps({"error": "No query provided"}),
            role="tool",
            name="routeToQuestions"
        )
        state["conversation_state"]["messages"].append(error_msg)
        return state
    
    # Parse the query
    tool_call = assistant_msg["tool_calls"][0]
    tool_call_id = tool_call["id"]
    arguments = json.loads(tool_call["function"]["arguments"])
    query = arguments.get("query", "")
    
    # Call mocked retrieve
    results = _mock_retrieve(query)
    
    # Create tool response with retrieved questions
    tool_response = create_tool_message(
        content=json.dumps(results, ensure_ascii=False, indent=2),
        role="tool",
        tool_call_id=tool_call_id,
        name="routeToQuestions"
    )
    
    state["conversation_state"]["messages"].append(tool_response)
    return state


def get_questions_agent_graph() -> StateGraph:
    """Build the questions retrieval sub-agent graph.
    
    This is a simple graph that just does retrieval.
    In the future, it could have multiple steps for
    query refinement, filtering, etc.
    
    Returns:
        Compiled StateGraph
    """
    graph = StateGraph(GraphState)
    
    graph.add_node("retrieve", retrieve_questions_node)
    
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", END)
    
    return graph.compile()
