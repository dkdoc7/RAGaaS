from typing import List, Dict, Any
from .base import RetrievalStrategy
from app.core.fuseki import fuseki_client
from app.core.config import settings
from app.core.milvus import create_collection
from openai import AsyncOpenAI
import json
import logging
import re
import urllib.parse
from app.services.embedding import embedding_service
import numpy as np

logger = logging.getLogger(__name__)

class GraphRetrievalStrategy(RetrievalStrategy):
    def __init__(self):
        self.namespace_entity = "http://rag.local/entity/"
        self.namespace_relation = "http://rag.local/relation/"
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def search(self, kb_id: str, query: str, top_k: int, **kwargs) -> List[Dict[str, Any]]:
        print(f"DEBUG: Graph Search Start for query: {query}")
        # 1. Extract Entities from Query
        entities = await self._extract_entities(kb_id, query)
        print(f"DEBUG: Extracted entities: {entities}")
        if not entities:
            print(f"No entities found in query: {query}")
            return []

        # 2. SPARQL Search (1-hop or 2-hop)
        graph_hops = kwargs.get("graph_hops", 1)
        print(f"DEBUG: Searching graph with hops={graph_hops}")
        graph_result = self._query_graph(kb_id, entities, hops=graph_hops)
        chunk_ids = graph_result["chunk_ids"]
        print(f"DEBUG: Found {len(chunk_ids)} chunks from graph: {chunk_ids}")
        
        # 3. Fetch content from Milvus (only if we have chunks)
        results = []
        if chunk_ids:
            results = await self._fetch_chunks(kb_id, chunk_ids, query, top_k)
        
        # 4. Add graph metadata
        # If we have results, attach to the first one.
        # If NO results found but we did a graph search, return a dummy result 
        # solely for carrying metadata (Hybrid strategy should handle this).
        
        metadata = {
            "sparql_query": graph_result["sparql_query"],
            "extracted_entities": entities,
            "triples": graph_result["triples"],
            "total_chunks_found": len(chunk_ids)
        }

        if results:
            print("DEBUG: Attaching graph metadata to results")
            results[0]["graph_metadata"] = metadata
        else:
            # Return dummy result with metadata
            print("DEBUG: Returning dummy result for metadata")
            results = [{
                "chunk_id": "GRAPH_METADATA_ONLY",
                "content": "",
                "score": 0.0,
                "metadata": {"source": "graph_metadata"},
                "graph_metadata": metadata
            }]
        
        return results

    async def _extract_entities(self, kb_id: str, query: str) -> List[str]:
        """Extract main entities from the query using LLM and spaCy Gazetteer."""
        entities = set()
        
        # 1. LLM Extraction
        prompt = f"""
        Extract key entities (subjects, objects, concepts, proper nouns) from the search query.
        Include specific terms that might be nodes in a knowledge graph.
        Don't be too generic (e.g., avoid "technology" if a specific name is implied, but include "1인자" or "Master" if present).
        
        Query: {query}
        
        Output format: {{"entities": ["Elon Musk", "SpaceX", "CEO"]}}
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini", # Use smarter model for extraction
                messages=[
                    {"role": "system", "content": "You are a precise entity extractor for Knowledge Graphs. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            content = response.choices[0].message.content
            data = json.loads(content)
            for e in data.get("entities", []):
                entities.add(e)
        except Exception as e:
            logger.error(f"Error extracting query entities with LLM: {e}")

        # 2. spaCy Gazetteer Extraction (Use known entities)
        try:
            from app.services.ingestion.spacy_processor import SpacyGraphProcessor
            # Instantiate processor to access known entities map
            processor = SpacyGraphProcessor(kb_id)
            
            # Use inner nlp pipeline directly? Or add a method to processor to extract from query?
            # Re-using extract_graph_elements seems too heavy as it builds triples.
            # We just want the entities.
            
            # Let's use the processor's resources
            doc = processor.nlp(query)
            
            # Matcher
            matches = processor.matcher(doc)
            for match_id, start, end in matches:
                span = doc[start:end]
                # Apply same normalization!
                norm = processor._normalize_entity(span)
                if norm:
                    entities.add(norm)
            
            # NER (Optional: LLM usually covers this, but spaCy local might catch specific patterns)
            for ent in doc.ents:
                norm = processor._normalize_entity(ent)
                if norm:
                    entities.add(norm)
                    
        except Exception as e:
            logger.warning(f"Error extracting query entities with spaCy: {e}")
            
        return list(entities)

    def _sanitize_uri(self, text: str) -> str:
        # Same logic as GraphProcessor
        clean = re.sub(r'[^a-zA-Z0-9_\uAC00-\uD7A3\u0400-\u04FF]+', '_', text.strip())
        return urllib.parse.quote(clean)

    def _query_graph(self, kb_id: str, entities: List[str], hops: int = 1) -> Dict[str, Any]:
        """Find chunks linked to entities within N hops."""
        
        if not entities:
            return {"chunk_ids": [], "sparql_query": "", "triples": []}

        # Instead of constructing URIs and assuming perfect match, 
        # we construct a Regex Filter for Labels and Predicates.
        
        # Escape entities for SPARQL regex
        import re
        safe_entities = [re.escape(e) for e in entities]
        regex_pattern = "|".join(safe_entities)
        
        # NOTE: This query finds nodes where Label matches one of the entities,
        # OR where a Predicate connecting to/from it matches.
        
        # SPARQL query
        sparql_query = f"""
        PREFIX rel: <{self.namespace_relation}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?chunkUri
        WHERE {{
            {{
                # 1. Entity-based Traversal (Variable Hops)
                # Find nodes with matching labels, then traverse graph (both directions)
                ?start rdfs:label ?label .
                FILTER regex(?label, "({regex_pattern})", "i")
                
                # Property Path: 0 to {hops} steps
                # Step: Any predicate except hasSource, in forward or inverse direction
                ?start ( !rel:hasSource | ^!rel:hasSource ){{0,{hops}}} ?reachable .
                
                ?reachable rel:hasSource ?chunkUri .
            }}
            UNION
            {{
                # 2. Predicate-based Match (Direct)
                # Direct match on relationship names
                ?s ?p ?o .
                FILTER regex(str(?p), "({regex_pattern})", "i")
                {{ ?s rel:hasSource ?chunkUri }} UNION {{ ?o rel:hasSource ?chunkUri }}
            }}
        }}
        LIMIT 100
        """
        
        print(f"DEBUG: SPARQL Query:\n{sparql_query}")
        
        results = fuseki_client.query_sparql(kb_id, sparql_query)
        
        chunk_ids = []
        for binding in results.get("results", {}).get("bindings", []):
            uri = binding.get("chunkUri", {}).get("value", "")
            if uri.startswith("http://rag.local/source/"):
                chunk_ids.append(uri.split("/")[-1])
        
        # Get triples for display - simplified query for UI
        # We just want triples related to the keywords to show context
        triples_query = f"""
        PREFIX rel: <{self.namespace_relation}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?s ?sLabel ?p ?o ?oLabel
        WHERE {{
            ?s ?p ?o .
            FILTER (?p != rel:hasSource)
            OPTIONAL {{ ?s rdfs:label ?sLabel }}
            OPTIONAL {{ ?o rdfs:label ?oLabel }}
            
            # Filter where s, p, or o label matches keywords
            FILTER (
                regex(?sLabel, "({regex_pattern})", "i") || 
                regex(?oLabel, "({regex_pattern})", "i") || 
                regex(str(?p), "({regex_pattern})", "i")
            )
        }}
        LIMIT 20
        """
        
        triples_results = fuseki_client.query_sparql(kb_id, triples_query)
        triples = []
        
        for binding in triples_results.get("results", {}).get("bindings", []):
            s_label = binding.get("sLabel", {}).get("value", binding.get("s", {}).get("value", ""))
            p_uri = binding.get("p", {}).get("value", "")
            o_label = binding.get("oLabel", {}).get("value", binding.get("o", {}).get("value", ""))
            
            p_display = p_uri.split("/")[-1] if "/" in p_uri else p_uri
            
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

    async def _fetch_chunks(self, kb_id: str, chunk_ids: List[str], query: str, top_k: int) -> List[Dict[str, Any]]:
        collection = create_collection(kb_id)
        collection.load()
        
        # Limit to avoid huge query
        target_ids = chunk_ids[:100] # Safety limit
        
        expr = f'chunk_id in {json.dumps(target_ids)}'
        
        results = collection.query(
            expr=expr,
            output_fields=["content", "doc_id", "chunk_id", "vector"]
        )
        
        retrieved = []
        
        # Calculate cosine similarity for scoring (so we can merge with vector results)
        query_vec = (await embedding_service.get_embeddings([query]))[0]
        
        for hit in results:
            chunk_vector = hit.get("vector")
            cosine_score = 0.0
            if chunk_vector:
                cosine_score = self._cosine_similarity(query_vec, chunk_vector)
            
            # Boost score for Graph results? 
            # Or just return raw cosine. 
            # Let's return raw cosine but maybe mark them as "graph" origin in metadata.
            
            retrieved.append({
                "chunk_id": hit.get("chunk_id"),
                "content": hit.get("content"),
                "score": cosine_score,
                "metadata": {
                    "doc_id": hit.get("doc_id"),
                    "source": "graph"
                }
            })
            
        retrieved.sort(key=lambda x: x["score"], reverse=True)
        return retrieved[:top_k]

    def _cosine_similarity(self, vec1, vec2) -> float:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return float(np.dot(v1, v2) / (norm1 * norm2))
