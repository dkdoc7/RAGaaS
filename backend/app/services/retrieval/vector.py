from typing import List, Dict, Any
import numpy as np
from app.core.milvus import create_collection
from app.services.embedding import embedding_service
from .base import RetrievalStrategy

class VectorRetrievalStrategy(RetrievalStrategy):
    async def search(self, kb_id: str, query: str, top_k: int, **kwargs) -> List[Dict[str, Any]]:
        score_threshold = kwargs.get("score_threshold", 0.0)
        metric_type = kwargs.get("metric_type", "COSINE")
        
        collection = create_collection(kb_id)
        collection.load()

        # 1. Embed query
        query_vectors = await embedding_service.get_embeddings([query])
        query_vec = query_vectors[0]
        
        # 2. Search
        search_params = {
            "metric_type": metric_type,
            "params": {"nprobe": 10},
        }
        
        results = collection.search(
            data=query_vectors, 
            anns_field="vector", 
            param=search_params, 
            limit=top_k * 3,  # Fetch more for filtering
            output_fields=["content", "doc_id", "chunk_id", "vector"]
        )
        
        retrieved = []
        for hits in results:
            for hit in hits:
                # Always compute cosine similarity for unified scoring
                chunk_vector = hit.entity.get("vector")
                cosine_score = 0.0
                if chunk_vector:
                    cosine_score = self._cosine_similarity(query_vec, chunk_vector)
                
                if cosine_score < score_threshold:
                    continue
                
                retrieved.append({
                    "chunk_id": hit.entity.get("chunk_id"),
                    "content": hit.entity.get("content"),
                    "score": cosine_score,
                    "metadata": {"doc_id": hit.entity.get("doc_id")}
                })
        
        retrieved.sort(key=lambda x: x["score"], reverse=True)
        return retrieved[:top_k]

    def _cosine_similarity(self, vec1, vec2) -> float:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))
