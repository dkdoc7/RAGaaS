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
        results = await retrieval_service.search_keyword(kb_id, request.query, request.top_k)
    elif request.strategy == "2-stage":
        results = await retrieval_service.search_2stage(kb_id, request.query, request.top_k, metric_type=metric_type)
    else: # Default to ANN
        results = await retrieval_service.search_ann(kb_id, request.query, request.top_k, request.score_threshold, metric_type=metric_type)
        
    return results
