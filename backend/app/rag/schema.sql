-- Enable the pgvector extension to support vector data types and similarity searches
CREATE EXTENSION IF NOT EXISTS vector;

-- Table to store chunked transcripts with 768-dimensional embeddings
CREATE TABLE IF NOT EXISTS transcript_chunks (
    id SERIAL PRIMARY KEY,
    source_file TEXT NOT NULL,
    guest_name TEXT NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_source_chunk UNIQUE (source_file, chunk_index)
);

-- B-Tree indexes for metadata filtering
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_source_file ON transcript_chunks (source_file);
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_guest_name ON transcript_chunks (guest_name);

-- IVFFlat index for fast approximate nearest neighbor (ANN) cosine similarity search
-- vector_cosine_ops supports cosine distance searches using the <=> operator
CREATE INDEX IF NOT EXISTS idx_transcript_chunks_embedding 
ON transcript_chunks 
USING ivfflat (embedding vector_cosine_ops) 
WITH (lists = 100);
