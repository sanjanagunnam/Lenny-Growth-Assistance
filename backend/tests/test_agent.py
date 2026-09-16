"""Tests for Agent Layer: Strict RAG grounding, Ship 30 writing skill, and artifact emitter."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from backend.app.agents.orchestrator import (
    AgentOrchestrator,
    parse_artifact_from_text,
)
from backend.app.agents.prompts import (
    BASE_SYSTEM_PROMPT,
    SHIP30_SYSTEM_PROMPT,
    STRICT_REFUSAL_MESSAGE,
)
from backend.app.core.llm_bridge import LLMBridge
from backend.app.db.models import Message, Session


# ---------------------------------------------------------------------------
# Strict Grounding & Refusal Behavior Tests
# ---------------------------------------------------------------------------

def test_strict_refusal_when_no_chunks_retrieved():
    """Verify that queries with zero retrieved chunks return the exact refusal string."""
    async def _test():
        orchestrator = AgentOrchestrator()
        with patch("backend.app.agents.orchestrator.retrieve_context", return_value=[]):
            result = await orchestrator.run(
                message="How do I bake a chocolate cake?",
                provider="ollama",
                mode="chat",
            )
            assert result["reply"] == STRICT_REFUSAL_MESSAGE
            assert result["sources"] == []
            assert result["artifact"] is None
            assert result["grounding_confidence"] == 0.0
            assert result["epistemic_status"] == "REFUSAL"

    asyncio.run(_test())


def test_strict_refusal_on_off_topic_query():
    """Verify that general coding or irrelevant topics return strict refusal message."""
    async def _test():
        orchestrator = AgentOrchestrator()
        with patch("backend.app.agents.orchestrator.retrieve_context", return_value=[]):
            result = await orchestrator.run(
                message="Write a Python script to scrape Twitter using Selenium.",
                provider="ollama",
                mode="chat",
            )
            assert result["reply"] == STRICT_REFUSAL_MESSAGE
            assert result["sources"] == []
            assert result["artifact"] is None
            assert result["grounding_confidence"] == 0.0
            assert result["epistemic_status"] == "REFUSAL"

    asyncio.run(_test())


def test_grounded_response_with_sources():
    """Verify that relevant context chunks are passed to the model and returned in the sources payload."""
    async def _test():
        mock_sources = [
            {
                "guest_name": "Brian Chesky",
                "source_file": "brian-chesky-airbnb.md",
                "chunk_index": 1,
                "content": "When COVID hit, we cut performance marketing and relied on our host-guest growth loop.",
                "similarity": 0.88,
            }
        ]

        mock_llm_reply = (
            "According to Brian Chesky, Airbnb reduced reliance on paid performance marketing during 2020 "
            "and instead leaned into their organic host-guest growth loop."
        )

        with patch("backend.app.agents.orchestrator.retrieve_context", return_value=mock_sources), \
             patch.object(LLMBridge, "generate", new_callable=AsyncMock) as mock_generate:

            mock_generate.return_value = mock_llm_reply
            orchestrator = AgentOrchestrator()

            result = await orchestrator.run(
                message="How did Brian Chesky handle marketing during the pandemic?",
                provider="ollama",
                mode="chat",
            )

            assert result["reply"] == mock_llm_reply
            assert len(result["sources"]) == 1
            assert result["sources"][0]["guest_name"] == "Brian Chesky"
            assert result["sources"][0]["similarity"] == 0.88
            assert result["artifact"] is None
            assert result["grounding_confidence"] == 0.88
            assert result["epistemic_status"] == "GROUNDED"

            call_args = mock_generate.call_args
            prompt_passed = call_args.kwargs["prompt"]
            assert "GROUNDED PODCAST TRANSCRIPT CONTEXT" in prompt_passed
            assert "Brian Chesky" in prompt_passed

    asyncio.run(_test())


# ---------------------------------------------------------------------------
# Artifact Parsing & Separation Tests
# ---------------------------------------------------------------------------

def test_parse_markdown_artifact_separation():
    """Verify <artifact> XML block is isolated from conversational chat text."""
    raw_response = (
        "Here is the execution checklist based on Shreyas Doshi's framework:\n\n"
        '<artifact type="markdown" title="LNO Daily Audit Checklist">\n'
        "# LNO Task Audit\n"
        "- [ ] Identify today's 10x Leverage tasks\n"
        "- [ ] Batch 1x Neutral tasks in the afternoon\n"
        "- [ ] Eliminate or automate <1x Overhead tasks\n"
        "</artifact>\n\n"
        "Let me know if you want to customize these thresholds."
    )

    clean_reply, artifact = parse_artifact_from_text(raw_response)

    # Conversational text check: no artifact tags leaked
    assert "<artifact" not in clean_reply
    assert "</artifact>" not in clean_reply
    assert "Here is the execution checklist" in clean_reply
    assert "Let me know if you want to customize these thresholds." in clean_reply

    # Artifact structure check
    assert artifact is not None
    assert artifact["type"] == "markdown"
    assert artifact["title"] == "LNO Daily Audit Checklist"
    assert "# LNO Task Audit" in artifact["content"]
    assert "- [ ] Identify today's 10x Leverage tasks" in artifact["content"]


def test_parse_html_artifact_separation():
    """Verify HTML artifacts for calculators or UI widgets are parsed correctly."""
    raw_response = (
        "I have created an interactive calculator for your host-guest loop:\n"
        '<artifact type="html" title="Growth Loop Calculator">\n'
        '<div class="calculator">\n'
        '  <input type="number" id="guests" value="1000" />\n'
        "</div>\n"
        "</artifact>"
    )

    clean_reply, artifact = parse_artifact_from_text(raw_response)
    assert "<artifact" not in clean_reply
    assert artifact is not None
    assert artifact["type"] == "html"
    assert artifact["title"] == "Growth Loop Calculator"
    assert '<div class="calculator">' in artifact["content"]


def test_parse_text_without_artifact():
    """Verify normal text without artifacts returns clean reply and None artifact."""
    raw_response = "Brian Chesky advocates for founders staying in the details of the product."
    clean_reply, artifact = parse_artifact_from_text(raw_response)
    assert clean_reply == raw_response
    assert artifact is None


# ---------------------------------------------------------------------------
# Ship 30 for 30 Essay Skill Tests
# ---------------------------------------------------------------------------

def test_ship30_mode_prompt_and_structure():
    """Verify Ship 30 mode injects SHIP30_SYSTEM_PROMPT and constructs structured essay."""
    async def _test():
        mock_sources = [
            {
                "guest_name": "Shreyas Doshi",
                "source_file": "shreyas-doshi-product.md",
                "chunk_index": 0,
                "content": "LNO classifies work into Leverage (10x), Neutral (1x), and Overhead (<1x). Most PMs spend 60% of time giving A+ effort to Neutral tasks.",
                "similarity": 0.91,
            }
        ]

        mock_ship30_essay = (
            "Most high achievers are drowning in their own perfectionism.\n\n"
            "They think giving 100% effort to 100% of tasks is the secret to leadership. It isn't. It's the fastest path to career stagnation.\n\n"
            "### The LNO Framework: How High-Agency Operators Prioritize\n\n"
            "As Shreyas Doshi shared on Lenny's Podcast, top performers categorize every responsibility into three buckets:\n\n"
            "**1. Leverage Tasks (10x Return)**\n"
            "- High impact decisions like core architecture and hiring\n"
            "- Demand obsessive excellence\n\n"
            "**2. Neutral Tasks (1x Return)**\n"
            "- Status updates and sprint planning\n"
            "- Aim for good enough\n\n"
            "**3. Overhead Tasks (<1x Return)**\n"
            "- Admin tasks and ticketing\n"
            "- Automate or execute with C-grade effort\n\n"
            "Stop optimizing for title velocity. Optimize for learning velocity."
        )

        with patch("backend.app.agents.orchestrator.retrieve_context", return_value=mock_sources), \
             patch.object(LLMBridge, "generate", new_callable=AsyncMock) as mock_generate:

            mock_generate.return_value = mock_ship30_essay
            orchestrator = AgentOrchestrator()

            result = await orchestrator.run(
                message="Write a Ship 30 essay on Shreyas Doshi's LNO framework.",
                provider="ollama",
                mode="ship30",
            )

            assert "Most high achievers are drowning" in result["reply"]
            assert len(result["sources"]) == 1
            assert result["sources"][0]["guest_name"] == "Shreyas Doshi"

            call_args = mock_generate.call_args
            system_passed = call_args.kwargs["system_prompt"]
            assert "Ship 30 for 30" in system_passed
            assert "The Hook (1-2 lines)" in system_passed

    asyncio.run(_test())


# ---------------------------------------------------------------------------
# Multi-Turn Session History Preservation Tests
# ---------------------------------------------------------------------------

def test_session_history_threading():
    """Verify previous conversation messages in a session are passed to the orchestrator."""
    async def _test():
        session = Session(id="test-session-uuid", title="Growth Loops Discussion")
        msg1 = Message(session_id="test-session-uuid", role="user", content="Tell me about Airbnb's host acquisition.")
        msg2 = Message(session_id="test-session-uuid", role="assistant", content="Brian Chesky explained that guests become hosts.")
        session.messages = [msg1, msg2]

        mock_sources = [
            {
                "guest_name": "Brian Chesky",
                "source_file": "brian-chesky-airbnb.md",
                "chunk_index": 2,
                "content": "Guests return home and list their own homes, completing the organic loop.",
                "similarity": 0.85,
            }
        ]

        with patch("backend.app.agents.orchestrator.retrieve_context", return_value=mock_sources), \
             patch.object(LLMBridge, "generate", new_callable=AsyncMock) as mock_generate:

            mock_generate.return_value = "This loop lowered Airbnb's customer acquisition cost dramatically."
            orchestrator = AgentOrchestrator()

            result = await orchestrator.run(
                message="What impact did this have on CAC?",
                session=session,
                provider="ollama",
                mode="chat",
            )

            call_args = mock_generate.call_args
            prompt_passed = call_args.kwargs["prompt"]
            assert "PREVIOUS CONVERSATION HISTORY" in prompt_passed
            assert "Tell me about Airbnb's host acquisition" in prompt_passed
            assert "Brian Chesky explained that guests become hosts" in prompt_passed

    asyncio.run(_test())
