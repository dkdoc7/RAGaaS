# RAG 관리 시스템 사양서 (Milvus 기반)

## 1. 개요
본 문서는 Milvus를 기반으로 하는 RAG (Retrieval-Augmented Generation) 관리 시스템의 사양을 정의합니다. 이 시스템은 사용자가 다수의 지식 베이스(Knowledge Base)를 생성 및 관리하고, 문서를 업로드하며, 검색 전략을 구성할 수 있도록 지원합니다. 디자인과 기능은 Dify의 Knowledge 기능을 참고하여 설계되었습니다.

## 2. 기술 스택
-   **프론트엔드**: React (Vite)
-   **백엔드**: FastAPI (Python)
-   **벡터 데이터베이스**: Milvus
-   **메타데이터 데이터베이스**: SQLite (간편함을 위해 선택, 추후 PostgreSQL로 확장 가능)
-   **임베딩 모델**: OpenAI `text-embedding-3-small`
-   **리랭킹 모델**: Cross-Encoder `cross-encoder/ms-marco-MiniLM-L-6-v2`
-   **키워드 검색**: BM25 (rank-bm25)

## 3. 핵심 기능

### 3.1 지식 베이스 관리 (Knowledge Base Management)
-   **지식 베이스 생성**: 이름과 설명을 입력하여 새로운 지식 베이스 생성.
-   **지식 베이스 목록 조회**: 문서 수, 크기, 마지막 업데이트 시간 등의 메타데이터와 함께 목록 조회.
-   **지식 베이스 삭제**: 지식 베이스 삭제 시 관련된 모든 문서와 Milvus 컬렉션을 자동으로 삭제 (Cascading Delete).
-   **설정**: 기본 검색 설정 구성 (Top K, Score Threshold), 청킹 전략 및 유사도 측정 방식(COSINE/L2/IP) 선택.

### 3.2 문서 관리 (Document Management)
-   **문서 업로드**: TXT, PDF, Markdown 파일 지원.
-   **데이터 처리**:
    -   **청킹 (Chunking)**: 3가지 방식 지원
        -   **Size 단위**: 고정된 문자 수 또는 토큰 수로 분할 (오버랩 지원).
        -   **Parent-Child**: 문서를 큰 청크(Parent)와 작은 청크(Child)로 나누어 저장. 검색은 Child로 하되, 컨텍스트는 Parent를 참조.
        -   **Context Aware**: 문맥을 고려하여 의미 단위로 분할 (예: 섹션, 문단 기준).
    -   **정제 (Cleaning)**: 기본적인 텍스트 정제.
-   **인덱싱 (Indexing)**: 청크를 벡터 임베딩으로 변환하여 Milvus에 저장.
-   **문서 목록**: 지식 베이스 내 문서 목록 조회.
-   **청크 조회**: 문서의 개별 청크 내용 확인.
-   **상태 추적**: 인덱싱 상태 실시간 확인 (대기 중, 처리 중, 완료, 실패).

### 3.3 검색 전략 (Retrieval Strategy)
시스템은 4가지 검색 전략을 지원하며, 모든 전략은 **코사인 유사도 (0~1 범위)**로 통일된 점수를 제공합니다.

-   **ANN (Approximate Nearest Neighbor)**: 벡터 유사도 기반 고속 검색. KB 설정(COSINE/L2/IP)에 관계없이 최종 점수는 코사인 유사도로 재계산됩니다.
-   **키워드 검색 (Keyword Search)**: Milvus LIKE 연산자를 이용한 텍스트 매칭. 매칭된 결과에 대해 코사인 유사도를 계산하여 점수를 부여합니다.
-   **2단계 검색 (Two-Stage Retrieval)**:
    -   **1단계 (Candidate Generation)**: ANN으로 상위 25개 후보 검색.
    -   **2단계 (Reranking)**: Cross-Encoder 모델(`cross-encoder/ms-marco-MiniLM-L-6-v2`)로 정밀 평가 후 순위 재정렬.
    -   **최종 점수**: 재정렬된 순서를 유지하되, 점수는 코사인 유사도로 표시.
-   **하이브리드 검색 (Hybrid Search - ANN + BM25)**:
    -   BM25 통계 기반 키워드 검색과 ANN 벡터 검색 결과를 결합.
    -   양쪽 결과의 합집합에 대해 코사인 유사도를 계산하여 최종 순위 결정.
    -   키워드 정확도와 의미적 유사성을 모두 고려한 최적의 검색 정확도 제공.

**통일된 점수 체계**: 모든 검색 전략은 Score Threshold (0~1)를 동일하게 적용할 수 있으며, 검색 결과 비교가 용이합니다.

### 3.4 검색 테스트 (Retrieval Testing)
-   **플레이그라운드**: 특정 지식 베이스에 대해 검색 쿼리를 테스트할 수 있는 UI.
-   **디버그 정보**: 검색된 청크, 유사도 점수, 메타데이터 표시.

### 3.4 API 통합
-   **외부 API**: 외부 애플리케이션에서 지식 베이스를 조회할 수 있는 엔드포인트 제공.

## 4. API 설계 (FastAPI)

### 지식 베이스 (Knowledge Base)
-   `POST /api/knowledge-bases`: 지식 베이스 생성.
-   `GET /api/knowledge-bases`: 지식 베이스 목록 조회.
-   `GET /api/knowledge-bases/{kb_id}`: 특정 지식 베이스 상세 정보 조회.
-   `DELETE /api/knowledge-bases/{kb_id}`: 지식 베이스 삭제.

### 문서 (Documents)
-   `POST /api/knowledge-bases/{kb_id}/documents`: 문서 업로드 및 인덱싱.
-   `GET /api/knowledge-bases/{kb_id}/documents`: 지식 베이스 내 문서 목록 조회.
-   `DELETE /api/knowledge-bases/{kb_id}/documents/{doc_id}`: 문서 삭제.
-   `GET /api/knowledge-bases/{kb_id}/documents/{doc_id}/chunks`: 문서의 청크 목록 조회.

### 검색 (Retrieval)
-   `POST /api/knowledge-bases/{kb_id}/retrieve`: 관련 청크 검색.
    -   Body: `{ "query": "...", "top_k": 5, "score_threshold": 0.5, "strategy": "ann" | "keyword" | "2-stage" | "hybrid" }`
    -   Response: `[{ "chunk_id": "...", "content": "...", "score": 0.87, "metadata": {...} }]`

## 5. 데이터베이스 스키마

### 5.1 관계형 DB (Metadata)
**테이블: knowledge_bases**
-   `id`: UUID (Primary Key)
-   `name`: String
-   `description`: String
-   `created_at`: Timestamp
-   `updated_at`: Timestamp

**테이블: documents**
-   `id`: UUID (Primary Key)
-   `kb_id`: UUID (Foreign Key)
-   `filename`: String
-   `file_type`: String (pdf, txt, md)
-   `status`: Enum (pending, processing, completed, error)
-   `created_at`: Timestamp

### 5.2 Milvus (Vector Data)
**컬렉션: knowledge_base_{kb_id}** (또는 파티션 키를 사용한 단일 컬렉션)
-   `id`: Int64 (Primary Key)
-   `doc_id`: String (Metadata)
-   `chunk_id`: String (Metadata)
-   `content`: String (실제 텍스트 청크)
-   `vector`: FloatVector (임베딩)

## 6. UI/UX (React)

### 6.1 대시보드 (Home)
-   **헤더**: "RAG Management System"
-   **메인 영역**: 지식 베이스 그리드/리스트 뷰.
-   **액션**: "지식 베이스 만들기" 버튼 (모달 열기).

### 6.2 지식 베이스 상세 (Knowledge Base Detail)
-   **사이드바**: 네비게이션 (문서, 설정, 테스트).
-   **문서 탭**:
    -   "문서 추가" 버튼 (Drag & Drop 영역).
    -   문서 테이블 (이름, 상태, 날짜, 작업).
-   **설정 탭**:
    -   이름, 설명 입력 필드.
    -   Top K, Score Threshold 슬라이더.
-   **테스트 탭**:
    -   쿼리 입력을 위한 채팅 스타일 인터페이스.
    -   결과 표시 (텍스트 청크 + 점수).

## 7. 구현 계획
1.  **설정**: React 및 FastAPI 프로젝트 초기화.
2.  **백엔드 코어**: 데이터베이스 (SQLite) 및 Milvus 연결 설정.
3.  **API 구현**: 지식 베이스 및 문서 CRUD 구현.
4.  **수집 파이프라인**: 파일 파싱, 청킹, 임베딩 로직 구현.
5.  **프론트엔드**: 대시보드 및 상세 화면 구축.
6.  **통합**: 프론트엔드와 백엔드 API 연동.
