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
        
        # 1. Analyze query for semantic understanding
        query_analysis = await self._analyze_query(query)
        print(f"DEBUG: Query analysis: {query_analysis}")
        
        # 2. Extract Entities from Query
        entities = await self._extract_entities(kb_id, query)
        print(f"DEBUG: Extracted entities: {entities}")
        
        # 3. Expand entities - find related entities in graph
        expanded_entities = await self._expand_entities(kb_id, entities)
        print(f"DEBUG: Expanded entities: {expanded_entities}")
        
        all_entities = list(set(entities + expanded_entities))
        
        if not all_entities:
            print(f"No entities found in query: {query}")
            return []

        # 4. SPARQL Search with semantic relationship understanding
        graph_hops = kwargs.get("graph_hops", 1)
        
        # Detect if query asks for multi-hop relationships
        if any(keyword in query.lower() for keyword in ["의 스승의", "의 제자의", "master's master", "student's student"]):
            graph_hops = max(graph_hops, 2)
            print(f"DEBUG: Detected multi-hop query, setting hops to {graph_hops}")
        
        print(f"DEBUG: Searching graph with hops={graph_hops}")
        graph_result = self._query_graph_semantic(
            kb_id, 
            all_entities, 
            hops=graph_hops,
            query_type=query_analysis.get("query_type"),
            relationship_keywords=query_analysis.get("relationship_keywords", [])
        )
        
        chunk_ids = graph_result["chunk_ids"]
        print(f"DEBUG: Found {len(chunk_ids)} chunks from graph: {chunk_ids}")
        
        # 5. Fetch content from Milvus
        results = []
        if chunk_ids:
            results = await self._fetch_chunks(kb_id, chunk_ids, query, top_k)
        
        # 6. Fallback: If graph search found nothing, use hybrid search on related content
        if not results or (len(results) == 1 and results[0].get("chunk_id") == "GRAPH_METADATA_ONLY"):
            print("DEBUG: Graph search incomplete, using hybrid fallback")
            fallback_results = await self._fallback_search(kb_id, query, all_entities, top_k)
            if fallback_results:
                results = fallback_results
        
        # 7. Add graph metadata
        metadata = {
            "sparql_query": graph_result["sparql_query"],
            "extracted_entities": entities,
            "expanded_entities": expanded_entities,
            "triples": graph_result["triples"],
            "total_chunks_found": len(chunk_ids),
            "query_analysis": query_analysis
        }

        if results and results[0].get("chunk_id") != "GRAPH_METADATA_ONLY":
            print("DEBUG: Attaching graph metadata to results")
            results[0]["graph_metadata"] = metadata
        else:
            # Return dummy result with metadata
            print("DEBUG: Returning metadata-only result")
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
    
    async def _analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze query to understand semantic intent and relationship types."""
        analysis = {
            "query_type": "simple",  # simple, relationship, multi_hop
            "relationship_keywords": [],
            "direction": None  # forward, backward, bidirectional
        }
        
        # Detect relationship queries
        relationship_patterns = {
            "master": ["스승", "선생", "master", "teacher", "mentor"],
            "student": ["제자", "학생", "student", "disciple"],
            "전수": ["전수", "전해", "배우", "가르치", "teach", "learn"],
            "관계": ["관계", "연결", "relationship", "connection"]
        }
        
        query_lower = query.lower()
        
        for rel_type, keywords in relationship_patterns.items():
            if any(kw in query_lower for kw in keywords):
                analysis["relationship_keywords"].append(rel_type)
        
        # Detect multi-hop queries
        multi_hop_patterns = ["의 스승의", "의 제자의", "'s master's", "'s student's", "누구의 누구"]
        if any(pattern in query_lower for pattern in multi_hop_patterns):
            analysis["query_type"] = "multi_hop"
            analysis["hops"] = 2  # Detect number of hops
        elif any(kw in query_lower for kw in ["스승", "제자", "master", "student", "teacher"]):
            analysis["query_type"] = "relationship"
        
        # Use LLM for better understanding
        try:
            prompt = f"""
            Analyze this search query and extract:
            1. The main subject/entity being asked about
            2. The type of relationship being queried (if any)
            3. Whether it's a multi-hop query (e.g., "A's B's C")
            4. Potential alternative entity names or aliases
            
            Query: {query}
            
            Output format:
            {{
                "subject": "main entity name",
                "relationship_type": "master/student/creator/etc or null",
                "is_multi_hop": true/false,
                "hop_count": 1 or 2 or 3,
                "alternatives": ["alternative names or related entities"]
            }}
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a query analyzer for graph search. Be precise and output only JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            llm_analysis = json.loads(response.choices[0].message.content)
            analysis.update(llm_analysis)
            
        except Exception as e:
            logger.warning(f"Error in LLM query analysis: {e}")
        
        return analysis
    
    async def _expand_entities(self, kb_id: str, entities: List[str]) -> List[str]:
        """Expand entities by finding related entities in the graph."""
        if not entities:
            return []
        
        expanded = set()
        
        # Escape entities for SPARQL
        safe_entities = [re.escape(e) for e in entities]
        regex_pattern = "|".join(safe_entities)
        
        # Find entities connected to the initial entities
        expand_query = f"""
        PREFIX rel: <{self.namespace_relation}>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT DISTINCT ?relatedLabel
        WHERE {{
            {{
                # Find entities with matching labels
                ?entity rdfs:label ?entityLabel .
                FILTER regex(?entityLabel, "({regex_pattern})", "i")
                
                # Get connected entities (1-hop)
                ?entity ?pred ?related .
                FILTER (?pred != rel:hasSource)
                FILTER (?pred != rdfs:label)
                
                OPTIONAL {{ ?related rdfs:label ?relatedLabel }}
            }}
            UNION
            {{
                # Inverse direction
                ?related ?pred ?entity .
                FILTER (?pred != rel:hasSource)
                FILTER (?pred != rdfs:label)
                
                ?entity rdfs:label ?entityLabel .
                FILTER regex(?entityLabel, "({regex_pattern})", "i")
                
                OPTIONAL {{ ?related rdfs:label ?relatedLabel }}
            }}
        }}
        LIMIT 50
        """
        
        try:
            results = fuseki_client.query_sparql(kb_id, expand_query)
            for binding in results.get("results", {}).get("bindings", []):
                label = binding.get("relatedLabel", {}).get("value", "")
                if label and label not in entities:
                    expanded.add(label)
        except Exception as e:
            logger.warning(f"Error expanding entities: {e}")
        
        return list(expanded)[:10]  # Limit to prevent explosion


    def _sanitize_uri(self, text: str) -> str:
        # Same logic as GraphProcessor
        clean = re.sub(r'[^a-zA-Z0-9_\uAC00-\uD7A3\u0400-\u04FF]+', '_', text.strip())
        return urllib.parse.quote(clean)

    def _query_graph_semantic(
        self, 
        kb_id: str, 
        entities: List[str], 
        hops: int = 1,
        query_type: str = "simple",
        relationship_keywords: List[str] = None
    ) -> Dict[str, Any]:
        """Enhanced graph query with semantic relationship understanding."""
        
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
        
        # Enhanced SPARQL query with semantic understanding
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
        
        print(f"DEBUG: Enhanced SPARQL Query:\n{sparql_query}")
        
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
    
    async def _fallback_search(self, kb_id: str, query: str, entities: List[str], top_k: int) -> List[Dict[str, Any]]:
        """Fallback to hybrid vector+keyword search when graph doesn't have complete data."""
        from .vector import VectorRetrievalStrategy
        from .hybrid import HybridRetrievalStrategy
        
        # Construct enhanced query with entities
        enhanced_query = query + " " + " ".join(entities)
        
        print(f"DEBUG: Fallback search with query: {enhanced_query}")
        
        try:
            # Use hybrid search for best results
            hybrid_strategy = HybridRetrievalStrategy()
            results = await hybrid_strategy.search(
                kb_id=kb_id,
                query=enhanced_query,
                top_k=top_k,
                score_threshold=0.0,
                metric_type="COSINE"
            )
            
            # Mark these as fallback results
            for result in results:
                if "metadata" not in result:
                    result["metadata"] = {}
                result["metadata"]["source"] = "graph_fallback"
            
            return results
        except Exception as e:
            logger.error(f"Error in fallback search: {e}")
            return []

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
            
            # BOOST: Graph-discovered chunks get a score boost
            # These were found through semantic graph relationships,
            # so they're likely more relevant than pure vector similarity suggests
            graph_boost = 1.5  # 50% boost for graph-discovered chunks
            boosted_score = min(cosine_score * graph_boost, 1.0)  # Cap at 1.0
            
            retrieved.append({
                "chunk_id": hit.get("chunk_id"),
                "content": hit.get("content"),
                "score": boosted_score,
                "metadata": {
                    "doc_id": hit.get("doc_id"),
                    "source": "graph",
                    "original_score": cosine_score,
                    "boosted": True
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
