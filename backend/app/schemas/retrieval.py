from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
    score_threshold: float = 0.5
    strategy: str = "ann"  # keyword, ann, hybrid, 2-stage
    
    # Reranking
    use_reranker: bool = False
    reranker_top_k: int = 5
    reranker_threshold: float = 0.0
    use_llm_reranker: bool = False
    llm_chunk_strategy: str = "full"
    
    # Filters
    use_ner: bool = False
    
    # Graph RAG (Placeholder for future ext)
    # enable_graph: bool = False

class RetrievalResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: Dict[str, Any] = {}
