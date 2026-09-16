"""Transcript ingestion pipeline with recursive chunking, Ollama embeddings, and pgvector storage."""

import argparse
import json
import logging
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
import tiktoken

from backend.app.rag.embeddings import EmbeddingService

load_dotenv()

# Structured logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("ingestion_pipeline")

CHUNK_SIZE_TOKENS = int(os.getenv("CHUNK_SIZE_TOKENS", "1000"))
CHUNK_OVERLAP_TOKENS = int(os.getenv("CHUNK_OVERLAP_TOKENS", "150"))
DEFAULT_BATCH_SIZE = int(os.getenv("BATCH_SIZE", "64"))


def parse_guest_name(content: str, filename: str) -> str:
    """Extract guest name from file metadata or filename.
    
    Checks frontmatter or markdown patterns like 'Guest: Brian Chesky'
    or parses clean titles from filenames like 'brian-chesky-airbnb.md'.
    """
    # 1. Regex check in content header (first 1000 characters)
    header_sample = content[:1000]
    guest_match = re.search(
        r"(?:Guest|Speaker|Interviewee):\s*([^\n\r]+)",
        header_sample,
        re.IGNORECASE,
    )
    if guest_match:
        return guest_match.group(1).strip().strip('"\'')

    # 2. Extract from filename: e.g. brian-chesky-airbnb.md -> Brian Chesky
    stem = Path(filename).stem
    # Remove common words like episode, interview, podcast
    cleaned_stem = re.sub(r"[-_](?:episode|interview|podcast|part|\d+)", "", stem, flags=re.IGNORECASE)
    parts = cleaned_stem.replace("_", "-").split("-")
    if len(parts) >= 2:
        return f"{parts[0].capitalize()} {parts[1].capitalize()}"
    return parts[0].capitalize()


class TranscriptIngester:
    """Handles parsing, token-aware chunking, embedding generation, and resilient DB insertion."""

    def __init__(
        self,
        db_url: Optional[str] = None,
        embedding_service: Optional[EmbeddingService] = None,
        chunk_size: int = CHUNK_SIZE_TOKENS,
        chunk_overlap: int = CHUNK_OVERLAP_TOKENS,
    ):
        self.db_url = db_url or os.getenv("DATABASE_URL")
        self.embedding_service = embedding_service or EmbeddingService()
        self.tokenizer = tiktoken.get_encoding("cl100k_base")
        self.text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name="cl100k_base",
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def connect_with_retry(
        self,
        max_retries: int = 5,
        initial_backoff: float = 1.0,
    ) -> psycopg2.extensions.connection:
        """Establish database connection with exponential backoff to handle container startup latency."""
        if not self.db_url:
            raise ValueError("DATABASE_URL environment variable is required to connect to the database.")

        backoff = initial_backoff
        for attempt in range(1, max_retries + 1):
            try:
                conn = psycopg2.connect(self.db_url)
                logger.info("Connected to database successfully on attempt %d.", attempt)
                return conn
            except (psycopg2.OperationalError, psycopg2.DatabaseError) as err:
                if attempt == max_retries:
                    logger.error(
                        "Max connection retries (%d) exceeded. Unable to connect to DB: %s",
                        max_retries,
                        err,
                    )
                    raise
                logger.warning(
                    "Database connection failed on attempt %d/%d (%s). Retrying in %.1fs...",
                    attempt,
                    max_retries,
                    err,
                    backoff,
                )
                time.sleep(backoff)
                backoff *= 2
        raise RuntimeError("Failed to connect to database.")

    def ensure_schema(self, conn: psycopg2.extensions.connection, schema_path: Optional[str] = None) -> None:
        """Execute schema.sql to ensure vector extension and tables exist."""
        if schema_path is None:
            schema_path = str(Path(__file__).parent / "schema.sql")

        logger.info("Verifying database schema from %s", schema_path)
        with open(schema_path, "r", encoding="utf-8") as f:
            ddl = f.read()

        with conn.cursor() as cursor:
            cursor.execute(ddl)
        conn.commit()
        logger.info("Database schema initialized and verified.")

    def chunk_transcript(
        self,
        file_path: Path,
    ) -> List[Tuple[str, str, int, str, int]]:
        """Read and recursively chunk a transcript file, preserving speaker and metadata.
        
        Returns a list of tuples: (source_file, guest_name, chunk_index, chunk_content, token_count)
        """
        filename = file_path.name
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        guest_name = parse_guest_name(raw_text, filename)
        chunks = self.text_splitter.split_text(raw_text)

        processed_chunks: List[Tuple[str, str, int, str, int]] = []
        for idx, chunk_text in enumerate(chunks):
            # Prepend guest context if chunk starts mid-turn without speaker cue
            token_count = len(self.tokenizer.encode(chunk_text))
            processed_chunks.append((filename, guest_name, idx, chunk_text, token_count))

        return processed_chunks

    def ingest_directory(
        self,
        transcripts_dir: Path,
        batch_size: int = DEFAULT_BATCH_SIZE,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Ingest all markdown/txt transcripts from a directory in batches."""
        start_time = time.time()
        files = sorted(
            list(transcripts_dir.glob("*.md")) + list(transcripts_dir.glob("*.txt"))
        )

        if not files:
            logger.warning("No transcript files found in %s", transcripts_dir)
            return {
                "status": "empty",
                "files_processed": 0,
                "total_chunks": 0,
                "elapsed_seconds": round(time.time() - start_time, 2),
            }

        logger.info("Found %d transcript files in %s", len(files), transcripts_dir)

        all_chunks: List[Tuple[str, str, int, str, int]] = []
        for f in files:
            file_chunks = self.chunk_transcript(f)
            all_chunks.extend(file_chunks)
            logger.info("File '%s' produced %d chunks", f.name, len(file_chunks))

        total_tokens = sum(c[4] for c in all_chunks)
        avg_tokens = (total_tokens // len(all_chunks)) if all_chunks else 0

        logger.info(
            "Total chunks created: %d (Avg tokens/chunk: %d, Total tokens: %d)",
            len(all_chunks),
            avg_tokens,
            total_tokens,
        )

        if dry_run:
            logger.info("Dry-run mode enabled. Skipping database insertion and embedding generation.")
            return {
                "status": "dry_run_success",
                "files_processed": len(files),
                "total_chunks": len(all_chunks),
                "avg_tokens_per_chunk": avg_tokens,
                "total_tokens": total_tokens,
                "elapsed_seconds": round(time.time() - start_time, 2),
            }

        # Connect to database with retry
        conn = self.connect_with_retry()
        try:
            self.ensure_schema(conn)

            # Insert chunks in batches
            upsert_query = """
                INSERT INTO transcript_chunks (
                    source_file,
                    guest_name,
                    chunk_index,
                    content,
                    embedding
                ) VALUES %s
                ON CONFLICT (source_file, chunk_index)
                DO UPDATE SET
                    guest_name = EXCLUDED.guest_name,
                    content = EXCLUDED.content,
                    embedding = EXCLUDED.embedding,
                    created_at = CURRENT_TIMESTAMP;
            """

            inserted_count = 0
            for i in range(0, len(all_chunks), batch_size):
                batch = all_chunks[i : i + batch_size]
                logger.info(
                    "Processing batch %d-%d of %d chunks (generating embeddings)...",
                    i + 1,
                    min(i + batch_size, len(all_chunks)),
                    len(all_chunks),
                )

                records_to_insert = []
                for source_file, guest_name, chunk_idx, content, _ in batch:
                    # Generate embedding
                    embedding = self.embedding_service.embed_text(content)
                    # Convert embedding list to PostgreSQL vector string format
                    vector_literal = f"[{','.join(str(x) for x in embedding)}]"
                    records_to_insert.append(
                        (source_file, guest_name, chunk_idx, content, vector_literal)
                    )

                with conn.cursor() as cursor:
                    execute_values(
                        cursor,
                        upsert_query,
                        records_to_insert,
                        template="(%s, %s, %s, %s, %s::vector)",
                        page_size=batch_size,
                    )
                conn.commit()
                inserted_count += len(batch)
                logger.info("Committed %d/%d chunks to database.", inserted_count, len(all_chunks))

        finally:
            conn.close()

        elapsed = round(time.time() - start_time, 2)
        stats = {
            "status": "success",
            "files_processed": len(files),
            "total_chunks": len(all_chunks),
            "avg_tokens_per_chunk": avg_tokens,
            "total_tokens": total_tokens,
            "batch_size": batch_size,
            "elapsed_seconds": elapsed,
        }

        # Output structured log summary
        logger.info("INGESTION_COMPLETED: %s", json.dumps(stats))
        return stats


def main() -> None:
    """CLI entrypoint for running ingestion pipeline."""
    parser = argparse.ArgumentParser(description="Ingest transcript files into PostgreSQL + pgvector.")
    parser.add_argument(
        "--transcripts-dir",
        type=str,
        default="data/transcripts",
        help="Path to folder containing transcripts (.md, .txt)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Batch size for embeddings and DB insertion",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chunk transcripts and compute stats without calling embeddings or database",
    )
    args = parser.parse_args()

    transcripts_path = Path(args.transcripts_dir)
    if not transcripts_path.exists():
        logger.error("Transcripts directory not found: %s", transcripts_path)
        sys.exit(1)

    ingester = TranscriptIngester()
    stats = ingester.ingest_directory(
        transcripts_dir=transcripts_path,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
