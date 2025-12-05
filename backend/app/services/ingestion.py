import io
from pypdf import PdfReader
from app.services.chunking import chunking_service
from app.services.embedding import embedding_service
from app.core.milvus import create_collection
from app.models.document import Document, DocumentStatus
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import SessionLocal

class IngestionService:
    async def process_document(
        self, 
        kb_id: str, 
        doc_id: str, 
        filename: str, 
        file_content: bytes, 
        chunking_strategy: str = "size"
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
            if chunking_strategy == "size":
                texts = chunking_service.chunk_by_size(text)
                chunks = [{"content": t, "metadata": {}} for t in texts]
            elif chunking_strategy == "parent_child":
                chunks = chunking_service.chunk_parent_child(text)
            elif chunking_strategy == "context_aware":
                texts = chunking_service.chunk_context_aware(text)
                chunks = [{"content": t, "metadata": {}} for t in texts]
            else:
                texts = chunking_service.chunk_by_size(text)
                chunks = [{"content": t, "metadata": {}} for t in texts]

            # 3. Embedding
            texts_to_embed = [c["content"] for c in chunks]
            # Batch embedding if needed, but for now simple
            vectors = await embedding_service.get_embeddings(texts_to_embed)

            # 4. Insert into Milvus
            collection = create_collection(kb_id)
            
            data = [
                [doc_id] * len(chunks), # doc_id
                [f"{doc_id}_{i}" for i in range(len(chunks))], # chunk_id
                texts_to_embed, # content
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
        except Exception as e:
            # Update status to ERROR on failure
            print(f"Error processing document {doc_id}: {str(e)}")
            async with SessionLocal() as db:
                result = await db.execute(select(Document).filter(Document.id == doc_id))
                doc = result.scalars().first()
                if doc:
                    doc.status = DocumentStatus.ERROR.value
                    await db.commit()

ingestion_service = IngestionService()
