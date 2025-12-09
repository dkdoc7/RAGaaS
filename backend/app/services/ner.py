from typing import List, Set
import re

class NERService:
    """Simple rule-based NER for Korean text"""
    
    def __init__(self):
        # For now, use simple pattern matching
        # Can be upgraded to spacy later
        self.nlp = None
    
    def extract_entities(self, text: str) -> Set[str]:
        """
        Extract named entities from text using simple Korean NER.
        Returns set of entity strings (names, organizations, etc.)
        """
        entities = set()
        
        # Simple Korean name pattern: 2-4 syllable words ending with common name patterns
        # This is a basic implementation - can be improved with spacy
        words = text.split()
        
        for word in words:
            # Remove punctuation
            clean_word = re.sub(r'[^\w\s]', '', word)
            
            # Korean person names (2-4 characters + 씨/선생/배우 등)
            if re.match(r'^[가-힣]{2,4}(씨|선생|배우|감독|작가|님)?$', clean_word):
                # Remove titles
                base_name = re.sub(r'(씨|선생|배우|감독|작가|님)$', '', clean_word)
                if len(base_name) >= 2:
                    entities.add(base_name)
            
            # Standalone 2-3 character names (common Korean name length)
            elif re.match(r'^[가-힣]{2,3}$', clean_word):
                entities.add(clean_word)
        
        return entities
    
    def filter_by_entities(
        self, 
        query: str, 
        results: List[dict], 
        penalty: float = 0.5
    ) -> List[dict]:
        """
        Filter/penalize results based on entity matching.
        
        Args:
            query: Search query
            results: Search results
            penalty: Score multiplier for results missing entities (0-1)
        
        Returns:
            Results with adjusted scores
        """
        # Extract entities from query
        query_entities = self.extract_entities(query)
        
        if not query_entities:
            # No entities found in query, return as-is
            return results
        
        print(f"[NER] Query entities: {query_entities}")
        
        # Check each result
        for result in results:
            content = result.get('content', '')
            content_entities = self.extract_entities(content)
            
            # Check if query entities are in content
            matched = query_entities & content_entities  # Intersection
            
            if not matched:
                # No entity match - apply penalty
                original_score = result['score']
                result['score'] = original_score * penalty
                
                # Store NER score in metadata (preserve existing metadata!)
                if 'metadata' not in result:
                    result['metadata'] = {}
                # Don't overwrite, just add NER fields
                result['metadata']['_ner_original'] = original_score
                result['metadata']['_ner_penalty'] = penalty
                
                print(f"[NER] Penalty applied: {original_score:.4f} → {result['score']:.4f}")
            else:
                print(f"[NER] Match found: {matched}")
        
        # Re-sort by adjusted scores
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results

ner_service = NERService()
