import sys
import json
sys.path.insert(0, ".")

from backend.app.rag.embeddings import EmbeddingService
from backend.app.rag.retrieval import compute_cosine_similarity

queries = [
    "What are the 3 non-obvious retention levers recommended by Lenny's guests for consumer apps?",
    "How to find product market fit according to founders?",
    "What is the LNO framework?",
    "How do I make chocolate chip cookies?",
    "What is the weather today in Tokyo?",
    "Write a quicksort in C++",
]

embedder = EmbeddingService()

with open("data/transcripts_cache.json", "r", encoding="utf-8") as f:
    chunks = json.load(f)

for q in queries:
    q_vec = embedder.embed_text(q)
    sims = [compute_cosine_similarity(q_vec, c["embedding"]) for c in chunks]
    max_sim = max(sims)
    avg_sim = sum(sims) / len(sims)
    print(f"Query: '{q[:50]}...'\n  Max Sim: {max_sim:.4f} | Avg Sim: {avg_sim:.4f}")
