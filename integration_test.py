import requests
import time

BASE_URL = "http://localhost:8000/api/knowledge-bases"

def test_flow():
    # 1. Create Knowledge Base
    print("Creating Knowledge Base...")
    kb_data = {"name": "Test KB", "description": "Integration Test"}
    res = requests.post(f"{BASE_URL}/", json=kb_data)
    if res.status_code != 200:
        print(f"Failed to create KB: {res.text}")
        return
    kb = res.json()
    kb_id = kb["id"]
    print(f"KB Created: {kb_id}")

    # 2. Upload Document
    print("Uploading Document...")
    files = {"file": ("test.txt", "This is a test document for RAG system verification. It contains some sample text to be chunked and indexed.", "text/plain")}
    data = {"chunking_strategy": "size"}
    res = requests.post(f"{BASE_URL}/{kb_id}/documents", files=files, data=data)
    if res.status_code != 200:
        print(f"Failed to upload document: {res.text}")
        return
    doc = res.json()
    doc_id = doc["id"]
    print(f"Document Uploaded: {doc_id}")

    # Wait for processing
    print("Waiting for processing...")
    for _ in range(10):
        time.sleep(2)
        res = requests.get(f"{BASE_URL}/{kb_id}/documents")
        docs = res.json()
        target_doc = next((d for d in docs if d["id"] == doc_id), None)
        if target_doc and target_doc["status"] == "completed":
            print("Document Processed!")
            break
    else:
        print("Document processing timed out or failed.")
        return

    # 3. Retrieve
    print("Testing Retrieval...")
    search_data = {
        "query": "test document",
        "top_k": 2,
        "score_threshold": 0.0,
        "strategy": "ann"
    }
    res = requests.post(f"{BASE_URL}/{kb_id}/retrieve", json=search_data)
    if res.status_code != 200:
        print(f"Retrieval failed: {res.text}")
        return
    results = res.json()
    print(f"Retrieved {len(results)} chunks.")
    for r in results:
        print(f"- {r['content']} (Score: {r['score']})")

    # Cleanup
    print("Cleaning up...")
    requests.delete(f"{BASE_URL}/{kb_id}")
    print("Done.")

if __name__ == "__main__":
    test_flow()
