"""Articles/Knowledge retrieval sub-agent.

This sub-agent retrieves educational articles from the knowledge base.
Currently mocked for hackathon P0.
"""

import json
from typing import Any, Dict, List

from langgraph.graph import StateGraph, START, END

from src.graphs.state import GraphState
from src.graphs.utils.messages import create_tool_message


# Mock articles data for P0
MOCK_ARTICLES = [
    {
        "id": "art1",
        "topic": "physics",
        "title": "Newton's Laws of Motion",
        "content": (
            "Newton's Three Laws of Motion form the foundation of classical mechanics. "
            "The First Law (Law of Inertia) states that an object remains at rest or in uniform motion "
            "unless acted upon by an external force. The Second Law defines the relationship between "
            "force, mass, and acceleration (F=ma). The Third Law states that for every action, "
            "there is an equal and opposite reaction."
        ),
        "paragraphs": [
            "Newton's First Law: An object at rest stays at rest, and an object in motion stays in motion with the same speed and direction, unless acted upon by an unbalanced external force.",
            "Newton's Second Law: The acceleration of an object is directly proportional to the net force acting on it and inversely proportional to its mass. Mathematically: F = ma.",
            "Newton's Third Law: For every action, there is an equal and opposite reaction. When object A exerts a force on object B, object B exerts an equal force in the opposite direction on object A."
        ]
    },
    {
        "id": "art2",
        "topic": "physics", 
        "title": "Energy and Work",
        "content": (
            "Energy is the capacity to do work. In physics, work is defined as force applied over a distance. "
            "Kinetic energy is the energy of motion (KE = ½mv²), while potential energy is stored energy "
            "due to position or configuration. The law of conservation of energy states that energy cannot "
            "be created or destroyed, only transformed from one form to another."
        ),
        "paragraphs": [
            "Kinetic Energy: The energy an object possesses due to its motion. Calculated as KE = ½mv², where m is mass and v is velocity.",
            "Potential Energy: Stored energy due to an object's position. Gravitational potential energy is PE = mgh, where h is height.",
            "Conservation of Energy: Energy cannot be created or destroyed in an isolated system. It can only change forms (e.g., potential to kinetic)."
        ]
    },
    {
        "id": "art3",
        "topic": "programming",
        "title": "Algorithm Complexity",
        "content": (
            "Algorithm complexity describes how the runtime or space requirements of an algorithm grow "
            "as the input size increases. Big O notation is used to express the upper bound of complexity. "
            "Common complexities include O(1) constant, O(log n) logarithmic, O(n) linear, "
            "O(n log n) linearithmic, and O(n²) quadratic."
        ),
        "paragraphs": [
            "O(1) - Constant Time: The algorithm takes the same amount of time regardless of input size. Example: accessing an array element by index.",
            "O(log n) - Logarithmic: The algorithm's time grows logarithmically with input size. Example: binary search.",
            "O(n) - Linear: Time grows directly proportional to input size. Example: iterating through an array."
        ]
    }
]


def _mock_retrieve(query: str) -> List[Dict[str, Any]]:
    """Mock retrieve function for articles.
    
    In production, this would query MongoDB/vector search.
    
    Args:
        query: Search query
        
    Returns:
        List of matching articles as JSON
    """
    query_lower = query.lower()
    
    # Simple keyword matching for mock
    results = []
    for article in MOCK_ARTICLES:
        if (query_lower in article["topic"].lower() or 
            query_lower in article["title"].lower() or
            query_lower in article["content"].lower()):
            results.append(article)
    
    # If no matches, return first article as fallback
    if not results:
        results = [MOCK_ARTICLES[0]]
    
    return results


async def retrieve_articles_node(state: GraphState) -> GraphState:
    """Node that retrieves articles based on the query.
    
    This is the core retrieval logic. It:
    1. Parses the query from the tool call
    2. Calls the (mocked) retrieve function
    3. Returns the results as a tool message
    """
    messages = state["conversation_state"]["messages"]
    
    # Get the tool call that routed here
    assistant_msg = None
    for msg in reversed(messages):
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            assistant_msg = msg
            break
    
    if not assistant_msg:
        error_msg = create_tool_message(
            content=json.dumps({"error": "No query provided"}),
            role="tool",
            name="routeToArticles"
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
    
    # Create tool response with retrieved articles
    tool_response = create_tool_message(
        content=json.dumps(results, ensure_ascii=False, indent=2),
        role="tool",
        tool_call_id=tool_call_id,
        name="routeToArticles"
    )
    
    state["conversation_state"]["messages"].append(tool_response)
    return state


def get_articles_agent_graph() -> StateGraph:
    """Build the articles retrieval sub-agent graph.
    
    Returns:
        Compiled StateGraph
    """
    graph = StateGraph(GraphState)
    
    graph.add_node("retrieve", retrieve_articles_node)
    
    graph.add_edge(START, "retrieve")
    graph.add_edge("retrieve", END)
    
    return graph.compile()
