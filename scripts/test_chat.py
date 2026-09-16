import httpx
import time

t0 = time.time()
client = httpx.Client(timeout=120.0)
resp = client.post("http://localhost:8000/api/v1/chat", json={
    "message": "How does Brian Chesky explain Airbnb's growth loops versus paid performance marketing?",
    "provider": "ollama",
    "mode": "chat",
})
elapsed = round(time.time() - t0, 2)
print(f"Status: {resp.status_code} in {elapsed}s")
if resp.status_code == 200:
    data = resp.json()
    print("Grounding confidence:", data.get("grounding_confidence"))
    print("Epistemic status:", data.get("epistemic_status"))
    print("Provider used:", data.get("provider_used"))
    print("Sources count:", len(data.get("sources", [])))
    for s in data.get("sources", []):
        print(f"  - {s.get('guest_name')} ({s.get('source_file')}): similarity {s.get('similarity')}")
    print("\nReply snippet:\n", data.get("reply", "")[:500])
else:
    print("Error:", resp.text)
