import sys
from backend.app.rag.embeddings import EmbeddingService
from backend.app.agents.retriever import retrieve_context

queries = [
    "How does Brian Chesky explain Airbnb growth loops versus paid performance marketing?",
    "What is the LNO framework recommended by Shreyas Doshi on Lenny's Podcast?",
    "What advice does Brian Chesky give on finding product-market fit and doing things that don't scale?",
    "What are the 3 non-obvious retention levers recommended by Lenny's guests?",
]

for q in queries:
    chunks = retrieve_context(q, threshold=0.65)
    print(f"Query: '{q}' -> {len(chunks)} chunks >= 0.65")
    for c in chunks:
        print(f"   [{c['similarity']}] {c['guest_name']}: {c['content'][:70]}...")
