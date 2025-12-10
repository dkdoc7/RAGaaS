from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum

class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    chunking_strategy: str = "size"
    chunking_config: dict = {}
    enable_graph_rag: bool = False
    graph_config: Optional[dict] = None

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBase(KnowledgeBaseBase):
    id: str
    created_at: datetime
    updated_at: datetime
    document_count: Optional[int] = 0
    total_size: Optional[int] = 0

    class Config:
        from_attributes = True

class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"

class DocumentBase(BaseModel):
    filename: str
    file_type: str

class Document(DocumentBase):
    id: str
    kb_id: str
    status: DocumentStatus
    created_at: datetime

    class Config:
        from_attributes = True

class RetrievalRequest(BaseModel):
    query: str
    top_k: int = 5
    score_threshold: float = 0.5
    strategy: str = "ann"  # keyword, ann, hybrid, 2-stage
    use_reranker: bool = False
    reranker_top_k: int = 5
    reranker_threshold: float = 0.0
    use_llm_reranker: bool = False  # Use LLM instead of Cross-Encoder
    llm_chunk_strategy: str = "full"  # full, smart, limited (1500 chars)
    use_ner: bool = False  # Named Entity Recognition filter
    # Graph RAG options
    use_graph_search: bool = False
    vector_weight: float = 0.6
    graph_weight: float = 0.4
    normalization_method: str = "minmax"  # minmax or zscore
    merge_strategy: str = "hybrid"  # graph_only, hybrid
    enable_adaptive_weights: bool = True
    max_hops: int = 2  # Maximum graph traversal hops (1-3)


class RetrievalResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: dict
