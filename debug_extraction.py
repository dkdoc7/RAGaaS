import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.getcwd())

from app.services.ingestion.graph import graph_processor
from app.core.config import settings

TEXT = "Duke는 장풍의 초절정 고수이며 이 분야의 1인자라고 알려져 있다."
CHUNK_ID = "test_chunk_13"

async def test_extraction():
    print("--- Testing Graph Extraction ---")
    print(f"Input Text: {TEXT}")
    
    triples = await graph_processor.extract_graph_elements(TEXT, CHUNK_ID)
    
    print(f"\nExtracted {len(triples)} triples:")
    for t in triples:
        print(t)

if __name__ == "__main__":
    if not settings.OPENAI_API_KEY:
        print("Error: OPENAI_API_KEY not set.")
        exit(1)
        
    asyncio.run(test_extraction())
