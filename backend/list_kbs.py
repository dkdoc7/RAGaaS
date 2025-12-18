
import requests
import json

BASE_URL = "http://localhost:8000/api"

def list_kbs():
    try:
        resp = requests.get(f"{BASE_URL}/knowledge-bases")
        if resp.status_code == 200:
            kbs = resp.json()
            print(f"Found {len(kbs)} KBs:")
            for kb in kbs:
                print(f"ID: {kb['id']}, Name: {kb['name']}, Doc Count: {kb.get('document_count', 'N/A')}, Metric: {kb.get('metric_type')}")
        else:
            print(f"Error: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_kbs()
