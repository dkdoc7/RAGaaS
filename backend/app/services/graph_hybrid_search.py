"""
Graph RAG Hybrid Search Implementation

This module implements the hybrid search combining:
1. Vector search (Milvus)  
2. Graph search (Fuseki)
3. Score normalization (min-max or z-score)
4. Adaptive weight adjustment
5. Three merge strategies (weighted_sum, top_n_boost, score_fusion)
"""

import numpy as np
import logging
from typing import List, Dict, Optional
from app.services.graph_service import graph_service
from app.services.ner import ner_service

logger = logging.getLogger(__name__)


class GraphHybridSearch:
    def __init__(self):
        pass
    
    def normalize_minmax(self, scores: List[float]) -> List[float]:
        """Min-max normalization to [0, 1]"""
        if len(scores) == 0:
            return []
        if len(scores) == 1:
            return [1.0]
        
        min_s = min(scores)
        max_s = max(scores)
        
        if max_s == min_s:
            return [1.0] * len(scores)
        
        return [(s - min_s) / (max_s - min_s) for s in scores]
    
    def normalize_zscore(self, scores: List[float]) -> List[float]:
        """Z-score normalization, clipped to [0, 1]"""
        if len(scores) < 2:
            return [0.5] * len(scores)
        
        mean = np.mean(scores)
        std = np.std(scores)
        
        if std == 0:
            return [0.5] * len(scores)
        
        # Normalize to z-scores
        z_scores = [(s - mean) / std for s in scores]
        
        # Simple sigmoid to map to [0, 1]
        normalized = [1 / (1 + np.exp(-z)) for z in z_scores]
        
        return normalized
    
    def adjust_weights_adaptively(
        self,
        query: str,
        graph_result_count: int,
        base_vector_weight: float,
        base_graph_weight: float,
        adaptive_rules: Dict
    ) -> tuple:
        """
        Adjust weights based on graph results and query content
        
        Returns:
            (vector_weight, graph_weight) tuple
        """
        min_results = adaptive_rules.get("min_graph_results", 3)
        fallback_v_weight = adaptive_rules.get("fallback_vector_weight", 0.9)
        fallback_g_weight = adaptive_rules.get("fallback_graph_weight", 0.1)
        relation_keywords = adaptive_rules.get("relation_keywords", ["관계", "연결", "사이"])
        relation_v_weight = adaptive_rules.get("relation_vector_weight", 0.4)
        relation_g_weight = adaptive_rules.get("relation_graph_weight", 0.6)
        
        # Check for relation keywords
        has_relation_keywords = any(kw in query for kw in relation_keywords)
        
        if graph_result_count == 0:
            # Complete fallback to vector
            return 1.0, 0.0
        elif graph_result_count < min_results:
            # Insufficient graph data
            return fallback_v_weight, fallback_g_weight
        elif has_relation_keywords:
            # Relation-focused query
            return relation_v_weight, relation_g_weight
        else:
            # Use base weights
            return base_vector_weight, base_graph_weight
    
    async def search_graph_hybrid(
        self,
        kb_id: str,
        query: str,
        vector_results: List[Dict],
        top_k: int = 5,
        vector_weight: float = 0.6,
        graph_weight: float = 0.4,
        normalization_method: str = "minmax",
        merge_strategy: str = "weighted_sum",
        enable_adaptive_weights: bool = True,
        graph_config: Optional[Dict] = None,
        max_hops: Optional[int] = None
    ) -> List[Dict]:
        """
        Perform hybrid search combining vector and graph results
        
        Args:
            kb_id: Knowledge base ID
            query: User query
            vector_results: Results from vector search (with 'chunk_id' and 'score')
            top_k: Number of final results to return
            vector_weight: Weight for vector scores
            graph_weight: Weight for graph scores
            normalization_method: "minmax" or "zscore"
            merge_strategy: "weighted_sum", "top_n_boost", or "score_fusion"
            enable_adaptive_weights: Whether to adjust weights adaptively
            graph_config: Graph RAG configuration
            
        Returns:
            List of results with final scores and metadata
        """
        if not graph_config:
            # Graph RAG not enabled, return vector results as-is
            return vector_results[:top_k]
        
        # Extract entities and keywords from query
        entities = ner_service.extract_entities(query)
        keywords = ner_service.extract_keywords(query)
        
        if not entities:
            logger.info("No entities found in query, skipping graph search")
            return vector_results[:top_k]
        
        # Log extracted entities and keywords
        logger.info(f"[Graph RAG] Query: '{query}'")
        logger.info(f"[Graph RAG] Extracted entities: {entities}")
        logger.info(f"[Graph RAG] Extracted keywords: {keywords}")
        
        # Get graph configuration
        if max_hops is None:
            max_hops = graph_config.get("max_hops", 2)
        
        expansion_limit = graph_config.get("expansion_limit", 50)
        
        logger.info(f"[Graph RAG] Config: max_hops={max_hops}, expansion_limit={expansion_limit}")
        
        # Perform graph search
        graph_results = await graph_service.search_by_entities(
            kb_id=kb_id,
            entity_names=entities,
            max_hops=max_hops,
            expansion_limit=expansion_limit,
            relation_keywords=list(keywords)
        )
        
        logger.info(f"Graph search found {len(graph_results)} results")
        
        # Adaptive weight adjustment
        if enable_adaptive_weights and graph_config.get("adaptive_fallback_rules"):
            rules = graph_config["adaptive_fallback_rules"]
            vector_weight, graph_weight = self.adjust_weights_adaptively(
                query=query,
                graph_result_count=len(graph_results),
                base_vector_weight=vector_weight,
                base_graph_weight=graph_weight,
                adaptive_rules=rules
            )
            logger.info(f"Adjusted weights: vector={vector_weight}, graph={graph_weight}")
        
        # Normalize scores
        if normalization_method == "zscore":
            normalize_fn = self.normalize_zscore
        else:  # minmax
            normalize_fn = self.normalize_minmax
        
        # Normalize vector scores
        vector_scores = [r.get("score", 0.0) for r in vector_results]
        norm_vector_scores = normalize_fn(vector_scores)
        
        for i, result in enumerate(vector_results):
            result["normalized_score"] = norm_vector_scores[i]
        
        # Normalize graph scores (distance-based, invert so closer = higher)
        if graph_results:
            # Convert distance to score (max_hops - distance) / max_hops
            graph_scores = [(max_hops - r.get("distance", 0)) / max_hops for r in graph_results]
            norm_graph_scores = normalize_fn(graph_scores)
            
            for i, result in enumerate(graph_results):
                result["normalized_score"] = norm_graph_scores[i]
        
        # Apply merge strategy
        # Apply merge strategy
        if merge_strategy == "graph_only":
            final_results = self._merge_graph_only(
                vector_results, graph_results, vector_weight, graph_weight, top_k, kb_id
            )
        else:
            # Default to "hybrid" (weighted sum)
            if merge_strategy != "hybrid":
                logger.warning(f"Unknown merge strategy '{merge_strategy}', defaulting to hybrid")
                
            final_results = self._merge_hybrid(
                vector_results, graph_results, vector_weight, graph_weight, top_k, kb_id
            )
        
        # Add metadata
        for result in final_results:
            # Move graph-specific fields to metadata
            if 'metadata' not in result:
                result['metadata'] = {}
            
            # Store graph RAG info in metadata
            result['metadata']['applied_weights'] = {
                "vector": vector_weight,
                "graph": graph_weight
            }
            
            # Move score breakdown to metadata if present
            if 'vector_score' in result:
                result['metadata']['vector_score'] = result.pop('vector_score')
            if 'graph_score' in result:
                result['metadata']['graph_score'] = result.pop('graph_score')
            if 'source' in result:
                result['metadata']['source'] = result.pop('source')
            if 'graph_distance' in result:
                result['metadata']['graph_distance'] = result.pop('graph_distance')
            if 'final_score' in result:
                # Replace score with final_score
                result['score'] = result.pop('final_score')
        
        # Debug: Check schema
        if final_results:
            sample = final_results[0]
            logger.info(f"Sample result keys: {list(sample.keys())}")
            logger.info(f"Sample metadata keys: {list(sample.get('metadata', {}).keys())}")
        
        return final_results
    
    def _merge_graph_only(
        self,
        vector_results: List[Dict],
        graph_results: List[Dict],
        vector_weight: float,
        graph_weight: float,
        top_k: int,
        kb_id: str
    ) -> List[Dict]:
        """
        Graph Only Strategy:
        Return ONLY results found in Graph search.
        If a chunk is also in vector results, combine scores.
        If a chunk is ONLY in graph results, fetch content from Milvus.
        """
        if not graph_results:
            return []
            
        combined = {}
        
        # Index vector results for quick lookup
        vector_map = {r["chunk_id"]: r for r in vector_results}
        
        # Process graph results
        for g_result in graph_results:
            chunk_id = g_result.get("chunk_id")
            g_score = g_result.get("normalized_score", 0.0)
            distance = g_result.get("distance", 0)
            
            if chunk_id in vector_map:
                # Also found in vector search
                v_result = vector_map[chunk_id]
                v_score = v_result.get("normalized_score", 0.0)
                
                combined[chunk_id] = {
                    **v_result,
                    "vector_score": v_score,
                    "graph_score": g_score,
                    "final_score": (vector_weight * v_score) + (graph_weight * g_score),
                    "source": "hybrid",
                    "graph_distance": distance
                }
            else:
                # Graph only - need to fetch content
                # We defer fetching content until we sort and slice to avoid unnecessary queries
                combined[chunk_id] = {
                    "chunk_id": chunk_id,
                    "vector_score": 0.0,
                    "graph_score": g_score,
                    "final_score": graph_weight * g_score,
                    "source": "graph",
                    "graph_distance": distance,
                    "needs_fetch": True
                }
        
        # Sort by final score
        sorted_results = sorted(combined.values(), key=lambda x: x["final_score"], reverse=True)
        top_results = sorted_results[:top_k]
        
        # Fetch content for missing chunks
        chunks_to_fetch = [r["chunk_id"] for r in top_results if r.get("needs_fetch")]
        
        if chunks_to_fetch:
            from app.core.milvus import create_collection
            collection = create_collection(kb_id)
            collection.load()
            
            # Batch query for efficiency
            expr = f'chunk_id in {str(chunks_to_fetch).replace("[", "(").replace("]", ")")}'
            # Fix for single item tuple string formatting
            if len(chunks_to_fetch) == 1:
                expr = f'chunk_id == "{chunks_to_fetch[0]}"'

            try:
                query_results = collection.query(
                    expr=expr,
                    output_fields=["chunk_id", "content", "doc_id", "metadata"]
                )
                
                # Map fetched content
                content_map = {r["chunk_id"]: r for r in query_results}
                
                # Update results
                for result in top_results:
                    if result.get("needs_fetch"):
                        fetched = content_map.get(result["chunk_id"], {})
                        result["content"] = fetched.get("content", "")
                        result["metadata"] = fetched.get("metadata", {})
                        if not result["metadata"]:
                            result["metadata"] = {"doc_id": fetched.get("doc_id", "")}
                        del result["needs_fetch"]
                        
            except Exception as e:
                logger.error(f"Error fetching chunks from Milvus: {e}")
                
        return top_results

    def _merge_hybrid(
        self,
        vector_results: List[Dict],
        graph_results: List[Dict],
        vector_weight: float,
        graph_weight: float,
        top_k: int,
        kb_id: str
    ) -> List[Dict]:
        """
        Hybrid Strategy (Weighted Sum):
        Combine all results from both Vector and Graph searches.
        Score = (Vector Weight * V_Score) + (Graph Weight * G_Score)
        Missing scores are treated as 0.
        """
        combined = {}
        
        # 1. Add Vector Results
        for result in vector_results:
            chunk_id = result.get("chunk_id")
            norm_score = result.get("normalized_score", 0.0)
            
            combined[chunk_id] = {
                **result,
                "vector_score": norm_score,
                "graph_score": 0.0,
                "final_score": vector_weight * norm_score,
                "source": "vector"
            }
            
        # 2. Add/Merge Graph Results
        for result in graph_results:
            chunk_id = result.get("chunk_id")
            norm_score = result.get("normalized_score", 0.0)
            distance = result.get("distance", 0)
            
            if chunk_id in combined:
                # Overlap
                combined[chunk_id]["graph_score"] = norm_score
                combined[chunk_id]["final_score"] += graph_weight * norm_score
                combined[chunk_id]["source"] = "hybrid"
                combined[chunk_id]["graph_distance"] = distance
            else:
                # Graph only
                combined[chunk_id] = {
                    "chunk_id": chunk_id,
                    "vector_score": 0.0,
                    "graph_score": norm_score,
                    "final_score": graph_weight * norm_score,
                    "source": "graph",
                    "graph_distance": distance,
                    "needs_fetch": True
                }
        
        # Sort by final score
        sorted_results = sorted(combined.values(), key=lambda x: x["final_score"], reverse=True)
        top_results = sorted_results[:top_k]
        
        # Fetch content for missing chunks
        chunks_to_fetch = [r["chunk_id"] for r in top_results if r.get("needs_fetch")]
        
        if chunks_to_fetch:
            from app.core.milvus import create_collection
            collection = create_collection(kb_id)
            collection.load()
            
            # Batch query for efficiency
            expr = f'chunk_id in {str(chunks_to_fetch).replace("[", "(").replace("]", ")")}'
            if len(chunks_to_fetch) == 1:
                expr = f'chunk_id == "{chunks_to_fetch[0]}"'

            try:
                query_results = collection.query(
                    expr=expr,
                    output_fields=["chunk_id", "content", "doc_id", "metadata"]
                )
                
                # Map fetched content
                content_map = {r["chunk_id"]: r for r in query_results}
                
                # Update results
                for result in top_results:
                    if result.get("needs_fetch"):
                        fetched = content_map.get(result["chunk_id"], {})
                        result["content"] = fetched.get("content", "")
                        result["metadata"] = fetched.get("metadata", {})
                        if not result["metadata"]:
                            result["metadata"] = {"doc_id": fetched.get("doc_id", "")}
                        del result["needs_fetch"]
                        
            except Exception as e:
                logger.error(f"Error fetching chunks from Milvus for hybrid search: {e}")
        
        return top_results


# Singleton instance
graph_hybrid_search = GraphHybridSearch()
