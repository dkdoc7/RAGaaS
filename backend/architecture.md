# Backend Architecture & Responsibility

This document defines the folder structure, responsibilities, and extension rules for the RAG Management System backend. This guide allows LLMs and developers to understand where to place code and how components interact.

## 1. Top-Level Directory Structure

```plaintext
backend/app/
├── api/             # API Router & Controllers (FastAPI endpoints)
├── core/            # Core Infrastructure (Configuration, Database, Milvus, Logging)
├── models/          # SQLAlchemy Database Models
├── schemas/         # Pydantic Schemas (Data Transfer Objects) -> Refactored from schemas.py
├── services/        # Business Logic & Service Layers
└── utils/           # Shared Utilities
```

## 2. Responsibilities by Module

### 2.1 API (`app/api/`)
*   **Purpose**: Handle HTTP requests, parse inputs (using Schemas), delegate to Services, and return HTTP responses.
*   **Rules**:
    *   No complex business logic here.
    *   Only dependencies injection (e.g., `db: Session`) and Service calls.
    *   One file per resource/domain (e.g., `knowledge_base.py`, `document.py`, `retrieval.py`).

### 2.2 Core (`app/core/`)
*   **Purpose**: singleton configurations and database connections.
*   **Components**:
    *   `config.py`: Environment variable loading (Pydantic Settings).
    *   `database.py`: SQLAlchemy engine & session factory.
    *   `milvus.py`: Milvus connection logic.
*   **Rules**: Global state or connection pools belong here.

### 2.3 Models (`app/models/`)
*   **Purpose**: Define database tables using SQLAlchemy ORM.
*   **files**:
    *   `knowledge_base.py`
    *   `document.py`
*   **Rules**: Only DB constraints and relationships. No business methods.

### 2.4 Schemas (`app/schemas/`)
*   **Purpose**: Define Pydantic models for request/response validation.
*   **Structure**:
    *   `common.py`: Shared enums, base models, pagination.
    *   `knowledge_base.py`: KB creation, updates, response.
    *   `document.py`: Document metadata, status.
    *   `retrieval.py`: Search requests, parameters, result formats.
*   **Rules**: Split `schemas.py` into these granular files to prevent circular imports and massive files.

### 2.5 Services (`app/services/`)
*   **Purpose**: Contain ALL business logic.
*   **Structure**:
    *   `ingestion/`: (Package)
        *   `pipeline.py`: Orchestrates parsing, splitting, embedding, storage.
        *   `text_splitter.py`: Chunking logic.
    *   `retrieval/`: (Package)
        *   `base.py`: Abstract Base Class for retrieval strategies.
        *   `vector.py`: ANN Search implementation.
        *   `keyword.py`: BM25/Keyword implementation.
        *   `hybrid.py`: Combination logic.
        *   `reranker.py`: Methods for Cross-Encoder / LLM reranking.
        *   `factory.py`: Returns the correct strategy based on request.
    *   `embedding.py`: Wrapper for embedding APIs (OpenAI etc).
    *   `ner.py`: Named Entity Recognition logic.
*   **Rules**:
    *   Services should return Pydantic models or plain DB objects, not HTTP Responses.
    *   `retrieval.py` needs refactoring into a `retrieval/` package using the Strategy Pattern.

## 3. Extension Rules

### Adding a New Retrieval Strategy (e.g., Graph RAG)
1.  **Schema**: Update `app/schemas/retrieval.py` to add new config parameters (e.g., `graph_hops`).
2.  **Service**: Create `app/services/retrieval/graph.py` implementing `RetrievalStrategy` interface.
3.  **Factory**: Register the new strategy in `app/services/retrieval/factory.py`.
4.  **API**: No changes needed in controller if Factory is used correctly.

### Adding a New Ingestion Method
1.  Modify `app/services/ingestion/` to accept new file types or parsing logic.

## 4. Design Patterns Applied

*   **Strategy Pattern**: Used in Retrieval (Vector vs Keyword vs Hybrid).
*   **Factory Pattern**: Used to instantiate Retrieval Strategies.
*   **Facade Pattern**: The Ingestion Service acts as a facade over Parsing, Chunking, and Embedding.

