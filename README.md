# AI Tutor API

A production-ready FastAPI-based AI tutoring system with a clean, maintainable architecture.

## Features

- RESTful API with FastAPI
- Type-safe request/response validation using Pydantic
- Environment-based configuration
- Health check and readiness endpoints
- Optional API key authentication
- CORS support
- Comprehensive error handling
- Async/await support
- Full test coverage setup

## Project Structure

```
hackathon-2026-ai-tutor/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── config.py            # Configuration management
│   ├── api/
│   │   ├── routes/
│   │   │   ├── health.py    # Health check endpoints
│   │   │   └── ai.py        # AI tutor endpoints
│   │   └── dependencies.py  # Dependency injection
│   ├── models/
│   │   └── schemas.py       # Pydantic request/response models
│   ├── services/
│   │   └── ai_service.py    # AI business logic
│   └── core/
│       └── exceptions.py    # Custom exception classes
├── tests/                   # Test suite
├── pyproject.toml          # Project dependencies and configuration
├── .env.example            # Example environment variables
└── README.md
```

## Quick Start

### Prerequisites

- Python 3.11 or higher
- pip or uv for package management

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd hackathon-2026-ai-tutor
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -e ".[dev]"
```

4. Create a `.env` file from the example:
```bash
cp .env.example .env
```

5. (Optional) Configure your environment variables in `.env`

### Running the Application

#### Development mode with auto-reload:
```bash
uvicorn app.main:app --reload
```

#### Production mode:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### Using Python directly:
```bash
python -m app.main
```

The API will be available at `http://localhost:8000`

### API Documentation

Once running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## API Endpoints

### Health & Status

- `GET /` - Root endpoint with API info
- `GET /api/v1/health` - Health check
- `GET /api/v1/ready` - Readiness check

### AI Tutor

- `POST /api/v1/tutor/ask` - Ask a question to the AI tutor
- `GET /api/v1/tutor/models` - List available models

### Example Request

```bash
curl -X POST "http://localhost:8000/api/v1/tutor/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is Python?",
    "context": "I am a beginner learning programming",
    "temperature": 0.7
  }'
```

With API key authentication:
```bash
curl -X POST "http://localhost:8000/api/v1/tutor/ask" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "question": "What is Python?"
  }'
```

## Configuration

Configuration is managed through environment variables. See [.env.example](.env.example) for all available options.

Key settings:
- `DEBUG`: Enable debug mode (default: false)
- `API_KEY`: Optional API key for authentication (leave empty to disable)
- `MODEL_NAME`: AI model identifier
- `ALLOWED_ORIGINS`: CORS allowed origins (comma-separated)

## Development

### Running Tests

```bash
pytest
```

With coverage:
```bash
pytest --cov=app --cov-report=html
```

### Type Checking

```bash
mypy app
```

### Code Formatting and Linting

```bash
ruff check .
ruff format .
```

### Running All Checks

```bash
pytest && mypy app && ruff check .
```

## Architecture Decisions

### Why FastAPI?
- Native async/await support for high performance
- Automatic API documentation with OpenAPI
- Built-in request/response validation with Pydantic
- Excellent type hint support for better IDE experience

### Why Pydantic Settings?
- Type-safe configuration management
- Automatic environment variable parsing
- Validation of configuration values
- `.env` file support out of the box

### Why Layered Architecture?
- **Routes**: Handle HTTP concerns (requests, responses, status codes)
- **Services**: Contain business logic, reusable across different interfaces
- **Models**: Define data structures and validation rules
- **Dependencies**: Centralize dependency injection for better testability

### Security Considerations
- Environment variables for sensitive data (no hardcoded secrets)
- Pydantic validation prevents injection attacks
- Optional API key authentication
- CORS configuration for cross-origin security
- Input sanitization in service layer

## Next Steps

To integrate a real AI model:

1. Choose your AI provider (OpenAI, Anthropic, local models, etc.)
2. Install required SDK: `pip install openai` or `pip install anthropic`
3. Update [app/services/ai_service.py](app/services/ai_service.py)
4. Replace `_generate_mock_response` with actual API calls
5. Add provider-specific configuration to [app/config.py](app/config.py)

Example OpenAI integration:
```python
import openai

def generate_response(self, request: TutorRequest) -> TutorResponse:
    response = openai.ChatCompletion.create(
        model=self.model_name,
        messages=[{"role": "user", "content": request.question}],
        temperature=request.temperature or 0.7,
    )
    return TutorResponse(
        answer=response.choices[0].message.content,
        model_used=self.model_name,
        tokens_used=response.usage.total_tokens,
    )
```

## License

[Your License Here]

## Contributing

[Your Contributing Guidelines Here]
