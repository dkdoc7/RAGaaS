import requests
import json

KB_ID = "09e9662c-e3ed-412c-98b8-dc73dd3a9745" # Actual "squid gr" KB
QUERY = "Duke"

def test_chat(hops=1):
    print(f"\n--- Testing Chat Endpoint with graph_hops={hops} ---")
    payload = {
        "query": QUERY,
        "top_k": 5,
        "score_threshold": 0.0,
        "strategy": "hybrid",
        "enable_graph_search": True,
        "graph_hops": hops
    }
    
    url = f"http://localhost:8000/api/knowledge-bases/{KB_ID}/chat"
    print(f"POST {url}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    try:
        resp = requests.post(url, json=payload)
        
        if resp.status_code == 200:
            data = resp.json()
            chunks = data.get("chunks", [])
            print(f"Found {len(chunks)} chunks.")
            
            if chunks:
                first = chunks[0]
                print(f"First Chunk ID: {first.get('chunk_id')}")
                # Check for graph metadata
                if "graph_metadata" in first:
                    print("✅ Graph Metadata Found in Chat Response!")
                    meta = first["graph_metadata"]
                    print("Extracted Entities:", meta.get("extracted_entities"))
                else:
                    print("❌ No Graph Metadata in first chunk of Chat Response.")
                    print("First Chunk Keys:", list(first.keys()))
        else:
            print(f"Error: {resp.status_code} - {resp.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_chat()
