"""
Entity and Relation Extraction Service using LLM

Extracts entities (Person, Organization, Location, Product, Concept) 
and relations from text chunks for graph RAG.
"""

import json
import logging
from typing import Dict, List, Optional
from openai import OpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

# Default prompts
DEFAULT_ENTITY_PROMPT = """Extract named entities from the following text. Identify:
- Person names
- Organizations
- Locations
- Products
- Concepts (important terms or ideas)

Return ONLY a JSON object in this exact format (no markdown, no code blocks):
{{
  "entities": [
    {{"id": "e1", "type": "Person", "name": "..."}},
    {{"id": "e2", "type": "Organization", "name": "..."}}
  ]
}}

Text: {chunk_text}"""

DEFAULT_RELATION_PROMPT = """Given the entities: {entities}

Extract relationships between them from this text: {chunk_text}

Identify relations like:
- works_at (Person -> Organization)
- located_in (Organization -> Location)
- part_of (Entity -> Entity)
- related_to (any connection)

Return ONLY a JSON object in this exact format (no markdown, no code blocks):
{{
  "relations": [
    {{"subject": "e1", "predicate": "works_at", "object": "e2"}}
  ]
}}"""


class EntityExtractionService:
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        
    def extract_entities_relations(
        self,
        chunk_text: str,
        entity_prompt: Optional[str] = None,
        relation_prompt: Optional[str] = None
    ) -> Dict[str, List]:
        """
        Extract entities and relations from a text chunk
        
        Args:
            chunk_text: Text to extract from
            entity_prompt: Custom entity extraction prompt (optional)
            relation_prompt: Custom relation extraction prompt (optional)
            
        Returns:
            Dictionary with 'entities' and 'relations' lists
        """
        # Step 1: Extract entities
        entities = self._extract_entities(chunk_text, entity_prompt)
        
        if not entities:
            return {"entities": [], "relations": []}
        
        # Step 2: Extract relations
        relations = self._extract_relations(chunk_text, entities, relation_prompt)
        
        return {
            "entities": entities,
            "relations": relations
        }
    
    def _extract_entities(
        self,
        chunk_text: str,
        custom_prompt: Optional[str] = None
    ) -> List[Dict]:
        """Extract entities using LLM"""
        prompt = custom_prompt or DEFAULT_ENTITY_PROMPT
        prompt = prompt.format(chunk_text=chunk_text)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at extracting named entities from text. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up the response - handle various formats
            # Remove markdown code blocks if present
            if "```json" in result_text:
                # Extract JSON from ```json ... ``` blocks
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()
            elif result_text.startswith("```"):
                # Remove generic ``` blocks
                lines = result_text.split("\n")
                result_text = "\n".join(lines[1:-1])
            
            # Try to find JSON object in the text
            if not result_text.startswith("{"):
                # Find first { and last }
                start_idx = result_text.find("{")
                end_idx = result_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    result_text = result_text[start_idx:end_idx+1]
            
            result = json.loads(result_text)
            entities = result.get("entities", [])
            
            logger.info(f"Extracted {len(entities)} entities")
            return entities
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse entity JSON: {e}")
            logger.error(f"Response text: {result_text[:500]}")  # Log first 500 chars
            return []
        except Exception as e:
            logger.error(f"Error extracting entities: {e}")
            return []
    
    def _extract_relations(
        self,
        chunk_text: str,
        entities: List[Dict],
        custom_prompt: Optional[str] = None
    ) -> List[Dict]:
        """Extract relations between entities using LLM"""
        if not entities:
            return []
        
        # Format entities for prompt
        entities_str = json.dumps(entities, ensure_ascii=False)
        
        prompt = custom_prompt or DEFAULT_RELATION_PROMPT
        prompt = prompt.format(chunk_text=chunk_text, entities=entities_str)
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert at identifying relationships between entities. Always return valid JSON."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.0,
                max_tokens=1000
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up the response - handle various formats
            if "```json" in result_text:
                start = result_text.find("```json") + 7
                end = result_text.find("```", start)
                result_text = result_text[start:end].strip()
            elif result_text.startswith("```"):
                lines = result_text.split("\n")
                result_text = "\n".join(lines[1:-1])
            
            # Try to find JSON object in the text
            if not result_text.startswith("{"):
                start_idx = result_text.find("{")
                end_idx = result_text.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    result_text = result_text[start_idx:end_idx+1]
            
            result = json.loads(result_text)
            relations = result.get("relations", [])
            
            logger.info(f"Extracted {len(relations)} relations")
            return relations
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse relation JSON: {e}")
            logger.error(f"Response text: {result_text[:500]}")
            return []
        except Exception as e:
            logger.error(f"Error extracting relations: {e}")
            return []


# Singleton instance
entity_extraction_service = EntityExtractionService()
