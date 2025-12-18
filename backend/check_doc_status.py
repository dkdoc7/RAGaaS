
import asyncio
import sys
import os
from sqlalchemy import select

# Add app to path
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.models.document import Document

async def main():
    kb_id = "0c0f4f26-f68a-479c-b76c-77a40eafc1aa"
    async with SessionLocal() as db:
        result = await db.execute(select(Document).filter(Document.kb_id == kb_id))
        docs = result.scalars().all()
        print(f"Found {len(docs)} documents:")
        for doc in docs:
            print(f"ID: {doc.id}, File: {doc.filename}, Status: {doc.status}, Updated: {doc.updated_at}")

if __name__ == "__main__":
    asyncio.run(main())
