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
from app.services.graph_service import graph_service

router = APIRouter()

@router.post("/", response_model=KnowledgeBase)
async def create_knowledge_base(kb: KnowledgeBaseCreate, db: AsyncSession = Depends(get_db)):
    db_kb = KBModel(
        name=kb.name, 
        description=kb.description,
        chunking_strategy=kb.chunking_strategy,
        chunking_config=kb.chunking_config,
        enable_graph_rag=kb.enable_graph_rag,
        graph_config=kb.graph_config
    )
    db.add(db_kb)
    await db.commit()
    await db.refresh(db_kb)
    
    # Create Milvus collection (always use COSINE metric)
    try:
        create_collection(db_kb.id, metric_type="COSINE")
    except Exception as e:
        print(f"Failed to create Milvus collection: {e}")
    
    # Create Fuseki dataset if Graph RAG is enabled
    if kb.enable_graph_rag:
        try:
            success = await graph_service.create_kb_dataset(db_kb.id)
            if not success:
                print(f"Warning: Failed to create Fuseki dataset for KB {db_kb.id}")
        except Exception as e:
            print(f"Error creating Fuseki dataset: {e}")
        
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
            "enable_graph_rag": kb.enable_graph_rag,
            "graph_config": kb.graph_config,
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
    
    # Delete Fuseki dataset if Graph RAG was enabled
    if kb.enable_graph_rag:
        try:
            await graph_service.delete_kb_dataset(kb_id)
        except Exception as e:
            print(f"Error deleting Fuseki dataset: {e}")
    
    # Delete all associated documents
    await db.execute(delete(DocModel).where(DocModel.kb_id == kb_id))
    
    await db.delete(kb)
    await db.commit()
    
    # Drop Milvus collection
    try:
        connect_milvus()
        collection_name = f"kb_{kb_id.replace('-', '_')}"
        try:
            col = Collection(collection_name)
            col.drop()
        except Exception:
            pass
            
    except Exception as e:
        print(f"Error during Milvus cleanup: {e}")
        
    return {"ok": True}
