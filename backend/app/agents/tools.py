"""Tool schemas and definitions for Anthropic Agent tool calling."""

from typing import Any, Dict, List

# Anthropic Tool Definitions
ANTHROPIC_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "search_podcast_transcripts",
        "description": (
            "Search across Lenny's Podcast transcripts for factual quotes, frameworks, "
            "and tactical advice from guests (e.g. Brian Chesky, Shreyas Doshi)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, concept, or guest name to retrieve transcript chunks for.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "generate_ship30_essay",
        "description": (
            "Generate a structured, viral Ship 30 for 30 essay (~1,250 words) based on "
            "grounded transcript evidence with punchy hooks, bold anchors, and tactical steps."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The central product or growth topic for the essay.",
                },
                "context": {
                    "type": "string",
                    "description": "The factual quotes, named models, and guest evidence to construct the essay around.",
                },
            },
            "required": ["topic", "context"],
        },
    },
    {
        "name": "emit_artifact",
        "description": (
            "Package a reusable document, checklist, matrix, or HTML/code widget into a "
            "renderable artifact for the user interface."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "artifact_type": {
                    "type": "string",
                    "enum": ["markdown", "html"],
                    "description": "The artifact format: 'markdown' for documents/checklists, 'html' for UI widgets.",
                },
                "title": {
                    "type": "string",
                    "description": "A clear, descriptive title for the artifact.",
                },
                "content": {
                    "type": "string",
                    "description": "The full code or markdown body of the artifact.",
                },
            },
            "required": ["artifact_type", "title", "content"],
        },
    },
]
