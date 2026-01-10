"""CLI 엔트리포인트"""

import uuid
from pathlib import Path
from typing import Optional

import click

from doc2onto.config import load_config, Config
from doc2onto.chunkers import OEChunker, RAGChunker
from doc2onto.extractors import LLMStubExtractor
from doc2onto.builders import TriGBuilder, ChunksBuilder, EntityRegistryBuilder
from doc2onto.loaders import FusekiLoader, MilvusLoader
from doc2onto.qa import QAReporter
from doc2onto.models.chunk import ChunkBatch


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Doc2Onto: 한국어 문서 → 온톨로지(OWL/RDF) + RAG 근거 연결 파이프라인"""
    pass


@main.command()
@click.option("--in", "input_dir", required=True, type=click.Path(exists=True), help="입력 문서 디렉토리")
@click.option("--out", "output_dir", required=True, type=click.Path(), help="출력 디렉토리")
@click.option("--config", "config_path", default="./config.yml", type=click.Path(), help="설정 파일 경로")
@click.option("--dry-run", is_flag=True, help="외부 서비스 없이 파일만 생성")
@click.option("--run-id", default=None, help="실행 ID (기본: 자동 생성)")
@click.option("--oe-chunk-size", default=None, type=int, help="OE-Chunk 크기 (기본: config 또는 2000)")
@click.option("--oe-chunk-overlap", default=None, type=int, help="OE-Chunk 오버랩 (기본: config 또는 500)")
@click.option("--external-chunks", default=None, type=click.Path(exists=True), help="외부 청크 파일 (RAGaaS chunks.jsonl)")
def build(
    input_dir: str, 
    output_dir: str, 
    config_path: str, 
    dry_run: bool, 
    run_id: Optional[str],
    oe_chunk_size: Optional[int],
    oe_chunk_overlap: Optional[int],
    external_chunks: Optional[str],
):
    """파이프라인 실행: 문서 → TriG + chunks.jsonl 생성"""
    
    # 설정 로드
    config = load_config(config_path)
    run_id = run_id or str(uuid.uuid4())[:8]
    
    # CLI 파라미터로 오버라이드
    final_oe_size = oe_chunk_size or config.chunking.oe_chunk_size
    final_oe_overlap = oe_chunk_overlap or config.chunking.oe_chunk_overlap
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    click.echo(f"🚀 Doc2Onto Pipeline (run_id: {run_id})")
    click.echo(f"   Input:  {input_path}")
    click.echo(f"   Output: {output_path}")
    click.echo(f"   Config: {config_path}")
    click.echo(f"   OE-Chunk: {final_oe_size} / overlap {final_oe_overlap}")
    if external_chunks:
        click.echo(f"   External Chunks: {external_chunks}")
    if dry_run:
        click.echo("   Mode:   DRY-RUN")
    
    # 초기화
    oe_chunker = OEChunker(
        chunk_size=final_oe_size,
        chunk_overlap=final_oe_overlap,
        section_aware=config.chunking.oe_section_aware,
    )
    rag_chunker = RAGChunker(
        chunk_size=config.chunking.rag_chunk_size,
        chunk_overlap=config.chunking.rag_chunk_overlap,
    )
    
    # LLM 추출기 선택
    if config.extraction.llm_model != "stub":
        from doc2onto.extractors.openai_extractor import OpenAIExtractor
        extractor = OpenAIExtractor(
            confidence_threshold=config.extraction.confidence_threshold,
            llm_endpoint=config.extraction.llm_endpoint,
            llm_model=config.extraction.llm_model,
            examples_path=config.extraction.examples_path,
        )
        click.echo(f"   LLM:    {config.extraction.llm_model}")
    else:
        extractor = LLMStubExtractor(
            confidence_threshold=config.extraction.confidence_threshold,
            llm_endpoint=config.extraction.llm_endpoint,
            llm_model=config.extraction.llm_model,
        )
    trig_builder = TriGBuilder(
        base_uri=config.ontology.base_uri,
        base_graph_uri=config.ontology.base_graph_uri,
        evidence_graph_prefix=config.ontology.evidence_graph_prefix,
    )
    chunks_builder = ChunksBuilder()
    registry_builder = EntityRegistryBuilder(base_uri=config.ontology.base_uri)
    qa_reporter = QAReporter(run_id=run_id)
    
    # 동의어 사전 로드 (synonyms.yaml)
    synonyms_path = Path("synonyms.yaml")
    if synonyms_path.exists():
        syn_count = registry_builder.load_synonyms_yaml(synonyms_path)
        click.echo(f"📚 Loaded synonyms: {syn_count} entities from {synonyms_path}")

    # 문서 처리
    doc_files = list(input_path.glob("*.txt"))
    if not doc_files:
        click.echo("⚠️  No .txt files found in input directory")
        return
    
    click.echo(f"\n📄 Processing {len(doc_files)} documents...")
    
    all_candidates_raw = []
    all_candidates_filtered = []
    
    for doc_file in doc_files:
        doc_id = doc_file.stem
        click.echo(f"   - {doc_id}")
        
        # 1. OE-Chunking
        oe_chunks = list(oe_chunker.chunk_file(doc_file, doc_id))
        
        # 2. RAG-Chunking (외부 청크 또는 자체 생성)
        rag_chunks = []
        external_chunk_map = {}  # offset -> chunk_id 매핑
        
        if external_chunks:
            # 외부 청크 파일 로드 (RAGaaS)
            import json
            with open(external_chunks, "r", encoding="utf-8") as f:
                for line in f:
                    chunk = json.loads(line)
                    if chunk.get("doc_id") == doc_id:
                        from doc2onto.models.chunk import RAGChunk
                        rag_chunk = RAGChunk(
                            chunk_id=chunk.get("chunk_id", ""),
                            doc_id=chunk.get("doc_id", ""),
                            doc_ver=chunk.get("doc_ver", "v1"),
                            text=chunk.get("text", ""),
                            chunk_idx=chunk.get("chunk_idx", 0),
                            start_offset=chunk.get("start_offset"),
                            end_offset=chunk.get("end_offset"),
                            section_path=chunk.get("section_path"),
                            chunk_hash=chunk.get("chunk_hash", ""),
                        )
                        rag_chunks.append(rag_chunk)
                        # offset 범위 매핑
                        if rag_chunk.start_offset is not None:
                            external_chunk_map[(rag_chunk.start_offset, rag_chunk.end_offset)] = rag_chunk.chunk_id
        else:
            # 자체 RAG-Chunking
            for oe_chunk in oe_chunks:
                for rag_chunk in rag_chunker.chunk_text(
                    oe_chunk.text, 
                    doc_id, 
                    source_oe_chunk_idx=oe_chunk.chunk_idx,
                    base_offset=oe_chunk.start_offset or 0,
                    section_path=oe_chunk.section_path,
                ):
                    rag_chunks.append(rag_chunk)
        
        chunks_builder.chunks.extend(rag_chunks)
        
        # 3. 후보 추출 (OE-Chunk에서)
        for oe_chunk in oe_chunks:
            raw_result = extractor.extract(oe_chunk, run_id)
            all_candidates_raw.append(raw_result)
            
            filtered_result = extractor.filter_by_confidence(raw_result)
            all_candidates_filtered.append(filtered_result)
            
            # TriG 빌더에 추가
            trig_builder.build_from_candidates(filtered_result, registry_builder.registry)
            
            # Evidence 추가 - 외부 청크 또는 자체 청크 매칭
            for triple in filtered_result.triples:
                if external_chunks and external_chunk_map:
                    # 외부 청크: OE-Chunk offset으로 매칭되는 청크 찾기
                    oe_start = oe_chunk.start_offset or 0
                    oe_end = oe_chunk.end_offset or oe_start + len(oe_chunk.text)
                    matching_chunks = [
                        c for c in rag_chunks 
                        if c.start_offset is not None 
                        and c.start_offset >= oe_start 
                        and (c.end_offset or 0) <= oe_end
                    ]
                else:
                    # 자체 청크: source_oe_chunk_idx로 매칭
                    matching_chunks = [c for c in rag_chunks if c.source_oe_chunk_idx == oe_chunk.chunk_idx]
                
                if matching_chunks:
                    trig_builder.add_evidence_triple(triple, matching_chunks[0], run_id)
            
            # 레지스트리 업데이트
            registry_builder.register_from_candidates(filtered_result)
        
        # QA 통계
        oe_avg_len = sum(len(c.text) for c in oe_chunks) / len(oe_chunks) if oe_chunks else 0
        rag_avg_len = sum(len(c.text) for c in rag_chunks) / len(rag_chunks) if rag_chunks else 0
        qa_reporter.add_document_stats(doc_id, len(oe_chunks), len(rag_chunks), oe_avg_len, rag_avg_len)
    
    # 추출 통계
    total_raw = sum(r.total_candidates + r.total_triples for r in all_candidates_raw)
    total_filtered = sum(r.total_candidates + r.total_triples for r in all_candidates_filtered)
    total_classes = sum(len(r.classes) for r in all_candidates_filtered)
    total_props = sum(len(r.properties) for r in all_candidates_filtered)
    total_rels = sum(len(r.relations) for r in all_candidates_filtered)
    total_insts = sum(len(r.instances) for r in all_candidates_filtered)
    total_triples = sum(len(r.triples) for r in all_candidates_filtered)
    
    qa_reporter.add_extraction_stats(
        total_raw, total_filtered,
        classes=total_classes,
        properties=total_props,
        relations=total_rels,
        instances=total_insts,
        triples=total_triples,
    )
    qa_reporter.add_entity_stats(registry_builder.registry.total_entities)
    
    # 출력 저장
    click.echo(f"\n💾 Saving outputs...")
    
    trig_builder.serialize_base(output_path / "base.trig")
    click.echo(f"   ✓ base.trig")
    
    trig_builder.serialize_evidence(output_path / "evidence.trig")
    click.echo(f"   ✓ evidence.trig")
    
    chunks_count = chunks_builder.serialize(output_path / "chunks.jsonl")
    click.echo(f"   ✓ chunks.jsonl ({chunks_count} chunks)")
    
    # candidates 저장
    import json
    with open(output_path / "candidates_raw.jsonl", "w", encoding="utf-8") as f:
        for r in all_candidates_raw:
            f.write(r.model_dump_json() + "\n")
    click.echo(f"   ✓ candidates_raw.jsonl")
    
    with open(output_path / "candidates_filtered.jsonl", "w", encoding="utf-8") as f:
        for r in all_candidates_filtered:
            f.write(r.model_dump_json() + "\n")
    click.echo(f"   ✓ candidates_filtered.jsonl")
    
    registry_builder.serialize(output_path / "entity_registry.json")
    click.echo(f"   ✓ entity_registry.json")
    
    qa_reporter.save(output_path / "qa_report.md")
    click.echo(f"   ✓ qa_report.md")
    
    click.echo(f"\n✅ Pipeline complete!")
    click.echo(f"   Documents: {len(doc_files)}")
    click.echo(f"   RAG Chunks: {chunks_count}")
    click.echo(f"   Triples: {total_triples}")


@main.command("load-fuseki")
@click.option("--in", "input_dir", required=True, type=click.Path(exists=True), help="TriG 파일이 있는 디렉토리")
@click.option("--fuseki", required=True, help="Fuseki 엔드포인트 (e.g., http://localhost:3030)")
@click.option("--dataset", default="ds", help="Fuseki 데이터셋 이름")
@click.option("--dry-run", is_flag=True, help="실제 업로드 없이 확인만")
def load_fuseki(input_dir: str, fuseki: str, dataset: str, dry_run: bool):
    """Fuseki에 TriG 파일 업로드"""
    
    input_path = Path(input_dir)
    loader = FusekiLoader(endpoint=fuseki, dataset=dataset)
    
    click.echo(f"📤 Loading to Fuseki: {fuseki}/{dataset}")
    if dry_run:
        click.echo("   Mode: DRY-RUN")
    
    for trig_file in input_path.glob("*.trig"):
        result = loader.upload(trig_file, dry_run=dry_run)
        status = "✓" if result["success"] else "✗"
        click.echo(f"   {status} {trig_file.name}: {result['message']}")
    
    click.echo("✅ Done!")


@main.command("load-milvus")
@click.option("--in", "chunks_path", required=True, type=click.Path(exists=True), help="chunks.jsonl 파일 경로")
@click.option("--milvus", required=True, help="Milvus 호스트:포트 (e.g., localhost:19530)")
@click.option("--collection", default="doc2onto_chunks", help="Milvus 컬렉션 이름")
@click.option("--dry-run", is_flag=True, help="실제 적재 없이 확인만")
def load_milvus(chunks_path: str, milvus: str, collection: str, dry_run: bool):
    """Milvus에 청크 적재"""
    
    host, port = milvus.split(":") if ":" in milvus else (milvus, "19530")
    loader = MilvusLoader(host=host, port=int(port), collection=collection)
    
    click.echo(f"📤 Loading to Milvus: {host}:{port}/{collection}")
    if dry_run:
        click.echo("   Mode: DRY-RUN")
    
    result = loader.load(chunks_path, dry_run=dry_run)
    status = "✓" if result["success"] else "✗"
    click.echo(f"   {status} {result['message']}")
    
    click.echo("✅ Done!")


@main.command("load")
@click.option("--in", "input_dir", required=True, type=click.Path(exists=True), help="산출물 디렉토리")
@click.option("--backend", default="fuseki", help="그래프 백엔드: fuseki, neo4j, fuseki,neo4j")
@click.option("--fuseki", default="http://localhost:3030", help="Fuseki 엔드포인트")
@click.option("--dataset", default="ds", help="Fuseki 데이터셋")
@click.option("--neo4j", "neo4j_uri", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--neo4j-user", default="neo4j", help="Neo4j 사용자")
@click.option("--neo4j-password", default="", help="Neo4j 비밀번호")
@click.option("--dry-run", is_flag=True, help="실제 적재 없이 확인만")
def load_graph(
    input_dir: str, 
    backend: str, 
    fuseki: str, 
    dataset: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    dry_run: bool
):
    """그래프 DB에 적재 (Fuseki/Neo4j)"""
    from doc2onto.builders.neo4j_builder import Neo4jBuilder
    from doc2onto.loaders.neo4j_loader import Neo4jLoader
    
    input_path = Path(input_dir)
    backends = [b.strip() for b in backend.split(",")]
    
    click.echo(f"📤 Graph Load")
    click.echo(f"   Input:    {input_path}")
    click.echo(f"   Backends: {backends}")
    if dry_run:
        click.echo("   Mode:     DRY-RUN")
    
    # Fuseki 적재
    if "fuseki" in backends:
        click.echo(f"\n🔷 Fuseki: {fuseki}/{dataset}")
        loader = FusekiLoader(endpoint=fuseki, dataset=dataset)
        
        for trig_file in input_path.glob("*.trig"):
            result = loader.upload(trig_file, dry_run=dry_run)
            status = "✓" if result["success"] else "✗"
            click.echo(f"   {status} {trig_file.name}: {result['message']}")
    
    # Neo4j 적재
    if "neo4j" in backends:
        click.echo(f"\n🔶 Neo4j: {neo4j_uri}")
        
        # TriG → Cypher 변환
        builder = Neo4jBuilder()
        
        base_trig = input_path / "base.trig"
        if base_trig.exists():
            count = builder.load_trig(base_trig)
            click.echo(f"   ✓ base.trig 파싱: {count} 트리플")
        
        evidence_trig = input_path / "evidence.trig"
        if evidence_trig.exists():
            count = builder.load_trig(evidence_trig)
            click.echo(f"   ✓ evidence.trig 파싱: {count} 트리플")
        
        chunks_jsonl = input_path / "chunks.jsonl"
        if chunks_jsonl.exists():
            count = builder.load_chunks(chunks_jsonl)
            click.echo(f"   ✓ chunks.jsonl 파싱: {count} 청크")
        
        # Cypher 저장
        cypher_path = input_path / "neo4j_load.cypher"
        result = builder.serialize(cypher_path)
        click.echo(f"   ✓ Cypher 생성: {result['nodes']} 노드, {result['relationships']} 관계")
        
        if not dry_run and neo4j_password:
            loader = Neo4jLoader(
                uri=neo4j_uri,
                user=neo4j_user,
                password=neo4j_password,
            )
            load_result = loader.execute_cypher_file(cypher_path, dry_run=False)
            status = "✓" if load_result["success"] else "✗"
            click.echo(f"   {status} Neo4j 적재: {load_result['message']}")
            loader.close()
        else:
            click.echo(f"   ℹ️  Cypher 파일 생성됨: {cypher_path}")
    
    click.echo("\n✅ Done!")


@main.command("load-neo4j")
@click.option("--in", "cypher_path", required=True, type=click.Path(exists=True), help="Cypher 파일 경로")
@click.option("--neo4j", "neo4j_uri", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--user", default="neo4j", help="Neo4j 사용자")
@click.option("--password", required=True, help="Neo4j 비밀번호")
@click.option("--clear", is_flag=True, help="기존 데이터 삭제")
@click.option("--dry-run", is_flag=True, help="실제 적재 없이 확인만")
def load_neo4j(cypher_path: str, neo4j_uri: str, user: str, password: str, clear: bool, dry_run: bool):
    """Neo4j에 Cypher 파일 실행"""
    from doc2onto.loaders.neo4j_loader import Neo4jLoader
    
    loader = Neo4jLoader(uri=neo4j_uri, user=user, password=password)
    
    click.echo(f"📤 Loading to Neo4j: {neo4j_uri}")
    if dry_run:
        click.echo("   Mode: DRY-RUN")
    
    conn = loader.connect()
    if not conn["success"]:
        click.echo(f"   ✗ 연결 실패: {conn['message']}")
        return
    click.echo(f"   ✓ 연결 성공")
    
    if clear:
        result = loader.clear(dry_run=dry_run)
        click.echo(f"   ✓ 데이터 초기화: {result['message']}")
    
    result = loader.execute_cypher_file(cypher_path, dry_run=dry_run)
    status = "✓" if result["success"] else "✗"
    click.echo(f"   {status} {result['message']}")
    
    if not dry_run:
        stats = loader.get_stats()
        if stats["success"]:
            click.echo(f"   📊 노드: {stats['nodes']}, 관계: {stats['relationships']}")
    
    loader.close()
    click.echo("✅ Done!")


@main.command("promote")
@click.option("--in", "input_dir", required=True, type=click.Path(exists=True), help="KG 산출물 디렉토리 (base.trig, evidence.trig)")
@click.option("--out", "output_dir", default="./ontology", type=click.Path(), help="Ontology 출력 디렉토리")
@click.option("--confidence", default=0.85, type=float, help="승격 최소 confidence (기본: 0.85)")
@click.option("--min-evidence", default=2, type=int, help="최소 근거 수 (기본: 2)")
@click.option("--version", "onto_version", default="v1.0", help="Ontology 버전")
@click.option("--dry-run", is_flag=True, help="실제 저장 없이 확인만")
def promote(
    input_dir: str,
    output_dir: str,
    confidence: float,
    min_evidence: int,
    onto_version: str,
    dry_run: bool,
):
    """KG → Ontology 승격: 7단계 파이프라인"""
    from doc2onto.promoters.ontology_promoter import OntologyPromoter
    
    input_path = Path(input_dir)
    base_trig = input_path / "base.trig"
    evidence_trig = input_path / "evidence.trig"
    
    if not base_trig.exists():
        click.echo(f"❌ base.trig 파일 없음: {base_trig}")
        return
    
    click.echo(f"🔄 Ontology Promotion")
    click.echo(f"   Input:      {input_path}")
    click.echo(f"   Output:     {output_dir}")
    click.echo(f"   Confidence: ≥ {confidence}")
    click.echo(f"   Min Evidence: {min_evidence}")
    click.echo(f"   Version:    {onto_version}")
    if dry_run:
        click.echo("   Mode:       DRY-RUN")
    
    promoter = OntologyPromoter(
        confidence_threshold=confidence,
        min_evidence_count=min_evidence,
        detect_cycles=True,
        remove_hypothetical=True,
    )
    
    click.echo("\n📊 Processing...")
    
    result = promoter.promote(
        base_trig=base_trig,
        evidence_trig=evidence_trig if evidence_trig.exists() else None,
        output_dir=output_dir,
        version=onto_version,
        dry_run=dry_run,
    )
    
    stats = result["stats"]
    validation = result["validation"]
    
    click.echo(f"\n📈 Statistics:")
    click.echo(f"   입력 트리플: {stats['input_triples']}")
    click.echo(f"   Step 1 후보: {stats['step1_candidates']}")
    click.echo(f"   Step 2 클래스: {stats['step2_classes']}, 속성: {stats['step2_properties']}")
    click.echo(f"   Step 3 cycle 제거: {stats['step3_cycles_removed']}")
    click.echo(f"   Step 5 evidence 제거: {stats['step5_evidence_removed']}")
    click.echo(f"   출력 트리플: {stats['output_triples']}")
    
    click.echo(f"\n🔍 Validation:")
    status = "✓" if validation["consistent"] else "✗"
    click.echo(f"   {status} Consistent: {validation['consistent']}")
    if validation["errors"]:
        for err in validation["errors"]:
            click.echo(f"   ⚠️  {err}")
    
    if not dry_run:
        click.echo(f"\n💾 Outputs:")
        click.echo(f"   ✓ {result.get('ontology_path')}")
        click.echo(f"   ✓ {result.get('schema_path')}")
        click.echo(f"   ✓ {result.get('report_path')}")
    
    click.echo("\n✅ Promotion complete!")


@main.group()
def registry():
    """동의어 사전(Entity Registry) 관리"""
    pass


@registry.command("list")
@click.option("--in", "registry_path", default="./out/entity_registry.json", help="레지스트리 파일 경로")
@click.option("--query", "-q", help="검색어 (라벨 또는 URI)")
def registry_list(registry_path: str, query: Optional[str]):
    """엔티티 목록 조회"""
    from doc2onto.builders.entity_registry import EntityRegistryBuilder
    
    path = Path(registry_path)
    if not path.exists():
        click.echo(f"❌ File not found: {path}")
        return

    builder = EntityRegistryBuilder.load(path)
    
    click.echo(f"📖 Registry: {path}")
    click.echo(f"   Total Entities: {builder.registry.total_entities}")
    click.echo("-" * 60)
    
    count = 0
    for uri, entry in builder.registry.entries.items():
        if query:
            match = query in entry.canonical_label or \
                    query in uri or \
                    any(query in alias for alias in entry.labels)
            if not match:
                continue
        
        click.echo(f"[{entry.entity_type}] {entry.canonical_label}")
        click.echo(f"  URI: {uri}")
        if len(entry.labels) > 1:
            aliases = [l for l in entry.labels if l != entry.canonical_label]
            click.echo(f"  Aliases: {', '.join(aliases)}")
        click.echo("")
        count += 1
        
        if count >= 50:
            click.echo("... (First 50 results shown)")
            break
            
    if count == 0:
        click.echo("Thinking... No entities found.")


@registry.command("add")
@click.option("--in", "registry_path", default="./out/entity_registry.json", help="레지스트리 파일 경로")
@click.option("--label", required=True, help="엔티티 라벨 (정규형)")
@click.option("--type", "entity_type", default="instance", type=click.Choice(['class', 'instance', 'property', 'relation']), help="엔티티 유형")
@click.option("--uri", help="엔티티 URI (미지정 시 자동생성)")
@click.option("--alias", multiple=True, help="동의어/별칭 (여러 개 가능)")
def registry_add(registry_path: str, label: str, entity_type: str, uri: Optional[str], alias: tuple):
    """새 엔티티 등록"""
    from doc2onto.builders.entity_registry import EntityRegistryBuilder
    
    path = Path(registry_path)
    
    # Load or Create
    if path.exists():
        builder = EntityRegistryBuilder.load(path)
    else:
        click.echo(f"🆕 Creating new registry at {path}")
        # Need base_uri from somewhere or default
        builder = EntityRegistryBuilder() 

    if not uri:
        # Use internal helper if available, or just construct
        uri = builder._to_uri(label, entity_type)
    
    entry = builder.registry.register(
        uri=uri,
        label=label,
        entity_type=entity_type,
        run_id="manual-cli",
        aliases=list(alias)
    )
    
    builder.serialize(path)
    
    click.echo(f"✅ Added Entity: {label}")
    click.echo(f"   URI: {uri}")
    click.echo(f"   Aliases: {entry.labels}")


@registry.command("alias")
@click.option("--in", "registry_path", default="./out/entity_registry.json", help="레지스트리 파일 경로")
@click.option("--label", required=True, help="대상 엔티티 라벨 (정규형)")
@click.option("--add", "aliases", required=True, multiple=True, help="추가할 동의어")
def registry_alias(registry_path: str, label: str, aliases: tuple):
    """기존 엔티티에 동의어 추가"""
    from doc2onto.builders.entity_registry import EntityRegistryBuilder
    
    path = Path(registry_path)
    if not path.exists():
        click.echo(f"❌ File not found: {path}")
        return
        
    builder = EntityRegistryBuilder.load(path)
    
    uri = builder.registry.lookup_by_label(label)
    if not uri:
        click.echo(f"❌ Entity not found with label: {label}")
        return
        
    success_count = 0
    for alias in aliases:
        if builder.add_alias(label, alias):
            click.echo(f"   + Added alias: {alias}")
            success_count += 1
        else:
            click.echo(f"   - Failed/Exists: {alias}")
            
    if success_count > 0:
        builder.serialize(path)
        click.echo(f"✅ Updated registry saved to {path}")


@main.group()
def examples():
    """Few-shot 예제(extraction_examples.yaml) 관리"""
    pass


@examples.command("list")
@click.option("--in", "file_path", default="./extraction_examples.yaml", help="예제 파일 경로")
def examples_list(file_path: str):
    """등록된 예제 목록 조회"""
    import yaml
    
    path = Path(file_path)
    if not path.exists():
        click.echo(f"❌ File not found: {path}")
        return
        
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
        
    click.echo(f"📖 Examples: {path}")
    click.echo(f"   Total Count: {len(data)}")
    click.echo("-" * 60)
    
    for idx, item in enumerate(data):
        text = item.get("text", "")
        triples = item.get("triples", [])
        click.echo(f"[{idx}] {text[:60]}{'...' if len(text)>60 else ''}")
        for t in triples:
            click.echo(f"    - ({t.get('subject')}) --[{t.get('predicate')}]--> ({t.get('object')})")
        click.echo("")


@examples.command("add")
@click.option("--in", "file_path", default="./extraction_examples.yaml", help="예제 파일 경로")
@click.option("--text", required=True, help="예제 텍스트")
@click.option("--triple", "triples_raw", multiple=True, help="트리플 (형식: 주어,서술어,목적어)")
def examples_add(file_path: str, text: str, triples_raw: tuple):
    """새 예제 추가 (트리플은 쉼표로 구분)"""
    import yaml
    
    path = Path(file_path)
    data = []
    
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or []
            
    new_triples = []
    for t_str in triples_raw:
        parts = [p.strip() for p in t_str.split(",")]
        if len(parts) != 3:
            click.echo(f"⚠️  Invalid triple format (skipped): {t_str}. Use 'Subject, Predicate, Object'")
            continue
        new_triples.append({
            "subject": parts[0],
            "predicate": parts[1],
            "object": parts[2]
        })
        
    if not new_triples:
        click.echo("❌ No valid triples provided.")
        return
        
    new_entry = {
        "text": text,
        "triples": new_triples
    }
    
    data.append(new_entry)
    
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        
    click.echo(f"✅ Added new example with {len(new_triples)} triples.")


@examples.command("remove")
@click.option("--in", "file_path", default="./extraction_examples.yaml", help="예제 파일 경로")
@click.option("--index", required=True, type=int, help="삭제할 예제 인덱스 (list 명령어로 확인)")
def examples_remove(file_path: str, index: int):
    """예제 삭제"""
    import yaml
    
    path = Path(file_path)
    if not path.exists():
        click.echo(f"❌ File not found: {path}")
        return
        
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or []
        
    if index < 0 or index >= len(data):
        click.echo(f"❌ Invalid index: {index}. Valid range: 0 ~ {len(data)-1}")
        return
        
    removed = data.pop(index)
    
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True, sort_keys=False)
        
    click.echo(f"✅ Removed example [{index}]: {removed.get('text', '')[:30]}...")


if __name__ == "__main__":
    main()

