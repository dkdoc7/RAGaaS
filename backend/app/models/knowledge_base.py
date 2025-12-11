from sqlalchemy import Column, String, DateTime, Boolean
from sqlalchemy.dialects.sqlite import JSON
from app.core.database import Base
import uuid
from datetime import datetime

class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    description = Column(String, nullable=True)
    chunking_strategy = Column(String, default="size")
    chunking_config = Column(JSON, default={})
    metric_type = Column(String, default="COSINE")  # COSINE or IP
    enable_graph_rag = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
