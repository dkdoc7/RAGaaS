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
        
        # Build relationship filter based on keywords
        relationship_filter = ""
        if relationship_keywords:
            rel_patterns = []
            for kw in relationship_keywords:
                if kw == "master":
                    rel_patterns.extend(["master", "스승", "teacher", "mentor"])
                elif kw == "student":
                    rel_patterns.extend(["student", "제자", "학생", "disciple"])
                elif kw == "전수":
                    rel_patterns.extend(["전수", "teach", "learn", "inherit"])
            
            if rel_patterns:
                rel_regex = "|".join([re.escape(p) for p in rel_patterns])
                relationship_filter = f'|| regex(str(?pred), "({rel_regex})", "i")'
        
        # Enhanced SPARQL query
        sparql_query = f"""
        PREFIX rel: <{self.namespace_relation}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?chunkUri
        WHERE {{
            {{
                # Entity-based Traversal with flexible relationship matching
                ?start rdfs:label ?label .
                FILTER regex(?label, "({regex_pattern})", "i")
                
                # Property Path: 0 to {hops} steps
                # Use negated property set (anything except hasSource and label)
                ?start (!(rel:hasSource|rdfs:label) | ^!(rel:hasSource|rdfs:label)){{0,{hops}}} ?reachable .
                
                ?reachable rel:hasSource ?chunkUri .
            }}
            UNION
            {{
                # Direct predicate match (relationship names)
                ?s ?p ?o .
                FILTER (
                    regex(str(?p), "({regex_pattern})", "i")
                    {relationship_filter.replace('?pred', '?p') if relationship_filter else ''}
                )
                {{ ?s rel:hasSource ?chunkUri }} UNION {{ ?o rel:hasSource ?chunkUri }}
            }}
            UNION
            {{
                # Content-based match - entities mentioned in same chunk
                ?e1 rdfs:label ?l1 .
                ?e2 rdfs:label ?l2 .
                FILTER regex(?l1, "({regex_pattern})", "i")
                FILTER regex(?l2, "({regex_pattern})", "i")
                FILTER (?e1 != ?e2)
                
                ?e1 rel:hasSource ?chunkUri .
                ?e2 rel:hasSource ?chunkUri .
            }}
        }}
        LIMIT 100
        """
        
        print(f"DEBUG: [Fuseki] SPARQL Query:\n{sparql_query}")
        
        results = fuseki_client.query_sparql(kb_id, sparql_query)
        
        chunk_ids = []
        for binding in results.get("results", {}).get("bindings", []):
            uri = binding.get("chunkUri", {}).get("value", "")
            if uri.startswith("http://rag.local/source/"):
                chunk_ids.append(uri.split("/")[-1])
        
        # Get triples for display
        triples_query = f"""
        PREFIX rel: <{self.namespace_relation}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?s ?sLabel ?p ?o ?oLabel
        WHERE {{
            ?s ?p ?o .
            FILTER (?p != rel:hasSource && ?p != rdfs:label)
            OPTIONAL {{ ?s rdfs:label ?sLabel }}
            OPTIONAL {{ ?o rdfs:label ?oLabel }}
            
            # More flexible filtering
            FILTER (
                regex(?sLabel, "({regex_pattern})", "i") || 
                regex(?oLabel, "({regex_pattern})", "i") || 
                regex(str(?p), "({regex_pattern})", "i")
                {relationship_filter.replace('?pred', '?p') if relationship_filter else ''}
            )
        }}
        LIMIT 30
        """
        
        triples_results = fuseki_client.query_sparql(kb_id, triples_query)
        triples = []
        
        for binding in triples_results.get("results", {}).get("bindings", []):
            s_label = binding.get("sLabel", {}).get("value", binding.get("s", {}).get("value", ""))
            p_uri = binding.get("p", {}).get("value", "")
            o_label = binding.get("oLabel", {}).get("value", binding.get("o", {}).get("value", ""))
            
            # Decode URL-encoded predicates
            p_display = urllib.parse.unquote(p_uri.split("/")[-1]) if "/" in p_uri else p_uri
            
            triples.append({
                "subject": s_label,
                "predicate": p_display,
                "object": o_label
            })
                
        return {
            "chunk_ids": list(set(chunk_ids)),
            "sparql_query": sparql_query.strip(),
            "triples": triples
        }
