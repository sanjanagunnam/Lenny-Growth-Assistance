"""End-to-end integration test suite validating the complete Lenny Growth Assistant pipeline."""

from typing import Generator
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as SQLAlchemySession, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.agents.prompts import STRICT_REFUSAL_MESSAGE
from backend.app.core.llm_bridge import LLMBridge
from backend.app.db.models import Base
from backend.app.db.session import get_db
from backend.app.main import app

# ---------------------------------------------------------------------------
# Test Database Setup (In-Memory SQLite with StaticPool)
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
    """Prevent network delay to real PostgreSQL during end-to-end test runs."""
    with patch("backend.app.main.init_db"), patch("backend.app.main.ping_db", return_value=True):
        yield


@pytest.fixture(scope="function")
def db_session() -> Generator[SQLAlchemySession, None, None]:
    """Provide clean database schema for each integration test."""
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: SQLAlchemySession) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with overridden database session."""
    def override_get_db() -> Generator[SQLAlchemySession, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# End-to-End Integration Tests
# ---------------------------------------------------------------------------

def test_e2e_healthz_probe(client: TestClient):
    """Verify healthz endpoint returns 200, status metrics, and X-Request-ID telemetry."""
    with patch("backend.app.api.routes.ping_db", return_value=True), \
         patch("httpx.AsyncClient.get") as mock_get:

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        response = client.get("/healthz")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "ollama" in data
        assert "providers_available" in data
        # Observability header check
        assert "X-Request-ID" in response.headers


def test_e2e_session_lifecycle(client: TestClient):
    """Verify full session creation, retrieval, and message persistence flow."""
    # 1. Create session explicitly
    create_res = client.post("/api/v1/sessions", json={"title": "E2E Growth Test"})
    assert create_res.status_code == status.HTTP_201_CREATED
    session_id = create_res.json()["id"]

    # 2. Verify session in list
    list_res = client.get("/api/v1/sessions")
    assert list_res.status_code == status.HTTP_200_OK
    sessions = list_res.json()["sessions"]
    assert any(s["id"] == session_id for s in sessions)

    # 3. Retrieve empty session
    get_res = client.get(f"/api/v1/sessions/{session_id}")
    assert get_res.status_code == status.HTTP_200_OK
    assert get_res.json()["messages"] == []


def test_e2e_rag_question_answering_pipeline(client: TestClient):
    """Verify end-to-end grounded question answering citing transcript evidence."""
    mock_chunks = [
        {
            "guest_name": "Brian Chesky",
            "source_file": "brian-chesky-airbnb.md",
            "chunk_index": 0,
            "content": "In Founder Mode, leaders must stay in the details rather than abdicating to bureaucracy.",
            "similarity": 0.895,
        }
    ]

    mock_answer = (
        "According to Brian Chesky on Lenny's Podcast, Founder Mode requires founders to remain "
        "deeply immersed in the product details and customer experience instead of delegating to bureaucracy."
    )

    with patch("backend.app.agents.orchestrator.retrieve_context", return_value=mock_chunks), \
         patch.object(LLMBridge, "generate", new_callable=AsyncMock) as mock_generate:

        mock_generate.return_value = mock_answer

        payload = {
            "message": "What is Brian Chesky's philosophy on Founder Mode?",
            "provider": "ollama",
            "mode": "chat",
        }

        res = client.post("/api/v1/chat", json=payload)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        # Grounding and reply validations
        assert data["reply"] == mock_answer
        assert len(data["sources"]) == 1
        assert data["sources"][0]["guest_name"] == "Brian Chesky"
        assert data["sources"][0]["source_file"] == "brian-chesky-airbnb.md"
        assert data["sources"][0]["similarity"] == 0.895
        assert data["grounding_confidence"] == 0.895
        assert data["epistemic_status"] == "GROUNDED"

        # Check persistence in database
        session_id = data["session_id"]
        sess_res = client.get(f"/api/v1/sessions/{session_id}")
        assert sess_res.status_code == status.HTTP_200_OK
        msgs = sess_res.json()["messages"]
        assert len(msgs) == 2
        assert msgs[0]["role"] == "user"
        assert msgs[1]["role"] == "assistant"
        assert msgs[1]["content"] == mock_answer


def test_e2e_non_grounded_query_refusal(client: TestClient):
    """Verify strict epistemic refusal when queries cannot be answered from transcripts."""
    with patch("backend.app.agents.orchestrator.retrieve_context", return_value=[]):
        payload = {
            "message": "How do I deploy an automated CI/CD pipeline using GitHub Actions?",
            "provider": "ollama",
            "mode": "chat",
        }

        res = client.post("/api/v1/chat", json=payload)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        assert data["reply"] == STRICT_REFUSAL_MESSAGE
        assert data["sources"] == []
        assert data["artifact"] is None
        assert data["grounding_confidence"] == 0.0
        assert data["epistemic_status"] == "REFUSAL"


def test_e2e_ship30_essay_generation_format(client: TestClient):
    """Verify Ship 30 for 30 mode produces structured essays with hooks and bold pillars."""
    mock_chunks = [
        {
            "guest_name": "Shreyas Doshi",
            "source_file": "shreyas-doshi-product.md",
            "chunk_index": 1,
            "content": "High agency is the refusal to accept the default world. High agency operators find a way when there seems to be no way.",
            "similarity": 0.92,
        }
    ]

    mock_essay = (
        "Most people stop the moment they hear 'No'.\n\n"
        "They think constraints are brick walls. They aren't. They're creative tests.\n\n"
        "### The High-Agency Operating Model\n\n"
        "As Shreyas Doshi detailed on Lenny's Podcast, top performers embody the refusal to accept the default world.\n\n"
        "**1. Treat Blockers as Hypotheses**\n"
        "- Never accept a third-party rejection passively\n"
        "- Dive into root causes directly\n\n"
        "Stop waiting for permission. Build high agency."
    )

    with patch("backend.app.agents.orchestrator.retrieve_context", return_value=mock_chunks), \
         patch.object(LLMBridge, "generate", new_callable=AsyncMock) as mock_generate:

        mock_generate.return_value = mock_essay

        payload = {
            "message": "Write a Ship 30 essay on high agency leadership.",
            "provider": "ollama",
            "mode": "ship30",
        }

        res = client.post("/api/v1/chat", json=payload)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        assert "The High-Agency Operating Model" in data["reply"]
        assert len(data["sources"]) == 1
        assert data["sources"][0]["guest_name"] == "Shreyas Doshi"
        assert data["grounding_confidence"] == 0.92
        assert data["epistemic_status"] == "GROUNDED"


def test_e2e_artifact_emission_pipeline(client: TestClient):
    """Verify artifact emission parses XML blocks into structured payloads and saves artifact metadata."""
    mock_chunks = [
        {
            "guest_name": "Shreyas Doshi",
            "source_file": "shreyas-doshi-product.md",
            "chunk_index": 0,
            "content": "LNO framework: Leverage, Neutral, and Overhead tasks.",
            "similarity": 0.90,
        }
    ]

    raw_agent_reply = (
        "Here is the LNO prioritization matrix:\n\n"
        '<artifact type="markdown" title="LNO Prioritization Framework">\n'
        "# LNO Matrix\n"
        "- **Leverage (10x)**: Core strategy\n"
        "- **Neutral (1x)**: Operational updates\n"
        "- **Overhead (<1x)**: Admin paperwork\n"
        "</artifact>\n\n"
        "Let me know if you want to customize this."
    )

    with patch("backend.app.agents.orchestrator.retrieve_context", return_value=mock_chunks), \
         patch.object(LLMBridge, "generate", new_callable=AsyncMock) as mock_generate:

        mock_generate.return_value = raw_agent_reply

        payload = {
            "message": "Create an LNO framework artifact.",
            "provider": "ollama",
            "mode": "chat",
        }

        res = client.post("/api/v1/chat", json=payload)
        assert res.status_code == status.HTTP_200_OK
        data = res.json()

        # Assertions on parsed artifact
        assert data["artifact"] is not None
        assert data["artifact"]["type"] == "markdown"
        assert data["artifact"]["title"] == "LNO Prioritization Framework"
        assert "# LNO Matrix" in data["artifact"]["content"]

        # Conversational reply should NOT have raw <artifact> tags
        assert "<artifact" not in data["reply"]
        assert "</artifact>" not in data["reply"]
        assert "Here is the LNO prioritization matrix:" in data["reply"]

        # Assert persistence in Message table
        session_id = data["session_id"]
        sess_res = client.get(f"/api/v1/sessions/{session_id}")
        assert sess_res.status_code == status.HTTP_200_OK
        assistant_msg = sess_res.json()["messages"][-1]
        assert assistant_msg["artifact_type"] == "markdown"
        assert "# LNO Matrix" in assistant_msg["artifact_content"]
