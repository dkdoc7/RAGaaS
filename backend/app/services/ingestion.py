import io
from pypdf import PdfReader
from app.services.chunking import chunking_service
from app.services.embedding import embedding_service
from app.core.milvus import create_collection
from app.models.document import Document, DocumentStatus
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
import logging

from app.core.database import SessionLocal, get_db
from app.services.entity_extraction import entity_extraction_service
from app.services.graph_service import graph_service

logger = logging.getLogger(__name__)

class IngestionService:
    async def process_document(
        self, 
        kb_id: str, 
        doc_id: str, 
        filename: str, 
        file_content: bytes, 
        chunking_strategy: str = "size",
        chunking_config: str = "{}",
        enable_graph_rag: bool = False,
        graph_config: dict = None
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
            
            # 5. Graph RAG Processing (if enabled)
            if enable_graph_rag and graph_config:
                logger.info(f"Graph RAG enabled for KB {kb_id}, extracting entities and relations...")
                
                # Get prompts from config or use None (entity_extraction_service has defaults)
                entity_prompt = graph_config.get("entity_extraction_prompt")
                relation_prompt = graph_config.get("relation_extraction_prompt")
                
                # Process each chunk
                for i, chunk_text in enumerate(texts_to_embed):
                    chunk_id = f"{doc_id}_{i}"
                    
                    try:
                        # Extract entities and relations (service will use defaults if prompts are None)
                        extraction_result = entity_extraction_service.extract_entities_relations(
                            chunk_text=chunk_text,
                            entity_prompt=entity_prompt,
                            relation_prompt=relation_prompt
                        )
                        
                        entities = extraction_result.get("entities", [])
                        relations = extraction_result.get("relations", [])
                        
                        if entities:
                            # Store in Fuseki
                            success = await graph_service.store_triples(
                                kb_id=kb_id,
                                entities=entities,
                                relations=relations,
                                chunk_id=chunk_id,
                                doc_id=doc_id,
                                chunk_content=chunk_text
                            )
                            
                            if success:
                                logger.info(f"Stored {len(entities)} entities, {len(relations)} relations for chunk {i}")
                            else:
                                logger.warning(f"Failed to store RDF triples for chunk {i}")
                        else:
                            logger.info(f"No entities extracted from chunk {i}")
                    
                    except Exception as e:
                        logger.error(f"Error processing chunk {i} for Graph RAG: {e}", exc_info=True)
                        # Continue processing other chunks even if one fails
                        continue
            
            # 6. Update Status to COMPLETED
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
            logger.error(f"Error processing document {doc_id}: {str(e)}", exc_info=True)
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
                logger.error(f"Error updating document status to ERROR: {str(db_err)}", exc_info=True)

ingestion_service = IngestionService()
