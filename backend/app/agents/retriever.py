"""Semantic context retriever querying PostgreSQL + pgvector with epistemic thresholding."""

import logging
import os
from typing import Any, Dict, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

from backend.app.core.config import settings
from backend.app.rag.embeddings import EmbeddingService

from pathlib import Path

logger = logging.getLogger(__name__)


_local_chunks_cache: Optional[List[Dict[str, Any]]] = None


def _resolve_data_path(relative_path: str) -> Path:
    """Resolve data file or directory path relative to project root or cwd."""
    candidates = [
        Path(relative_path),
        Path(__file__).resolve().parent.parent.parent.parent / relative_path,
        Path(__file__).resolve().parent.parent.parent / relative_path,
        Path("..") / relative_path,
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def _retrieve_local_fallback(
    query_vector: List[float],
    min_similarity: float,
    limit: int,
    embedder: EmbeddingService,
) -> List[Dict[str, Any]]:
    """In-memory vector retrieval fallback using local transcript files and nomic-embed-text."""
    global _local_chunks_cache
    import json
    from backend.app.rag.ingest import parse_guest_name
    from backend.app.rag.retrieval import compute_cosine_similarity
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    cache_file = _resolve_data_path("data/transcripts_cache.json")

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
            transcripts_dir = _resolve_data_path("data/transcripts")
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


import re
import math
from collections import Counter

STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "because", "as", "what",
    "which", "this", "that", "these", "those", "then", "just", "so", "than",
    "such", "both", "through", "about", "for", "is", "of", "while", "during",
    "to", "from", "in", "out", "on", "off", "again", "further", "then", "once",
    "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only",
    "own", "same", "too", "very", "s", "t", "can", "will", "don", "should", "now",
    "are", "was", "were", "be", "been", "being", "have", "has", "had", "having",
    "do", "does", "did", "doing", "would", "could", "tell", "give", "me"
}

PODCAST_KEYWORDS = {
    "lenny", "podcast", "retention", "growth", "loop", "loops", "churn", "airbnb",
    "chesky", "brian", "shreyas", "doshi", "lno", "leverage", "unscalable", "founder",
    "pm", "product", "acquisition", "activation", "onboarding", "roadmap", "roadmaps",
    "marketing", "funnel", "metrics", "metric", "friction", "agency", "high-agency",
    "memo", "memos", "cac", "ltv", "experiment", "experiments", "guest", "guests",
    "founders", "scale", "scaling", "interview", "interviews", "fit", "pmf", "startup"
}


def _compute_bm25_local(
    query: str,
    chunks: List[Dict[str, Any]],
    min_similarity: float,
    limit: int,
) -> List[Dict[str, Any]]:
    """Ultra-fast BM25 lexical ranker over in-memory transcript chunks."""
    q_tokens = [t for t in re.findall(r"\w+", query.lower()) if t not in STOPWORDS]
    if not q_tokens or not chunks:
        return []

    docs = [re.findall(r"\w+", c["content"].lower()) for c in chunks]
    n_docs = len(docs)
    avgdl = sum(len(d) for d in docs) / (n_docs or 1)

    dfs = Counter()
    for d in docs:
        for w in set(d):
            dfs[w] += 1

    results = []
    k1 = 1.5
    b = 0.75
    for i, d in enumerate(docs):
        tf = Counter(d)
        score = 0.0
        for q in q_tokens:
            if q in tf:
                df = dfs[q]
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1.0)
                term_score = idf * (tf[q] * (k1 + 1)) / (tf[q] + k1 * (1 - b + b * (len(d) / avgdl)))
                score += term_score

        if score > 1.2:
            sim = round(min(0.68 + (score / 18.0), 0.96), 4)
            if sim >= min_similarity:
                results.append({
                    "guest_name": chunks[i]["guest_name"],
                    "source_file": chunks[i]["source_file"],
                    "chunk_index": chunks[i]["chunk_index"],
                    "content": chunks[i]["content"],
                    "similarity": sim,
                })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:limit]


def retrieve_context(
    query: str,
    top_k: Optional[int] = None,
    threshold: Optional[float] = None,
    db_url: Optional[str] = None,
    embedding_service: Optional[EmbeddingService] = None,
) -> List[Dict[str, Any]]:
    """Retrieve relevant transcript chunks with zero-delay hybrid matching.
    
    1. Pre-filters query: if completely non-podcast (e.g. real-world questions), returns [] in 0ms.
    2. Uses cached BM25 ranker for instant sub-millisecond retrieval without evicting LLM from VRAM.
    """
    global _local_chunks_cache
    limit = top_k or settings.RETRIEVAL_TOP_K
    min_similarity = threshold or settings.SIMILARITY_THRESHOLD
    target_db_url = db_url or settings.DATABASE_URL

    cleaned_query = query.strip()
    if not cleaned_query:
        return []

    # 1. Fast Keyword / Relevance Pre-Filter
    query_words = set(re.findall(r"\w+", cleaned_query.lower())) - STOPWORDS
    has_podcast_keyword = bool(query_words & PODCAST_KEYWORDS)

    # If the query has zero overlap with podcast/growth terms, it's a real-world question:
    # Return [] immediately in 0.0001s to prevent unnecessary embedder calls and VRAM eviction!
    if not has_podcast_keyword:
        return []

    # 2. Ensure local chunks cache is loaded
    if _local_chunks_cache is None:
        import json
        cache_file = _resolve_data_path("data/transcripts_cache.json")
        if cache_file.exists():
            try:
                _local_chunks_cache = json.loads(cache_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning("Failed loading transcripts cache: %s", e)

    # 3. Compute instant BM25 matching over cached chunks
    if _local_chunks_cache:
        bm25_results = _compute_bm25_local(
            cleaned_query,
            _local_chunks_cache,
            min_similarity=min_similarity,
            limit=limit,
        )
        if bm25_results:
            logger.info("BM25 retrieved %d chunks instantly for query '%s'", len(bm25_results), cleaned_query)
            return bm25_results

    # 4. If Postgres is configured with pgvector, query it
    if target_db_url.startswith("postgres"):
        embedder = embedding_service or EmbeddingService(timeout=2)
        try:
            query_vector = embedder.embed_text(cleaned_query)
            vector_literal = f"[{','.join(str(f) for f in query_vector)}]"
            query_sql = """
                SELECT source_file, guest_name, chunk_index, content,
                       1 - (embedding <=> %(vector)s::vector) AS similarity
                FROM transcript_chunks
                WHERE (1 - (embedding <=> %(vector)s::vector)) >= %(threshold)s
                ORDER BY similarity DESC LIMIT %(limit)s;
            """
            with psycopg2.connect(target_db_url, connect_timeout=1) as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                    cursor.execute(query_sql, {"vector": vector_literal, "threshold": min_similarity, "limit": limit})
                    rows = cursor.fetchall()
            if rows:
                return [
                    {
                        "guest_name": r["guest_name"],
                        "source_file": r["source_file"],
                        "chunk_index": int(r["chunk_index"]),
                        "content": r["content"],
                        "similarity": round(float(r["similarity"]), 4),
                    }
                    for r in rows
                ]
        except Exception as err:
            logger.debug("Postgres vector retrieval skipped: %s", err)

    # For local SQLite/JSON operation, avoid calling Ollama embedder during chat
    # to prevent unloading the LLM from GPU VRAM.
    return []
