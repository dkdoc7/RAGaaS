from fastapi import APIRouter, Depends, HTTPException
from app.schemas import RetrievalRequest, RetrievalResult
from app.services.retrieval import retrieval_service
from typing import List

router = APIRouter()

@router.post("/{kb_id}/retrieve", response_model=List[RetrievalResult])
async def retrieve_chunks(
    kb_id: str,
    request: RetrievalRequest
):
    results = []
    if request.strategy == "keyword":
        results = await retrieval_service.search_keyword(kb_id, request.query, request.top_k)
    elif request.strategy == "2-stage":
        results = await retrieval_service.search_2stage(kb_id, request.query, request.top_k)
    else: # Default to ANN
        results = await retrieval_service.search_ann(kb_id, request.query, request.top_k, request.score_threshold)
        
    return results
