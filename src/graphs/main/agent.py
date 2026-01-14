"""Main orchestrator agent for the AI Tutor.

This is the central agent that:
1. Receives student messages
2. Decides which tools to use (send message, wait for input, route to retrieval)
3. Coordinates with retrieval sub-agents
4. Returns responses to the student
"""

import json
import traceback
import uuid
from textwrap import dedent
from typing import Any, Dict, List

from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt
from loguru import logger

from src.graphs.state import GraphState, Message
from src.graphs.tools import (
    build_send_message_tool,
    build_route_to_questions_tool,
    build_route_to_articles_tool,
)
from src.graphs.utils.messages import create_tool_message, get_last_message
from src.graphs.retrieval import get_questions_agent_graph, get_articles_agent_graph
from src.llms.gemini_client import GeminiClient
from src.config import settings


# System prompt for the AI Tutor
SYSTEM_PROMPT = dedent("""
<system>
    <role>
    You are an AI Tutor assistant helping students learn. Your role is to:
    - Answer questions clearly and educationally
    - Provide practice questions when requested
    - Explain concepts with examples
    - Be encouraging and supportive
    </role>
    
    <tools>
    You have access to the following tools:
    
    1. sendMessage: Send a response to the student. Include citedParagraphs when referencing retrieved content. Set interrupt=True to pause and wait for student response.
    

    3. routeToQuestions: When the student wants practice questions, use this to retrieve relevant questions.
    
    4. routeToArticles: When the student wants to learn about a topic, use this to retrieve educational content.
    </tools>
    
    <guidelines>
    - Always be helpful and educational
    - When you retrieve content, cite the relevant paragraphs in your response
    - When you retrieve content, cite the relevant paragraphs in your response
    - If you need clarification, ask the student and use sendMessage with interrupt=True
    - Keep responses clear and appropriately sized
    - Respond in the same language the student uses
    </guidelines>
</system>
""").strip()


def build_llm_tools(state: GraphState) -> GraphState:
    """Build and store tool definitions in state."""
    tools = [
        build_send_message_tool(),
        build_route_to_questions_tool(),
        build_route_to_articles_tool(),
    ]
    state["llm_tools"] = tools
    return state


async def agent_node(state: GraphState) -> GraphState:
    """Main agent node that calls the LLM.
    
    Uses Gemini client to generate a response with tool calls.
    """
    logger.info("🤖 Agent node executing")
    # Build messages for Gemini
    messages = state["conversation_state"]["messages"]
    logger.debug(f"Processing {len(messages)} messages in history")
    
    # Format messages for Gemini API
    gemini_messages = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        
        if role == "user":
            gemini_messages.append({
                "role": "user",
                "parts": [{"text": content}]
            })
        elif role == "assistant":
            if msg.get("tool_calls"):
                # Assistant with tool call
                tool_call = msg["tool_calls"][0]
                part_dict = {
                    "functionCall": {
                        "name": tool_call["function"]["name"],
                        "args": json.loads(tool_call["function"]["arguments"])
                    }
                }
                # Include thought_signature if present (required for Gemini 3)
                if "thought_signature" in msg and msg["thought_signature"]:
                    part_dict["thought_signature"] = msg["thought_signature"]
                
                gemini_messages.append({
                    "role": "model",
                    "parts": [part_dict]
                })
            elif content:
                gemini_messages.append({
                    "role": "model",
                    "parts": [{"text": content}]
                })
        elif role == "tool":
            # Tool response
            gemini_messages.append({
                "role": "function",
                "parts": [{
                    "functionResponse": {
                        "name": msg.get("name", "tool"),
                        "response": {"result": content}
                    }
                }]
            })
    
    # Create Gemini client and call
    client = GeminiClient()
    
    try:
        # Split into history and current message for chat session
        if not gemini_messages:
             # Should not happen in normal flow
             raise ValueError("No messages to send")
        
        logger.info(f"📤 Calling Gemini with {len(gemini_messages)} messages")
        response = await client.call_llm(
            call_content=gemini_messages,
            system_instruction=SYSTEM_PROMPT,
            model=settings.gemini_model,
            tools=state["llm_tools"],
        )
        logger.success("✅ Gemini response received")
        
        # Parse response
        if not response.candidates:
            raise ValueError("No candidates in response")
            
        candidate = response.candidates[0]
        
        if not candidate.content or not candidate.content.parts:
            # No content parts, create default response
            assistant_message = create_tool_message(
                content="",
                role="assistant",
                tool_calls=[{
                    "id": f"call_{uuid.uuid4().hex[:24]}",
                    "type": "function",
                    "function": {
                        "name": "sendMessage",
                        "arguments": json.dumps({"message": "I'm here to help! What would you like to learn about?"})
                    }
                }]
            )
            state["conversation_state"]["messages"].append(assistant_message)
            return state
        
        content_parts = candidate.content.parts
        
        # Check if there's a function call
        assistant_message: Message
        for part in content_parts:
            if hasattr(part, 'function_call') and part.function_call:
                func_call = part.function_call
                tool_call_id = f"call_{uuid.uuid4().hex[:24]}"
                
                # Extract thought_signature if present
                thought_signature = getattr(part, "thought_signature", None)
                
                assistant_message = create_tool_message(
                    content="",
                    role="assistant",
                    tool_calls=[{
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": func_call.name,
                            "arguments": json.dumps(dict(func_call.args) if func_call.args else {})
                        }
                    }]
                )
                
                # Store thought_signature in the message
                if thought_signature:
                    assistant_message["thought_signature"] = thought_signature
                    logger.debug(f"💭 Captured thought_signature")
                
                logger.info(f"🔧 Tool call: {func_call.name}")
                break
            elif hasattr(part, 'text') and part.text:
                # Plain text response - wrap in sendMessage
                assistant_message = create_tool_message(
                    content="",
                    role="assistant",
                    tool_calls=[{
                        "id": f"call_{uuid.uuid4().hex[:24]}",
                        "type": "function",
                        "function": {
                            "name": "sendMessage",
                            "arguments": json.dumps({"message": part.text})
                        }
                    }]
                )
                break
        else:
            # Fallback
            assistant_message = create_tool_message(
                content="",
                role="assistant",
                tool_calls=[{
                    "id": f"call_{uuid.uuid4().hex[:24]}",
                    "type": "function",
                    "function": {
                        "name": "sendMessage",
                        "arguments": json.dumps({"message": "I'm not sure how to help with that."})
                    }
                }]
            )
        
        state["conversation_state"]["messages"].append(assistant_message)
        return state
        
    except Exception as e:
        # On error, print full traceback and send error message
        print(f"Agent error: {e}")
        traceback.print_exc()
        assistant_message = create_tool_message(
            content="",
            role="assistant",
            tool_calls=[{
                "id": f"call_{uuid.uuid4().hex[:24]}",
                "type": "function",
                "function": {
                    "name": "sendMessage",
                    "arguments": json.dumps({"message": f"Sorry, I encountered an error. Please try again."})
                }
            }]
        )
        state["conversation_state"]["messages"].append(assistant_message)
        return state


def tool_router(state: GraphState) -> str:
    """Route to appropriate tool handler based on agent's tool call."""
    messages = state["conversation_state"]["messages"]
    assistant_msg = get_last_message(messages, "assistant")
    
    if not assistant_msg or not assistant_msg.get("tool_calls"):
        logger.info("🏁 No tool call - ending")
        return "end"
    
    tool_call = assistant_msg["tool_calls"][0]
    tool_name = tool_call["function"]["name"]
    logger.info(f"🔀 Routing to: {tool_name}")
    
    if tool_name == "sendMessage":
        return "handle_send_message"
    elif tool_name == "routeToQuestions":
        return "route_to_questions"
    elif tool_name == "routeToArticles":
        return "route_to_articles"
    else:
        return "end"


def post_send_message_router(state: GraphState) -> str:
    """Decide next step after sending message."""
    messages = state["conversation_state"]["messages"]
    assistant_msg = get_last_message(messages, "assistant")
    
    if not assistant_msg or not assistant_msg.get("tool_calls"):
        return "agent"
        
    tool_call = assistant_msg["tool_calls"][0]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    if arguments.get("interrupt", True):
        return "wait_for_input"
    return "agent"


async def handle_send_message(state: GraphState) -> GraphState:
    """Handle sendMessage tool call."""
    logger.info("💬 Handling sendMessage")
    messages = state["conversation_state"]["messages"]
    assistant_msg = get_last_message(messages, "assistant")
    
    if not assistant_msg or not assistant_msg.get("tool_calls"):
        return state
    
    tool_call = assistant_msg["tool_calls"][0]
    tool_call_id = tool_call["id"]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    message_text = arguments.get("message", "")
    cited_paragraphs = arguments.get("citedParagraphs", [])
    
    # Store cited paragraphs in response for API to extract
    response_content = json.dumps({
        "message": message_text,
        "citedParagraphs": cited_paragraphs
    })
    
    tool_response = create_tool_message(
        content=response_content,
        role="tool",
        tool_call_id=tool_call_id,
        name="sendMessage"
    )
    
    state["conversation_state"]["messages"].append(tool_response)
    logger.success(f"✅ Message sent: {message_text[:100]}...")
    
    return state


def wait_for_input(state: GraphState) -> GraphState:
    """Pause graph and wait for user input."""
    # Trigger interrupt - graph will pause here
    state["status"] = "waiting_for_input"
    new_messages = interrupt("waiting_for_input")
    
    # When resumed, add new messages
    if new_messages:
        if isinstance(new_messages, list):
            state["conversation_state"]["messages"].extend(new_messages)
        else:
            state["conversation_state"]["messages"].append(new_messages)
            
    return state





def get_main_graph(checkpointer: Any = None) -> StateGraph:
    """Build the main AI Tutor graph.
    
    Args:
        checkpointer: Optional checkpointer for state persistence
        
    Returns:
        Compiled StateGraph
    """
    # Get sub-agent graphs
    questions_graph = get_questions_agent_graph()
    articles_graph = get_articles_agent_graph()
    
    graph = StateGraph(GraphState)
    
    # Add nodes
    graph.add_node("build_tools", build_llm_tools)
    graph.add_node("agent", agent_node)
    graph.add_node("handle_send_message", handle_send_message)
    graph.add_node("wait_for_input", wait_for_input)
    graph.add_node("route_to_questions", questions_graph)
    graph.add_node("route_to_articles", articles_graph)
    
    # Start -> build tools -> agent
    graph.add_edge(START, "build_tools")
    graph.add_edge("build_tools", "agent")
    
    # Agent routes to tool handlers
    graph.add_conditional_edges(
        "agent",
        tool_router,
        {
            "handle_send_message": "handle_send_message",
            "route_to_questions": "route_to_questions",
            "route_to_articles": "route_to_articles",
            "end": END
        }
    )
    
    # After send_message, decide whether to wait or go back
    graph.add_conditional_edges(
        "handle_send_message",
        post_send_message_router,
        {
            "wait_for_input": "wait_for_input",
            "agent": "agent"
        }
    )
    
    # After waiting, go back to agent
    graph.add_edge("wait_for_input", "agent")
    
    # After retrieval, go back to agent to process results
    graph.add_edge("route_to_questions", "agent")
    graph.add_edge("route_to_articles", "agent")
    
    return graph.compile(checkpointer=checkpointer)


if __name__ == "__main__":
    import asyncio
    
    async def main():
        graph = get_main_graph()
        print(graph.get_graph().draw_mermaid())
    
    asyncio.run(main())
