import requests
import json

KB_ID = "1dbb131e-653c-46e4-89a9-24d30c9fbb76"
DOC_ID = "e2385138-cc1b-4762-81e2-e3ef8467be49"
CHUNK_ID = "e2385138-cc1b-4762-81e2-e3ef8467be49_13"

content = """YouTube 경유. 
●  Maas, Jennifer; Minton, Matt (2024년 12월 26일). “'Squid Game' Creator Br
eaks Down 'Heavy' Season 2 Finale Death, Mid-Credits Scene Clues and When S
eason 3 Is Coming”. 《Variety》. 2024년 12월 28일에 원본 문서에서 보존된 
문서. 2024년 12월 28일에 확인함."""

print(f"Updating chunk {CHUNK_ID} in KB {KB_ID}...")
files = {'content': (None, content)}
resp = requests.put(
    f"http://localhost:8000/api/knowledge-bases/{KB_ID}/documents/{DOC_ID}/chunks/{CHUNK_ID}",
    files=files
)

if resp.status_code == 200:
    print("✅ Chunk updated successfully!")
    print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
else:
    print(f"❌ Error updating chunk: {resp.status_code}")
    print(resp.text)
