import requests
import json

# Get knowledge bases
response = requests.get("http://localhost:8000/api/knowledge-bases")
print("=== Knowledge Bases ===")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
