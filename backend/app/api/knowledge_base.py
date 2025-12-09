from fastapi import APIRouter, Depends, HTTPException
from pymilvus import Collection
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.models.knowledge_base import KnowledgeBase as KBModel
from app.schemas import KnowledgeBaseCreate, KnowledgeBase
from app.core.milvus import create_collection, utility, connect_milvus
from app.models.document import Document as DocModel
from sqlalchemy import delete

router = APIRouter()

@router.post("/", response_model=KnowledgeBase)
async def create_knowledge_base(kb: KnowledgeBaseCreate, db: AsyncSession = Depends(get_db)):
    db_kb = KBModel(
        name=kb.name, 
        description=kb.description,
        chunking_strategy=kb.chunking_strategy,
        chunking_config=kb.chunking_config,
        metric_type=kb.metric_type
    )
    db.add(db_kb)
    await db.commit()
    await db.refresh(db_kb)
    
    # Create Milvus collection
    try:
        create_collection(db_kb.id, metric_type=db_kb.metric_type)
    except Exception as e:
        # Rollback if Milvus fails? Or just log error?
        # For now, let's assume it works or we handle it later
        print(f"Failed to create Milvus collection: {e}")
        
    return db_kb

@router.get("/", response_model=List[KnowledgeBase])
async def list_knowledge_bases(skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    
    # Get KBs with document count
    result = await db.execute(
        select(
            KBModel,
            func.count(DocModel.id).label('document_count')
        )
        .outerjoin(DocModel, KBModel.id == DocModel.kb_id)
        .group_by(KBModel.id)
        .offset(skip)
        .limit(limit)
    )
    
    kbs_with_stats = []
    for row in result:
        kb = row[0]
        
        # Get Milvus collection stats
        collection_size = 0
        try:
            connect_milvus()
            collection_name = f"kb_{kb.id.replace('-', '_')}"
            if utility.has_collection(collection_name):
                col = Collection(collection_name)
                col.load()
                stats = col.num_entities
                # Rough estimate: each entity ~= 1.5KB (vector + metadata)
                collection_size = int(stats * 1.5 * 1024)  # bytes
        except Exception as e:
            print(f"Error getting collection size for {kb.id}: {e}")
        
        # Convert to dict and add stats
        kb_dict = {
            "id": kb.id,
            "name": kb.name,
            "description": kb.description,
            "created_at": kb.created_at,
            "updated_at": kb.updated_at,
            "chunking_strategy": kb.chunking_strategy,
            "chunking_config": kb.chunking_config,
            "metric_type": kb.metric_type,
            "document_count": row[1],
            "total_size": collection_size
        }
        kbs_with_stats.append(kb_dict)
    
    return kbs_with_stats

@router.get("/{kb_id}", response_model=KnowledgeBase)
async def get_knowledge_base(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KBModel).filter(KBModel.id == kb_id))
    kb = result.scalars().first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
    return kb

@router.delete("/{kb_id}")
async def delete_knowledge_base(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(KBModel).filter(KBModel.id == kb_id))
    kb = result.scalars().first()
    if kb is None:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")
    
    # Delete all associated documents
    await db.execute(delete(DocModel).where(DocModel.kb_id == kb_id))
    
    await db.delete(kb)
    await db.commit()
    
    # Drop Milvus collection
    try:
        connect_milvus()
        collection_name = f"kb_{kb_id.replace('-', '_')}"
        # Try to drop directly without checking existence to avoid race conditions/flakiness
        try:
            col = Collection(collection_name)
            col.drop()
        except Exception:
            # Fallback or ignore if already gone
            pass
            
    except Exception as e:
        print(f"Error during Milvus cleanup: {e}")
        
    return {"ok": True}
