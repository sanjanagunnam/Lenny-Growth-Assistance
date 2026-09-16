import httpx

client = httpx.Client(timeout=30.0)
resp = client.post("http://localhost:8000/api/v1/chat", json={
    "message": "How do I make chocolate chip cookies?",
    "provider": "ollama",
    "mode": "chat",
})
print("Status:", resp.status_code)
data = resp.json()
print("Reply:", data.get("reply"))
print("Epistemic status:", data.get("epistemic_status"))
print("Sources count:", len(data.get("sources", [])))
assert data.get("reply") == "The available podcast transcripts do not cover this specific question."
assert data.get("epistemic_status") == "REFUSAL"
assert len(data.get("sources", [])) == 0
print("Refusal test PASSED successfully!")
