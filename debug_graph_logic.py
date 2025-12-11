import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from app.services.retrieval.graph import GraphRetrievalStrategy
from app.core.config import settings

KB_ID = "1dbb131e-653c-46e4-89a9-24d30c9fbb76"
QUERY = "1인자 Duke"

async def test_direct_search():
    print("--- Starting Direct Graph Search Test ---")
    strategy = GraphRetrievalStrategy()
    
    # 1. Extract Entities (Test internal method)
    print(f"\n[Step 1] Extracting entities for: {QUERY}")
    entities = await strategy._extract_entities(QUERY)
    print(f"Extracted Entities: {entities}")
    
    if not entities:
        print("❌ Failed to extract entities.")
        return

    # 2. Query Graph (Test internal method)
    print(f"\n[Step 2] Querying Graph (Hops=2) for extracted entities...")
    graph_data = strategy._query_graph(KB_ID, entities, hops=2)
    
    chunk_ids = graph_data.get('chunk_ids', [])
    print(f"\nFound {len(chunk_ids)} chunks: {chunk_ids}")
    
    triples = graph_data.get('triples', [])
    print(f"Graph Triples Found: {len(triples)}")
    for t in triples[:15]:
        print(f" - {t['subject']} -> {t['predicate']} -> {t['object']}")
        
    if not chunk_ids:
        print("❌ No chunks found via Graph Search.")
    else:
        print("✅ Graph Search Successful!")

if __name__ == "__main__":
    if not settings.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set.")
        exit(1)
        
    asyncio.run(test_direct_search())
