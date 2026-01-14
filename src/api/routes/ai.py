"""AI tutor endpoints using LangGraph for orchestration.

Provides the /ask endpoint for students to interact with the AI tutor.
"""

import json
import traceback
from typing import List, Optional

from fastapi import APIRouter, HTTPException, status
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger
from pydantic import BaseModel, Field

from src.graphs.main import get_main_graph
from src.graphs.state import get_initial_state, Message
from src.graphs.utils import run_or_resume_graph

router = APIRouter(prefix="/tutor", tags=["ai-tutor"])

# Shared checkpointer for all conversations (in-memory for hackathon)
_checkpointer = MemorySaver()
_graph = None


def get_graph():
    """Get or create the main graph instance."""
    global _graph
    if _graph is None:
        _graph = get_main_graph(checkpointer=_checkpointer)
    return _graph


# Pydantic models for request/response
class AskRequest(BaseModel):
    """Request to ask the AI tutor a question."""
    conversation_id: str = Field(..., description="Unique conversation identifier")
    message: str = Field(..., description="Student's message/question")
    user_id: str = Field(default="hackathon_judge", description="User identifier (mocked)")


class AskResponse(BaseModel):
    """Response from the AI tutor."""
    conversation_id: str
    message: str = Field(..., description="AI tutor's response message")
    cited_paragraphs: List[str] = Field(default_factory=list, description="Cited paragraphs from retrieved content")
    waiting_for_input: bool = Field(default=False, description="Whether the agent is waiting for more input")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    details: dict = {}


@router.post(
    "/ask",
    response_model=AskResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask the AI tutor a question",
    description="Submit a question to the AI tutor and receive an educational response",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid input"},
        503: {"model": ErrorResponse, "description": "Service unavailable"},
    },
)
async def ask_tutor(request: AskRequest) -> AskResponse:
    """Process a student question and return an AI-generated response.
    
    This endpoint:
    1. Creates or resumes a conversation graph
    2. Adds the new message
    3. Runs the graph until completion or interrupt
    4. Returns the latest response with citations
    """
    logger.info(f"💬 New request: conversation_id={request.conversation_id}")
    logger.debug(f"Message: {request.message[:100]}...")
    
    try:
        graph = get_graph()
        config = {"configurable": {"thread_id": request.conversation_id}}
        
        # Create user message
        user_message: Message = {
            "role": "user",
            "content": request.message,
            "id": f"msg_{request.conversation_id}_{len(request.message)}"
        }
        
        # Check if this is a new conversation or resuming
        existing_state = await graph.aget_state(config)
        is_first_execution = existing_state.values == {}
        
        if is_first_execution:
            # New conversation - create initial state
            initial_state = get_initial_state(
                conversation_id=request.conversation_id,
                messages=[user_message],
            )
            result = await run_or_resume_graph(
                graph=graph,
                config=config,
                initial_state=initial_state,
            )
        else:
            # Resuming - pass new message as resume value
            result = await run_or_resume_graph(
                graph=graph,
                config=config,
                resume_value=[user_message],
            )
        
        # Extract response from result
        messages = result.get("conversation_state", {}).get("messages", [])
        graph_status = result.get("status", "complete")
        
        # Find the last sendMessage tool response
        response_message = ""
        cited_paragraphs: List[str] = []
        
        for msg in reversed(messages):
            if msg.get("role") == "tool" and msg.get("name") == "sendMessage":
                try:
                    content = json.loads(msg.get("content", "{}"))
                    response_message = content.get("message", "")
                    cited_paragraphs = content.get("citedParagraphs", [])
                    break
                except json.JSONDecodeError:
                    response_message = msg.get("content", "")
                    break
        
        # If no sendMessage found, check for assistant message
        if not response_message:
            for msg in reversed(messages):
                if msg.get("role") == "assistant" and msg.get("content"):
                    response_message = msg.get("content", "")
                    break
        
        return AskResponse(
            conversation_id=request.conversation_id,
            message=response_message or "I'm processing your request...",
            cited_paragraphs=cited_paragraphs,
            waiting_for_input=graph_status == "waiting_for_input",
        )
        
    except Exception as e:
        print(f"API error: {e}")
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"error": str(e), "details": {}},
        ) from e


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check for AI tutor service",
)
async def health_check() -> dict:
    """Check if the AI tutor service is healthy."""
    return {"status": "healthy", "service": "ai-tutor"}
