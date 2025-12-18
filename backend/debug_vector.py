
import asyncio
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.services.retrieval.vector import VectorRetrievalStrategy
from app.core.milvus import connect_milvus, create_collection
from app.services.embedding import embedding_service

async def main():
    try:
        connect_milvus()
        print("Connected to Milvus.")
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    kb_id = "0c0f4f26-f68a-479c-b76c-77a40eafc1aa"
    query = "오영수 배우의 역할은?"
    strategy = VectorRetrievalStrategy()
    
    print(f"Testing Vector Search for KB: {kb_id}, Query: {query}")
    try:
        # Check actual vectors in DB first
        collection = create_collection(kb_id)
        collection.load()
        count = collection.num_entities
        print(f"Collection count: {count}")
        
        # Simple verify of content diversity
        res = collection.query(expr="id >= 0", output_fields=["content", "chunk_id"], limit=10)
        print("\n--- Sample Documents in DB ---")
        seen_content = set()
        for r in res:
            content_snippet = r.get('content')[:50].replace('\n', ' ')
            if content_snippet in seen_content:
                print(f"[DUPLICATE] {content_snippet}...")
            else:
                print(f"ID: {r.get('chunk_id')}, Content: {content_snippet}...")
                seen_content.add(content_snippet)
        
        print("\n--- Search Results ---")
        results = await strategy.search(kb_id, query, top_k=5, metric_type="COSINE")
        for i, r in enumerate(results):
            content_snippet = r.get('content')[:100].replace('\n', ' ')
            print(f"Rank {i+1}: Score={r.get('score'):.4f}, ID={r.get('chunk_id')}")
            print(f"Content: {content_snippet}...")
            
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
