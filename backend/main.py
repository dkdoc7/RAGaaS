from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="RAG Management System API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Welcome to RAG Management System API"}

from app.api import knowledge_base, document, retrieval
from app.core.database import engine, Base
from app.core.milvus import connect_milvus

app.include_router(knowledge_base.router, prefix="/api/knowledge-bases", tags=["Knowledge Base"])
app.include_router(document.router, prefix="/api/knowledge-bases", tags=["Documents"])
app.include_router(retrieval.router, prefix="/api/knowledge-bases", tags=["Retrieval"])

@app.on_event("startup")
async def startup():
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Connect to Milvus
    try:
        connect_milvus()
    except Exception as e:
        print(f"Failed to connect to Milvus: {e}")

