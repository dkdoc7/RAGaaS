
import requests
import json

BASE_URL = "http://localhost:8000/api"
KB_ID = "test-kb"  # I need a valid KB ID. I'll search for one or list them.

def get_kb_id():
    try:
        resp = requests.get(f"{BASE_URL}/knowledge-bases")
        if resp.status_code == 200:
            kbs = resp.json()
            if kbs:
                return kbs[0]['id']
    except Exception as e:
        print(f"Error fetching KBs: {e}")
    return None

def test_search(kb_id):
    print(f"Testing search on KB: {kb_id}")
    
    # 1. Normal Search
    print("\n[Normal Search]")
    payload = {
        "query": "오영수",
        "top_k": 3,
        "strategy": "ann",
        "use_brute_force": False
    }
    try:
        resp = requests.post(f"{BASE_URL}/knowledge-bases/{kb_id}/retrieve", json=payload)
        if resp.status_code == 200:
            results = resp.json()
            print(f"Results count: {len(results)}")
            if results:
                print(f"First result keys: {results[0].keys()}")
                print(f"First result score: {results[0].get('score')}")
                print(f"First result l2_score: {results[0].get('l2_score')}")
        else:
            print(f"Error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Flat Index (Brute Force) Search
    print("\n[Flat Index Search]")
    payload_bf = {
        "query": "오영수",
        "top_k": 3,
        "strategy": "ann",
        "use_brute_force": True,
        "brute_force_top_k": 3,
        "brute_force_threshold": 2.0
    }
    try:
        resp = requests.post(f"{BASE_URL}/knowledge-bases/{kb_id}/retrieve", json=payload_bf)
        if resp.status_code == 200:
            results = resp.json()
            print(f"Results count: {len(results)}")
            if results:
                print(f"First result keys: {results[0].keys()}")
                print(f"First result score: {results[0].get('score')}")
                print(f"First result l2_score: {results[0].get('l2_score')}")
        else:
            print(f"Error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    kb_id = get_kb_id()
    if kb_id:
        test_search(kb_id)
    else:
        print("No Knowledge Base found.")
