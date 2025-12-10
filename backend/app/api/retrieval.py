from fastapi import APIRouter, Depends, HTTPException
from app.schemas import RetrievalRequest, RetrievalResult
from app.services.retrieval import retrieval_service
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.services.graph_hybrid_search import graph_hybrid_search

router = APIRouter()

@router.post("/{kb_id}/retrieve", response_model=List[RetrievalResult])
async def retrieve_chunks(
    kb_id: str,
    request: RetrievalRequest,
    db: AsyncSession = Depends(get_db)
):
    # Fetch KB to get configuration
    from app.models.knowledge_base import KnowledgeBase
    result = await db.execute(select(KnowledgeBase).filter(KnowledgeBase.id == kb_id))
    kb = result.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    # Always use COSINE metric
    metric_type = "COSINE"

    results = []
    if request.strategy == "keyword":
        results = await retrieval_service.search_keyword(kb_id, request.query, request.top_k, request.score_threshold)
    elif request.strategy == "2-stage":
        results = await retrieval_service.search_2stage(kb_id, request.query, request.top_k, metric_type=metric_type, score_threshold=request.score_threshold)
    elif request.strategy == "hybrid":
        results = await retrieval_service.search_hybrid(kb_id, request.query, request.top_k, metric_type=metric_type, score_threshold=request.score_threshold)
    else: # Default to ANN
        results = await retrieval_service.search_ann(kb_id, request.query, request.top_k, request.score_threshold, metric_type=metric_type)
    
    # Apply Graph RAG hybrid search if enabled
    if request.use_graph_search and kb.enable_graph_rag and results:
        print(f"[DEBUG] Applying Graph RAG hybrid search")
        print(f"[DEBUG] Vector results: {len(results)}, weights: v={request.vector_weight}, g={request.graph_weight}")
        
        try:
            results = await graph_hybrid_search.search_graph_hybrid(
                kb_id=kb_id,
                query=request.query,
                vector_results=results,
                top_k=request.top_k,
                vector_weight=request.vector_weight,
                graph_weight=request.graph_weight,
                normalization_method=request.normalization_method,
                merge_strategy=request.merge_strategy,
                enable_adaptive_weights=request.enable_adaptive_weights,
                graph_config=kb.graph_config,
                max_hops=request.max_hops
            )
            
            print(f"[DEBUG] After Graph RAG hybrid: {len(results)} results")
        except Exception as e:
            import traceback
            print(f"[ERROR] Graph RAG hybrid search failed: {e}")
            print(f"[ERROR] Traceback: {traceback.format_exc()}")
            # Continue with vector-only results
            print(f"[DEBUG] Continuing with vector-only results")
    
    # Apply optional reranking FIRST (not for 2-stage, which already uses Cross-Encoder)
    # Reranker should run before NER to ensure NER penalty is applied to final scores
    if request.use_reranker and request.strategy != "2-stage" and results:
        print(f"[DEBUG] Applying reranker: top_k={request.reranker_top_k}, threshold={request.reranker_threshold}")
        print(f"[DEBUG] LLM Reranker: {request.use_llm_reranker}")
        print(f"[DEBUG] Initial results count: {len(results)}")
        
        if request.use_llm_reranker:
            # Store strategy in service for access in llm_rerank_results
            retrieval_service._llm_chunk_strategy = request.llm_chunk_strategy
            # Use LLM for reranking
            results = await retrieval_service.llm_rerank_results(
                query=request.query,
                results=results,
                top_k=request.reranker_top_k,
                threshold=request.reranker_threshold
            )
        else:
            # Use Cross-Encoder for reranking
            results = await retrieval_service.rerank_results(
                query=request.query,
                results=results,
                top_k=request.reranker_top_k,
                threshold=request.reranker_threshold
            )
        
        print(f"[DEBUG] After reranking count: {len(results)}")
        if results:
            print(f"[DEBUG] Top result score: {results[0]['score']:.4f} (cosine similarity)")
    
    # Apply optional NER filtering AFTER reranking
    # This ensures NER penalty is applied to the final cosine similarity scores
    if request.use_ner and results:
        from app.services.ner import ner_service
        print(f"[DEBUG] Applying NER filter")
        print(f"[DEBUG] Results before NER: {len(results)}")
        results = ner_service.filter_by_entities(request.query, results, penalty=0.3)
        print(f"[DEBUG] Results after NER: {len(results)}")
    
    # Debug: Print result structure before return
    if results:
        print(f"[DEBUG] Final result count: {len(results)}")
        print(f"[DEBUG] Sample result keys: {list(results[0].keys())}")
        if 'metadata' in results[0]:
            print(f"[DEBUG] Sample metadata type: {type(results[0]['metadata'])}")
        
    return results
