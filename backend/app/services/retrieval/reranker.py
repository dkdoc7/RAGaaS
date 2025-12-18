from typing import List, Dict, Any, Optional
from app.services.embedding import embedding_service
from sentence_transformers import CrossEncoder # type: ignore
import numpy as np
import math

class RerankingService:
    def __init__(self):
        self.reranker = None
    
    def _get_reranker(self):
        if not self.reranker:
            self.reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
        return self.reranker
        
    def _cosine_similarity(self, vec1, vec2) -> float:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))

    async def rerank_results(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 5,
        threshold: float = 0.0
    ) -> List[Dict]:
        """Rerank using Cross-Encoder"""
        if not results:
            return []
            
        reranker = self._get_reranker()
        pairs = [[query, result['content']] for result in results]
        reranker_scores = reranker.predict(pairs)
        
        # Sigmoid normalization
        normalized_scores = [1 / (1 + math.exp(-score)) for score in reranker_scores]
        
        for result, score in zip(results, normalized_scores):
            result['_reranker_score'] = float(score)
            
        filtered = [r for r in results if r['_reranker_score'] >= threshold]
        filtered.sort(key=lambda x: x['_reranker_score'], reverse=True)
        top_results = filtered[:top_k]
        
        # Reset score to Cosine for uniformity
        # Need embeddings for cosine
        query_vec = (await embedding_service.get_embeddings([query]))[0]
        
        for result in top_results:
            content_vec = (await embedding_service.get_embeddings([result['content']]))[0]
            result['score'] = self._cosine_similarity(query_vec, content_vec)
            
            if 'metadata' not in result: result['metadata'] = {}
            result['metadata']['_reranker_score'] = result.pop('_reranker_score')
            
        return top_results

    async def llm_rerank_results(
        self,
        query: str,
        results: List[Dict],
        top_k: int = 5,
        threshold: float = 0.0,
        strategy: str = "full"
    ) -> List[Dict]:
        """Rerank using LLM (OpenAI)"""
        if not results:
            return []
            
        from openai import AsyncOpenAI
        from app.core.config import settings
        import asyncio
        
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        
        async def evaluate(result: Dict) -> tuple[Dict, float]:
            chunk_content = result['content']
            
            # Simple truncation for brevity in prompt (implement 'smart' logic if needed from original)
            if strategy == 'limited':
                chunk_content = chunk_content[:1500]
            
            prompt = f"""Query: {query}\n\nChunk: {chunk_content}\n\nRate relevance from 0.0 to 1.0 (float). Output ONLY the number."""
            
            try:
                resp = await client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0, max_tokens=10
                )
                score = float(resp.choices[0].message.content.strip())
                return (result, max(0.0, min(1.0, score)))
            except:
                return (result, 0.0)
                
        tasks = [evaluate(r) for r in results]
        evaluated = await asyncio.gather(*tasks)
        
        for result, score in evaluated:
            result['_llm_score'] = score
            if 'metadata' not in result: result['metadata'] = {}
            result['metadata']['_llm_reranker_score'] = score
            
        filtered = [r for r in results if r.get('_llm_score', 0) >= threshold]
        filtered.sort(key=lambda x: x.get('_llm_score', 0), reverse=True)
        
        # Cleanup
        for r in filtered:
            r.pop('_llm_score', None)
            
        return filtered[:top_k]

reranking_service = RerankingService()
