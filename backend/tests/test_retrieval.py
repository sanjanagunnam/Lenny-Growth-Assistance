"""Tests for vector embeddings, similarity calculation, and epistemic thresholding."""

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, patch
import pytest

from backend.app.rag.embeddings import EmbeddingService, TARGET_DIMENSION
from backend.app.rag.retrieval import (
    RetrievalService,
    compute_cosine_similarity,
    apply_epistemic_threshold,
    SearchResult,
)
from backend.app.rag.ingest import (
    TranscriptIngester,
    parse_guest_name,
)


# ---------------------------------------------------------------------------
# Embedding Tests (Ollama Mock & Fallback)
# ---------------------------------------------------------------------------

def test_embedding_generation_ollama_mock():
    """Verify successful 768-dimensional embedding generation via mocked Ollama endpoint."""
    fake_vector: List[float] = [0.01 * (i % 10) for i in range(TARGET_DIMENSION)]

    service = EmbeddingService(
        ollama_base_url="http://localhost:11434",
        ollama_model="nomic-embed-text",
        preferred_provider="ollama",
    )

    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": fake_vector}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        query_text = "How does Airbnb design for organic growth loops?"
        embedding = service.embed_text(query_text)

        # Assertions on HTTP request
        mock_post.assert_called_once_with(
            "http://localhost:11434/api/embeddings",
            json={"model": "nomic-embed-text", "prompt": query_text},
            timeout=30,
        )
        assert len(embedding) == TARGET_DIMENSION
        assert embedding == fake_vector


def test_embedding_generation_dimension_validation():
    """Verify that dimension mismatches from Ollama are rejected immediately."""
    service = EmbeddingService()
    with patch("requests.post") as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"embedding": [0.1] * 512}  # Incorrect dimension
        mock_post.return_value = mock_response

        with pytest.raises(ValueError, match="Expected Ollama embedding dimension 768"):
            service.embed_text("Sample prompt")


def test_embedding_generation_openai_fallback():
    """Verify fallback to OpenAI text-embedding-3-small when Ollama is unreachable."""
    service = EmbeddingService(
        ollama_base_url="http://localhost:11434",
        openai_api_key="sk-test-key-mock",
        preferred_provider="ollama",
    )

    fake_vector: List[float] = [0.05] * TARGET_DIMENSION

    # Ollama raises ConnectionError, triggering OpenAI fallback
    with patch("requests.post", side_effect=Exception("Connection refused")), \
         patch("openai.OpenAI") as mock_openai_cls:

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_item = MagicMock()
        mock_item.embedding = fake_vector
        mock_response.data = [mock_item]
        mock_client.embeddings.create.return_value = mock_response
        mock_openai_cls.return_value = mock_client

        embedding = service.embed_text("Fallback test prompt")
        assert len(embedding) == TARGET_DIMENSION
        assert embedding == fake_vector
        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="Fallback test prompt",
            dimensions=768,
        )


# ---------------------------------------------------------------------------
# Vector Similarity Calculation Tests
# ---------------------------------------------------------------------------

def test_vector_similarity_calculation():
    """Verify cosine similarity calculation logic across known mathematical vectors."""
    # Identical vectors -> similarity = 1.0
    vec_a = [1.0, 2.0, 3.0]
    assert pytest.approx(compute_cosine_similarity(vec_a, vec_a), 1e-5) == 1.0

    # Orthogonal vectors -> similarity = 0.0
    vec_b = [1.0, 0.0]
    vec_c = [0.0, 1.0]
    assert pytest.approx(compute_cosine_similarity(vec_b, vec_c), 1e-5) == 0.0

    # Opposing vectors -> similarity = -1.0
    vec_d = [1.0, 1.0]
    vec_e = [-1.0, -1.0]
    assert pytest.approx(compute_cosine_similarity(vec_d, vec_e), 1e-5) == -1.0

    # 45-degree angle vectors -> cos(45 deg) ~ 0.7071
    vec_f = [1.0, 0.0]
    vec_g = [1.0, 1.0]
    expected_cos_45 = 1.0 / (1.0 * (2.0 ** 0.5))
    assert pytest.approx(compute_cosine_similarity(vec_f, vec_g), 1e-4) == expected_cos_45


# ---------------------------------------------------------------------------
# Epistemic Thresholding Tests
# ---------------------------------------------------------------------------

def test_epistemic_thresholding_retention():
    """Verify that results above threshold 0.65 are retained and lower ones rejected."""
    candidates = [
        {"id": 1, "similarity": 0.88, "content": "High confidence match"},
        {"id": 2, "similarity": 0.66, "content": "Just above threshold"},
        {"id": 3, "similarity": 0.64, "content": "Just below threshold"},
        {"id": 4, "similarity": 0.32, "content": "Irrelevant noise"},
    ]

    filtered = apply_epistemic_threshold(candidates, threshold=0.65)
    assert len(filtered) == 2
    assert [x["id"] for x in filtered] == [1, 2]


def test_epistemic_thresholding_returns_empty_when_below_cutoff():
    """Verify that epistemic thresholding returns an empty list if no results exceed 0.65."""
    candidates = [
        {"id": 10, "similarity": 0.6499, "content": "Borderline noise"},
        {"id": 11, "similarity": 0.4500, "content": "Weak match"},
        {"id": 12, "similarity": 0.1200, "content": "Complete hallucination"},
    ]

    # Strict epistemic gate: returns empty list
    filtered = apply_epistemic_threshold(candidates, threshold=0.65)
    assert filtered == []


# ---------------------------------------------------------------------------
# Retrieval Service Database Query Mock Tests
# ---------------------------------------------------------------------------

def test_retrieval_service_search_query_execution():
    """Verify RetrievalService executes parameterized query and returns SearchResult models."""
    mock_rows = [
        {
            "id": 42,
            "source_file": "brian-chesky-airbnb.md",
            "guest_name": "Brian Chesky",
            "chunk_index": 2,
            "content": "Our real growth loop is the host-guest loop...",
            "similarity": 0.8523,
        }
    ]

    query_vec = [0.0] * 768

    with patch("psycopg2.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = mock_rows
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_connect.return_value.__enter__.return_value = mock_conn

        service = RetrievalService(db_url="postgresql://mock:mock@localhost:5432/mockdb")
        results = service.search(query_vec, limit=3, threshold=0.65, guest_name="Brian Chesky")

        assert len(results) == 1
        res = results[0]
        assert isinstance(res, SearchResult)
        assert res.id == 42
        assert res.guest_name == "Brian Chesky"
        assert res.similarity == 0.8523
        assert mock_cursor.execute.called

        # Verify query SQL contains parameterized threshold and cosine operator (<=>)
        call_args = mock_cursor.execute.call_args
        sql_query = call_args[0][0]
        params = call_args[0][1]
        assert "<=>" in sql_query
        assert params["threshold"] == 0.65
        assert params["guest_name"] == "Brian Chesky"


# ---------------------------------------------------------------------------
# Transcript Parsing & Chunking Metadata Preservation Tests
# ---------------------------------------------------------------------------

def test_guest_name_extraction():
    """Verify speaker and guest extraction from headers and filenames."""
    content_header = "# Guest: Brian Chesky\n# Episode: Design-Led Growth\n..."
    assert parse_guest_name(content_header, "some-file.md") == "Brian Chesky"

    content_plain = "Welcome to Lenny's Podcast..."
    assert parse_guest_name(content_plain, "shreyas-doshi-product.md") == "Shreyas Doshi"


def test_chunking_metadata_preservation(tmp_path: Path):
    """Verify recursive chunker produces metadata-rich chunks with proper token boundaries."""
    test_doc = tmp_path / "brian-chesky-airbnb.md"
    test_doc.write_text(
        "# Guest: Brian Chesky\n\n"
        "**Lenny Rachitsky:** Tell us about product design.\n\n"
        + ("**Brian Chesky:** Great design is when form and function are in complete harmony. " * 60),
        encoding="utf-8",
    )

    ingester = TranscriptIngester(
        db_url="postgresql://test:test@localhost:5432/test",
        chunk_size=100,
        chunk_overlap=20,
    )

    chunks = ingester.chunk_transcript(test_doc)
    assert len(chunks) > 1
    for filename, guest, idx, text, tokens in chunks:
        assert filename == "brian-chesky-airbnb.md"
        assert guest == "Brian Chesky"
        assert isinstance(idx, int)
        assert tokens > 0
        assert len(text) > 0
