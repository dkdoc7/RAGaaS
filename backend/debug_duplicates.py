
import asyncio
import sys
import os

# Add app to path
sys.path.append(os.getcwd())

from app.services.retrieval.vector import VectorRetrievalStrategy
from app.core.milvus import connect_milvus, create_collection

async def main():
    try:
        connect_milvus()
    except Exception as e:
        print(f"Failed to connect: {e}")
        return

    kb_id = "0c0f4f26-f68a-479c-b76c-77a40eafc1aa"
    query = "합류하면" # Trigger for the duplicate chunk
    strategy = VectorRetrievalStrategy()
    
    print(f"Testing Duplicate Search for KB: {kb_id}, Query: {query}")
    try:
        # 1. Direct Vector Search
        results = await strategy.search(kb_id, query, top_k=10, metric_type="COSINE")
        print(f"\nFound {len(results)} results:")
        
        content_counts = {}
        for i, r in enumerate(results):
            c = r.get('content', '').strip()
            cid = r.get('chunk_id')
            score = r.get('score')
            
            # Signature for duplicate detection (first 50 chars)
            sig = c[:50]
            if sig not in content_counts:
                content_counts[sig] = []
            content_counts[sig].append(cid)
            
            print(f"[{i+1}] Score: {score:.4f} | ID: {cid}")
            print(f"Content: {c[:60]}...")
            print("-" * 20)

        print("\n--- Duplicate Analysis ---")
        for sig, ids in content_counts.items():
            if len(ids) > 1:
                print(f"Duplicate Content Found ({len(ids)} times):")
                print(f"Preview: {sig}...")
                print(f"Chunk IDs: {ids}")
            
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
