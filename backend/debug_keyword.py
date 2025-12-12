
import asyncio
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.services.retrieval.keyword import KeywordRetrievalStrategy
from app.core.milvus import connect_milvus

async def main():
    try:
        connect_milvus()
        print("Connected to Milvus.")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    kb_id = "0c0f4f26-f68a-479c-b76c-77a40eafc1aa"
    query = "성기훈의 참가번호"
    strategy = KeywordRetrievalStrategy()
    
    print(f"Testing Keyword Search for KB: {kb_id}, Query: {query}")
    try:
        results = await strategy.search(kb_id, query, top_k=3)
        print("Results found:", len(results))
        for r in results:
            print(r)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
