import sys
sys.path.insert(0, '/Users/dukekimm/Works/RAGaaS/backend')

from pymilvus import Collection
from app.core.milvus import connect_milvus, create_collection

# Connect
connect_milvus()

# Get collection
collection = create_collection("171dbd5b-c42d-4cd5-8bb7-ea2044060aed")
collection.load()

# Test query
expr = 'chunk_id == "423074fa-ceb1-401d-8236-5e81b9d236bc_0"'
results = collection.query(
    expr=expr,
    output_fields=["chunk_id", "content", "doc_id", "metadata"],
    limit=1
)

print("Query results:")
print(results)

# Test insert with entity format
if results:
    test_entity = [{
        "doc_id": "test_doc",
        "chunk_id": "test_chunk_999",
        "content": "Test content",
        "metadata": {},
        "vector": [0.1] * 1536
    }]
    
    try:
        collection.insert(test_entity)
        collection.flush()
        print("\nInsert successful!")
        
        # Clean up
        collection.delete('chunk_id == "test_chunk_999"')
        collection.flush()
        print("Cleanup successful!")
    except Exception as e:
        print(f"\nInsert failed: {e}")
        import traceback
        traceback.print_exc()
