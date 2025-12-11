import requests
import json
import time

KB_ID = "09e9662c-e3ed-412c-98b8-dc73dd3a9745" # squid gr
DOC_ID = "b5625e14-b81e-47d2-aa6f-92c591c649f4"

# Chunk contents as described by user
chunks_to_update = [
    {
        "chunk_id": f"{DOC_ID}_11",
        "content": "성기훈은 오일남에게 장풍을 전수 받았다. 성기훈은 이 기술로 게임에서 유리한 고지를 점했다."
    },
    {
        "chunk_id": f"{DOC_ID}_12",
        "content": "오일남은 장풍의 고수이다. 하지만 그는 사실 Duke의 제자이다. Duke는 전설적인 인물이다."
    },
    {
        "chunk_id": f"{DOC_ID}_13",
        "content": "Duke는 장풍의 초절정 고수이며 이 분야의 1인자라고 알려져 있다. 그의 실력은 타의 추종을 불허한다."
    }
]

print(f"Updating 3 chunks in KB {KB_ID} to build graph connections...")

# Update chunks sequentially
for item in chunks_to_update:
    chunk_id = item["chunk_id"]
    print(f"\nUpdating {chunk_id}...")
    
    files = {'content': (None, item["content"])}
    resp = requests.put(
        f"http://localhost:8000/api/knowledge-bases/{KB_ID}/documents/{DOC_ID}/chunks/{chunk_id}",
        files=files
    )
    
    if resp.status_code == 200:
        print(f"✅ Updated {chunk_id}")
        data = resp.json()
        print(f"Graph Updated: {data.get('graph_updated')}")
    else:
        print(f"❌ Failed to update {chunk_id}: {resp.status_code}")
        print(resp.text)
    
    # Wait a bit to avoid rate limits on LLM extraction
    time.sleep(2)

print("\nAll chunks updated. Verify Graph update manually or via search.")
