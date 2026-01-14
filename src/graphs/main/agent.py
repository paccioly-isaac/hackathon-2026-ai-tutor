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
    build_show_questions_tool,
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
    
    2. showQuestions: Display multiple choice questions to the student. Use this after retrieving questions with routeToQuestions. The student can answer some or all questions at their pace.

    3. routeToQuestions: When the student wants practice questions, use this to retrieve relevant questions.
    
    4. routeToArticles: When the student wants to learn about a topic, use this to retrieve educational content.

    ATTENTION: ONLY USE THE ROUTE TOOLS ONCE PER ITERATION LOOP.
    </tools>
    
    <guidelines>
    - Always be helpful and educational
    - When you retrieve content, cite the relevant paragraphs in your response
    - Use Markdown for formatting (bold, italics, lists, code blocks) to make responses clearer
    - If you need clarification, ask the student and use sendMessage with interrupt=True
    - Keep responses clear and appropriately sized
    - Respond in the same language the student uses
    - When presenting questions, use showQuestions tool with the question IDs
    - You can reference previous questions using [q1], [q2], [q3], etc. notation in your messages
    - Note: When you write [q1], [q2], etc., they will be displayed to the user as interactive "Questão 1", "Questão 2", etc. badges
    - When the student answers questions, review their answers and provide helpful feedback
    </guidelines>
</system>
""").strip()


def build_llm_tools(state: GraphState) -> GraphState:
    """Build and store tool definitions in state."""
    tools = [
        build_send_message_tool(),
        build_route_to_questions_tool(),
        build_route_to_articles_tool(),
        build_show_questions_tool(),
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
    elif tool_name == "showQuestions":
        return "handle_show_questions"
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


# Mock questions storage (same as in questions_agent.py for lookup)
QUESTIONS_DB = {
    "q1": {
        "id": "q1",
        "question": "Em que ano Pedro Álvares Cabral chegou ao território que hoje conhecemos como Brasil?",
        "options": [
            {"id": "A", "text": "1492", "isCorrect": False},
            {"id": "B", "text": "1500", "isCorrect": True},
            {"id": "C", "text": "1530", "isCorrect": False},
            {"id": "D", "text": "1822", "isCorrect": False}
        ],
        "explanation": "A esquadra de Pedro Álvares Cabral chegou ao Brasil em 22 de abril de 1500."
    },
    "q2": {
        "id": "q2",
        "question": "Qual era o principal objetivo oficial da esquadra de Cabral ao zarpar de Portugal?",
        "options": [
            {"id": "A", "text": "Explorar o interior da Amazônia", "isCorrect": False},
            {"id": "B", "text": "Colonizar a região do Rio da Prata", "isCorrect": False},
            {"id": "C", "text": "Estabelecer uma rota comercial com as Índias", "isCorrect": True},
            {"id": "D", "text": "Encontrar ouro nas Minas Gerais", "isCorrect": False}
        ],
        "explanation": "O objetivo principal da expedição era seguir para as Índias para estabelecer relações comerciais e trazer especiarias."
    },
    "q3": {
        "id": "q3",
        "question": "Qual foi o primeiro nome dado pelos portugueses à terra descoberta, antes de ser chamada de Brasil?",
        "options": [
            {"id": "A", "text": "Ilha de Vera Cruz", "isCorrect": True},
            {"id": "B", "text": "Terra de Santa Cruz", "isCorrect": False},
            {"id": "C", "text": "Província de São Vicente", "isCorrect": False},
            {"id": "D", "text": "Capitania Geral", "isCorrect": False}
        ],
        "explanation": "Inicialmente, acreditando tratar-se de uma ilha, os portugueses chamaram a terra de Ilha de Vera Cruz."
    },
    "q4": {
        "id": "q4",
        "question": "Quem era o rei de Portugal na época do descobrimento do Brasil?",
        "options": [
            {"id": "A", "text": "D. Pedro II", "isCorrect": False},
            {"id": "B", "text": "D. João VI", "isCorrect": False},
            {"id": "C", "text": "D. Manuel I", "isCorrect": True},
            {"id": "D", "text": "D. Afonso Henriques", "isCorrect": False}
        ],
        "explanation": "D. Manuel I, o Venturoso, era o monarca português no ano de 1500."
    },
    "q5": {
        "id": "q5",
        "question": "A famosa carta que relatava o descobrimento ao rei de Portugal foi escrita por quem?",
        "options": [
            {"id": "A", "text": "Pedro Álvares Cabral", "isCorrect": False},
            {"id": "B", "text": "Pero Vaz de Caminha", "isCorrect": True},
            {"id": "C", "text": "Américo Vespúcio", "isCorrect": False},
            {"id": "D", "text": "Fernão de Magalhães", "isCorrect": False}
        ],
        "explanation": "Pero Vaz de Caminha era o escrivão da frota e escreveu a detalhada carta relatando o achamento da terra."
    },
    "q6": {
        "id": "q6",
        "question": "Qual foi o primeiro recurso natural explorado intensivamente pelos portugueses no litoral brasileiro?",
        "options": [
            {"id": "A", "text": "Cana-de-açúcar", "isCorrect": False},
            {"id": "B", "text": "Ouro", "isCorrect": False},
            {"id": "C", "text": "Pau-brasil", "isCorrect": True},
            {"id": "D", "text": "Café", "isCorrect": False}
        ],
        "explanation": "O pau-brasil, madeira que fornecia um pigmento vermelho muito valorizado na Europa, foi o primeiro foco de exploração."
    },
    "q7": {
        "id": "q7",
        "question": "Como se chamava o primeiro monte avistado pela esquadra de Cabral ao se aproximar do litoral?",
        "options": [
            {"id": "A", "text": "Pão de Açúcar", "isCorrect": False},
            {"id": "B", "text": "Monte Pascoal", "isCorrect": True},
            {"id": "C", "text": "Pico da Neblina", "isCorrect": False},
            {"id": "D", "text": "Morro do Chapéu", "isCorrect": False}
        ],
        "explanation": "O monte foi batizado de Monte Pascoal por ter sido avistado na época da Páscoa."
    },
    "q8": {
        "id": "q8",
        "question": "Que povo indígena habitava majoritariamente o litoral brasileiro no momento da chegada dos portugueses?",
        "options": [
            {"id": "A", "text": "Incas", "isCorrect": False},
            {"id": "B", "text": "Astecas", "isCorrect": False},
            {"id": "C", "text": "Tupis/Tupinambás", "isCorrect": True},
            {"id": "D", "text": "Maias", "isCorrect": False}
        ],
        "explanation": "Os povos de tronco linguístico Tupi, como os Tupinambás, eram os principais habitantes do litoral em 1500."
    },
    "q9": {
        "id": "q9",
        "question": "Quantas embarcações faziam parte da frota original liderada por Pedro Álvares Cabral?",
        "options": [
            {"id": "A", "text": "3", "isCorrect": False},
            {"id": "B", "text": "7", "isCorrect": False},
            {"id": "C", "text": "13", "isCorrect": True},
            {"id": "D", "text": "20", "isCorrect": False}
        ],
        "explanation": "A esquadra de Cabral era composta por 13 embarcações (9 naus, 3 caravelas e 1 naveta de mantimentos)."
    },
    "q10": {
        "id": "q10",
        "question": "Em que local do atual estado da Bahia a esquadra de Cabral aportou pela primeira vez?",
        "options": [
            {"id": "A", "text": "Salvador", "isCorrect": False},
            {"id": "B", "text": "Porto Seguro (Cabrália)", "isCorrect": True},
            {"id": "C", "text": "Ilhéus", "isCorrect": False},
            {"id": "D", "text": "Itacaré", "isCorrect": False}
        ],
        "explanation": "A frota ancorou primeiro na região de Porto Seguro, especificamente na Baía de Cabrália."
    }
}


async def handle_show_questions(state: GraphState) -> GraphState:
    """Handle showQuestions tool call."""
    logger.info("📝 Handling showQuestions")
    messages = state["conversation_state"]["messages"]
    assistant_msg = get_last_message(messages, "assistant")
    
    if not assistant_msg or not assistant_msg.get("tool_calls"):
        return state
    
    tool_call = assistant_msg["tool_calls"][0]
    tool_call_id = tool_call["id"]
    arguments = json.loads(tool_call["function"]["arguments"])
    
    question_ids = arguments.get("questionIds", [])
    title = arguments.get("title", "Questions")
    message = arguments.get("message", "")
    
    # Look up questions from the mock database
    questions = []
    for qid in question_ids:
        if qid in QUESTIONS_DB:
            questions.append(QUESTIONS_DB[qid])
        else:
            logger.warning(f"Question {qid} not found in database")
    
    # Create response with questions data
    response_content = json.dumps({
        "type": "questions",
        "title": title,
        "message": message,
        "questions": questions
    })
    
    tool_response = create_tool_message(
        content=response_content,
        role="tool",
        tool_call_id=tool_call_id,
        name="showQuestions"
    )
    
    state["conversation_state"]["messages"].append(tool_response)
    logger.success(f"✅ Showing {len(questions)} questions")
    
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
    graph.add_node("handle_show_questions", handle_show_questions)
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
            "handle_show_questions": "handle_show_questions",
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
    
    # After showing questions, always wait for input
    graph.add_edge("handle_show_questions", "wait_for_input")
    
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
