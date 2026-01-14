import os
import random
import time
from abc import ABC, abstractmethod
from typing import Any, cast

from google import genai as genai  # type: ignore[import-not-found]
from google.api_core.exceptions import (  # type: ignore[import-not-found]
    DeadlineExceeded,
    GoogleAPIError,
    InternalServerError,
    InvalidArgument,
    PermissionDenied,
    ResourceExhausted,
    ServiceUnavailable,
    Unauthenticated,
)
from google.genai import types  # type: ignore[import-not-found]
from loguru import logger  # type: ignore[import-not-found]

# Import httpx exceptions for connection errors
try:
    import httpx  # type: ignore[import-not-found]

    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Import OpenAI SDK and exceptions
from openai import (  # type: ignore[import-not-found]
    APIConnectionError,
    APIError,
    APIStatusError,
    OpenAI,
    RateLimitError,
)
from openai import Timeout as OpenAITimeout


class Embedder(ABC):
    """Abstract base class for embedding generation.

    This class defines the interface for all embedding implementations.
    Concrete implementations should provide methods to generate embeddings
    from text using various embedding models/APIs.
    """

    @abstractmethod
    def embed(self, text: str) -> list[float] | None:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Optional[List[float]]: Embedding vector as a list of floats, or None on error
        """
        pass

    @abstractmethod
    def batch_embed(self, texts: list[str]) -> list[list[float]] | None:
        """Generate embeddings for multiple texts.

        Args:
            texts: List of text strings to embed

        Returns:
            Optional[List[List[float]]]: List of embedding vectors, or None on error
        """
        pass

    @abstractmethod
    def get_config(self) -> dict[str, Any]:
        """Return embedder configuration.

        Returns:
            Dict[str, Any]: Configuration dictionary containing embedder parameters
        """
        pass

    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Return embedding dimension.

        Returns:
            int: Dimensionality of the embedding vectors
        """
        pass


class GeminiEmbedder(Embedder):
    """Google Gemini embedding implementation with robust retry logic.

    This class provides embedding generation using Google's Gemini API with
    sophisticated retry logic including circuit breaker pattern, connection
    error handling, and exponential backoff.

    Args:
        api_key: Google Gemini API key (defaults to GEMINI_API_KEY env var)
        task_type: Task type for embedding optimization (e.g., "RETRIEVAL_QUERY")
        output_dimensionality: Output dimension size (128-3072)
        max_retries: Maximum number of retry attempts on failure
        restart_client_on_connection_error: Whether to recreate client on connection errors

    Example:
        >>> embedder = GeminiEmbedder(
        ...     task_type="RETRIEVAL_QUERY",
        ...     output_dimensionality=3072,
        ...     max_retries=15
        ... )
        >>> embedding = embedder.embed("Hello world")
        >>> embeddings = embedder.batch_embed(["Text 1", "Text 2"])
    """

    def __init__(
        self,
        api_key: str | None = None,
        task_type: str = "RETRIEVAL_QUERY",
        output_dimensionality: int = 3072,
        max_retries: int = 15,
        restart_client_on_connection_error: bool = True,
    ):
        """Initialize the GeminiEmbedder with configuration."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set in GEMINI_API_KEY environment variable"
            )

        self.task_type = task_type
        self.output_dimensionality = output_dimensionality
        self.max_retries = max_retries
        self.restart_client_on_connection_error = restart_client_on_connection_error

        # Initialize client
        self.client = genai.Client(api_key=self.api_key)
        logger.info(
            f"GeminiEmbedder initialized with dimension={output_dimensionality}, task_type={task_type}"
        )

    @property
    def embedding_dimension(self) -> int:
        """Return embedding dimension."""
        return self.output_dimensionality

    def get_config(self) -> dict[str, Any]:
        """Return embedder configuration."""
        return {
            "model": "gemini-embedding-001",
            "task_type": self.task_type,
            "output_dimensionality": self.output_dimensionality,
            "max_retries": self.max_retries,
            "restart_client_on_connection_error": self.restart_client_on_connection_error,
        }

    def __repr__(self) -> str:
        """Return string representation of embedder."""
        return (
            f"GeminiEmbedder(task_type='{self.task_type}', "
            f"output_dimensionality={self.output_dimensionality}, "
            f"max_retries={self.max_retries})"
        )

    def embed(self, text: str) -> list[float] | None:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Optional[List[float]]: Embedding vector, or None on error

        Raises:
            ValueError: If text is empty
            Various Google API exceptions if all retries fail
        """
        if not text or text.strip() == "":
            raise ValueError("Cannot embed empty text")

        embeddings = self.batch_embed([text])
        return embeddings[0] if embeddings else None

    def batch_embed(self, texts: str | list[str]) -> list[list[float]] | None:
        """Generate embeddings for multiple texts with retry logic.

        This method implements sophisticated retry logic including:
        - Exponential backoff with jitter
        - Circuit breaker for persistent connection issues
        - Automatic client reset on connection errors
        - Specific handling for different error types

        Args:
            texts: Text string or list of text strings to embed

        Returns:
            Optional[List[List[float]]]: List of embedding vectors, or None if invalid input

        Raises:
            PermissionDenied: If authentication/permission errors occur
            Unauthenticated: If authentication fails
            ServiceUnavailable: If service is unavailable after all retries
            ResourceExhausted: If rate limits are exceeded after all retries
            GoogleAPIError: If other Google API errors occur after all retries
            Exception: If unexpected errors occur after all retries
        """
        # Validate input before making API call
        if not texts or (isinstance(texts, str) and texts.strip() == ""):
            logger.warning("Empty text provided for embedding, skipping API call")
            return None

        # Track consecutive connection errors for circuit breaker pattern
        consecutive_connection_errors = 0
        max_consecutive_connection_errors = 5

        # Store the current client reference for potential reset
        current_client = self.client

        for attempt in range(self.max_retries):
            try:
                response = current_client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=texts,
                    config=types.EmbedContentConfig(
                        task_type=self.task_type,
                        output_dimensionality=self.output_dimensionality,
                    ),
                )
                # Reset connection error counter on success
                consecutive_connection_errors = 0
                # According to the docs, the response is an object with an 'embeddings' attribute
                return cast(list[list[float]], response.embeddings)
            except InvalidArgument as e:
                # Don't retry on invalid argument errors (like empty content)
                logger.error(f"Invalid content provided for embedding: {e}")
                return None

            except (PermissionDenied, Unauthenticated) as e:
                # Don't retry on authentication/permission errors
                logger.error(f"Authentication error: {e}")
                raise e

            except ServiceUnavailable as e:
                # Handle 503 UNAVAILABLE errors with special retry logic
                logger.warning(f"Service unavailable on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    # Longer wait for 503 errors: 3x base delay with jitter
                    base_wait = 2**attempt * 3  # 3x longer than normal
                    max_wait = 300  # Cap at 5 minutes
                    wait_time = min(base_wait, max_wait)
                    # Add jitter to prevent thundering herd (10-20% random variation)
                    jitter = random.uniform(0.9, 1.1)
                    wait_time = int(wait_time * jitter)
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Service unavailable after {self.max_retries} attempts, giving up"
                    )
                    raise e

            except ResourceExhausted as e:
                # Handle rate limit errors with standard retry logic
                logger.warning(
                    f"Resource exhausted (rate limit) on attempt {attempt + 1}: {e}"
                )
                if attempt < self.max_retries - 1:
                    # Standard exponential backoff with jitter for rate limits
                    base_wait = 2**attempt
                    max_wait = 60  # Cap at 1 minute for rate limits
                    wait_time = min(base_wait, max_wait)
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = int(wait_time * jitter)
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Resource exhausted after {self.max_retries} attempts: {e}"
                    )
                    raise e

            except (DeadlineExceeded, InternalServerError) as e:
                # Handle server-side errors that might be connection-related
                consecutive_connection_errors += 1
                logger.warning(
                    f"Server error on attempt {attempt + 1} (consecutive: {consecutive_connection_errors}): {e}"
                )
                if attempt < self.max_retries - 1:
                    # Circuit breaker for persistent connection issues
                    if (
                        consecutive_connection_errors
                        >= max_consecutive_connection_errors
                    ):
                        logger.warning(
                            f"Too many consecutive connection errors ({consecutive_connection_errors}), implementing circuit breaker"
                        )
                        base_wait = 300  # 5 minutes
                        consecutive_connection_errors = 0
                    else:
                        # Progressive backoff for connection issues
                        if attempt == 0:
                            base_wait = 10  # Start with 10 seconds
                        else:
                            base_wait = 2**attempt * 3  # 3x longer than normal

                    max_wait = 600  # Cap at 10 minutes
                    wait_time = min(base_wait, max_wait)
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = int(wait_time * jitter)
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

                    # Reset client if enabled and we've had connection issues
                    if (
                        self.restart_client_on_connection_error
                        and consecutive_connection_errors > 0
                    ):
                        try:
                            logger.info("Attempting to reset client connection...")
                            # Create a new client instance with the same API key
                            if self.api_key:
                                current_client = genai.Client(api_key=self.api_key)
                                logger.info("Client connection reset successfully")
                            else:
                                logger.warning(
                                    "Could not reset client: GEMINI_API_KEY not found"
                                )
                        except Exception as reset_error:
                            logger.warning(f"Failed to reset client: {reset_error}")
                else:
                    logger.error(f"Server error after {self.max_retries} attempts: {e}")
                    raise e

            except GoogleAPIError as e:
                # Handle other Google API errors
                logger.error(f"Google API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    # Standard exponential backoff with jitter
                    base_wait = 2**attempt
                    max_wait = 60  # Cap at 1 minute for other errors
                    wait_time = min(base_wait, max_wait)
                    # Add jitter to prevent thundering herd
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = int(wait_time * jitter)
                    logger.error(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Google API error after {self.max_retries} attempts: {e}"
                    )
                    raise e

            except Exception as e:
                # Handle httpx connection errors specifically if available
                if HTTPX_AVAILABLE and isinstance(
                    e,
                    (
                        httpx.RemoteProtocolError,
                        httpx.ConnectError,
                        httpx.TimeoutException,
                        httpx.NetworkError,
                    ),
                ):
                    # Treat httpx connection errors with client reset
                    consecutive_connection_errors += 1
                    logger.warning(
                        f"HTTPX connection error on attempt {attempt + 1} (consecutive: {consecutive_connection_errors}): {e}"
                    )

                    if attempt < self.max_retries - 1:
                        # Circuit breaker for persistent connection issues
                        if (
                            consecutive_connection_errors
                            >= max_consecutive_connection_errors
                        ):
                            logger.warning(
                                f"Too many consecutive connection errors ({consecutive_connection_errors}), implementing circuit breaker"
                            )
                            base_wait = 300  # 5 minutes
                            consecutive_connection_errors = 0
                        else:
                            # Progressive backoff for connection issues
                            if attempt == 0:
                                base_wait = 10  # Start with 10 seconds
                            else:
                                base_wait = 2**attempt * 3  # 3x longer than normal

                        max_wait = 600  # Cap at 10 minutes
                        wait_time = min(base_wait, max_wait)
                        jitter = random.uniform(0.8, 1.2)
                        wait_time = int(wait_time * jitter)
                        logger.warning(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)

                        # Reset client if enabled and we've had connection issues
                        if (
                            self.restart_client_on_connection_error
                            and consecutive_connection_errors > 0
                        ):
                            try:
                                logger.info("Attempting to reset client connection...")
                                # Create a new client instance with the same API key
                                if self.api_key:
                                    current_client = genai.Client(api_key=self.api_key)
                                    logger.info("Client connection reset successfully")
                                else:
                                    logger.warning(
                                        "Could not reset client: GEMINI_API_KEY not found in environment"
                                    )
                            except Exception as reset_error:
                                logger.warning(f"Failed to reset client: {reset_error}")
                    else:
                        logger.error(
                            f"HTTPX connection error after {self.max_retries} attempts: {e}"
                        )
                        raise e
                    continue

                # Generic exception handling for other errors
                # Check if this is a connection-related error by examining the error message
                error_msg = str(e).lower()
                connection_keywords = [
                    "disconnected",
                    "connection",
                    "network",
                    "timeout",
                    "reset",
                    "server disconnected",
                    "connection aborted",
                    "broken pipe",
                    "connection refused",
                    "connection reset",
                    "socket",
                    "tcp",
                    "remote end closed",
                    "connection lost",
                    "connection dropped",
                    "without sending a response",
                    "protocol error",
                    "connection error",
                ]

                # Also check if it's an httpx connection error
                is_httpx_connection_error = HTTPX_AVAILABLE and (
                    isinstance(
                        e,
                        (
                            httpx.RemoteProtocolError,
                            httpx.ConnectError,
                            httpx.TimeoutException,
                            httpx.NetworkError,
                        ),
                    )
                )

                is_connection_error = (
                    any(keyword in error_msg for keyword in connection_keywords)
                    or is_httpx_connection_error
                )

                # Log the error message for debugging
                logger.debug(
                    f"Generic exception caught: '{error_msg}' - Connection error: {is_connection_error}"
                )

                if is_connection_error:
                    # Treat as connection error with longer wait times and client reset
                    consecutive_connection_errors += 1
                    logger.warning(
                        f"Connection error detected on attempt {attempt + 1} (consecutive: {consecutive_connection_errors}): {e}"
                    )

                    if attempt < self.max_retries - 1:
                        # Circuit breaker for persistent connection issues
                        if (
                            consecutive_connection_errors
                            >= max_consecutive_connection_errors
                        ):
                            logger.warning(
                                f"Too many consecutive connection errors ({consecutive_connection_errors}), implementing circuit breaker"
                            )
                            base_wait = 300  # 5 minutes
                            consecutive_connection_errors = 0
                        else:
                            # Progressive backoff for connection issues
                            if attempt == 0:
                                base_wait = 10  # Start with 10 seconds
                            else:
                                base_wait = 2**attempt * 3  # 3x longer than normal

                        max_wait = 600  # Cap at 10 minutes
                        wait_time = min(base_wait, max_wait)
                        jitter = random.uniform(0.8, 1.2)
                        wait_time = int(wait_time * jitter)
                        logger.warning(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)

                        # Reset client if enabled (always reset on connection errors)
                        if self.restart_client_on_connection_error:
                            try:
                                logger.info("Attempting to reset client connection...")
                                # Create a new client instance with the same API key
                                if self.api_key:
                                    current_client = genai.Client(api_key=self.api_key)
                                    logger.info("Client connection reset successfully")
                                else:
                                    logger.warning(
                                        "Could not reset client: GEMINI_API_KEY not found in environment"
                                    )
                            except Exception as reset_error:
                                logger.warning(f"Failed to reset client: {reset_error}")
                    else:
                        logger.error(
                            f"Connection error after {self.max_retries} attempts: {e}"
                        )
                        raise e
                else:
                    # Handle other unexpected errors with standard logic
                    logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        base_wait = 2**attempt
                        max_wait = 60
                        wait_time = min(base_wait, max_wait)
                        jitter = random.uniform(0.8, 1.2)
                        wait_time = int(wait_time * jitter)
                        logger.error(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"Unexpected error after {self.max_retries} attempts: {e}"
                        )
                        raise e
        return None


def embed_with_retries(
    client: genai.Client,  # noqa: ARG001  # Kept for backwards compatibility
    texts: str,
    output_dimensionality: int,
    task_type: str = "RETRIEVAL_QUERY",
    max_retries: int = 15,
    restart_client_on_connection_error: bool = True,
) -> list[float] | None:
    """
    DEPRECATED: Use GeminiEmbedder class instead.

    Generate embeddings for a batch of texts using Google's Gemini embedding model with retry logic.
    This function is kept for backwards compatibility but wraps the new GeminiEmbedder class.

    Args:
        client: Google GenAI client instance (not used, kept for compatibility)
        texts: Text string or list of text strings to embed
        output_dimensionality: Output dimension size (128-3072, recommended: 768, 1536, 3072)
        task_type: The task type for embedding optimization. Defaults to "RETRIEVAL_QUERY"
        max_retries: Maximum number of retry attempts on failure. Defaults to 15
        restart_client_on_connection_error: Whether to recreate client on connection errors. Defaults to True

    Returns:
        Optional[List[float]]: Embedding vector (or None if invalid input)

    Raises:
        PermissionDenied: If authentication/permission errors occur
        Unauthenticated: If authentication fails
        ServiceUnavailable: If service is unavailable after all retries
        ResourceExhausted: If rate limits are exceeded after all retries
        GoogleAPIError: If other Google API errors occur after all retries
        Exception: If unexpected errors occur after all retries
    """
    logger.warning(
        "embed_with_retries function is deprecated. Use GeminiEmbedder class instead."
    )

    # Create embedder instance using environment API key (ignoring passed client for backwards compat)
    embedder = GeminiEmbedder(
        task_type=task_type,
        output_dimensionality=output_dimensionality,
        max_retries=max_retries,
        restart_client_on_connection_error=restart_client_on_connection_error,
    )

    # Call batch_embed and return result
    return embedder.embed(texts)


class OpenAIEmbedder(Embedder):
    """OpenAI embedding implementation with robust retry logic.

    This class provides embedding generation using OpenAI's embedding API with
    sophisticated retry logic including circuit breaker pattern, connection
    error handling, and exponential backoff. Compatible with text-embedding-3-small,
    text-embedding-3-large, and text-embedding-ada-002 models.

    Args:
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
        model: Model name (default: "text-embedding-3-large")
            Supported models:
            - "text-embedding-3-small": 1536 dimensions, cost-effective
            - "text-embedding-3-large": 3072 dimensions, highest quality
            - "text-embedding-ada-002": 1536 dimensions, legacy model
        dimensions: Optional dimension reduction for v3 models only.
            - text-embedding-3-small: can reduce to 512-1536
            - text-embedding-3-large: can reduce to 256-3072
            - text-embedding-ada-002: does not support dimension reduction
            If None, uses model's default dimensionality
        max_retries: Maximum number of retry attempts on failure
        restart_client_on_error: Whether to recreate client on connection errors

    Example:
        >>> embedder = OpenAIEmbedder(
        ...     model="text-embedding-3-large",
        ...     dimensions=1024,  # Optional dimension reduction
        ...     max_retries=15
        ... )
        >>> embedding = embedder.embed("Hello world")
        >>> embeddings = embedder.batch_embed(["Text 1", "Text 2"])
    """

    # Supported models and their default dimensions
    MODEL_DIMENSIONS = {
        "text-embedding-3-small": 1536,
        "text-embedding-3-large": 3072,
        "text-embedding-ada-002": 1536,
    }

    # Models that support dimension reduction
    DIMENSION_REDUCTION_MODELS = {"text-embedding-3-small", "text-embedding-3-large"}

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "text-embedding-3-large",
        dimensions: int | None = None,
        max_retries: int = 15,
        restart_client_on_error: bool = True,
    ):
        """Initialize the OpenAIEmbedder with configuration and validation."""
        # Validate and set API key
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "API key must be provided or set in OPENAI_API_KEY environment variable"
            )

        # Validate model
        if model not in self.MODEL_DIMENSIONS:
            supported = ", ".join(self.MODEL_DIMENSIONS.keys())
            raise ValueError(
                f"Unsupported model '{model}'. Supported models: {supported}"
            )
        self.model = model

        # Validate dimensions parameter
        if dimensions is not None:
            if model not in self.DIMENSION_REDUCTION_MODELS:
                raise ValueError(
                    f"Model '{model}' does not support dimension reduction. "
                    f"Only {', '.join(self.DIMENSION_REDUCTION_MODELS)} support this feature."
                )

            # Warn if dimensions are outside recommended ranges
            if model == "text-embedding-3-small" and not (512 <= dimensions <= 1536):
                logger.warning(
                    f"Dimensions {dimensions} for text-embedding-3-small is outside "
                    f"recommended range [512, 1536]. This may impact quality."
                )
            elif model == "text-embedding-3-large" and not (256 <= dimensions <= 3072):
                logger.warning(
                    f"Dimensions {dimensions} for text-embedding-3-large is outside "
                    f"recommended range [256, 3072]. This may impact quality."
                )

        self.dimensions = dimensions
        self.max_retries = max_retries
        self.restart_client_on_error = restart_client_on_error

        # Initialize OpenAI client
        self.client = OpenAI(api_key=self.api_key)

        dim_info = (
            f"dimensions={dimensions}"
            if dimensions
            else f"default={self.MODEL_DIMENSIONS[model]}"
        )
        logger.info(f"OpenAIEmbedder initialized with model={model}, {dim_info}")

    @property
    def embedding_dimension(self) -> int:
        """Return embedding dimension.

        Returns the configured dimensions if set, otherwise returns the
        model's default dimensionality.
        """
        if self.dimensions is not None:
            return self.dimensions
        return self.MODEL_DIMENSIONS[self.model]

    def get_config(self) -> dict[str, Any]:
        """Return embedder configuration.

        Returns:
            Dict[str, Any]: Configuration dictionary containing embedder parameters
        """
        return {
            "model": self.model,
            "dimensions": self.dimensions,
            "max_retries": self.max_retries,
            "restart_client_on_error": self.restart_client_on_error,
        }

    def __repr__(self) -> str:
        """Return string representation of embedder."""
        dim_str = f", dimensions={self.dimensions}" if self.dimensions else ""
        return (
            f"OpenAIEmbedder(model='{self.model}'{dim_str}, "
            f"max_retries={self.max_retries})"
        )

    def embed(self, text: str) -> list[float] | None:
        """Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            List[float]: Embedding vector, or None if text is empty

        Raises:
            ValueError: If text is empty
            Various OpenAI API exceptions if all retries fail
        """
        if not text or text.strip() == "":
            raise ValueError("Cannot embed empty text")

        embeddings = self.batch_embed([text])
        return embeddings[0] if embeddings else None

    def batch_embed(self, texts: str | list[str]) -> list[list[float]] | None:
        """Generate embeddings for multiple texts with retry logic.

        This method implements sophisticated retry logic including:
        - Exponential backoff with jitter
        - Circuit breaker for persistent connection issues
        - Automatic client reset on connection errors
        - Specific handling for different error types

        Args:
            texts: Text string or list of text strings to embed

        Returns:
            Optional[List[List[float]]]: List of embedding vectors, or None if invalid input

        Raises:
            APIStatusError: If authentication/permission errors occur (401, 403)
            APIConnectionError: If connection fails after all retries
            RateLimitError: If rate limits are exceeded after all retries
            APIError: If other API errors occur after all retries
            Exception: If unexpected errors occur after all retries
        """
        # Validate input before making API call
        if not texts or (isinstance(texts, str) and texts.strip() == ""):
            logger.warning("Empty text provided for embedding, skipping API call")
            return None

        # Normalize input to list
        if isinstance(texts, str):
            texts = [texts]

        # Track consecutive connection errors for circuit breaker pattern
        consecutive_connection_errors = 0
        max_consecutive_connection_errors = 5

        # Store the current client reference for potential reset
        current_client = self.client

        for attempt in range(self.max_retries):
            try:
                # Prepare API call parameters
                params: dict[str, Any] = {"input": texts, "model": self.model}
                if self.dimensions is not None:
                    params["dimensions"] = self.dimensions

                # Make API call
                response = current_client.embeddings.create(**params)

                # Reset connection error counter on success
                consecutive_connection_errors = 0

                # Extract embeddings from response
                embeddings = [item.embedding for item in response.data]
                return embeddings

            except APIStatusError as e:
                # Handle HTTP status errors based on status code
                status_code = e.status_code

                # Authentication/permission errors - don't retry
                if status_code in (401, 403):
                    logger.error(f"Authentication error (status {status_code}): {e}")
                    raise e

                # Invalid input - don't retry
                if status_code == 400:
                    logger.error(f"Invalid input provided for embedding: {e}")
                    return None

                # Service unavailable (503) - retry with special logic
                if status_code == 503:
                    logger.warning(f"Service unavailable on attempt {attempt + 1}: {e}")
                    if attempt < self.max_retries - 1:
                        # Longer wait for 503 errors: 3x base delay with jitter
                        base_wait = 2**attempt * 3
                        max_wait = 300  # Cap at 5 minutes
                        wait_time = min(base_wait, max_wait)
                        jitter = random.uniform(0.9, 1.1)
                        wait_time = int(wait_time * jitter)
                        logger.warning(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"Service unavailable after {self.max_retries} attempts"
                        )
                        raise e

                # Server errors (500, 502) - retry with client reset
                elif status_code in (500, 502):
                    consecutive_connection_errors += 1
                    logger.warning(
                        f"Server error {status_code} on attempt {attempt + 1} "
                        f"(consecutive: {consecutive_connection_errors}): {e}"
                    )
                    if attempt < self.max_retries - 1:
                        # Circuit breaker for persistent issues
                        if (
                            consecutive_connection_errors
                            >= max_consecutive_connection_errors
                        ):
                            logger.warning(
                                f"Too many consecutive connection errors ({consecutive_connection_errors}), "
                                f"implementing circuit breaker"
                            )
                            base_wait = 300  # 5 minutes
                            consecutive_connection_errors = 0
                        else:
                            # Progressive backoff
                            if attempt == 0:
                                base_wait = 10
                            else:
                                base_wait = 2**attempt * 3

                        max_wait = 600  # Cap at 10 minutes
                        wait_time = min(base_wait, max_wait)
                        jitter = random.uniform(0.8, 1.2)
                        wait_time = int(wait_time * jitter)
                        logger.warning(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)

                        # Reset client if enabled
                        if (
                            self.restart_client_on_error
                            and consecutive_connection_errors > 0
                        ):
                            try:
                                logger.info("Attempting to reset client connection...")
                                current_client = OpenAI(api_key=self.api_key)
                                logger.info("Client connection reset successfully")
                            except Exception as reset_error:
                                logger.warning(f"Failed to reset client: {reset_error}")
                    else:
                        logger.error(
                            f"Server error after {self.max_retries} attempts: {e}"
                        )
                        raise e

                # Other status errors - standard retry
                else:
                    logger.warning(
                        f"API status error {status_code} on attempt {attempt + 1}: {e}"
                    )
                    if attempt < self.max_retries - 1:
                        base_wait = 2**attempt
                        max_wait = 60
                        wait_time = min(base_wait, max_wait)
                        jitter = random.uniform(0.8, 1.2)
                        wait_time = int(wait_time * jitter)
                        logger.warning(f"Retrying in {wait_time} seconds...")
                        time.sleep(wait_time)
                    else:
                        logger.error(
                            f"API status error after {self.max_retries} attempts: {e}"
                        )
                        raise e

            except RateLimitError as e:
                # Handle rate limit errors with standard retry logic
                logger.warning(f"Rate limit error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    # Standard exponential backoff with jitter for rate limits
                    base_wait = 2**attempt
                    max_wait = 60  # Cap at 1 minute for rate limits
                    wait_time = min(base_wait, max_wait)
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = int(wait_time * jitter)
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Rate limit exceeded after {self.max_retries} attempts: {e}"
                    )
                    raise e

            except (APIConnectionError, OpenAITimeout) as e:
                # Handle connection and timeout errors with client reset
                consecutive_connection_errors += 1
                error_type = "Timeout" if isinstance(e, OpenAITimeout) else "Connection"
                logger.warning(
                    f"{error_type} error on attempt {attempt + 1} "
                    f"(consecutive: {consecutive_connection_errors}): {e}"
                )

                if attempt < self.max_retries - 1:
                    # Circuit breaker for persistent connection issues
                    if (
                        consecutive_connection_errors
                        >= max_consecutive_connection_errors
                    ):
                        logger.warning(
                            f"Too many consecutive connection errors ({consecutive_connection_errors}), "
                            f"implementing circuit breaker"
                        )
                        base_wait = 300  # 5 minutes
                        consecutive_connection_errors = 0
                    else:
                        # Progressive backoff for connection issues
                        if attempt == 0:
                            base_wait = 10  # Start with 10 seconds
                        else:
                            base_wait = 2**attempt * 3  # 3x longer than normal

                    max_wait = 600  # Cap at 10 minutes
                    wait_time = min(base_wait, max_wait)
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = int(wait_time * jitter)
                    logger.warning(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

                    # Reset client if enabled
                    if (
                        self.restart_client_on_error
                        and consecutive_connection_errors > 0
                    ):
                        try:
                            logger.info("Attempting to reset client connection...")
                            current_client = OpenAI(api_key=self.api_key)
                            logger.info("Client connection reset successfully")
                        except Exception as reset_error:
                            logger.warning(f"Failed to reset client: {reset_error}")
                else:
                    logger.error(
                        f"{error_type} error after {self.max_retries} attempts: {e}"
                    )
                    raise e

            except APIError as e:
                # Handle other OpenAI API errors
                logger.error(f"OpenAI API error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    # Standard exponential backoff with jitter
                    base_wait = 2**attempt
                    max_wait = 60
                    wait_time = min(base_wait, max_wait)
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = int(wait_time * jitter)
                    logger.error(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"OpenAI API error after {self.max_retries} attempts: {e}"
                    )
                    raise e

            except Exception as e:
                # Handle unexpected errors
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}")
                if attempt < self.max_retries - 1:
                    base_wait = 2**attempt
                    max_wait = 60
                    wait_time = min(base_wait, max_wait)
                    jitter = random.uniform(0.8, 1.2)
                    wait_time = int(wait_time * jitter)
                    logger.error(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Unexpected error after {self.max_retries} attempts: {e}"
                    )
                    raise e

        return None
