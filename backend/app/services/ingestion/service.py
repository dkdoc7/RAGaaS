import io
from pypdf import PdfReader
from .text_splitter import chunking_service
from app.services.embedding import embedding_service
from app.core.milvus import create_collection
from app.models.document import Document, DocumentStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.core.database import SessionLocal, get_db

class IngestionService:
    async def process_document(
        self, 
        kb_id: str, 
        doc_id: str, 
        filename: str, 
        file_content: bytes, 
        chunking_strategy: str = "size",
        chunking_config: str = "{}"
    ):
        try:
            # 1. Parse File
            text = ""
            if filename.endswith(".pdf"):
                pdf = PdfReader(io.BytesIO(file_content))
                for page in pdf.pages:
                    text += page.extract_text()
            else:
                text = file_content.decode("utf-8")

            # 2. Chunking
            chunks = []
            
            # Parse config if it's a string (from FormData)
            import json
            config = {}
            if chunking_config and isinstance(chunking_config, str):
                try:
                    config = json.loads(chunking_config)
                except:
                    pass
            elif isinstance(chunking_config, dict):
                config = chunking_config

            if chunking_strategy == "size":
                texts = chunking_service.chunk_by_size(
                    text,
                    chunk_size=int(config.get("chunk_size", 1000)),
                    overlap=int(config.get("overlap", 200)),
                    separators=config.get("separators")
                )
                chunks = [{"content": t, "metadata": {}} for t in texts]
            elif chunking_strategy == "parent_child":
                chunks = chunking_service.chunk_parent_child(
                    text,
                    parent_size=int(config.get("parent_size", 2000)),
                    child_size=int(config.get("child_size", 500)),
                    parent_overlap=int(config.get("parent_overlap", 0)),
                    child_overlap=int(config.get("child_overlap", 100)),
                    separators=config.get("separators")
                )
            elif chunking_strategy == "context_aware":
                if config.get("semantic_mode"):
                    texts = chunking_service.chunk_semantic(
                        text,
                        buffer_size=int(config.get("buffer_size", 1)),
                        breakpoint_threshold_type=config.get("breakpoint_type", "percentile"),
                        breakpoint_threshold_amount=float(config.get("breakpoint_amount", 95.0))
                    )
                else:
                    # Convert config headers (e.g. {"h1": true}) to list of tuples
                    headers = []
                    if config.get("h1"): headers.append(("#", "Header 1"))
                    if config.get("h2"): headers.append(("##", "Header 2"))
                    if config.get("h3"): headers.append(("###", "Header 3"))
                    
                    texts = chunking_service.chunk_context_aware(
                        text,
                        headers_to_split_on=headers if headers else None
                    )
                chunks = [{"content": t, "metadata": {}} for t in texts]
            else:
                texts = chunking_service.chunk_by_size(text)
                chunks = [{"content": t, "metadata": {}} for t in texts]

            # 3. Embedding
            texts_to_embed = [c["content"] for c in chunks if c["content"].strip()]
            
            if not texts_to_embed:
                print(f"Warning: No text content found in document {filename}")
                # We can either raise error or just mark as completed with 0 chunks
                # For now, let's raise error to inform user
                raise ValueError("No text content could be extracted from the document.")

            # Batch embedding if needed, but for now simple
            vectors = await embedding_service.get_embeddings(texts_to_embed)

            # 4. Insert into Milvus
            collection = create_collection(kb_id)
            
            # Extract metadata
            metadatas = [c["metadata"] for c in chunks if c["content"].strip()]

            data = [
                [doc_id] * len(texts_to_embed), # doc_id
                [f"{doc_id}_{i}" for i in range(len(texts_to_embed))], # chunk_id
                texts_to_embed, # content
                metadatas, # metadata
                vectors # vector
            ]
            
            collection.insert(data)
            collection.flush() # Ensure data is visible
            
            # 5. Update Status to COMPLETED
            async with SessionLocal() as db:
                result = await db.execute(select(Document).filter(Document.id == doc_id))
                doc = result.scalars().first()
                if doc:
                    doc.status = DocumentStatus.COMPLETED.value
                    await db.commit()
                    
                    # Broadcast WebSocket notification
                    from app.core.websocket_manager import manager
                    await manager.broadcast(kb_id, {
                        "type": "document_status_update",
                        "doc_id": doc_id,
                        "status": DocumentStatus.COMPLETED.value,
                        "filename": filename
                    })
        except Exception as e:
            # Update status to ERROR on failure
            print(f"Error processing document {doc_id}: {str(e)}")
            try:
                async with SessionLocal() as db:
                    result = await db.execute(select(Document).filter(Document.id == doc_id))
                    doc = result.scalars().first()
                    if doc:
                        doc.status = DocumentStatus.ERROR.value
                        await db.commit()
                        
                        # Broadcast WebSocket notification for error
                        from app.core.websocket_manager import manager
                        await manager.broadcast(kb_id, {
                            "type": "document_status_update",
                            "doc_id": doc_id,
                            "status": DocumentStatus.ERROR.value,
                            "filename": filename
                        })
            except Exception as db_err:
                print(f"Error updating document status to ERROR: {str(db_err)}")

ingestion_service = IngestionService()
