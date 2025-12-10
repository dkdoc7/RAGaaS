# Jena Fuseki UI 사용 가이드

## 1. Fuseki UI 접속

브라우저에서 http://localhost:3030 으로 접속하세요.

**로그인 정보**:
- Username: `admin`
- Password: `admin`

---

## 2. Dataset 확인

### 2.1 메인 화면
로그인 후 메인 화면에서 현재 존재하는 모든 **Datasets**를 볼 수 있습니다.

- Graph RAG가 활성화된 각 Knowledge Base마다 하나의 Dataset이 생성됩니다
- Dataset 이름 형식: `kb_{knowledge_base_id}`
- 예: `kb_171dbd5b-c42d-4cd5-8bb7-ea2044060aed`

### 2.2 Dataset 정보
각 Dataset 카드에서 확인 가능한 정보:
- **Triples**: 저장된 RDF 트리플 총 개수
- **Type**: TDB2 (Jena의 네이티브 트리플 스토어)
- **Actions**: query, info, upload 등

---

## 3. 저장된 데이터 보기 (SPARQL Query 사용)

### 3.1 Query 탭 접속
1. 원하는 Dataset 카드에서 **"query"** 버튼 클릭
2. SPARQL Query 에디터 화면으로 이동

### 3.2 모든 트리플 조회
가장 간단한 쿼리로 모든 데이터를 확인:

```sparql
SELECT ?subject ?predicate ?object
WHERE {
  ?subject ?predicate ?object
}
LIMIT 100
```

**설명**:
- `?subject`: 주어 (엔티티)
- `?predicate`: 술어 (관계 타입)
- `?object`: 목적어 (연결된 엔티티 또는 값)
- `LIMIT 100`: 최대 100개 결과만 표시

### 3.3 특정 엔티티와 관련된 데이터 조회

**특정 엔티티의 모든 관계 보기**:
```sparql
PREFIX kb: <http://example.org/kb/>
PREFIX rel: <http://example.org/relation/>

SELECT ?relation ?target
WHERE {
  kb:홍길동 ?relation ?target
}
```

**특정 타입의 엔티티만 조회**:
```sparql
PREFIX kb: <http://example.org/kb/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?entity ?type
WHERE {
  ?entity rdf:type ?type
}
```

### 3.4 관계 기반 검색

**특정 관계로 연결된 엔티티 쌍 찾기**:
```sparql
PREFIX kb: <http://example.org/kb/>
PREFIX rel: <http://example.org/relation/>

SELECT ?person ?organization
WHERE {
  ?person rel:works_at ?organization
}
```

**2-hop 관계 탐색** (A → B → C):
```sparql
PREFIX kb: <http://example.org/kb/>
PREFIX rel: <http://example.org/relation/>

SELECT ?start ?intermediate ?end
WHERE {
  ?start ?relation1 ?intermediate .
  ?intermediate ?relation2 ?end
}
LIMIT 50
```

### 3.5 엔티티 타입별 통계

```sparql
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

SELECT ?type (COUNT(?entity) as ?count)
WHERE {
  ?entity rdf:type ?type
}
GROUP BY ?type
ORDER BY DESC(?count)
```

---

## 4. 쿼리 실행 방법

1. **쿼리 입력**: 위의 SPARQL 쿼리를 에디터에 붙여넣기
2. **Run Query 버튼 클릭**: 오른쪽 상단의 실행 버튼
3. **결과 확인**: 
   - **Table** 형식: 표 형태로 결과 표시
   - **JSON** 형식: JSON 형태로 다운로드 가능
   - **CSV** 형식: CSV로 내보내기 가능

---

## 5. Dataset 상세 정보 보기

### 5.1 Info 탭
Dataset 카드에서 **"info"** 버튼 클릭하면:
- Dataset 통계
- Endpoint URL
- 지원되는 쿼리 타입 (SPARQL Query, Update)
- 접근 권한 정보

### 5.2 통계 정보
- **Total Triples**: 전체 트리플 수
- **Named Graphs**: 그래프 개수
- **Storage**: 디스크 사용량

---

## 6. 실제 사용 시나리오

### 시나리오 1: 문서 업로드 후 추출된 엔티티 확인

1. RAG 시스템에서 Graph RAG 활성화 KB 생성
2. 문서 업로드 (예: 회사 소개서)
3. Fuseki UI → 해당 KB dataset → query 탭
4. 다음 쿼리 실행:

```sparql
SELECT ?entity ?type
WHERE {
  ?entity <http://www.w3.org/1999/02/22-rdf-syntax-ns#type> ?type
}
ORDER BY ?type
```

5. 추출된 Person, Organization, Location 등 확인

### 시나리오 2: 특정 인물의 연결망 확인

```sparql
PREFIX kb: <http://example.org/kb/>
PREFIX rel: <http://example.org/relation/>

SELECT ?relation ?connected
WHERE {
  kb:홍길동 ?relation ?connected
}
```

### 시나리오 3: 모든 회사-직원 관계 추출

```sparql
PREFIX rel: <http://example.org/relation/>

SELECT ?person ?company
WHERE {
  ?person rel:works_at ?company
}
```

---

## 7. 데이터가 없는 경우

만약 쿼리 결과가 비어있다면:

1. **KB에 Graph RAG가 활성화되었는지 확인**
   - KB 생성 시 `enable_graph_rag: true` 설정 필요

2. **문서가 업로드되었는지 확인**
   - 문서 업로드 후에만 엔티티 추출 및 저장

3. **Dataset이 생성되었는지 확인**
   - Fuseki 메인 화면에서 `kb_{id}` dataset 존재 확인

4. **백엔드 로그 확인**
   ```bash
   # 엔티티 추출 로그 확인
   docker logs ragaas-backend | grep "entity"
   ```

---

## 8. 유용한 SPARQL 쿼리 모음

### 모든 엔티티 나열
```sparql
SELECT DISTINCT ?entity
WHERE {
  ?entity ?p ?o
}
ORDER BY ?entity
LIMIT 100
```

### 엔티티 타입별 개수
```sparql
SELECT ?type (COUNT(DISTINCT ?entity) as ?count)
WHERE {
  ?entity a ?type
}
GROUP BY ?type
```

### 특정 chunk와 연결된 엔티티
```sparql
PREFIX chunk: <http://example.org/chunk/>

SELECT ?entity
WHERE {
  ?entity chunk:from_chunk "chunk-id-here"
}
```

### 모든 관계 타입 나열
```sparql
SELECT DISTINCT ?relation
WHERE {
  ?s ?relation ?o
  FILTER(STRSTARTS(STR(?relation), "http://example.org/relation/"))
}
```

---

## 9. 팁 & 트러블슈팅

### 쿼리가 너무 느릴 때
- `LIMIT` 값을 작게 설정 (예: 10, 50)
- 특정 조건으로 필터링 추가

### 한글이 깨질 때
- Fuseki는 UTF-8을 지원하므로 정상 표시되어야 함
- 브라우저 인코딩 설정 확인

### Dataset이 안 보일 때
```bash
# Fuseki 로그 확인
docker logs ragaas-fuseki

# 백엔드에서 Dataset 생성 확인
curl -u admin:admin http://localhost:3030/$/datasets
```

---

## 10. API로 직접 조회

UI 대신 API로도 조회 가능:

```bash
# SPARQL Query 실행
curl -X POST http://localhost:3030/kb_your-kb-id/sparql \
  -H "Content-Type: application/sparql-query" \
  -u admin:admin \
  --data 'SELECT * WHERE { ?s ?p ?o } LIMIT 10'
```

---

이 가이드를 따라하면 Fuseki UI에서 저장된 모든 RDF 데이터를 쉽게 탐색하고 분석할 수 있습니다!
