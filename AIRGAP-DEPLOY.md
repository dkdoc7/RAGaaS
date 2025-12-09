# 폐쇄망(Air-gapped) 환경 배포 가이드

## 개요

인터넷 연결이 없는 폐쇄망 환경에서 RAGaaS를 배포하는 방법입니다.

## 준비 단계 (인터넷 연결된 환경)

### 1. Docker 이미지 빌드 및 저장

```bash
# 프로젝트 디렉토리에서 실행
cd /path/to/RAGaaS

# 모든 이미지 빌드
docker-compose build

# 필요한 이미지 목록
IMAGES=(
  "ragaas-backend:latest"
  "ragaas-frontend:latest"
  "milvusdb/milvus:v2.3.3"
  "quay.io/coreos/etcd:v3.5.5"
  "minio/minio:RELEASE.2023-03-20T20-16-18Z"
)

# 각 이미지를 tar 파일로 저장
mkdir -p docker-images
for img in "${IMAGES[@]}"; do
  filename=$(echo $img | tr '/:' '_')
  docker save $img -o docker-images/${filename}.tar
  echo "Saved: ${filename}.tar"
done
```

### 2. 로컬 임베딩 모델 다운로드 (OpenAI 대체)

OpenAI API 대신 로컬 모델 사용:

```bash
# sentence-transformers 모델 다운로드
mkdir -p models
cd models

# 임베딩 모델 다운로드
python3 << EOF
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')
model.save('./all-MiniLM-L6-v2')
print("Model downloaded successfully")
EOF

cd ..
```

### 3. Python 의존성 다운로드 (오프라인 설치용)

```bash
# backend 디렉토리에서
cd backend

# 모든 의존성을 wheels로 다운로드
pip download -r requirements.txt -d wheels/

cd ..
```

### 4. Node.js 의존성 다운로드

```bash
# frontend 디렉토리에서
cd frontend

# node_modules를 tar로 압축
npm ci
tar -czf node_modules.tar.gz node_modules/

cd ..
```

### 5. 전체 패키지 압축

```bash
# 배포 패키지 생성
tar -czf ragaas-airgap-deployment.tar.gz \
  backend/ \
  frontend/ \
  docker-images/ \
  models/ \
  docker-compose.airgap.yml \
  AIRGAP-DEPLOY.md \
  --exclude 'backend/venv' \
  --exclude 'backend/__pycache__' \
  --exclude 'frontend/node_modules' \
  --exclude 'frontend/dist' \
  --exclude '.git'
```

## 수정된 설정 파일

### backend/app/services/embedding.py (로컬 모델 사용)

```python
# 기존 OpenAI 대신 로컬 모델 사용
from sentence_transformers import SentenceTransformer
import os

class EmbeddingService:
    def __init__(self):
        model_path = os.getenv('LOCAL_MODEL_PATH', '/app/models/all-MiniLM-L6-v2')
        self.model = SentenceTransformer(model_path)
    
    async def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(texts)
        return embeddings.tolist()

embedding_service = EmbeddingService()
```

### docker-compose.airgap.yml

```yaml
version: '3.5'

services:
  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/etcd:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls=http://0.0.0.0:2379 --data-dir /etcd
    restart: unless-stopped

  minio:
    container_name: milvus-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    ports:
      - "9001:9001"
      - "9000:9000"
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/minio:/minio_data
    command: minio server /minio_data --console-address ":9001"
    restart: unless-stopped

  standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v2.3.3
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
      MINIO_ACCESS_KEY_ID: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/milvus:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - etcd
      - minio
    restart: unless-stopped

  backend:
    container_name: ragaas-backend
    image: ragaas-backend:latest
    environment:
      - USE_LOCAL_MODEL=true
      - LOCAL_MODEL_PATH=/app/models/all-MiniLM-L6-v2
      - MILVUS_HOST=standalone
      - MILVUS_PORT=19530
      - DATABASE_URL=sqlite:////app/data/rag_system.db
    volumes:
      - ./backend/data:/app/data
      - ./models:/app/models:ro
    ports:
      - "8000:8000"
    depends_on:
      - standalone
    restart: unless-stopped

  frontend:
    container_name: ragaas-frontend
    image: ragaas-frontend:latest
    ports:
      - "80:80"
    depends_on:
      - backend
    restart: unless-stopped

networks:
  default:
    name: milvus
```

## 폐쇄망 환경 배포 절차

### 1. 패키지 전송

```bash
# USB나 안전한 경로로 파일 전송
# ragaas-airgap-deployment.tar.gz를 폐쇄망 서버로 복사
```

### 2. 압축 해제

```bash
# 폐쇄망 서버에서
tar -xzf ragaas-airgap-deployment.tar.gz
cd RAGaaS
```

### 3. Docker 이미지 로드

```bash
# 모든 이미지 로드
for tarfile in docker-images/*.tar; do
  echo "Loading $tarfile..."
  docker load -i $tarfile
done

# 이미지 확인
docker images
```

### 4. 서비스 시작

```bash
# docker-compose로 실행
docker-compose -f docker-compose.airgap.yml up -d

# 로그 확인
docker-compose -f docker-compose.airgap.yml logs -f
```

## 검증

```bash
# 서비스 상태 확인
docker-compose -f docker-compose.airgap.yml ps

# API 테스트
curl http://localhost:8000/docs

# Frontend 접속
# 브라우저에서 http://localhost
```

## 로컬 모델 성능 비교

| 항목 | OpenAI (text-embedding-3-small) | Local (all-MiniLM-L6-v2) |
|------|----------------------------------|---------------------------|
| 차원 | 1536 | 384 |
| 속도 | API 의존 (느림) | 매우 빠름 |
| 비용 | 종량제 | 무료 |
| 품질 | 높음 | 중간~높음 |
| 인터넷 | 필요 | 불필요 |

## 주의사항

1. **임베딩 모델 변경 시**: 기존 벡터 DB와 호환되지 않으므로, 새로운 환경에서 문서를 다시 업로드해야 합니다.

2. **벡터 차원 변경**: 
   - OpenAI: 1536차원
   - Local 모델: 384차원
   - Milvus 스키마가 자동으로 생성되므로 문제없음

3. **성능**: 로컬 모델이 OpenAI보다 품질이 약간 낮을 수 있지만, 대부분의 사용 사례에서 충분합니다.

## 대안 로컬 모델

더 나은 성능이 필요한 경우:

```python
# 한국어 특화 모델
model = SentenceTransformer('jhgan/ko-sroberta-multitask')

# 다국어 고성능 모델
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
```

## 문제 해결

### 이미지 로드 실패
```bash
# 이미지 파일 무결성 확인
md5sum docker-images/*.tar

# 수동으로 하나씩 로드
docker load -i docker-images/ragaas-backend_latest.tar
```

### 모델 로드 실패
```bash
# 모델 경로 확인
docker exec ragaas-backend ls -la /app/models/

# 권한 확인
chmod -R 755 models/
```

### Milvus 연결 실패
```bash
# Milvus 로그 확인
docker logs milvus-standalone

# 재시작
docker-compose -f docker-compose.airgap.yml restart standalone
```

## 업데이트 방법

1. 인터넷 연결 환경에서 새 버전 빌드
2. 새 Docker 이미지를 tar로 저장
3. 폐쇄망으로 전송
4. 기존 이미지 삭제 후 새 이미지 로드
5. 서비스 재시작

```bash
# 업데이트 절차
docker-compose -f docker-compose.airgap.yml down
docker rmi ragaas-backend ragaas-frontend
docker load -i new-images/ragaas-backend_latest.tar
docker load -i new-images/ragaas-frontend_latest.tar
docker-compose -f docker-compose.airgap.yml up -d
```
