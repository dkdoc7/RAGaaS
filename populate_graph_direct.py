import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from app.services.ingestion.graph import graph_processor
from app.core.fuseki import fuseki_client

KB_ID = "1dbb131e-653c-46e4-89a9-24d30c9fbb76"
# Using real chunk ID
TEST_CHUNK_ID = "e2385138-cc1b-4762-81e2-e3ef8467be49_13"
CONTENT = "Duke는 장풍의 초절정 고수이며 이 분야의 1인자라고 알려져 있다."

async def test_direct_pipeline():
    print(f"--- Testing Direct Graph Pipeline for KB {KB_ID} ---")
    
    # 1. Extraction
    print(f"Extracting from: {CONTENT}")
    triples = await graph_processor.extract_graph_elements(CONTENT, TEST_CHUNK_ID)
    
    print(f"Extracted {len(triples)} triples:")
    for t in triples:
        print(t)
        
    if not triples:
        print("❌ Extraction failed (empty list).")
        return

    # 2. Insertion
    print(f"\nInserting into Fuseki...")
    success = fuseki_client.insert_triples(KB_ID, triples)
    
    if success:
        print("✅ Insertion successful!")
        
        # 3. Verification
        print("Verifying in Fuseki...")
        query = f"""
        SELECT ?s ?p ?o WHERE {{
            ?s <http://rag.local/relation/hasSource> <http://rag.local/source/{TEST_CHUNK_ID}> .
            ?s ?p ?o .
        }}
        """
        results = fuseki_client.query_sparql(KB_ID, query)
        count = len(results.get("results", {}).get("bindings", []))
        print(f"Found {count} triples linked to source {TEST_CHUNK_ID}")
    else:
        print("❌ Insertion failed (fuseki_client returned False).")

if __name__ == "__main__":
    from app.core.config import settings
    if not settings.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set.")
        exit(1)
        
    asyncio.run(test_direct_pipeline())
