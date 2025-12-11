from typing import List, Dict, Any
from .base import RetrievalStrategy
from .vector import VectorRetrievalStrategy
from .graph import GraphRetrievalStrategy
from app.core.milvus import create_collection
from app.services.embedding import embedding_service
from rank_bm25 import BM25Okapi
import numpy as np

class HybridRetrievalStrategy(RetrievalStrategy):
    """Combines BM25, Vector, and optional Graph Search results."""
    
    def __init__(self):
        self.vector_strategy = VectorRetrievalStrategy()
        self.graph_strategy = GraphRetrievalStrategy()

    async def search(self, kb_id: str, query: str, top_k: int, **kwargs) -> List[Dict[str, Any]]:
        metric_type = kwargs.get("metric_type", "COSINE")
        score_threshold = kwargs.get("score_threshold", 0.0)
        enable_graph = kwargs.get("enable_graph_search", False)
        
        collection = create_collection(kb_id)
        collection.load()
        
        # 1. Embed query
        query_vectors = await embedding_service.get_embeddings([query])
        query_vec = query_vectors[0]
        
        # 2. Fetch all docs for BM25 (Note: Not scalable for huge datasets, okay for MVP)
        all_docs = collection.query(
            expr="chunk_id != ''",
            output_fields=["content", "doc_id", "chunk_id", "vector"],
            limit=10000 
        )
        
        if not all_docs:
            return []
        
        # 3. BM25 Search
        corpus = [doc["content"] for doc in all_docs]
        tokenized_corpus = [content.lower().split() for content in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)
        
        bm25_candidates = []
        for idx, score in enumerate(bm25_scores):
            if score > 0:
                bm25_candidates.append({"idx": idx, "bm25_score": float(score)})
        
        bm25_candidates.sort(key=lambda x: x["bm25_score"], reverse=True)
        top_bm25_indices = set([c["idx"] for c in bm25_candidates[:top_k * 3]])
        
        # 4. Vector Search
        ann_results = await self.vector_strategy.search(kb_id, query, top_k=top_k * 3, metric_type=metric_type, score_threshold=0.0)
        ann_chunk_ids = set([r["chunk_id"] for r in ann_results])
        # 4.5 Graph Search (Optional)
        graph_chunk_ids = set()
        graph_metadata = None
        if enable_graph:
            graph_results = await self.graph_strategy.search(kb_id, query, top_k=top_k * 3, **kwargs)
            
            # Filter dummy results and capture metadata
            real_graph_results = []
            for res in graph_results:
                if res.get("chunk_id") == "GRAPH_METADATA_ONLY":
                    # Capture metadata from dummy result
                    if "graph_metadata" in res:
                        graph_metadata = res["graph_metadata"]
                else:
                    real_graph_results.append(res)
                    # Capture metadata from real result if first result
                    if "graph_metadata" in res:
                        graph_metadata = res["graph_metadata"]
            
            graph_chunk_ids = set([r["chunk_id"] for r in real_graph_results])
        
        # 5. Union of results
        combined_indices = set()
        chunk_id_to_idx = {doc["chunk_id"]: idx for idx, doc in enumerate(all_docs)}
        
        combined_indices.update(top_bm25_indices)
        for chunk_id in ann_chunk_ids:
            if chunk_id in chunk_id_to_idx:
                combined_indices.add(chunk_id_to_idx[chunk_id])
        
        for chunk_id in graph_chunk_ids:
            if chunk_id in chunk_id_to_idx:
                combined_indices.add(chunk_id_to_idx[chunk_id])
                
        # 6. Recalculate Scores (Cosine)
        final_results = []
        for idx in combined_indices:
            doc = all_docs[idx]
            chunk_vector = doc.get("vector")
            cosine_score = 0.0
            if chunk_vector:
                cosine_score = self._cosine_similarity(query_vec, chunk_vector)
            
            # Boost score if found in graph?
            # For now, just rely on the fact that it was included in the candidate set.
            # Reranker can handle the final ordering better.
            
            if cosine_score < score_threshold:
                continue
            
            final_results.append({
                "chunk_id": doc["chunk_id"],
                "content": doc["content"],
                "score": cosine_score,
                "metadata": {"doc_id": doc["doc_id"]}
            })
            
        final_results.sort(key=lambda x: x["score"], reverse=True)
        
        # Attach graph metadata to first result if available
        if final_results and graph_metadata:
            final_results[0]["graph_metadata"] = graph_metadata
            
        return final_results[:top_k]

    def _cosine_similarity(self, vec1, vec2) -> float:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))
