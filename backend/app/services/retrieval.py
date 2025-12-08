from app.core.milvus import create_collection
from app.services.embedding import embedding_service
from typing import List, Dict
from sentence_transformers import CrossEncoder
from rank_bm25 import BM25Okapi
import asyncio
import numpy as np

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
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

    async def search_ann(self, kb_id: str, query: str, top_k: int = 5, score_threshold: float = 0.0, metric_type: str = "L2") -> List[Dict]:
        collection = create_collection(kb_id)
        collection.load()

        # 1. Embed query
        query_vectors = await embedding_service.get_embeddings([query])
        query_vec = query_vectors[0]
        
        # 2. Search (fetch more candidates to ensure we have enough after threshold filtering)
        search_params = {
            "metric_type": metric_type,
            "params": {"nprobe": 10},
        }
        
        results = collection.search(
            data=query_vectors, 
            anns_field="vector", 
            param=search_params, 
            limit=top_k * 3,  # Fetch 3x to allow for filtering
            output_fields=["content", "doc_id", "chunk_id", "vector"]  # Include vector for cosine calculation
        )
        
        retrieved = []
        for hits in results:
            for hit in hits:
                # Always compute cosine similarity for unified scoring
                chunk_vector = hit.entity.get("vector")
                if chunk_vector:
                    cosine_score = self._cosine_similarity(query_vec, chunk_vector)
                else:
                    # Fallback if vector not available
                    cosine_score = 0.0
                
                # Apply threshold filter
                if cosine_score < score_threshold:
                    continue
                
                retrieved.append({
                    "chunk_id": hit.entity.get("chunk_id"),
                    "content": hit.entity.get("content"),
                    "score": cosine_score,
                    "metadata": {"doc_id": hit.entity.get("doc_id")}
                })
        
        # Sort by cosine score and return top_k
        retrieved.sort(key=lambda x: x["score"], reverse=True)
        return retrieved[:top_k]

    async def search_2stage(self, kb_id: str, query: str, top_k: int = 5, metric_type: str = "L2", score_threshold: float = 0.0) -> List[Dict]:
        # 1. Candidate Generation (ANN) - Fetch more candidates
        # Get vectors for cosine calculation later
        collection = create_collection(kb_id)
        collection.load()
        
        query_vectors = await embedding_service.get_embeddings([query])
        query_vec = query_vectors[0]
        
        search_params = {
            "metric_type": metric_type,
            "params": {"nprobe": 10},
        }
        
        results = collection.search(
            data=query_vectors, 
            anns_field="vector", 
            param=search_params, 
            limit=top_k * 5,  # Fetch 5x candidates
            output_fields=["content", "doc_id", "chunk_id", "vector"]
        )
        
        candidates = []
        for hits in results:
            for hit in hits:
                candidates.append({
                    "chunk_id": hit.entity.get("chunk_id"),
                    "content": hit.entity.get("content"),
                    "metadata": {"doc_id": hit.entity.get("doc_id")},
                    "vector": hit.entity.get("vector")
                })
        
        if not candidates:
            return []

        # 2. Reranking with Cross-Encoder (for ordering only)
        reranker = self._get_reranker()
        
        pairs = [[query, doc["content"]] for doc in candidates]
        cross_scores = reranker.predict(pairs)
        
        # Sort by Cross-Encoder score
        for i, doc in enumerate(candidates):
            doc["cross_score"] = float(cross_scores[i])
        
        candidates.sort(key=lambda x: x["cross_score"], reverse=True)
        
        # 3. Compute cosine similarity for final scoring and filtering
        filtered = []
        for doc in candidates:
            chunk_vector = doc.get("vector")
            if chunk_vector:
                cosine_score = self._cosine_similarity(query_vec, chunk_vector)
            else:
                cosine_score = 0.0
            
            # Calculate cosine for all candidates first
            doc["score"] = cosine_score
            doc.pop("vector", None)
            doc.pop("cross_score", None)
            filtered.append(doc)
        
        # Filter by threshold (keep Cross-Encoder ranking order)
        filtered = [doc for doc in filtered if doc["score"] >= score_threshold]
        
        return filtered[:top_k]

    async def search_keyword(self, kb_id: str, query: str, top_k: int = 5, score_threshold: float = 0.0) -> List[Dict]:
        collection = create_collection(kb_id)
        collection.load()
        
        # Embed query for cosine calculation
        query_vectors = await embedding_service.get_embeddings([query])
        query_vec = query_vectors[0]
        
        # Milvus query with wildcards
        expr = f'content like "%{query}%"'
        
        results = collection.query(
            expr=expr,
            output_fields=["content", "doc_id", "chunk_id", "vector"],
            limit=top_k * 3  # Fetch more to allow filtering
        )
        
        retrieved = []
        for hit in results:
            # Compute cosine similarity
            chunk_vector = hit.get("vector")
            if chunk_vector:
                cosine_score = self._cosine_similarity(query_vec, chunk_vector)
            else:
                cosine_score = 0.0
            
            # Apply threshold
            if cosine_score < score_threshold:
                continue
            
            retrieved.append({
                "chunk_id": hit.get("chunk_id"),
                "content": hit.get("content"),
                "score": cosine_score,
                "metadata": {"doc_id": hit.get("doc_id")}
            })
        
        # Sort by cosine score
        retrieved.sort(key=lambda x: x["score"], reverse=True)
        return retrieved[:top_k]

    async def search_hybrid(self, kb_id: str, query: str, top_k: int = 5, metric_type: str = "COSINE", score_threshold: float = 0.0) -> List[Dict]:
        """
        Hybrid search combining BM25 (keyword-based) and ANN (vector-based) search.
        Final scoring uses cosine similarity.
        """
        collection = create_collection(kb_id)
        collection.load()
        
        # Embed query for cosine calculation
        query_vectors = await embedding_service.get_embeddings([query])
        query_vec = query_vectors[0]
        
        # Fetch all documents from collection for BM25 indexing
        all_docs = collection.query(
            expr="chunk_id != ''",  # Get all documents
            output_fields=["content", "doc_id", "chunk_id", "vector"],
            limit=10000  # Adjust based on your dataset size
        )
        
        if not all_docs:
            return []
        
        # Prepare BM25 index
        corpus = [doc["content"] for doc in all_docs]
        tokenized_corpus = [content.lower().split() for content in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        
        # 1. BM25 Search - use as retrieval method
        tokenized_query = query.lower().split()
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # Get top candidates from BM25
        bm25_candidates = []
        for idx, score in enumerate(bm25_scores):
            if score > 0:  # Only include documents with some relevance
                bm25_candidates.append({
                    "idx": idx,
                    "bm25_score": float(score)
                })
        
        # Sort by BM25 score
        bm25_candidates.sort(key=lambda x: x["bm25_score"], reverse=True)
        top_bm25_indices = set([c["idx"] for c in bm25_candidates[:top_k * 3]])
        
        # 2. ANN Search - use as retrieval method (without threshold)
        ann_results = await self.search_ann(kb_id, query, top_k=top_k * 3, metric_type=metric_type, score_threshold=0.0)
        ann_chunk_ids = set([r["chunk_id"] for r in ann_results])
        
        # 3. Combine: get union of both methods
        combined_indices = set()
        chunk_id_to_idx = {doc["chunk_id"]: idx for idx, doc in enumerate(all_docs)}
        
        # Add BM25 results
        combined_indices.update(top_bm25_indices)
        
        # Add ANN results
        for chunk_id in ann_chunk_ids:
            if chunk_id in chunk_id_to_idx:
                combined_indices.add(chunk_id_to_idx[chunk_id])
        
        # 4. Compute cosine similarity for all combined results
        final_results = []
        for idx in combined_indices:
            doc = all_docs[idx]
            chunk_vector = doc.get("vector")
            
            if chunk_vector:
                cosine_score = self._cosine_similarity(query_vec, chunk_vector)
            else:
                cosine_score = 0.0
            
            # Apply threshold
            if cosine_score < score_threshold:
                continue
            
            final_results.append({
                "chunk_id": doc["chunk_id"],
                "content": doc["content"],
                "score": cosine_score,
                "metadata": {"doc_id": doc["doc_id"]}
            })
        
        # Sort by cosine similarity
        final_results.sort(key=lambda x: x["score"], reverse=True)
        
        return final_results[:top_k]

retrieval_service = RetrievalService()
