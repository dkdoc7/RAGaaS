from typing import List, Tuple, Dict, Any
from app.services.ingestion.spacy_processor import SpacyGraphProcessor
from openai import AsyncOpenAI
from app.core.config import settings
import json
import logging
import re
import urllib.parse
from app.core.fuseki import fuseki_client

logger = logging.getLogger(__name__)

class GraphProcessor:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.namespace_entity = "http://rag.local/entity/"
        self.namespace_relation = "http://rag.local/relation/"
        self.namespace_source = "http://rag.local/source/"

    def _sanitize_uri(self, text: str) -> str:
        """Sanitize text to be used in URI."""
        # Replace spaces with underscores, remove special chars (preserve Korean and Cyrillic)
        clean = re.sub(r'[^a-zA-Z0-9_\uAC00-\uD7A3\u0400-\u04FF]+', '_', text.strip())
        return urllib.parse.quote(clean)

    async def extract_graph_elements(self, text: str, chunk_id: str, kb_id: str, config: Dict[str, Any] = {}) -> Dict[str, Any]:
        """
        Extracts entities and relations from text and returns structured data and RDF triples.
        """
        # Check config for method
        graph_settings = config.get("graph_settings", {})
        method = graph_settings.get("method", "llm") # Default to LLM
        
        if method == "spacy":
            processor = SpacyGraphProcessor(kb_id)
            # Pass merged config or graph_settings? Pass graph_settings
            # Spacy processor currently returns list[str]. 
            # We might need to adjust it later, but for now let's wrap it?
            # Or better, just assume LLM for Neo4j for this task to minimize complexity.
            # But to keep type consistency:
            rdf_triples = await processor.extract_graph_elements(text, chunk_id, graph_settings)
            return {"rdf_triples": rdf_triples, "structured_triples": []}

        # Fallback to LLM (Original Logic)
        # Enhanced Prompt for General-Purpose Graph Extraction
        system_prompt = """
        You are a knowledge-graph construction agent specialized in extracting strict factual relationships.
        
        **Objective:**
        Extract structured knowledge (triples) from the text, adhering to strict factual accuracy and specific formatting rules.

        **STRICT RULES:**
        1. **Do NOT infer or guess relationships.** Only extract what is explicitly written in the text.
        2. **Do NOT create entities** that are not explicitly mentioned.
        3. **DO NOT TRANSLATE ENTITIES.** Keep them in their original language (e.g., "성기훈" -> "성기훈", "Steve Jobs" -> "Steve Jobs").
        4. **PREDICATES MUST BE ENGLISH ONLY** and use **snake_case** (e.g., `creator_of`, `works_at`, `master_of`).
        5. **INVERSE RELATIONS:** For hierarchical or social relationships, output both directions if applicable (e.g., `student_of` AND `teacher_of`) to enrich the graph connectivity.
        6. **CANONICAL NAMES:** Remove titles and honorifics where possible (e.g., "President Lee" -> "Lee").

        **Graph Schema & Relationship Types:**
        **Node Types (Implicit):** Person, Organization, Location, Event, Concept, Creation
        
        **Recommended Relationship Types (snake_case):**
        - **Social/Hierarchical**: `student_of`, `teacher_of`, `master_of`, `subordinate_of`, `leader_of`, `parent_of`, `child_of`, `spouse_of`, `friend_of`, `enemy_of`
        - **Professional/Action**: `works_at`, `employs`, `creator_of`, `created_by`, `member_of`, `participates_in`, `plays_role`, `founded_by`
        - **General/Attribute**: `located_in`, `is_a` (classification), `part_of`, `related_to`, `owns`, `operates`

        **Few-Shot Examples:**
        
        Input: "Apple의 CEO인 팀 쿡은 새로운 아이폰을 발표했다. 이 행사는 캘리포니아에서 열렸다."
        Output:
        {
            "triples": [
                {"subject": "팀 쿡", "predicate": "is_ceo_of", "object": "Apple"},
                {"subject": "Apple", "predicate": "has_ceo", "object": "팀 쿡"},
                {"subject": "팀 쿡", "predicate": "announced", "object": "새로운 아이폰"},
                {"subject": "새로운 아이폰", "predicate": "product_of", "object": "Apple"},
                {"subject": "이 행사", "predicate": "located_in", "object": "캘리포니아"}
            ]
        }
        
        Input: "홍길동은 구미호에게 도술을 배웠다. 그는 이후 산적으로 활동했다."
        Output:
        {
            "triples": [
                {"subject": "홍길동", "predicate": "learned_from", "object": "구미호"},
                {"subject": "홍길동", "predicate": "student_of", "object": "구미호"},
                {"subject": "구미호", "predicate": "teacher_of", "object": "홍길동"},
                {"subject": "홍길동", "predicate": "learned", "object": "도술"},
                {"subject": "홍길동", "predicate": "is_a", "object": "산적"}
            ]
        }
        
        Input: "RAG(Retrieval-Augmented Generation)는 LLM의 할루시네이션을 줄이는 기술이다."
        Output:
        {
            "triples": [
                {"subject": "RAG", "predicate": "is_a", "object": "기술"},
                {"subject": "RAG", "predicate": "reduces", "object": "할루시네이션"},
                {"subject": "할루시네이션", "predicate": "related_to", "object": "LLM"}
            ]
        }
        """

        user_prompt = f"""
        Analyze the following text and extract all relevant triples.
        
        Text:
        {text[:3000]}
        
        Output JSON only.
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            print(f"DEBUG: LLM Response for Graph Extraction:\n{content}")
            
            data = json.loads(content)
            triples_data = data.get("triples", [])
            print(f"DEBUG: Extracted {len(triples_data)} triples from JSON")
            
            rdf_triples = []
            
            # Chunk URI
            chunk_uri = f"<{self.namespace_source}{chunk_id}>"
            
            for item in triples_data:
                subj = self._sanitize_uri(item['subject'])
                pred = self._sanitize_uri(item['predicate'])
                obj = self._sanitize_uri(item['object'])
                
                # URIs
                s_uri = f"<{self.namespace_entity}{subj}>"
                p_uri = f"<{self.namespace_relation}{pred}>"
                o_uri = f"<{self.namespace_entity}{obj}>"
                
                # Triple: Subject - Predicate - Object
                rdf_triples.append(f"{s_uri} {p_uri} {o_uri} .")
                
                # Link Subject to Chunk (provenance)
                # s_uri <http://rag.local/relation/hasSource> chunk_uri
                rdf_triples.append(f"{s_uri} <{self.namespace_relation}hasSource> {chunk_uri} .")
                
                # Link Object to Chunk (optional, but good for discovery)
                rdf_triples.append(f"{o_uri} <{self.namespace_relation}hasSource> {chunk_uri} .")
                
                # Annotate Subject with Label (for human readability / debugging)
                # s_uri <http://www.w3.org/2000/01/rdf-schema#label> "Subject Name"
                rdf_triples.append(f'{s_uri} <http://www.w3.org/2000/01/rdf-schema#label> "{item["subject"]}" .')

                # Annotate Subject with Label (for human readability / debugging)
                # s_uri <http://www.w3.org/2000/01/rdf-schema#label> "Subject Name"
                rdf_triples.append(f'{s_uri} <http://www.w3.org/2000/01/rdf-schema#label> "{item["subject"]}" .')

            return {
                "rdf_triples": rdf_triples,
                "structured_triples": triples_data
            }

        except Exception as e:
            logger.error(f"Error extracting graph elements: {e}")
            return {"rdf_triples": [], "structured_triples": []}

    async def extract_schema_from_text(self, text: str) -> str:
        """
        Generates an ontology schema (Turtle format) from the provided text sample.
        """
        prompt = f"""
        Analyze the following text and design a simple ontology (RDFS/OWL) that represents the key concepts and relationships found in the text.
        
        Text Sample:
        {text[:4000]}
        
        Instructions:
        1. Identify key classes (Class) and properties (Property).
        2. Define them using Turtle (.ttl) syntax.
        3. Use the namespace: @prefix : <http://rag.local/schema#> .
        4. Include standard prefixes (rdf, rdfs, owl, xsd).
        5. Output ONLY the Turtle code. No explanation.
        """
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert Ontology Engineer. Output valid Turtle syntax only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error extracting schema: {e}")
            return "# Error generating schema. Please try again or write manually."
            
graph_processor = GraphProcessor()
