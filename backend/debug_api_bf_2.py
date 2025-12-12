
import requests
import json

BASE_URL = "http://localhost:8000/api"
KB_ID = "0c0f4f26-f68a-479c-b76c-77a40eafc1aa"

def debug_bf():
    print(f"Checking Flat Index on KB: {KB_ID}")
    
    # payload: Keyword Search + Flat Index re-ranking
    # Because Vector Search returned 0 for me, I suspect Keyword Search is what yields candidates.
    # Brute Force applies to CANDIDATES.
    # So I must use "keyword" strategy first.
    
    payload = {
        "query": "오영수",
        "top_k": 5,
        "strategy": "keyword",
        "use_brute_force": True,
        "brute_force_top_k": 5, # Fetch top 5
        "brute_force_threshold": 2.5 # Max relaxed
    }
    
    try:
        search_resp = requests.post(f"{BASE_URL}/knowledge-bases/{KB_ID}/retrieve", json=payload)
        if search_resp.status_code == 200:
            results = search_resp.json()
            print(f"FOUND {len(results)} results!")
            for idx, res in enumerate(results):
                print(f"Result {idx+1}:")
                print(f"  Score: {res.get('score')}")
                print(f"  L2 Score: {res.get('l2_score')}")
        else:
            print(f"Search failed: {search_resp.status_code} {search_resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_bf()
