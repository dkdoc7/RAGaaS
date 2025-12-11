#!/usr/bin/env python3
"""
Test Graph RAG update when chunk is modified
"""
import requests
import json

KB_ID = "171dbd5b-c42d-4cd5-8bb7-ea2044060aed"
DOC_ID = "423074fa-ceb1-401d-8236-5e81b9d236bc"
CHUNK_ID = "423074fa-ceb1-401d-8236-5e81b9d236bc_0"

# Check if KB has graph RAG enabled
print("Checking KB settings...")
kb_resp = requests.get(f"http://localhost:8000/api/knowledge-bases/{KB_ID}")
if kb_resp.status_code == 200:
    kb_data = kb_resp.json()
    print(f"KB Name: {kb_data.get('name')}")
    print(f"Graph RAG Enabled: {kb_data.get('enable_graph_rag')}")
else:
    print(f"Error fetching KB: {kb_resp.status_code}")
    exit(1)

# Update chunk with new content
print(f"\nUpdating chunk {CHUNK_ID}...")
new_content = """
오징어 게임은 황동혁 감독이 제작한 넷플릭스 시리즈입니다.
이정재가 주연을 맡았으며, 2021년 9월 17일에 공개되었습니다.
전 세계적으로 큰 인기를 얻었습니다.
"""

files = {'content': (None, new_content)}
update_resp = requests.put(
    f"http://localhost:8000/api/knowledge-bases/{KB_ID}/documents/{DOC_ID}/chunks/{CHUNK_ID}",
    files=files
)

if update_resp.status_code == 200:
    result = update_resp.json()
    print("✅ Chunk updated successfully!")
    print(json.dumps(result, indent=2, ensure_ascii=False))
else:
    print(f"❌ Error updating chunk: {update_resp.status_code}")
    print(update_resp.text)
