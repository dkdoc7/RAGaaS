from app.core.milvus import create_collection
from app.services.embedding import embedding_service
from typing import List, Dict
from sentence_transformers import CrossEncoder
import asyncio

class RetrievalService:
    def __init__(self):
        # Load a lightweight cross-encoder for reranking
        # We load it lazily or here. For a demo, here is fine but might slow down startup.
        # To avoid startup delay, we could load it on first use or use a separate service.
        # For now, let's assume it's fast enough or we'll load it globally.
        self.reranker = None

    def _get_reranker(self):
        if not self.reranker:
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        return self.reranker

    async def search_ann(self, kb_id: str, query: str, top_k: int = 5, score_threshold: float = 0.0, metric_type: str = "L2") -> List[Dict]:
        collection = create_collection(kb_id)
        collection.load()

        # 1. Embed query
        query_vectors = await embedding_service.get_embeddings([query])
        
        # 2. Search
        search_params = {
            "metric_type": metric_type,
            "params": {"nprobe": 10},
        }
        
        results = collection.search(
            data=query_vectors, 
            anns_field="vector", 
            param=search_params, 
            limit=top_k, 
            output_fields=["content", "doc_id", "chunk_id"]
        )
        
        retrieved = []
        for hits in results:
            for hit in hits:
                # L2 distance: smaller is better. But usually we want similarity.
                # If we used IP (Inner Product) with normalized vectors, it would be cosine similarity.
                # For L2, we might want to convert or just return distance.
                # Let's assume the user handles the score interpretation or we normalize.
                # For now, just return the score.
                if hit.score < score_threshold and score_threshold > 0: # Check logic for L2
                     continue
                
                retrieved.append({
                    "chunk_id": hit.entity.get("chunk_id"),
                    "content": hit.entity.get("content"),
                    "score": hit.score,
                    "metadata": {"doc_id": hit.entity.get("doc_id")}
                })
        
        return retrieved

    async def search_2stage(self, kb_id: str, query: str, top_k: int = 5, metric_type: str = "L2") -> List[Dict]:
        # 1. Candidate Generation (ANN) - Fetch more candidates (e.g., top_k * 5)
        candidates = await self.search_ann(kb_id, query, top_k=top_k * 5, metric_type=metric_type)
        
        if not candidates:
            return []

        # 2. Reranking
        reranker = self._get_reranker()
        
        pairs = [[query, doc["content"]] for doc in candidates]
        scores = reranker.predict(pairs)
        
        # Attach scores and sort
        for i, doc in enumerate(candidates):
            doc["score"] = float(scores[i]) # Update score to reranker score
            
        # Sort by new score (descending)
        candidates.sort(key=lambda x: x["score"], reverse=True)
        
        return candidates[:top_k]

    async def search_keyword(self, kb_id: str, query: str, top_k: int = 5) -> List[Dict]:
        # Placeholder for keyword search. 
        # Since we don't have an inverted index, we can't do efficient keyword search.
        # We could implement a basic scan if data is small, but that's bad practice.
        # For this demo, we will return an empty list or throw not implemented, 
        # OR we can use Milvus scalar filtering with `like` if we had a keyword field?
        # No, let's just use ANN for now and label it as a limitation, 
        # or maybe use a simple string match on the retrieved ANN results? No that's filtering.
        
        # Let's try to use Milvus query with wildcards if possible? 
        # Milvus supports `like` operator.
        collection = create_collection(kb_id)
        collection.load()
        
        # This is VERY inefficient for large datasets and only supports prefix/postfix usually.
        # But for a demo it might work.
        expr = f'content like "%{query}%"'
        
        results = collection.query(
            expr=expr,
            output_fields=["content", "doc_id", "chunk_id"],
            limit=top_k
        )
        
        retrieved = []
        for hit in results:
            retrieved.append({
                "chunk_id": hit.get("chunk_id"),
                "content": hit.get("content"),
                "score": 1.0, # Dummy score
                "metadata": {"doc_id": hit.get("doc_id")}
            })
            
        return retrieved

retrieval_service = RetrievalService()
