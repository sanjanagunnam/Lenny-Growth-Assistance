"""API endpoints for health diagnostics, session management, and chat completion."""

import json
import logging
from typing import Any, Dict, List, Optional
import uuid
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.api.schemas import (
    ArtifactPayload,
    ChatRequest,
    ChatResponse,
    HealthResponse,
    MessageResponse,
    SessionCreateRequest,
    SessionListResponse,
    SessionResponse,
    SourceItem,
)
from backend.app.core.config import settings
from backend.app.core.llm_bridge import (
    LLMBridge,
    LLMBridgeError,
    LLMConfigurationError,
    LLMGenerationError,
    LLMTimeoutError,
    LLMUnavailableError,
)
from backend.app.agents.orchestrator import AgentOrchestrator
from backend.app.db.models import Message, Session, utcnow
from backend.app.db.session import get_db, ping_db

logger = logging.getLogger(__name__)

router = APIRouter()
llm_bridge = LLMBridge()
orchestrator = AgentOrchestrator(llm_bridge=llm_bridge)

DEFAULT_SYSTEM_PROMPT = (
    "You are the Lenny Growth Assistant, an elite AI product and growth strategist inspired by "
    "Lenny's Podcast and top tech operators. You provide tactical, high-agency, and evidence-grounded "
    "advice on product-market fit, growth loops, metrics, and leadership. Be concise, direct, and actionable."
)


def _format_message_response(msg: Message) -> MessageResponse:
    """Format SQLAlchemy Message model into Pydantic MessageResponse with parsed sources."""
    parsed_sources = None
    if msg.sources:
        try:
            parsed_sources = json.loads(msg.sources)
        except Exception:
            parsed_sources = [{"raw": msg.sources}]

    return MessageResponse(
        id=msg.id,
        session_id=msg.session_id,
        role=msg.role,
        content=msg.content,
        provider=msg.provider,
        sources=parsed_sources,
        artifact_type=msg.artifact_type,
        artifact_content=msg.artifact_content,
        created_at=msg.created_at,
    )


def _format_session_response(session: Session) -> SessionResponse:
    """Format SQLAlchemy Session model with all associated messages."""
    return SessionResponse(
        id=session.id,
        title=session.title,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[_format_message_response(m) for m in session.messages],
    )


# ---------------------------------------------------------------------------
# Health & Diagnostics
# ---------------------------------------------------------------------------

@router.get("/healthz", response_model=HealthResponse, tags=["Diagnostics"])
async def health_check() -> HealthResponse:
    """Inspects database connectivity and Ollama daemon reachability."""
    # 1. Database Ping
    db_ok = ping_db()

    # 2. Ollama Reachability Check
    ollama_ok = False
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(2.0, connect=1.5)) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            ollama_ok = resp.status_code == 200
    except Exception as err:
        logger.debug("Healthz Ollama probe failed: %s", err)
        ollama_ok = False

    # 3. Available Providers
    providers: List[str] = []
    if ollama_ok:
        providers.append("ollama")
    if settings.ANTHROPIC_API_KEY:
        providers.append("anthropic")

    overall_status = "healthy" if (db_ok and (ollama_ok or bool(settings.ANTHROPIC_API_KEY))) else "degraded"

    return HealthResponse(
        status=overall_status,
        database=db_ok,
        ollama=ollama_ok,
        providers_available=providers,
    )


@router.get("/api/v1/models", tags=["Diagnostics"])
async def list_available_models() -> Dict[str, Any]:
    """Return available LLM models grouped by provider, highlighting glm-5.3-flash."""
    return {
        "providers": {
            "ollama": [
                {
                    "id": "glm-5.3-flash",
                    "name": "GLM-5.3-Flash (Ultra-Fast)",
                    "description": "Ultra-fast product & growth reasoning model",
                    "recommended": True,
                },
                {
                    "id": "llama3.2",
                    "name": "Llama 3.2 3B Instruct",
                    "description": "Meta 3B high-density instruction model",
                    "recommended": False,
                },
                {
                    "id": "phi3",
                    "name": "Phi-3 Mini 128k (Reasoning)",
                    "description": "Microsoft 128k context product reasoning",
                    "recommended": False,
                },
                {
                    "id": "qwen2.5",
                    "name": "Qwen 2.5 3B (Multilingual)",
                    "description": "Alibaba high-speed operator model",
                    "recommended": False,
                },
                {
                    "id": "mistral",
                    "name": "Mistral 7B (Operator)",
                    "description": "Dense European startup instruction model",
                    "recommended": False,
                },
            ],
            "anthropic": [
                {
                    "id": "claude-3-5-sonnet-latest",
                    "name": "Claude 3.5 Sonnet",
                    "description": "State-of-the-art cloud frontier intelligence",
                    "recommended": True,
                },
            ],
        },
        "default_provider": "ollama",
        "default_model": "glm-5.3-flash",
    }


# ---------------------------------------------------------------------------
# Session Management
# ---------------------------------------------------------------------------

@router.post(
    "/api/v1/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Sessions"],
)
def create_session(
    payload: Optional[SessionCreateRequest] = None,
    db: SQLAlchemySession = Depends(get_db),
) -> SessionResponse:
    """Explicitly create a new isolated conversation session."""
    title = (payload.title if payload and payload.title else "New Conversation").strip()
    session = Session(
        id=str(uuid.uuid4()),
        title=title or "New Conversation",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    logger.info("Created new session: %s", session.id)
    return _format_session_response(session)


@router.get("/api/v1/sessions", response_model=SessionListResponse, tags=["Sessions"])
def list_sessions(
    db: SQLAlchemySession = Depends(get_db),
) -> SessionListResponse:
    """List all sessions ordered by most recent activity."""
    sessions = db.query(Session).order_by(Session.updated_at.desc()).all()
    return SessionListResponse(
        sessions=[_format_session_response(s) for s in sessions]
    )


@router.get("/api/v1/sessions/{session_id}", response_model=SessionResponse, tags=["Sessions"])
def get_session(
    session_id: str,
    db: SQLAlchemySession = Depends(get_db),
) -> SessionResponse:
    """Retrieve complete message history for a specific conversation session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session '{session_id}' was not found.",
        )
    return _format_session_response(session)


# ---------------------------------------------------------------------------
# Chat Completion Route
# ---------------------------------------------------------------------------

@router.post("/api/v1/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_completion(
    request: ChatRequest,
    db: SQLAlchemySession = Depends(get_db),
) -> ChatResponse:
    """Handles chat interaction: persists user prompt, executes LLM generation, and saves assistant reply."""
    # 1. Resolve or create session
    session_id = request.session_id
    session = None

    if session_id:
        session = db.query(Session).filter(Session.id == session_id).first()

    if not session:
        # Create new session if missing or not supplied
        new_id = session_id or str(uuid.uuid4())
        # Summarize title from first prompt
        summary_title = request.message[:45].strip()
        if len(request.message) > 45:
            summary_title += "..."

        session = Session(
            id=new_id,
            title=summary_title or "New Conversation",
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    # 2. Persist user message
    user_msg = Message(
        session_id=session.id,
        role="user",
        content=request.message,
        provider=None,
        created_at=utcnow(),
    )
    db.add(user_msg)
    db.commit()

    # 3. Determine active provider & model
    provider = request.provider.lower()
    model = request.model
    if provider == "ollama":
        model_name = model or settings.OLLAMA_DEFAULT_MODEL
    elif provider == "anthropic":
        model_name = model or settings.ANTHROPIC_DEFAULT_MODEL
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported provider '{provider}'.",
        )

    provider_descriptor = f"{provider}:{model_name}"

    # 4. Generate response via AgentOrchestrator (handling RAG grounding, Ship 30, and artifacts)
    try:
        agent_result = await orchestrator.run(
            message=request.message,
            session=session,
            provider=provider,
            model=model,
            mode=request.mode,
            db=db,
        )
    except LLMTimeoutError as err:
        logger.error("LLM timeout encountered during chat: %s", err)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail={
                "error": "LLM_TIMEOUT",
                "message": str(err),
                "provider": provider,
                "suggestion": "Local Ollama model timed out (15s). Ensure Ollama is running, or toggle the model provider to 'Anthropic Claude' in the top bar.",
            },
        )
    except LLMUnavailableError as err:
        logger.error("LLM unavailable encountered during chat: %s", err)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": "LLM_UNAVAILABLE",
                "message": str(err),
                "provider": provider,
                "suggestion": "Ollama service is not reachable. Ensure 'ollama serve' is active or choose 'anthropic'.",
            },
        )
    except LLMConfigurationError as err:
        logger.error("LLM configuration error: %s", err)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "LLM_CONFIG_ERROR",
                "message": str(err),
                "provider": provider,
            },
        )
    except Exception as err:
        logger.error("Unhandled error in LLM generation: %s", err)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "LLM_GENERATION_FAILED",
                "message": f"Failed to generate response: {str(err)}",
                "provider": provider,
            },
        )

    reply_text = agent_result["reply"]
    raw_sources = agent_result.get("sources", [])
    raw_artifact = agent_result.get("artifact")

    # Serialize sources and artifacts for database storage
    sources_json = json.dumps(raw_sources) if raw_sources else None
    artifact_type = raw_artifact["type"] if raw_artifact else None
    artifact_content = raw_artifact["content"] if raw_artifact else None

    # 5. Persist assistant message
    assistant_msg = Message(
        session_id=session.id,
        role="assistant",
        content=reply_text,
        provider=provider_descriptor,
        sources=sources_json,
        artifact_type=artifact_type,
        artifact_content=artifact_content,
        created_at=utcnow(),
    )
    db.add(assistant_msg)

    # Update session activity timestamp
    session.updated_at = utcnow()
    db.commit()
    db.refresh(assistant_msg)

    # Format structured response schemas
    source_items = [
        SourceItem(
            source_file=s.get("source_file", "Transcript"),
            guest_name=s.get("guest_name", "Unknown"),
            chunk_index=s.get("chunk_index", 0),
            similarity=s.get("similarity", 0.0),
            content=s.get("content", ""),
        )
        for s in raw_sources
    ]

    artifact_payload = None
    if raw_artifact:
        artifact_payload = ArtifactPayload(
            type=raw_artifact["type"],
            title=raw_artifact.get("title"),
            content=raw_artifact["content"],
        )

    return ChatResponse(
        session_id=session.id,
        message_id=assistant_msg.id,
        reply=reply_text,
        sources=source_items,
        artifact=artifact_payload,
        provider_used=provider_descriptor,
        grounding_confidence=agent_result.get("grounding_confidence", 0.0),
        epistemic_status=agent_result.get("epistemic_status", "REFUSAL"),
    )
