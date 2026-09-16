"""Semantic context retriever querying PostgreSQL + pgvector with epistemic thresholding."""

import logging
import os
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.app.core.config import settings
from backend.app.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


_local_chunks_cache: Optional[List[Dict[str, Any]]] = None


def _retrieve_local_fallback(
    query_vector: List[float],
    min_similarity: float,
    limit: int,
    embedder: EmbeddingService,
) -> List[Dict[str, Any]]:
    """In-memory vector retrieval fallback using local transcript files and nomic-embed-text."""
    global _local_chunks_cache
    import json
    from pathlib import Path
    from backend.app.rag.ingest import parse_guest_name
    from backend.app.rag.retrieval import compute_cosine_similarity
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    cache_file = Path("data/transcripts_cache.json")

    if _local_chunks_cache is None:
        if cache_file.exists():
            try:
                _local_chunks_cache = json.loads(cache_file.read_text(encoding="utf-8"))
                logger.info("Loaded %d cached transcript chunks from %s", len(_local_chunks_cache), cache_file)
            except Exception as e:
                logger.warning("Failed loading transcripts cache: %s", e)
                _local_chunks_cache = None

        if _local_chunks_cache is None:
            logger.info("Initializing local in-memory transcript vector index from data/transcripts/...")
            splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
                encoding_name="cl100k_base",
                chunk_size=1000,
                chunk_overlap=150,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            loaded_chunks: List[Dict[str, Any]] = []
            transcripts_dir = Path("data/transcripts")
            if transcripts_dir.exists():
                for md_file in sorted(transcripts_dir.glob("*.md")):
                    try:
                        text = md_file.read_text(encoding="utf-8")
                        guest = parse_guest_name(text, md_file.name)
                        chunks = splitter.split_text(text)
                        for idx, chunk_text in enumerate(chunks):
                            try:
                                vec = embedder.embed_text(chunk_text)
                                loaded_chunks.append({
                                    "guest_name": guest,
                                    "source_file": md_file.name,
                                    "chunk_index": idx,
                                    "content": chunk_text,
                                    "embedding": vec,
                                })
                            except Exception as e:
                                logger.debug("Failed to embed %s chunk %d: %s", md_file.name, idx, e)
                    except Exception as read_err:
                        logger.warning("Failed reading transcript %s: %s", md_file, read_err)

            _local_chunks_cache = loaded_chunks
            try:
                cache_file.write_text(json.dumps(_local_chunks_cache, indent=2), encoding="utf-8")
                logger.info("Persisted %d chunks to %s", len(_local_chunks_cache), cache_file)
            except Exception as write_err:
                logger.warning("Failed saving cache: %s", write_err)

    # Score and filter chunks
    results: List[Dict[str, Any]] = []
    for chunk in (_local_chunks_cache or []):
        try:
            sim = compute_cosine_similarity(query_vector, chunk["embedding"])
            if sim >= min_similarity:
                results.append({
                    "guest_name": chunk["guest_name"],
                    "source_file": chunk["source_file"],
                    "chunk_index": chunk["chunk_index"],
                    "content": chunk["content"],
                    "similarity": round(float(sim), 4),
                })
        except Exception:
            continue

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:limit]


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
    Returns an empty list if no chunks meet the threshold.
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

    # 2. Check if SQLite fallback is active
    try:
        from backend.app.db.session import is_sqlite
        if is_sqlite or target_db_url.startswith("sqlite"):
            return _retrieve_local_fallback(
                query_vector=query_vector,
                min_similarity=min_similarity,
                limit=limit,
                embedder=embedder,
            )
    except Exception:
        pass

    # 3. Query PostgreSQL + pgvector with local fallback
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
        with psycopg2.connect(target_db_url, connect_timeout=1) as conn:
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
        logger.info("PostgreSQL unreachable (%s). Seamlessly engaging local vector retrieval.", err)
        return _retrieve_local_fallback(
            query_vector=query_vector,
            min_similarity=min_similarity,
            limit=limit,
            embedder=embedder,
        )
