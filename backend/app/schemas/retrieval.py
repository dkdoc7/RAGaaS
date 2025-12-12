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
    use_llm_keyword_extraction: bool = False
    
    # Graph Search
    enable_graph_search: bool = False
    graph_hops: int = 1
    
    # Brute Force
    use_brute_force: bool = False
    brute_force_top_k: int = 1
    brute_force_threshold: float = 1.5
    
    # Graph RAG
    enable_graph_search: bool = False
    graph_hops: int = 1

class RetrievalResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    l2_score: Optional[float] = None
    metadata: Dict[str, Any] = {}
    graph_metadata: Optional[Dict[str, Any]] = None
