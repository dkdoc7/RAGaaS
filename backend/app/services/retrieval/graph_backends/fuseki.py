import re
import urllib.parse
from typing import List, Dict, Any
from .base import GraphBackend
from app.core.fuseki import fuseki_client

class FusekiBackend(GraphBackend):
    """Fuseki (Ontology) implementation of GraphBackend."""

    def __init__(self):
        self.namespace_relation = "http://rag.local/relation/"

    async def query(
        self,
        kb_id: str,
        entities: List[str],
        hops: int,
        query_type: str,
        relationship_keywords: List[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute graph query on Fuseki using SPARQL."""
        
        if not entities:
            return {"chunk_ids": [], "sparql_query": "", "triples": []}

        # Escape entities for SPARQL regex
        safe_entities = [re.escape(e) for e in entities]
        regex_pattern = "|".join(safe_entities)
        
        chunk_ids = []
        path_triples = []
        sparql_query = ""
        
        if query_type == "multi_hop" and hops >= 2:
            # Multi-hop specific query
            sparql_query = f"""
            PREFIX rel: <{self.namespace_relation}>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT DISTINCT ?startLabel ?p1 ?midLabel ?p2 ?endLabel ?chunkUri
            WHERE {{
                # Start Entity
                ?start rdfs:label ?startLabel .
                FILTER regex(?startLabel, "({regex_pattern})", "i")
                
                # Hop 1
                {{ ?start ?p1 ?mid . }} UNION {{ ?mid ?p1 ?start . }}
                FILTER (?p1 != rel:hasSource && ?p1 != rdfs:label)
                ?mid rdfs:label ?midLabel .
                
                # Hop 2
                {{ ?mid ?p2 ?end . }} UNION {{ ?end ?p2 ?mid . }}
                FILTER (?p2 != rel:hasSource && ?p2 != rdfs:label)
                ?end rdfs:label ?endLabel .
                
                # Get Source Chunks from involved entities
                {{ ?start rel:hasSource ?chunkUri . }}
                UNION
                {{ ?mid rel:hasSource ?chunkUri . }}
                UNION
                {{ ?end rel:hasSource ?chunkUri . }}
            }}
            LIMIT 50
            """
            
            print(f"DEBUG: [Fuseki] Multi-hop Query:\n{sparql_query}")
            results = fuseki_client.query_sparql(kb_id, sparql_query)
            
            for binding in results.get("results", {}).get("bindings", []):
                # Extract chunk
                uri = binding.get("chunkUri", {}).get("value", "")
                if uri.startswith("http://rag.local/source/"):
                    chunk_ids.append(uri.split("/")[-1])
                
                # Extract triples from the path
                s = binding.get("startLabel", {}).get("value", "")
                p1_uri = binding.get("p1", {}).get("value", "")
                m = binding.get("midLabel", {}).get("value", "")
                p2_uri = binding.get("p2", {}).get("value", "")
                o = binding.get("endLabel", {}).get("value", "")
                
                p1 = urllib.parse.unquote(p1_uri.split("/")[-1])
                p2 = urllib.parse.unquote(p2_uri.split("/")[-1])
                
                path_triples.append({"subject": s, "predicate": p1, "object": m})
                path_triples.append({"subject": m, "predicate": p2, "object": o})
                
        # Fallback (or if not multi-hop): Standard neighborhood search
        # Execute this if it's NOT multi-hop, OR if multi-hop returned nothing
        if not path_triples:
            if query_type == "multi_hop":
                print("DEBUG: [Fuseki] Multi-hop returned 0 results. Falling back to 1-hop neighborhood.")

            relationship_filter = ""
            if relationship_keywords:
                rel_patterns = []
                for kw in relationship_keywords:
                    # Expand common KD terms
                    if kw in ["master", "스승", "teacher"]:
                        rel_patterns.extend(["master", "스승", "teacher", "mentor"])
                    elif kw in ["student", "제자", "학생"]:
                        rel_patterns.extend(["student", "제자", "학생", "disciple"])
                    else:
                        rel_patterns.append(kw)
                
                if rel_patterns:
                    rel_regex = "|".join([re.escape(p) for p in rel_patterns])
                    relationship_filter = f'FILTER regex(str(?p), "({rel_regex})", "i")'

            sparql_query = f"""
            PREFIX rel: <{self.namespace_relation}>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            
            SELECT DISTINCT ?sLabel ?p ?oLabel ?chunkUri
            WHERE {{
                {{
                    # Forward
                    ?s rdfs:label ?sLabel .
                    FILTER regex(?sLabel, "({regex_pattern})", "i")
                    ?s ?p ?o .
                    FILTER (?p != rel:hasSource && ?p != rdfs:label)
                    {relationship_filter}
                    ?o rdfs:label ?oLabel .
                    OPTIONAL {{ ?o rel:hasSource ?chunkUri }}
                }}
                UNION
                {{
                    # Backward
                    ?o rdfs:label ?oLabel .
                    FILTER regex(?oLabel, "({regex_pattern})", "i")
                    ?s ?p ?o .
                    FILTER (?p != rel:hasSource && ?p != rdfs:label)
                    {relationship_filter}
                    ?s rdfs:label ?sLabel .
                    OPTIONAL {{ ?s rel:hasSource ?chunkUri }}
                }}
            }}
            LIMIT 50
            """
            
            print(f"DEBUG: [Fuseki] Standard Query (Fallback/Normal):\n{sparql_query}")
            results = fuseki_client.query_sparql(kb_id, sparql_query)
            
            for binding in results.get("results", {}).get("bindings", []):
                uri = binding.get("chunkUri", {}).get("value", "")
                if uri.startswith("http://rag.local/source/"):
                    chunk_ids.append(uri.split("/")[-1])
                
                s = binding.get("sLabel", {}).get("value", "")
                p_uri = binding.get("p", {}).get("value", "")
                o = binding.get("oLabel", {}).get("value", "")
                p = urllib.parse.unquote(p_uri.split("/")[-1])
                
                path_triples.append({"subject": s, "predicate": p, "object": o})

        # Deduplicate triples
        unique_triples = []
        seen = set()
        for t in path_triples:
            key = (t['subject'], t['predicate'], t['object'])
            if key not in seen:
                seen.add(key)
                unique_triples.append(t)
                
        return {
            "chunk_ids": list(set(chunk_ids)),
            "sparql_query": sparql_query,
            "triples": unique_triples
        }
