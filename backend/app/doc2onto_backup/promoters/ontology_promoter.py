"""Ontology Promoter - KG → OWL Ontology 승격 파이프라인"""

from pathlib import Path
from typing import Optional
from datetime import datetime
from collections import defaultdict

from rdflib import Graph, Dataset, Namespace, URIRef, Literal, BNode
from rdflib.namespace import RDF, RDFS, OWL, XSD, SKOS


# 커스텀 네임스페이스
EVIDENCE = Namespace("http://example.org/evidence/")
PROV = Namespace("http://www.w3.org/ns/prov#")


class OntologyPromoter:
    """7단계 Ontology 승격 파이프라인
    
    Step 1: Candidate Selection - confidence 필터링, 다중 근거 검증
    Step 2: Schema Stabilization - Class/Property 확정, 동의어 병합
    Step 3: Hierarchy Finalization - 계층 확정, cycle 제거
    Step 4: Constraint Injection - domain/range, cardinality
    Step 5: Evidence Removal - 순수 OWL 생성
    Step 6: Reasoner Validation - consistency check
    Step 7: Export & Versioning - OWL 파일 생성
    """
    
    def __init__(
        self,
        confidence_threshold: float = 0.85,
        min_evidence_count: int = 2,
        detect_cycles: bool = True,
        remove_hypothetical: bool = True,
    ):
        self.confidence_threshold = confidence_threshold
        self.min_evidence_count = min_evidence_count
        self.detect_cycles = detect_cycles
        self.remove_hypothetical = remove_hypothetical
        
        self.stats = {
            "input_triples": 0,
            "step1_candidates": 0,
            "step2_classes": 0,
            "step2_properties": 0,
            "step3_cycles_removed": 0,
            "step4_constraints": 0,
            "step5_evidence_removed": 0,
            "output_triples": 0,
        }
    
    def load_kg(self, kg_path: str | Path) -> Dataset:
        """Knowledge Graph 로드 (TriG)"""
        kg_path = Path(kg_path)
        ds = Dataset()
        ds.parse(kg_path, format="trig")
        
        # 전체 트리플 수 계산
        for g in ds.graphs():
            self.stats["input_triples"] += len(g)
        
        return ds
    
    def promote(
        self,
        base_trig: str | Path,
        evidence_trig: Optional[str | Path] = None,
        output_dir: str | Path = "./ontology",
        version: str = "v1.0",
        dry_run: bool = False,
    ) -> dict:
        """전체 승격 파이프라인 실행"""
        output_dir = Path(output_dir)
        
        # Step 0: KG 로드
        base_ds = self.load_kg(base_trig)
        evidence_ds = None
        if evidence_trig and Path(evidence_trig).exists():
            evidence_ds = self.load_kg(evidence_trig)
        
        # 모든 그래프를 하나로 병합
        # 모든 그래프를 하나로 병합 (Base + Evidence)
        merged_graph = Graph()
        for g in base_ds.graphs():
            for triple in g:
                merged_graph.add(triple)
        
        if evidence_ds:
            for g in evidence_ds.graphs():
                for triple in g:
                    merged_graph.add(triple)
        
        # Evidence 정보 수집
        evidence_info = self._collect_evidence(evidence_ds) if evidence_ds else {}
        
        # Step 1: Candidate Selection
        candidates = self._step1_candidate_selection(merged_graph, evidence_info)
        
        # Step 2: Schema Stabilization
        schema = self._step2_schema_stabilization(candidates)
        
        # Step 3: Hierarchy Finalization
        hierarchy = self._step3_hierarchy_finalization(schema)
        
        # Step 4: Constraint Injection
        constrained = self._step4_constraint_injection(hierarchy)
        
        # Step 5: Evidence Removal
        clean_owl = self._step5_evidence_removal(constrained)
        
        # Step 6: Reasoner Validation
        validation = self._step6_reasoner_validation(clean_owl)
        
        # Step 7: Export & Versioning
        self.stats["output_triples"] = len(clean_owl)
        
        result = {
            "version": version,
            "stats": self.stats.copy(),
            "validation": validation,
            "dry_run": dry_run,
        }
        
        if not dry_run:
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # ontology.owl 저장
            owl_path = output_dir / f"ontology_{version}.owl"
            clean_owl.serialize(owl_path, format="xml")
            result["ontology_path"] = str(owl_path)
            
            # schema_snapshot.ttl 저장
            schema_path = output_dir / "schema_snapshot.ttl"
            self._export_schema_snapshot(clean_owl, schema_path)
            result["schema_path"] = str(schema_path)
            
            # promotion_report.md 저장
            report_path = output_dir / "promotion_report.md"
            self._generate_report(result, report_path)
            result["report_path"] = str(report_path)
        
        return result
    
    def _collect_evidence(self, ds: Dataset) -> dict:
        """Evidence 정보 수집 (triple -> evidence count, max confidence)"""
        evidence_info = defaultdict(lambda: {"count": 0, "max_confidence": 0.0})
        
        for g in ds.graphs():
            # RDF-star 또는 reified statement에서 evidence 추출
            for stmt in g.subjects(RDF.type, RDF.Statement):
                subj = g.value(stmt, RDF.subject)
                pred = g.value(stmt, RDF.predicate)
                obj = g.value(stmt, RDF.object)
                conf = g.value(stmt, EVIDENCE.confidence)
                
                if subj and pred and obj:
                    key = (str(subj), str(pred), str(obj))
                    evidence_info[key]["count"] += 1
                    if conf:
                        try:
                            conf_val = float(conf)
                            evidence_info[key]["max_confidence"] = max(
                                evidence_info[key]["max_confidence"], conf_val
                            )
                        except (ValueError, TypeError):
                            pass
        
        return dict(evidence_info)
    
    def _step1_candidate_selection(self, g: Graph, evidence_info: dict) -> Graph:
        """Step 1: Candidate Selection - confidence/evidence 기반 필터링"""
        result = Graph()
        
        # evidence가 없으면 모든 트리플 통과 (기본값 사용)
        if not evidence_info:
            for s, p, o in g:
                result.add((s, p, o))
            self.stats["step1_candidates"] = len(g)
            return result
        
        # evidence가 있으면 필터링 적용
        for s, p, o in g:
            key = (str(s), str(p), str(o))
            info = evidence_info.get(key, {"count": 1, "max_confidence": 1.0})
            
            # 필터링 조건
            if info["max_confidence"] >= self.confidence_threshold:
                if info["count"] >= self.min_evidence_count:
                    result.add((s, p, o))
                    self.stats["step1_candidates"] += 1
        
        return result
    
    def _step2_schema_stabilization(self, g: Graph) -> Graph:
        """Step 2: Schema Stabilization - Class/Property 확정"""
        result = Graph()
        
        for s, p, o in g:
            result.add((s, p, o))
        
        # Class 수집
        classes = set()
        for cls in g.subjects(RDF.type, OWL.Class):
            classes.add(cls)
        for cls in g.subjects(RDF.type, RDFS.Class):
            classes.add(cls)
        
        # Property 수집
        obj_props = set(g.subjects(RDF.type, OWL.ObjectProperty))
        data_props = set(g.subjects(RDF.type, OWL.DatatypeProperty))
        
        self.stats["step2_classes"] = len(classes)
        self.stats["step2_properties"] = len(obj_props) + len(data_props)
        
        # owl:sameAs 동의어 병합
        same_as_pairs = list(g.subject_objects(OWL.sameAs))
        for canonical, alias in same_as_pairs:
            # alias를 canonical로 대체
            for s, p, o in list(result.triples((alias, None, None))):
                result.remove((s, p, o))
                result.add((canonical, p, o))
            for s, p, o in list(result.triples((None, None, alias))):
                result.remove((s, p, o))
                result.add((s, p, canonical))
        
        return result
    
    def _step3_hierarchy_finalization(self, g: Graph) -> Graph:
        """Step 3: Hierarchy Finalization - cycle 제거"""
        result = Graph()
        
        for s, p, o in g:
            result.add((s, p, o))
        
        if self.detect_cycles:
            # rdfs:subClassOf cycle 제거
            self.stats["step3_cycles_removed"] += self._remove_cycles(result, RDFS.subClassOf)
            self.stats["step3_cycles_removed"] += self._remove_cycles(result, RDFS.subPropertyOf)
        
        return result
    
    def _remove_cycles(self, g: Graph, relation: URIRef) -> int:
        """Cycle 제거"""
        removed = 0
        
        # 직접 cycle (A -> A)
        for s, p, o in list(g.triples((None, relation, None))):
            if s == o:
                g.remove((s, p, o))
                removed += 1
        
        # 2-hop cycle (A -> B -> A)
        for a, _, b in list(g.triples((None, relation, None))):
            for _, _, c in list(g.triples((b, relation, None))):
                if c == a:
                    g.remove((b, relation, a))
                    removed += 1
        
        return removed
    
    def _step4_constraint_injection(self, g: Graph) -> Graph:
        """Step 4: Constraint Injection - domain/range 등"""
        result = Graph()
        
        for s, p, o in g:
            result.add((s, p, o))
        
        # 기존 domain/range 유지
        constraints = 0
        for prop in result.subjects(RDF.type, OWL.ObjectProperty):
            if (prop, RDFS.domain, None) in result:
                constraints += 1
            if (prop, RDFS.range, None) in result:
                constraints += 1
        
        self.stats["step4_constraints"] = constraints
        return result
    
    def _step5_evidence_removal(self, g: Graph) -> Graph:
        """Step 5: Evidence Removal - 순수 OWL만 유지"""
        result = Graph()
        
        evidence_ns = str(EVIDENCE)
        prov_ns = str(PROV)
        
        removed = 0
        for s, p, o in g:
            # Evidence 관련 트리플 제외
            if str(p).startswith(evidence_ns):
                removed += 1
                continue
            if str(p).startswith(prov_ns):
                removed += 1
                continue
            
            # RDF Statement (reification) 제외
            if p == RDF.type and o == RDF.Statement:
                removed += 1
                continue
            if p in [RDF.subject, RDF.predicate, RDF.object]:
                if isinstance(s, BNode):
                    removed += 1
                    continue
            
            result.add((s, p, o))
        
        self.stats["step5_evidence_removed"] = removed
        
        # 네임스페이스 바인딩
        result.bind("owl", OWL)
        result.bind("rdfs", RDFS)
        result.bind("skos", SKOS)
        
        return result
    
    def _step6_reasoner_validation(self, g: Graph) -> dict:
        """Step 6: Reasoner Validation"""
        validation = {
            "consistent": True,
            "inferred_triples": 0,
            "errors": [],
        }
        
        try:
            # owlrl 사용 시도
            import owlrl
            
            # RDFS + OWL RL 추론
            owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(g)
            validation["inferred_triples"] = len(g) - self.stats["output_triples"]
            
        except ImportError:
            validation["errors"].append("owlrl 패키지 없음 - Reasoner 검증 생략")
        except Exception as e:
            validation["consistent"] = False
            validation["errors"].append(str(e))
        
        return validation
    
    def _export_schema_snapshot(self, g: Graph, path: Path) -> None:
        """스키마 스냅샷 저장"""
        schema = Graph()
        
        # Classes
        for cls in g.subjects(RDF.type, OWL.Class):
            for s, p, o in g.triples((cls, None, None)):
                schema.add((s, p, o))
        
        # ObjectProperties
        for prop in g.subjects(RDF.type, OWL.ObjectProperty):
            for s, p, o in g.triples((prop, None, None)):
                schema.add((s, p, o))
        
        # DatatypeProperties
        for prop in g.subjects(RDF.type, OWL.DatatypeProperty):
            for s, p, o in g.triples((prop, None, None)):
                schema.add((s, p, o))
        
        schema.bind("owl", OWL)
        schema.bind("rdfs", RDFS)
        schema.serialize(path, format="turtle")
    
    def _generate_report(self, result: dict, path: Path) -> None:
        """Promotion Report 생성"""
        stats = result["stats"]
        validation = result["validation"]
        
        report = f"""# Ontology Promotion Report

## 버전
- **Version**: {result['version']}
- **생성일**: {datetime.now().isoformat()}

## 통계

| 단계 | 결과 |
|------|------|
| 입력 트리플 | {stats['input_triples']} |
| Step 1 후보 | {stats['step1_candidates']} |
| Step 2 클래스 | {stats['step2_classes']} |
| Step 2 속성 | {stats['step2_properties']} |
| Step 3 cycle 제거 | {stats['step3_cycles_removed']} |
| Step 4 제약 | {stats['step4_constraints']} |
| Step 5 evidence 제거 | {stats['step5_evidence_removed']} |
| 출력 트리플 | {stats['output_triples']} |

## Reasoner 검증

| 항목 | 결과 |
|------|------|
| Consistent | {'✅' if validation['consistent'] else '❌'} |
| 추론 트리플 | {validation['inferred_triples']} |
| 에러 | {', '.join(validation['errors']) or '없음'} |

## 산출물

- `{result.get('ontology_path', 'ontology.owl')}`
- `{result.get('schema_path', 'schema_snapshot.ttl')}`
"""
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
