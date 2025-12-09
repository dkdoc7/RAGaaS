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

    async def rerank_results(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 5,
        threshold: float = 0.0
    ) -> List[Dict]:
        """
        Rerank results using Cross-Encoder but preserve cosine similarity scores.
        
        Args:
            query: Search query
            results: List of initial search results
            top_k: Number of results to return after reranking
            threshold: Minimum reranker score threshold (0-1) for filtering
        
        Returns:
            Results reranked by Cross-Encoder but with cosine similarity scores
        """
        if not results:
            return []
        
        # Get reranker model
        reranker = self._get_reranker()
        
        # Prepare query-document pairs for reranking
        pairs = [[query, result['content']] for result in results]
        
        # Get reranker scores (-inf to +inf range)
        reranker_scores = reranker.predict(pairs)
        
        # Normalize reranker scores to 0-1 using sigmoid for filtering
        import math
        normalized_scores = [1 / (1 + math.exp(-score)) for score in reranker_scores]
        
        # Attach reranker scores temporarily for filtering and sorting
        for result, reranker_score in zip(results, normalized_scores):
            result['_reranker_score'] = float(reranker_score)
        
        # Filter by reranker threshold
        filtered_results = [r for r in results if r['_reranker_score'] >= threshold]
        
        # Sort by reranker score (descending)
        filtered_results.sort(key=lambda x: x['_reranker_score'], reverse=True)
        
        # Get top-k
        top_results = filtered_results[:top_k]
        
        # Now recalculate cosine similarity for final scores
        # Get query embedding
        query_embeddings = await embedding_service.get_embeddings([query])
        query_vec = query_embeddings[0]
        
        # Calculate cosine similarity for each result
        for result in top_results:
            # Get chunk embedding from result (should be available from initial search)
            # If not available, we need to re-embed
            content = result['content']
            content_embeddings = await embedding_service.get_embeddings([content])
            content_vec = content_embeddings[0]
            
            # Calculate cosine similarity
            cosine_score = self._cosine_similarity(query_vec, content_vec)
            
            # Store reranker score in metadata before replacing
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['_reranker_score'] = result['_reranker_score']
            
            # Set final score to cosine similarity
            result['score'] = cosine_score
            
            # Remove temporary reranker score from top level
            result.pop('_reranker_score', None)
        
        # Results are already sorted by reranker score
        # We keep that order but show cosine similarity scores
        return top_results

    async def llm_rerank_results(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 5,
        threshold: float = 0.0
    ) -> List[Dict]:
        """
        Rerank results using LLM (OpenAI) for more accurate relevance evaluation.
        
        Args:
            query: Search query
            results: List of initial search results
            top_k: Number of results to return after reranking
            threshold: Minimum relevance score threshold (0-1)
        
        Returns:
            Results reranked by LLM with relevance scores
        """
        if not results:
            return []
        
        from openai import AsyncOpenAI
        from app.core.config import settings
        import asyncio
        
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Prepare prompts for parallel evaluation
        async def evaluate_relevance(result: Dict) -> tuple[Dict, float]:
            # Prepare chunk based on strategy
            from app.services.ner import ner_service
            
            chunk_content = result['content']
            strategy = getattr(self, '_llm_chunk_strategy', 'full')
            
            if strategy == 'limited':
                # Method 1: 1500 character limit
                chunk_content = chunk_content[:1500]
                if len(result['content']) > 1500:
                    chunk_content += "..."
                    
            elif strategy == 'smart':
                # Method 2: Smart truncation - extract entities and surrounding context
                if len(chunk_content) > 1000:
                    # Extract entities from query
                    query_entities = ner_service.extract_entities(query)
                    
                    if query_entities:
                        # Find entity positions in chunk
                        snippets = []
                        for entity in query_entities:
                            pos = chunk_content.find(entity)
                            if pos != -1:
                                # Extract ±300 chars around entity
                                start = max(0, pos - 300)
                                end = min(len(chunk_content), pos + 300)
                                snippet = chunk_content[start:end]
                                if start > 0:
                                    snippet = "..." + snippet
                                if end < len(chunk_content):
                                    snippet = snippet + "..."
                                snippets.append(snippet)
                        
                        if snippets:
                            chunk_content = "\n\n".join(snippets)
                        else:
                            # No entities found, use beginning + middle
                            mid = len(chunk_content) // 2
                            chunk_content = chunk_content[:500] + "\n\n...\n\n" + chunk_content[mid-250:mid+250]
                    else:
                        # No entities in query, use beginning + middle
                        mid = len(chunk_content) // 2
                        chunk_content = chunk_content[:500] + "\n\n...\n\n" + chunk_content[mid-250:mid+250]
            
            # Method 3 (full) is already the default - use entire chunk_content
            
            prompt = f"""You are evaluating how well a text chunk answers a specific query.

Query: {query}

Text Chunk:
{chunk_content}

Scoring Guidelines:
- 1.0: Perfect match - chunk directly and completely answers the query with all requested information
- 0.8-0.9: Very relevant - chunk contains the answer but may include extra information
- 0.5-0.7: Partially relevant - chunk is related but doesn't fully answer the query
- 0.2-0.4: Weakly relevant - chunk is on the same topic but missing key information
- 0.0-0.1: Not relevant - chunk doesn't help answer the query

Important:
- If the query asks about a specific person/entity, the chunk MUST mention that exact person/entity to score above 0.5
- If the chunk answers the question completely, give a high score (0.8+) regardless of extra content

Output ONLY a single number between 0.0 and 1.0, nothing else."""

            
            try:
                response = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a relevance scoring assistant. Output only a single number between 0.0 and 1.0."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0,
                    max_tokens=10
                )
                
                score_text = response.choices[0].message.content.strip()
                llm_score = float(score_text)
                llm_score = max(0.0, min(1.0, llm_score))  # Clamp to 0-1
                
                print(f"[LLM Reranker] Score: {llm_score:.4f} for chunk: {result['content'][:50]}...")
                
                return (result, llm_score)
            except Exception as e:
                import traceback
                print(f"[LLM Reranker] ERROR: {str(e)}")
                print(f"[LLM Reranker] ERROR Type: {type(e).__name__}")
                print(f"[LLM Reranker] Traceback: {traceback.format_exc()}")
                return (result, 0.0)
        
        # Evaluate all results in parallel
        tasks = [evaluate_relevance(result) for result in results]
        evaluated = await asyncio.gather(*tasks)
        
        # Attach LLM scores to results
        for result, llm_score in evaluated:
            # Store LLM score in metadata
            if 'metadata' not in result:
                result['metadata'] = {}
            result['metadata']['_llm_reranker_score'] = llm_score
            
            # Use LLM score for sorting temporarily
            result['_llm_sort_score'] = llm_score
        
        # Filter by LLM threshold
        filtered_results = [r for r in results if r['_llm_sort_score'] >= threshold]
        
        # Sort by LLM score (descending)
        filtered_results.sort(key=lambda x: x['_llm_sort_score'], reverse=True)
        
        # Get top-k and clean up temporary score
        top_results = filtered_results[:top_k]
        for result in top_results:
            result.pop('_llm_sort_score', None)
        
        return top_results

retrieval_service = RetrievalService()
