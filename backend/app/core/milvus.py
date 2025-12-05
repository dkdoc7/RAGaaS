from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, utility
from app.core.config import settings

def connect_milvus():
    connections.connect(
        alias="default", 
        host=settings.MILVUS_HOST, 
        port=settings.MILVUS_PORT
    )

def create_collection(kb_id: str):
    collection_name = f"kb_{kb_id.replace('-', '_')}"
    
    if utility.has_collection(collection_name):
        return Collection(collection_name)
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="doc_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="chunk_id", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=1536) # Assuming OpenAI embedding dim
    ]
    
    schema = CollectionSchema(fields, "Knowledge Base Collection")
    collection = Collection(collection_name, schema)
    
    index_params = {
        "metric_type": "L2",
        "index_type": "IVF_FLAT",
        "params": {"nlist": 1024}
    }
    collection.create_index(field_name="vector", index_params=index_params)
    return collection
