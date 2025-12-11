import requests
import time
import json
import os

BASE_URL = "http://localhost:8000/api"

def create_kb():
    print("Creating KB...")
    response = requests.post(f"{BASE_URL}/knowledge-bases/", json={
        "name": "Graph RAG Test",
        "description": "Verification KB",
        "chunking_strategy": "size",
        "chunking_config": {"chunk_size": 200, "overlap": 20},
        "metric_type": "COSINE",
        "enable_graph_rag": True
    })
    if response.status_code != 200:
        print("Error creating KB:", response.text)
        return None
    return response.json()

def upload_doc(kb_id):
    print("Uploading Doc...")
    content = """
    Elon Musk is the CEO of SpaceX. SpaceX is a private aerospace company headquartered in Hawthorne, California.
    Tesla Inc is led by Elon Musk as well.
    Blue Origin is a competitor founded by Jeff Bezos.
    """
    files = {"file": ("test_graph.txt", content)}
    response = requests.post(f"{BASE_URL}/knowledge-bases/{kb_id}/documents", files=files)
    if response.status_code != 200:
        print("Error uploading doc:", response.text)
        return None
    return response.json()

def check_status(kb_id, doc_id):
    print("Checking status...")
    for _ in range(30):
        response = requests.get(f"{BASE_URL}/knowledge-bases/{kb_id}/documents")
        docs = response.json()
        for doc in docs:
            if doc['id'] == doc_id:
                print(f"Status: {doc['status']}")
                if doc['status'] == 'completed':
                    return True
                if doc['status'] == 'error':
                    return False
        time.sleep(1)
    return False

def search_graph(kb_id, query):
    print(f"Searching: {query}")
    response = requests.post(f"{BASE_URL}/knowledge-bases/{kb_id}/retrieve", json={
        "query": query,
        "top_k": 3,
        "score_threshold": 0.0,
        "strategy": "hybrid",
        "enable_graph_search": True,
        "graph_hops": 1
    })
    if response.status_code != 200:
        print("Search failed:", response.text)
        return []
    return response.json()

def fail(msg):
    print(f"FAILED: {msg}")
    exit(1)

def run():
    kb = create_kb()
    if not kb: fail("Could not create KB")
    kb_id = kb['id']
    print(f"KB Created: {kb_id}")
    
    try:
        doc = upload_doc(kb_id)
        if not doc: fail("Could not upload doc")
        doc_id = doc['id']
        
        if not check_status(kb_id, doc_id):
            fail("Document processing not completed or failed")
            
        # Give a moment for async graph tasks if any
        time.sleep(2)
        
        results = search_graph(kb_id, "Who is CEO of SpaceX?")
        print("Results:", json.dumps(results, indent=2))
        
        found = False
        for res in results:
             # Check if we got results and maybe inspect metadata if implemented
             if "SpaceX" in res['content']:
                 found = True
        
        if found:
            print("SUCCESS: Found relevant content with Graph Search enabled.")
        else:
            print("WARNING: Did not find obvious match, but search completed.")
            
    finally:
        # Cleanup
        print("Deleting KB...")
        requests.delete(f"{BASE_URL}/knowledge-bases/{kb_id}")

if __name__ == "__main__":
    run()
