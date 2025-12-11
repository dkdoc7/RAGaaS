import requests
import json

KB_ID = "1dbb131e-653c-46e4-89a9-24d30c9fbb76" # squid gr
QUERY = "Duke 1인자"

def test_search(hops=1):
    print(f"\n--- Testing Search with graph_hops={hops} ---")
    payload = {
        "query": QUERY,
        "top_k": 5,
        "strategy": "hybrid",
        "enable_graph_search": True,
        "graph_hops": hops,
        "score_threshold": 0.0
    }
    
    # Using retrieve endpoint to see raw chunks + metadata
    resp = requests.post(f"http://localhost:8000/api/knowledge-bases/{KB_ID}/retrieve", json=payload)
    
    if resp.status_code == 200:
        results = resp.json()
        print(f"Found {len(results)} chunks.")
        
        if results:
            first = results[0]
            print("First Result Content Preview:", first.get("content")[:50])
            
            # Check for graph metadata
            if "graph_metadata" in first:
                print("✅ Graph Metadata Found!")
                meta = first["graph_metadata"]
                print("Extracted Entities:", meta.get("extracted_entities"))
                q = meta.get("sparql_query")
                print(f"SPARQL Query Preview: {q[:50]}...")
                print("Triples Found:", len(meta.get("triples", [])))
            else:
                print("❌ No Graph Metadata in first result.")
    else:
        print(f"Error: {resp.status_code}")
        print(resp.text)

# Test with 1 hop and 2 hops
test_search(hops=1)
test_search(hops=2)
