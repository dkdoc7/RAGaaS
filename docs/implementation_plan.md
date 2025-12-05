# Implementation Plan - RAG Management System

# Goal Description
Build a Milvus-based RAG management system with React frontend and FastAPI backend. The system will support multiple Knowledge Bases, document management, and advanced retrieval strategies (Keyword, ANN, 2-Stage).

## User Review Required
> [!IMPORTANT]
> - **Database**: SQLite will be used for metadata for simplicity.
> - **Vector DB**: Milvus is expected to be running or accessible. I will assume a local Docker setup or similar is available or I will provide instructions.
> - **Embeddings**: Will use a default model (e.g., OpenAI or a local HuggingFace model) but this needs to be configurable.

## Proposed Changes

### Project Structure
#### [NEW] /Users/dukekimm/Works/RAGaaS
- `backend/`: FastAPI application
- `frontend/`: React application
- `docker-compose.yml`: For Milvus and other services (optional but recommended)

### Backend (FastAPI)
#### [NEW] backend/
- `main.py`: Entry point
- `app/api/`: API routers (knowledge_base.py, document.py, retrieval.py)
- `app/core/`: Config, database connection, Milvus client
- `app/models/`: SQLModel/Pydantic models
- `app/services/`: Business logic (Ingestion, Chunking, Retrieval)
    - `chunking.py`: Size, Parent-Child, Context-Aware logic
    - `retrieval.py`: Keyword, ANN, 2-Stage logic

### Frontend (React)
#### [NEW] frontend/
- `src/components/`: Reusable components
- `src/pages/`: Dashboard, KnowledgeBaseDetail
- `src/services/`: API client
- `src/types/`: TypeScript interfaces

## Verification Plan

### Automated Tests
- Backend: `pytest` for API endpoints and logic.
- Frontend: Basic rendering tests.

### Manual Verification
- **Setup**: Run backend and frontend.
- **Flow**:
    1.  Create a Knowledge Base.
    2.  Upload a PDF/TXT file.
    3.  Check if chunks are created (Size, Parent-Child, etc.).
    4.  Perform a search (Keyword, ANN, 2-Stage) and verify results.
