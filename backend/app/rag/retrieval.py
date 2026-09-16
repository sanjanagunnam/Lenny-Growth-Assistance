"""Vector retrieval service with cosine similarity calculation and epistemic thresholding."""

import logging
import math
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.65"))


class SearchResult(BaseModel):
    """Pydantic model representing a retrieved transcript chunk with grounding metadata."""
    id: int
    source_file: str
    guest_name: str
    chunk_index: int
    content: str
    similarity: float = Field(..., ge=-1.0, le=1.0)


def compute_cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """Compute exact cosine similarity between two vectors."""
    if len(vec_a) != len(vec_b):
        raise ValueError(
            f"Vector dimension mismatch: len(a)={len(vec_a)}, len(b)={len(vec_b)}"
        )
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


def apply_epistemic_threshold(
    items: List[Dict[str, Any]],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> List[Dict[str, Any]]:
    """Filter retrieved items against an epistemic confidence threshold (default 0.65).
    
    If cosine similarity is below the threshold, items are rejected to prevent hallucinated
    or ungrounded answers. If no items meet the threshold, returns an empty list.
    """
    return [item for item in items if item.get("similarity", 0.0) >= threshold]


class RetrievalService:
    """Service to execute vector similarity queries against PostgreSQL + pgvector."""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        if not self.db_url:
            raise ValueError("DATABASE_URL is not set in environment or constructor.")

    def search(
        self,
        query_vector: List[float],
        limit: int = 5,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        guest_name: Optional[str] = None,
    ) -> List[SearchResult]:
        """Perform cosine similarity search with epistemic threshold filtering.
        
        Uses pgvector's cosine distance operator (<=>).
        Cosine similarity = 1 - (embedding <=> query_vector).
        """
        if len(query_vector) != 768:
            raise ValueError(f"Query vector dimension must be 768, got {len(query_vector)}")

        # Convert list of floats to pgvector string format: '[x1,x2,...]'
        vector_str = f"[{','.join(str(f) for f in query_vector)}]"

        query_sql = """
            SELECT 
                id,
                source_file,
                guest_name,
                chunk_index,
                content,
                1 - (embedding <=> %(vector)s::vector) AS similarity
            FROM transcript_chunks
            WHERE (1 - (embedding <=> %(vector)s::vector)) >= %(threshold)s
        """
        params: Dict[str, Any] = {
            "vector": vector_str,
            "threshold": threshold,
            "limit": limit,
        }

        if guest_name:
            query_sql += " AND guest_name = %(guest_name)s"
            params["guest_name"] = guest_name

        query_sql += " ORDER BY similarity DESC LIMIT %(limit)s;"

        with psycopg2.connect(self.db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query_sql, params)
                rows = cursor.fetchall()

        results: List[SearchResult] = []
        for row in rows:
            results.append(
                SearchResult(
                    id=row["id"],
                    source_file=row["source_file"],
                    guest_name=row["guest_name"],
                    chunk_index=row["chunk_index"],
                    content=row["content"],
                    similarity=round(float(row["similarity"]), 4),
                )
            )

        logger.info(
            "Retrieved %d chunks exceeding similarity threshold %.2f",
            len(results),
            threshold,
        )
        return results
