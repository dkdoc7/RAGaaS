from fastapi import APIRouter, Depends, HTTPException
from app.schemas import RetrievalRequest, RetrievalResult
from app.services.retrieval import retrieval_service
from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

router = APIRouter()

@router.post("/{kb_id}/retrieve", response_model=List[RetrievalResult])
async def retrieve_chunks(
    kb_id: str,
    request: RetrievalRequest,
    db: AsyncSession = Depends(get_db)
):
    # Fetch KB to get metric_type
    from app.models.knowledge_base import KnowledgeBase
    result = await db.execute(select(KnowledgeBase).filter(KnowledgeBase.id == kb_id))
    kb = result.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
        
    metric_type = kb.metric_type or "COSINE"

    results = []
    if request.strategy == "keyword":
        results = await retrieval_service.search_keyword(kb_id, request.query, request.top_k, request.score_threshold)
    elif request.strategy == "2-stage":
        results = await retrieval_service.search_2stage(kb_id, request.query, request.top_k, metric_type=metric_type, score_threshold=request.score_threshold)
    elif request.strategy == "hybrid":
        results = await retrieval_service.search_hybrid(kb_id, request.query, request.top_k, metric_type=metric_type, score_threshold=request.score_threshold)
    else: # Default to ANN
        results = await retrieval_service.search_ann(kb_id, request.query, request.top_k, request.score_threshold, metric_type=metric_type)
    
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
        
    return results
