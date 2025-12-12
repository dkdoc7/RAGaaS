# RAG Management System

Milvus 기반의 다수의 RAG (Retrieval-Augmented Generation) 지식 베이스를 생성하고 관리하는 시스템입니다.

## 기술 스택

- **Backend**: FastAPI (Python)
- **Frontend**: React + TypeScript (Vite)
- **Vector DB**: Milvus
- **Metadata DB**: SQLite
- **Embeddings**: OpenAI `text-embedding-3-small`
- **Reranking**: Cross-Encoder `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Keyword Search**: BM25 (rank-bm25)

## 주요 기능

### 지식 베이스 관리
- 다수의 지식 베이스 생성/조회/삭제
- 메타데이터 관리

### 문서 관리
- TXT, PDF, Markdown 파일 업로드
- 3가지 청킹 전략:
  - **Size 단위**: 고정 크기 분할
  - **Parent-Child**: 계층적 청크 구조
  - **Context Aware**: 의미 단위 분할

### 검색 전략 (4가지)
모든 검색 방식은 **코사인 유사도 (0~1)** 로 통일된 점수를 제공합니다.

- **ANN (Vector Search)**: 고속 벡터 유사도 검색
- **Keyword Search**: BM25 기반 키워드 매칭 검색
- **2-Stage Retrieval**: ANN 후보 검색 + Cross-Encoder 정밀 재평가
- **Hybrid (ANN + BM25)**: 벡터 검색과 키워드 검색을 결합한 최고 정확도 검색

### 고급 검색 기능
- **선택적 리랭커**: Cross-Encoder 기반 의미적 관련성 재평가
- **NER 필터**: 엔티티 매칭 기반 점수 조정으로 정확도 향상
- **Flat Index (L2)**: 정밀 L2 거리 계산을 통한 최고 정확도 검색
  - 후보군에 대해 정확한 유클리드 거리 계산
  - L2 거리 임계값 필터링 (0.0-2.0)
  - Score와 L2 거리를 모두 표시하여 투명성 제공
- **Graph RAG**: 지식 그래프 기반 관계 탐색 검색

### 데이터 관리
- **Cascading Delete**: 지식 베이스 삭제 시 관련 문서 및 벡터 자동 삭제
- **실시간 상태 추적**: WebSocket을 통한 문서 처리 상태 업데이트

### 청크 뷰어
- 문서 클릭 시 청크 목록 조회

## 시작하기

### 1. Milvus 시작

```bash
docker-compose up -d
```

### 2. Backend 설정

```bash
cd backend

# 가상환경 생성 (선택사항)
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 설정

# 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend 실행

```bash
cd frontend
npm install
npm run dev
```

### 4. 접속

- Frontend: http://localhost:5173
- Backend API Docs: http://localhost:8000/docs

## 문서

- [시스템 사양서](docs/specification.md)
- [구현 계획](docs/implementation_plan.md)
- [구현 완료 보고서](docs/walkthrough.md)
- [설정 가이드](SETUP.md)

## 프로젝트 구조

```
RAGaaS/
├── backend/              # FastAPI 백엔드
│   ├── app/
│   │   ├── api/         # API 라우터
│   │   ├── core/        # 설정 및 연결
│   │   ├── models/      # 데이터 모델
│   │   └── services/    # 비즈니스 로직
│   └── main.py
├── frontend/            # React 프론트엔드
│   └── src/
│       ├── pages/       # 페이지 컴포넌트
│       └── services/    # API 클라이언트
├── docs/                # 프로젝트 문서
├── docker-compose.yml   # Milvus 설정
└── README.md
```

## 라이선스

MIT
