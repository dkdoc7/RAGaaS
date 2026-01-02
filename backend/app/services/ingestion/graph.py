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
        prompt = f"""
        Analyze the following text and extract key entities and their relationships.
        Return a JSON object with a list of "triples".
        Each triple should have:
        - "subject": Entity name (Person, Org, Location, Concept, etc.)
        - "predicate": Relationship (verb phrase, e.g., "is CEO of", "located in", "part of", "master of", "student of")
        - "object": Entity name (Person, Org, Location, Concept, etc.)

        Text:
        {text[:2000]}  # Limit text length to avoid token limits

        Output format:
        {{
            "triples": [
                {{"subject": "Elon Musk", "predicate": "is CEO of", "object": "SpaceX"}},
                ...
            ]
        }}
        """

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a knowledge graph extractor. Extract specific entities and relations. Support Korean text. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            data = json.loads(content)
            triples_data = data.get("triples", [])
            
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

graph_processor = GraphProcessor()
