from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum

class KnowledgeBaseBase(BaseModel):
    name: str
    description: Optional[str] = None
    chunking_strategy: str = "size"
    chunking_config: dict = {}
    metric_type: str = "COSINE"  # COSINE or IP

class KnowledgeBaseCreate(KnowledgeBaseBase):
    pass

class KnowledgeBase(KnowledgeBaseBase):
    id: str
    created_at: datetime
    updated_at: datetime

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
    strategy: str = "ann" # keyword, ann, hybrid, 2-stage

class RetrievalResult(BaseModel):
    chunk_id: str
    content: str
    score: float
    metadata: dict
