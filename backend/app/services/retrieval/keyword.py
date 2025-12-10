from typing import List, Dict, Any
from app.core.milvus import create_collection
from app.services.embedding import embedding_service
from .base import RetrievalStrategy
import numpy as np

class KeywordRetrievalStrategy(RetrievalStrategy):
    async def search(self, kb_id: str, query: str, top_k: int, **kwargs) -> List[Dict[str, Any]]:
        score_threshold = kwargs.get("score_threshold", 0.0)
        
        collection = create_collection(kb_id)
        collection.load()
        
        # Embed query for cosine calculation (needed for unified scoring)
        query_vectors = await embedding_service.get_embeddings([query])
        query_vec = query_vectors[0]
        
        # Milvus scalar query (LIKE)
        expr = f'content like "%{query}%"'
        
        results = collection.query(
            expr=expr,
            output_fields=["content", "doc_id", "chunk_id", "vector"],
            limit=top_k * 3
        )
        
        retrieved = []
        for hit in results:
            chunk_vector = hit.get("vector")
            cosine_score = 0.0
            if chunk_vector:
                cosine_score = self._cosine_similarity(query_vec, chunk_vector)
            
            if cosine_score < score_threshold:
                continue
            
            retrieved.append({
                "chunk_id": hit.get("chunk_id"),
                "content": hit.get("content"),
                "score": cosine_score,
                "metadata": {"doc_id": hit.get("doc_id")}
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
