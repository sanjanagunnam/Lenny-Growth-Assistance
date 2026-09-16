import httpx
import time


def main():
    t0 = time.time()
    client = httpx.Client(timeout=300.0)
    resp = client.post("http://localhost:8000/api/v1/chat", json={
        "message": "What are the 3 non-obvious retention levers recommended by Lenny's guests for consumer apps?",
        "provider": "ollama",
        "model": "glm-5.3-flash",
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


if __name__ == "__main__":
    main()
