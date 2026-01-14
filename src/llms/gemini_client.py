"""Simplified Gemini client for AI Tutor.

A streamlined wrapper for Google's Gemini API with retry logic.
"""

import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, Union

from google import genai
from google.genai import types
from pydantic import BaseModel
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config import settings


# Retryable exceptions
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    OSError,
    Exception,  # Broad catch for hackathon
)


class GeminiClient:
    """Async wrapper for Google Gemini API.
    
    Features:
    - Automatic retries with exponential backoff
    - Tool/function calling support
    - Response validation
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        """Initialize the Gemini client.
        
        Args:
            api_key: API key (defaults to settings.gemini_api_key or GEMINI_API_KEY env var)
            model: Model name (defaults to settings.gemini_model)
        """
        self.api_key = api_key or settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
        self.model = model or settings.gemini_model
        
        if not self.api_key:
            raise ValueError(
                "Gemini API key not found. Set GEMINI_API_KEY environment variable."
            )
        
        self.client = genai.Client(api_key=self.api_key)
    
    def _validate_response(self, response: types.GenerateContentResponse) -> None:
        """Validate that the response is usable."""
        if not response.candidates:
            raise ValueError("Empty response from Gemini API (no candidates)")
        
        candidate = response.candidates[0]
        if hasattr(candidate, "finish_reason"):
            finish_reason = candidate.finish_reason
            if finish_reason in ("SAFETY", "RECITATION"):
                raise ValueError(
                    f"Response blocked by Gemini API (finish_reason={finish_reason})"
                )
    
    async def call_llm(
        self,
        call_content: Union[str, List[Dict[str, Any]]],
        model: Optional[str] = None,
        structured_output: Optional[Type[BaseModel]] = None,
        temperature: Optional[float] = None,
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> types.GenerateContentResponse:
        """Async method to call Gemini LLM with automatic retries.
        
        Args:
            call_content: The content to send (string or list of messages)
            model: Model to use (defaults to instance model)
            structured_output: Pydantic model for structured response
            temperature: Temperature for generation
            system_instruction: System prompt
            tools: List of tool definitions for function calling
            
        Returns:
            GenerateContentResponse from Gemini
        """
        target_model = model or self.model
        max_retries = 3
        
        # Build configuration
        config_kwargs: Dict[str, Any] = {}
        if structured_output:
            config_kwargs["response_schema"] = structured_output.model_json_schema()
            config_kwargs["response_mime_type"] = "application/json"
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools:
            # Convert to Gemini tool format
            # Tools are now in direct format: {name, description, parameters}
            function_declarations = []
            for tool in tools:
                # Handle both wrapped and direct formats
                if "function" in tool:
                    func = tool["function"]
                else:
                    func = tool
                
                function_declarations.append(
                    types.FunctionDeclaration(
                        name=func["name"],
                        description=func.get("description", ""),
                        parameters=func.get("parameters", {})
                    )
                )
            
            if function_declarations:
                config_kwargs["tools"] = [types.Tool(function_declarations=function_declarations)]
        
        generate_config = types.GenerateContentConfig(**config_kwargs)
        
        # Retry logic
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            reraise=True,
        ):
            with attempt:
                response = await self.client.aio.models.generate_content(
                    model=target_model,
                    contents=call_content,
                    config=generate_config,
                )
                
                self._validate_response(response)
                self._log_call(
                    method="call_llm",
                    model=target_model,
                    contents=call_content,
                    config=config_kwargs,
                    response=response
                )
                return response
        
        raise RuntimeError("Max retries exceeded")

    async def send_chat_message(
        self,
        history: List[Dict[str, Any]],
        message: Union[str, List[Any]],
        model: Optional[str] = None,
        structured_output: Optional[Type[BaseModel]] = None,
        temperature: Optional[float] = None,
        system_instruction: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> types.GenerateContentResponse:
        """Async method to send a message in a chat session.
        
        Args:
            history: Conversation history
            message: New message content to send
            model: Model to use
            structured_output: Pydantic model for structured response
            temperature: Temperature
            system_instruction: System prompt
            tools: Tools definition
            
        Returns:
            GenerateContentResponse
        """
        target_model = model or self.model
        max_retries = 3
        
        # Build configuration
        config_kwargs: Dict[str, Any] = {}
        if structured_output:
            config_kwargs["response_schema"] = structured_output.model_json_schema()
            config_kwargs["response_mime_type"] = "application/json"
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if tools:
            # Convert to Gemini tool format
            function_declarations = []
            for tool in tools:
                if "function" in tool:
                    func = tool["function"]
                else:
                    func = tool
                
                function_declarations.append(
                    types.FunctionDeclaration(
                        name=func["name"],
                        description=func.get("description", ""),
                        parameters=func.get("parameters", {})
                    )
                )
            
            if function_declarations:
                config_kwargs["tools"] = [types.Tool(function_declarations=function_declarations)]
        
        generate_config = types.GenerateContentConfig(**config_kwargs)
        
        # Retry logic
        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=10),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            reraise=True,
        ):
            with attempt:
                # Create chat session with history
                chat = self.client.aio.chats.create(
                    model=target_model,
                    history=history,
                    config=generate_config,
                )
                
                # Convert message to appropriate format for send_message
                if isinstance(message, str):
                    send_content = message
                elif isinstance(message, dict):
                    # Handle Content dict with role and parts
                    if "parts" in message:
                        parts = message["parts"]
                        if len(parts) == 1:
                            part = parts[0]
                            if "text" in part:
                                send_content = part["text"]
                            elif "functionResponse" in part:
                                send_content = types.Part.from_function_response(
                                    name=part["functionResponse"]["name"],
                                    response=part["functionResponse"]["response"]
                                )
                            else:
                                send_content = message
                        else:
                            send_content = message
                    else:
                        send_content = message
                else:
                    send_content = message
                
                # Send new message
                response = await chat.send_message(send_content)
                
                self._validate_response(response)
                self._log_call(
                    method="send_chat_message",
                    model=target_model,
                    history=history,
                    message=send_content,
                    config=config_kwargs,
                    response=response
                )
                return response
        

        raise RuntimeError("Max retries exceeded")

    def _log_call(
        self,
        method: str,
        model: str,
        config: Dict[str, Any],
        contents: Any = None,
        history: Any = None,
        message: Any = None,
        response: Any = None,
    ) -> None:
        """Log the LLM call to a timestamped file."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            log_dir = os.path.join(os.getcwd(), "logs", "gemini")
            os.makedirs(log_dir, exist_ok=True)
            
            filename = f"{timestamp}_{method}.json"
            filepath = os.path.join(log_dir, filename)
            
            # Prepare log data
            log_data = {
                "timestamp": datetime.now().isoformat(),
                "method": method,
                "model": model,
                "config": self._serialize_for_log(config),
                "request": {
                    "contents": self._serialize_for_log(contents) if contents else None,
                    "history": self._serialize_for_log(history) if history else None,
                    "message": self._serialize_for_log(message) if message else None,
                },
            }
            
            if response:
                # Safely extract response text or function calls
                resp_data = {}
                try:
                    if hasattr(response, "text"):
                        resp_data["text"] = response.text
                except Exception:
                    pass
                
                try:
                    # Capture tool calls if any
                    candidates = getattr(response, "candidates", [])
                    if candidates:
                        parts = getattr(candidates[0].content, "parts", [])
                        tool_calls = [
                            {"name": p.function_call.name, "args": p.function_call.args}
                            for p in parts if p.function_call
                        ]
                        if tool_calls:
                            resp_data["tool_calls"] = tool_calls
                except Exception:
                    pass
                
                log_data["response"] = resp_data

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            # Don't let logging failures crash the main process
            print(f"Error logging Gemini call: {e}")

    def _serialize_for_log(self, obj: Any) -> Any:
        """Simple serializer for log data."""
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
            if isinstance(obj, dict):
                return {k: self._serialize_for_log(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [self._serialize_for_log(i) for i in obj]
            return obj
        return str(obj)
