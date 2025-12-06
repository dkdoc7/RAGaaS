from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.core.database import get_db
from app.models.document import Document as DocModel, DocumentStatus
from app.models.knowledge_base import KnowledgeBase as KBModel
from app.schemas import Document
from app.services.ingestion import ingestion_service

router = APIRouter()

@router.post("/{kb_id}/documents", response_model=Document)
async def upload_document(
    kb_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Fetch Knowledge Base to get chunking config
    result = await db.execute(select(KBModel).filter(KBModel.id == kb_id))
    kb = result.scalars().first()
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge Base not found")

    # Create Document record
    doc = DocModel(
        kb_id=kb_id,
        filename=file.filename,
        file_type=file.filename.split(".")[-1],
        status=DocumentStatus.PROCESSING.value # Start as processing or pending
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    
    # Read file content
    content = await file.read()
    
    # Start background task
    background_tasks.add_task(
        ingestion_service.process_document,
        kb_id,
        doc.id,
        doc.filename,
        content,
        kb.chunking_strategy,
        kb.chunking_config
    )
    
    return doc

@router.get("/{kb_id}/documents", response_model=List[Document])
async def list_documents(kb_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocModel).filter(DocModel.kb_id == kb_id))
    return result.scalars().all()

@router.delete("/{kb_id}/documents/{doc_id}")
async def delete_document(kb_id: str, doc_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DocModel).filter(DocModel.id == doc_id, DocModel.kb_id == kb_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    await db.delete(doc)
    await db.commit()
    
    # TODO: Delete from Milvus as well (requires deleting by expression)
    
    return {"ok": True}

@router.get("/{kb_id}/documents/{doc_id}/chunks")
async def get_document_chunks(kb_id: str, doc_id: str, db: AsyncSession = Depends(get_db)):
    from app.core.milvus import create_collection
    from pymilvus import Collection
    
    # Verify document exists
    result = await db.execute(select(DocModel).filter(DocModel.id == doc_id, DocModel.kb_id == kb_id))
    doc = result.scalars().first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Query Milvus for chunks
    collection = create_collection(kb_id)
    collection.load()
    
    # Query by doc_id
    expr = f'doc_id == "{doc_id}"'
    results = collection.query(
        expr=expr,
        output_fields=["chunk_id", "content", "doc_id"],
        limit=1000  # Adjust as needed
    )
    
    return {
        "document": {
            "id": doc.id,
            "filename": doc.filename,
            "status": doc.status
        },
        "chunks": results
    }
