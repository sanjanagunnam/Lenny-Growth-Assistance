"""Semantic context retriever querying PostgreSQL + pgvector with epistemic thresholding."""

import logging
import os
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.app.core.config import settings
from backend.app.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


def retrieve_context(
    query: str,
    top_k: Optional[int] = None,
    threshold: Optional[float] = None,
    db_url: Optional[str] = None,
    embedding_service: Optional[EmbeddingService] = None,
) -> List[Dict[str, Any]]:
    """Retrieve relevant transcript chunks exceeding the epistemic similarity threshold.
    
    Returns a list of structured source dictionaries:
    [
        {
            "guest_name": str,
            "source_file": str,
            "chunk_index": int,
            "content": str,
            "similarity": float
        },
        ...
    ]
    Returns an empty list if no chunks meet the threshold or if the database is offline.
    """
    limit = top_k or settings.RETRIEVAL_TOP_K
    min_similarity = threshold or settings.SIMILARITY_THRESHOLD
    target_db_url = db_url or settings.DATABASE_URL
    embedder = embedding_service or EmbeddingService()

    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    # 1. Generate query embedding (dimension: 768)
    try:
        query_vector = embedder.embed_text(cleaned_query)
    except Exception as err:
        logger.warning("Failed to generate query embedding: %s", err)
        return []

    # 2. Query PostgreSQL + pgvector
    vector_literal = f"[{','.join(str(f) for f in query_vector)}]"
    query_sql = """
        SELECT 
            source_file,
            guest_name,
            chunk_index,
            content,
            1 - (embedding <=> %(vector)s::vector) AS similarity
        FROM transcript_chunks
        WHERE (1 - (embedding <=> %(vector)s::vector)) >= %(threshold)s
        ORDER BY similarity DESC
        LIMIT %(limit)s;
    """

    try:
        with psycopg2.connect(target_db_url) as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(
                    query_sql,
                    {
                        "vector": vector_literal,
                        "threshold": min_similarity,
                        "limit": limit,
                    },
                )
                rows = cursor.fetchall()

        results: List[Dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "guest_name": row["guest_name"],
                    "source_file": row["source_file"],
                    "chunk_index": int(row["chunk_index"]),
                    "content": row["content"],
                    "similarity": round(float(row["similarity"]), 4),
                }
            )

        logger.info(
            "Retrieved %d chunks for query (threshold: %.2f)",
            len(results),
            min_similarity,
        )
        return results

    except Exception as err:
        logger.warning("Database retrieval error (PostgreSQL may be initializing or offline): %s", err)
        return []
