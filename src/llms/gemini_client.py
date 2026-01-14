import os
from typing import List, Optional, Type, Union, cast

from circuitbreaker import CircuitBreaker, CircuitBreakerError
from google import genai
from google.api_core.exceptions import (
    DeadlineExceeded,
    InternalServerError,
    NotFound,
    PermissionDenied,
    ResourceExhausted,
    ServiceUnavailable,
)
from google.genai import errors, types
from loguru import logger
from pydantic import BaseModel
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential_jitter,
)

from ia_lms_redacoes.config.llm_clients_config import GeminiConfig
from ia_lms_redacoes.llms.clients.gemini_cache_manager import GeminiCacheManager

# Cache-related exceptions
CACHE_EXCEPTIONS = (NotFound, PermissionDenied, errors.ClientError)

# Connection-related exceptions that indicate client should be reset
CONNECTION_EXCEPTIONS = (ConnectionError, OSError)

# Retryable exceptions (PermissionDenied removed - auth errors don't self-resolve)
RETRYABLE_EXCEPTIONS = (
    ServiceUnavailable,
    ResourceExhausted,
    DeadlineExceeded,
    InternalServerError,
    NotFound,
    errors.ServerError,
    errors.ClientError,  # Sometimes 429/404 comes as ClientError
    ConnectionError,  # Connection issues should be retried
    OSError,  # OS-level connection issues
)

# Exceptions that should trigger circuit breaker (server-side errors only)
CIRCUIT_BREAKER_EXCEPTIONS = (
    ServiceUnavailable,
    ResourceExhausted,
    InternalServerError,
)


class GeminiCircuitBreaker(CircuitBreaker):
    """Circuit breaker for Gemini API calls.

    Opens after FAILURE_THRESHOLD consecutive failures of EXPECTED_EXCEPTION types.
    Stays open for RECOVERY_TIMEOUT seconds before allowing a test request.
    """

    FAILURE_THRESHOLD = 5
    RECOVERY_TIMEOUT = 30
    EXPECTED_EXCEPTION = CIRCUIT_BREAKER_EXCEPTIONS


class GeminiClient:
    """
    Async, stateless, and thread-safe wrapper for Google Gemini API.
    Uses GeminiCacheManager for cache lifecycle management.

    Features:
    - Automatic retries with exponential backoff (via tenacity)
    - Circuit breaker to fail fast on systemic failures (via circuitbreaker)
    - Proactive client reset on retries to handle stale connections
    - Response validation to catch empty/blocked responses early

    Note: CircuitBreakerError may be raised when the circuit is open.
    Callers should handle this for requeue/retry logic if needed.
    """

    # Shared circuit breaker by default (matches API reality: one endpoint)
    # Can be overridden per-instance for isolation (e.g., testing)
    _default_circuit: CircuitBreaker = GeminiCircuitBreaker()

    def __init__(
        self,
        config: Optional[GeminiConfig] = None,
        cache_manager: Optional[GeminiCacheManager] = None,
        circuit: Optional[CircuitBreaker] = None,
    ) -> None:
        if config is None:
            config = GeminiConfig()

        self.config = config
        self.client = self._create_client()
        self.cache_manager = cache_manager or GeminiCacheManager()
        self._circuit = circuit or GeminiClient._default_circuit

    def _create_client(self) -> genai.Client:
        """Create a new Gemini client with timeout configuration.

        Extracted to allow recreation on connection errors.
        """
        api_key = os.getenv(self.config.api_key_env_var)
        if not api_key:
            raise ValueError(f"{self.config.api_key_env_var} not found in environment")

        return genai.Client(
            api_key=api_key,
            http_options={"timeout": self.config.default_timeout * 1000},
        )

    def _validate_response(self, response: types.GenerateContentResponse) -> None:
        """Validate that the response is usable.

        Raises:
            ValueError: If response has no candidates or was blocked.
        """
        if not response.candidates:
            raise ValueError("Empty response from Gemini API (no candidates)")

        candidate = response.candidates[0]
        if hasattr(candidate, "finish_reason"):
            finish_reason = candidate.finish_reason
            if finish_reason in ("SAFETY", "RECITATION"):
                raise ValueError(
                    f"Response blocked by Gemini API (finish_reason={finish_reason})"
                )

    async def generate_llm_cache(
        self,
        cache_payload: types.CreateCachedContentConfig,
        model: Optional[str] = None,
    ) -> types.CachedContent:
        """
        Creates a cached content entry and registers it with the manager.
        Uses the cache manager to handle deduplication (returning existing cache if available).
        """
        target_model = model or self.config.model

        # Create or retrieve cache via manager (handles deduplication and registration)
        return await self.cache_manager.get_or_create(
            cache_payload=cache_payload, client=self.client, model=target_model
        )

    def list_available_models(self) -> List[str]:
        """Lists available Gemini models supporting generateContent."""

        models: List[str] = []

        for m in self.client.models.list():
            if m.name and (
                hasattr(m, "supported_generation_methods")
                and "generateContent" in m.supported_generation_methods  # type: ignore
            ):
                models.append(m.name)
            else:
                logger.warning(f"Model {m.name} does not support generateContent")

        return models

    async def _make_api_call(
        self,
        target_model: str,
        call_content: types.ContentListUnion,
        generate_config: types.GenerateContentConfig,
    ) -> types.GenerateContentResponse:
        """Make the actual API call, wrapped by circuit breaker.

        Uses self._circuit (shared by default, can be overridden per-instance).
        The circuit breaker will:
        - Track failures of CIRCUIT_BREAKER_EXCEPTIONS
        - Open after FAILURE_THRESHOLD consecutive failures
        - Raise CircuitBreakerError when open (fail fast)
        """

        # Apply circuit breaker as decorator to inner async function
        # This works because CircuitBreaker instances are callable decorators
        # and the library detects async def and handles it correctly
        @self._circuit
        async def _call() -> types.GenerateContentResponse:
            return await self.client.aio.models.generate_content(
                model=target_model,
                contents=call_content,
                config=generate_config,
            )

        return await _call()

    async def call_llm(
        self,
        call_content: Union[str, List[types.Content]],
        model: Optional[str] = None,
        cache_name: Optional[str] = None,
        structured_output: Optional[Type[BaseModel]] = None,
        temperature: Optional[float] = None,
        thinking_config: Optional[types.ThinkingConfig] = None,
        system_instruction: Optional[Union[str, types.Content]] = None,
    ) -> types.GenerateContentResponse:
        """
        Async method to call Gemini LLM with automatic retries and cache recovery.
        State is local to the execution context to ensure thread safety.

        Features:
        - Retries with exponential backoff on transient errors
        - Circuit breaker to fail fast on systemic failures
        - Proactive client reset on retries
        - Response validation

        Raises:
            CircuitBreakerError: When circuit is open (API unavailable)
            ValueError: When response is empty or blocked
            Various Google API exceptions after retries exhausted
        """
        target_model = model or self.config.model
        max_retries = self.config.max_retries

        # Build initial configuration
        config_kwargs: dict = {}
        if structured_output:
            config_kwargs["response_schema"] = structured_output.model_json_schema()
            config_kwargs["response_mime_type"] = "application/json"
        if temperature is not None:
            config_kwargs["temperature"] = temperature
        if thinking_config:
            config_kwargs["thinking_config"] = thinking_config
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction

        # Local state for retries
        current_cache_name = cache_name

        # Define the retry strategy with total timeout
        async for attempt in AsyncRetrying(
            stop=(
                stop_after_attempt(max_retries)
                | stop_after_delay(self.config.total_retry_timeout)
            ),
            wait=wait_exponential_jitter(
                initial=self.config.starting_retry_delay, max=30
            ),
            retry=retry_if_exception_type(RETRYABLE_EXCEPTIONS),
            reraise=True,
        ):
            with attempt:
                attempt_num = attempt.retry_state.attempt_number

                # Proactive client reset on retries (before circuit breaker check)
                # Concurrent recreation is possible and benign:
                # - In-flight calls keep their client reference
                # - New calls get a valid client
                # - Worst case: slight resource waste, not corruption
                if attempt_num >= 2:
                    logger.info(
                        f"LLM call | model={target_model} | retry={attempt_num} | "
                        "recreating client proactively"
                    )
                    self.client = self._create_client()

                # 1. Prepare Config with current cache
                current_config_kwargs = config_kwargs.copy()
                if current_cache_name:
                    # Ensure cache is valid before use
                    valid_cache_name = await self.cache_manager.get_or_regenerate(
                        current_cache_name,
                        self.client,
                        target_model,
                        self.config.cache_ttl,
                    )
                    if valid_cache_name:
                        current_cache_name = valid_cache_name
                        current_config_kwargs["cached_content"] = current_cache_name
                    else:
                        logger.warning(
                            f"LLM call | model={target_model} | "
                            f"cache regeneration failed for {current_cache_name}"
                        )
                        # Note: We do NOT update current_cache_name to None here.
                        # This allows subsequent retries to attempt regeneration again.

                generate_config = types.GenerateContentConfig(**current_config_kwargs)

                try:
                    # 2. Log attempt
                    logger.debug(
                        f"LLM call | model={target_model} | "
                        f"attempt={attempt_num}/{max_retries} | "
                        f"cache={'yes' if current_cache_name else 'no'}"
                    )

                    # 3. Make Request (circuit breaker applied via decorator)
                    response = await self._make_api_call(
                        target_model=target_model,
                        call_content=cast(types.ContentListUnion, call_content),
                        generate_config=generate_config,
                    )

                    # 4. Validate response before returning
                    self._validate_response(response)

                    return response

                except CircuitBreakerError:
                    # Don't retry circuit breaker errors - fail fast
                    logger.warning(
                        f"LLM call | model={target_model} | "
                        "circuit breaker open, API unavailable"
                    )
                    raise

                except CONNECTION_EXCEPTIONS as e:
                    # Reactive client reset on connection errors (fallback)
                    logger.warning(
                        f"LLM call failed | model={target_model} | "
                        f"attempt={attempt_num} | error_type={type(e).__name__} | "
                        "recreating client"
                    )
                    self.client = self._create_client()
                    raise

                except CACHE_EXCEPTIONS as e:
                    # Handle specific cache failures that happened DURING the call
                    # (e.g. expired exactly between check and usage)
                    is_cache_error = "cache" in str(e).lower()
                    if current_cache_name and (
                        is_cache_error or isinstance(e, NotFound)
                    ):
                        logger.warning(
                            f"LLM call failed | model={target_model} | "
                            f"attempt={attempt_num} | cache error: {e}"
                        )
                        # Force regeneration in next loop iteration
                        await self.cache_manager.invalidate_cache(current_cache_name)
                        raise e
                    # Log non-cache errors
                    logger.warning(
                        f"LLM call failed | model={target_model} | "
                        f"attempt={attempt_num} | error_type={type(e).__name__}"
                    )
                    raise e

                except Exception as e:
                    # Log any other failures
                    logger.warning(
                        f"LLM call failed | model={target_model} | "
                        f"attempt={attempt_num} | error_type={type(e).__name__}"
                    )
                    raise

        # Should be unreachable due to reraise=True, but satisfies linter
        raise RuntimeError("Max retries exceeded")
