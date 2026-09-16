"""Agent orchestrator coordinating semantic retrieval, dual-LLM dispatch, and artifact parsing."""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session as SQLAlchemySession

from backend.app.agents.prompts import (
    ARTIFACT_INSTRUCTION_PROMPT,
    BASE_SYSTEM_PROMPT,
    SHIP30_SYSTEM_PROMPT,
    STRICT_REFUSAL_MESSAGE,
)
from backend.app.agents.retriever import retrieve_context
from backend.app.core.llm_bridge import LLMBridge
from backend.app.db.models import Message, Session

logger = logging.getLogger(__name__)

ARTIFACT_REGEX = re.compile(
    r'<artifact\s+type=[\'"](?P<type>[^\'"]+)[\'"](?:\s+title=[\'"](?P<title>[^\'"]*)[\'"])?\s*>(?P<content>.*?)</artifact>',
    re.DOTALL | re.IGNORECASE,
)


def parse_artifact_from_text(raw_text: str) -> Tuple[str, Optional[Dict[str, Any]]]:
    """Extract <artifact> XML blocks and separate clean conversational text from artifact payload."""
    match = ARTIFACT_REGEX.search(raw_text)
    if not match:
        return raw_text.strip(), None

    artifact_type = match.group("type").strip().lower()
    artifact_title = (match.group("title") or "Generated Artifact").strip()
    artifact_content = match.group("content").strip()

    # Remove the artifact XML block from conversational reply text
    cleaned_reply = ARTIFACT_REGEX.sub("", raw_text).strip()

    artifact_data = {
        "type": artifact_type,
        "title": artifact_title,
        "content": artifact_content,
    }

    return cleaned_reply, artifact_data


class AgentOrchestrator:
    """Orchestrator for grounded conversation, Ship 30 generation, and artifact emission."""

    def __init__(self, llm_bridge: Optional[LLMBridge] = None):
        self.llm_bridge = llm_bridge or LLMBridge()

    def _format_context_block(self, sources: List[Dict[str, Any]], max_chunks: int = 2, max_chars_per_chunk: int = 1200) -> str:
        """Format retrieved chunks into a concise, high-signal context block for the LLM."""
        if not sources:
            return ""

        blocks = []
        # Keep top N most relevant chunks to preserve low latency on CPU
        for idx, s in enumerate(sources[:max_chunks], 1):
            guest = s.get("guest_name", "Unknown Guest")
            file_name = s.get("source_file", "Transcript")
            content = s.get("content", "").strip()
            if len(content) > max_chars_per_chunk:
                content = content[:max_chars_per_chunk] + "..."
            sim = s.get("similarity", 0.0)
            blocks.append(
                f"[Chunk {idx} | Source: {file_name} | Guest: {guest} | Relevance: {sim:.2f}]\n{content}"
            )

        return "\n\n---\n\n".join(blocks)

    def _format_history_block(self, messages: List[Message], max_turns: int = 6) -> str:
        """Format recent multi-turn conversation history for context preservation."""
        if not messages:
            return ""

        # Take last N messages
        recent = messages[-max_turns:]
        turns = []
        for m in recent:
            role_label = "User" if m.role == "user" else "Assistant"
            # Truncate overly long historical content to preserve token budget
            content_preview = m.content[:400].strip()
            if len(m.content) > 400:
                content_preview += "..."
            turns.append(f"{role_label}: {content_preview}")

        return "\n".join(turns)

    async def run(
        self,
        message: str,
        session: Optional[Session] = None,
        provider: str = "ollama",
        model: Optional[str] = None,
        mode: str = "chat",
        db: Optional[SQLAlchemySession] = None,
    ) -> Dict[str, Any]:
        """Execute grounded conversation or Ship 30 essay generation.
        
        Returns:
            {
                "reply": str,
                "sources": List[Dict[str, Any]],
                "artifact": Optional[Dict[str, Any]],
                "grounding_confidence": float,
                "epistemic_status": str,
            }
        """
        cleaned_query = message.strip()
        if not cleaned_query:
            return {
                "reply": STRICT_REFUSAL_MESSAGE,
                "sources": [],
                "artifact": None,
                "grounding_confidence": 0.0,
                "epistemic_status": "REFUSAL",
            }

        # 1. Retrieve grounded context from vector store
        sources = retrieve_context(query=cleaned_query)

        # Calculate grounding metrics
        if sources:
            avg_sim = round(float(sum(s.get("similarity", 0.0) for s in sources) / len(sources)), 4)
            confidence = min(max(avg_sim, 0.0), 1.0)
            epistemic_status = "GROUNDED" if confidence >= 0.75 else "PARTIAL"
        else:
            confidence = 0.0
            epistemic_status = "REFUSAL"

        # 2. Strict Epistemic Gating:
        # If no transcript chunks exceed 0.65 similarity, refuse immediately
        if not sources:
            # Check if there is existing session context from prior conversation turns
            has_prior_history = (
                session
                and session.messages
                and any(m.role == "assistant" for m in session.messages)
            )
            if not has_prior_history:
                logger.info("Refusal triggered: query '%s' yielded 0 chunks >= 0.65 and no prior assistant history", cleaned_query)
                return {
                    "reply": STRICT_REFUSAL_MESSAGE,
                    "sources": [],
                    "artifact": None,
                    "grounding_confidence": 0.0,
                    "epistemic_status": "REFUSAL",
                }

        # 3. Select and assemble system prompt
        context_str = self._format_context_block(sources)
        if mode == "ship30":
            system_prompt = SHIP30_SYSTEM_PROMPT
        else:
            system_prompt = f"{BASE_SYSTEM_PROMPT}\n\n{ARTIFACT_INSTRUCTION_PROMPT}"

        # 4. Construct user prompt with context and multi-turn history
        history_str = ""
        if session and session.messages:
            history_str = self._format_history_block(session.messages)

        prompt_parts = []
        if context_str:
            prompt_parts.append(f"### GROUNDED PODCAST TRANSCRIPT CONTEXT:\n{context_str}")
        if history_str:
            prompt_parts.append(f"### PREVIOUS CONVERSATION HISTORY:\n{history_str}")

        prompt_parts.append(f"### USER QUERY:\n{cleaned_query}")
        full_prompt = "\n\n".join(prompt_parts)

        # 5. Call LLM Bridge
        raw_response = await self.llm_bridge.generate(
            system_prompt=system_prompt,
            prompt=full_prompt,
            provider=provider,
            model=model,
        )

        # 6. Parse and isolate artifacts
        clean_reply, artifact = parse_artifact_from_text(raw_response)

        # If the model itself generated the refusal, ensure sources and artifacts are empty
        if STRICT_REFUSAL_MESSAGE in clean_reply:
            return {
                "reply": STRICT_REFUSAL_MESSAGE,
                "sources": [],
                "artifact": None,
                "grounding_confidence": 0.0,
                "epistemic_status": "REFUSAL",
            }

        return {
            "reply": clean_reply,
            "sources": sources,
            "artifact": artifact,
            "grounding_confidence": confidence,
            "epistemic_status": epistemic_status,
        }
