"""
Debug Milvus collection status and data
"""

from pymilvus import connections, Collection, utility
from app.core.config import settings

def debug_milvus():
    connections.connect(
        alias="default",
        host=settings.MILVUS_HOST,
        port=settings.MILVUS_PORT
    )
    
    collections = utility.list_collections()
    print(f"Collections: {collections}")
    
    for collection_name in collections:
        col = Collection(collection_name)
        col.load()
        print(f"\nCollection: {collection_name}")
        print(f"Schema: {col.schema}")
        print(f"Num entities: {col.num_entities}")
        
        # Check index
        for index in col.indexes:
            print(f"Index: {index.params}")
            
        # Try a dummy search
        import numpy as np
        dummy_vector = np.random.rand(1, 1536).tolist()
        try:
            results = col.search(
                data=dummy_vector, 
                anns_field="vector", 
                param={"metric_type": "COSINE", "params": {"nprobe": 10}}, 
                limit=1
            )
            print("Search functionality check: OK")
        except Exception as e:
            print(f"Search functionality check: FAILED - {e}")

if __name__ == "__main__":
    debug_milvus()
