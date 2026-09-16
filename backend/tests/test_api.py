"""Integration and unit tests for FastAPI backend, session persistence, and LLM bridge."""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLAlchemySession, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.core.llm_bridge import (
    LLMBridge,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMConfigurationError,
)
from backend.app.db.models import Base
from backend.app.db.session import get_db
from backend.app.main import app

# ---------------------------------------------------------------------------
# In-Memory SQLite Test Database Setup
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(autouse=True)
def mock_db_lifecycle():
    """Mock lifespan database initialization and offline retrieval to prevent network delays."""
    sample_source = [{
        "guest_name": "Brian Chesky",
        "source_file": "brian-chesky-airbnb.md",
        "chunk_index": 1,
        "content": "Our real growth loop is the host-guest loop.",
        "similarity": 0.89,
    }]
    with patch("backend.app.main.init_db"), \
         patch("backend.app.main.ping_db", return_value=True), \
         patch("backend.app.agents.orchestrator.retrieve_context", return_value=sample_source):
        yield


@pytest.fixture(scope="function")
def db_session() -> Generator[SQLAlchemySession, None, None]:
    """Provide an isolated in-memory SQLite database session for each test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: SQLAlchemySession) -> Generator[TestClient, None, None]:
    """Provide a FastAPI TestClient with overridden get_db dependency."""
    def override_get_db() -> Generator[SQLAlchemySession, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Healthz Diagnostics Tests
# ---------------------------------------------------------------------------

def test_healthz_endpoint(client: TestClient):
    """Verify /healthz returns 200 with structured component diagnostics."""
    with patch("backend.app.api.routes.ping_db", return_value=True), \
         patch("httpx.AsyncClient.get") as mock_get:

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        response = client.get("/healthz")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["database"] is True
        assert data["ollama"] is True
        assert "ollama" in data["providers_available"]
        assert data["status"] == "healthy"


def test_healthz_degraded_when_ollama_offline(client: TestClient):
    """Verify /healthz returns degraded status when Ollama daemon is offline."""
    with patch("backend.app.api.routes.ping_db", return_value=True), \
         patch("httpx.AsyncClient.get", side_effect=Exception("Connection refused")):

        response = client.get("/healthz")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["database"] is True
        assert data["ollama"] is False
        assert "ollama" not in data["providers_available"]


# ---------------------------------------------------------------------------
# Session Management Tests
# ---------------------------------------------------------------------------

def test_session_creation_and_listing(client: TestClient):
    """Verify session creation, listing, and individual retrieval."""
    # 1. Create Session
    create_resp = client.post(
        "/api/v1/sessions",
        json={"title": "Airbnb Product Strategy Discussion"},
    )
    assert create_resp.status_code == status.HTTP_201_CREATED
    session_data = create_resp.json()
    session_id = session_data["id"]
    assert session_data["title"] == "Airbnb Product Strategy Discussion"
    assert session_data["messages"] == []

    # 2. List Sessions
    list_resp = client.get("/api/v1/sessions")
    assert list_resp.status_code == status.HTTP_200_OK
    all_sessions = list_resp.json()["sessions"]
    assert len(all_sessions) == 1
    assert all_sessions[0]["id"] == session_id

    # 3. Retrieve Individual Session
    get_resp = client.get(f"/api/v1/sessions/{session_id}")
    assert get_resp.status_code == status.HTTP_200_OK
    assert get_resp.json()["id"] == session_id


def test_session_not_found_returns_404(client: TestClient):
    """Verify requesting a non-existent session UUID returns 404."""
    response = client.get("/api/v1/sessions/non-existent-uuid-12345")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Chat Completion & Dynamic Provider Selection Tests
# ---------------------------------------------------------------------------

def test_chat_dynamic_provider_ollama(client: TestClient):
    """Verify chat completion with dynamic Ollama provider selection and persistence."""
    mock_llm_reply = "A product-driven growth loop uses customer output to create new acquisition."

    with patch.object(LLMBridge, "generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_llm_reply

        payload = {
            "message": "Explain Airbnb's host-guest growth loop.",
            "provider": "ollama",
            "model": "llama3.2",
            "mode": "chat",
        }

        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["reply"] == mock_llm_reply
        assert data["provider_used"] == "ollama:llama3.2"
        assert data["grounding_confidence"] > 0
        assert data["epistemic_status"] in ["GROUNDED", "PARTIAL"]
        session_id = data["session_id"]
        assert session_id is not None

        # Verify messages persisted in the database
        session_resp = client.get(f"/api/v1/sessions/{session_id}")
        assert session_resp.status_code == status.HTTP_200_OK
        history = session_resp.json()["messages"]
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Explain Airbnb's host-guest growth loop."
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == mock_llm_reply
        assert history[1]["provider"] == "ollama:llama3.2"


def test_chat_dynamic_provider_anthropic(client: TestClient):
    """Verify chat completion with dynamic Anthropic Claude provider selection."""
    mock_claude_reply = "The LNO framework categorizes tasks into Leverage (10x), Neutral (1x), and Overhead (<1x)."

    with patch.object(LLMBridge, "generate", new_callable=AsyncMock) as mock_generate:
        mock_generate.return_value = mock_claude_reply

        payload = {
            "message": "How does Shreyas Doshi define the LNO framework?",
            "provider": "anthropic",
            "model": "claude-3-5-sonnet-latest",
            "mode": "chat",
        }

        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data["reply"] == mock_claude_reply
        assert data["provider_used"] == "anthropic:claude-3-5-sonnet-latest"
        assert data["grounding_confidence"] > 0
        assert data["epistemic_status"] in ["GROUNDED", "PARTIAL"]


# ---------------------------------------------------------------------------
# Resilience & Error Handling Tests
# ---------------------------------------------------------------------------

def test_chat_ollama_timeout_resilience(client: TestClient):
    """Verify Ollama 15-second timeout returns clean 504 JSON response rather than 500 crash."""
    with patch.object(
        LLMBridge,
        "generate",
        side_effect=LLMTimeoutError(
            "Local Ollama model timed out (15s). Ensure Ollama is running, or toggle the model provider to 'Anthropic Claude' in the top bar."
        ),
    ):
        payload = {
            "message": "Analyze our retention funnel.",
            "provider": "ollama",
        }
        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        data = response.json()
        assert data["detail"]["error"] == "LLM_TIMEOUT"
        assert "Local Ollama model timed out (15s)" in data["detail"]["message"]
        assert "toggle the model provider to 'Anthropic Claude'" in data["detail"]["suggestion"]
        assert data["detail"]["provider"] == "ollama"


def test_chat_ollama_offline_resilience(client: TestClient):
    """Verify offline Ollama daemon returns clean 503 JSON response."""
    with patch.object(
        LLMBridge,
        "generate",
        side_effect=LLMUnavailableError("Ollama daemon is offline at http://localhost:11434."),
    ):
        payload = {
            "message": "Analyze our retention funnel.",
            "provider": "ollama",
        }
        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["detail"]["error"] == "LLM_UNAVAILABLE"
        assert "Ensure 'ollama serve' is active" in data["detail"]["suggestion"]


def test_chat_anthropic_missing_key_resilience(client: TestClient):
    """Verify unconfigured Anthropic credentials return 400 Bad Request."""
    with patch.object(
        LLMBridge,
        "generate",
        side_effect=LLMConfigurationError("ANTHROPIC_API_KEY is not configured on the server."),
    ):
        payload = {
            "message": "Synthesize growth experiment.",
            "provider": "anthropic",
        }
        response = client.post("/api/v1/chat", json=payload)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert data["detail"]["error"] == "LLM_CONFIG_ERROR"


# ---------------------------------------------------------------------------
# Input Validation & Review Gate Tests
# ---------------------------------------------------------------------------

def test_chat_empty_prompt_blocked(client: TestClient):
    """Verify empty or whitespace-only messages are blocked with 422 Unprocessable Content."""
    # Empty string
    resp1 = client.post("/api/v1/chat", json={"message": "", "provider": "ollama"})
    assert resp1.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

    # Whitespace only
    resp2 = client.post("/api/v1/chat", json={"message": "    \n   ", "provider": "ollama"})
    assert resp2.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_chat_invalid_provider_rejected(client: TestClient):
    """Verify unsupported provider values are rejected by schema validation."""
    response = client.post(
        "/api/v1/chat",
        json={"message": "Hello", "provider": "unknown_ai_provider"},
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
