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
        
# Common generic terms that are likely relations or types rather than specific entities
GENERIC_KEYWORDS = {
    "역할", "배우", "감독", "작가", "내용", "정보", "검색", "결과", "질문", "답변",
    "영화", "드라마", "주연", "조연", "등장", "인물", "사람", "남자", "여자",
    "대해", "알려", "설명", "누구", "무엇", "언제", "어디", "어떻게", "왜",
    "하나", "둘", "셋", "우리", "당신", "그", "그녀", "그들", "이것", "저것", "그것",
    "문제", "해결", "방법", "시간", "장소", "이유", "원인", "결과", "특징", "장점", "단점",
    "시즌", "에피소드", "화", "편", "줄거리", "요약", "참고", "문서", "파일", "데이터",
    "오징어", "게", "참가자", "번호", "게임", "승리", "우승", "상금", "죽음", "생존",
    "관련", "관계"
}

# Backward compatibility alias
BLACKLIST = GENERIC_KEYWORDS

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
        Excludes generic keywords.
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
                if len(base_name) >= 2 and base_name not in GENERIC_KEYWORDS:
                    entities.add(base_name)
            
            # Standalone 2-3 character names (common Korean name length)
            elif re.match(r'^[가-힣]{2,3}$', clean_word):
                if clean_word not in GENERIC_KEYWORDS:
                    entities.add(clean_word)
        
        return entities

    def extract_keywords(self, text: str) -> Set[str]:
        """
        Extract generic keywords (relation hints) from text.
        Filters out too broad terms that might overtighten graph search.
        """
        # Terms that are too generic and might cause 0 results if used as strict filters
        # We only want to keep keywords that are likely to appear in relation names (e.g. role, actor)
        RELATION_STOPWORDS = {
            "인물", "사람", "남자", "여자", "내용", "정보", "검색", "결과", 
            "질문", "답변", "대해", "알려", "설명", "누구", "무엇", "언제", 
            "어디", "어떻게", "왜", "하나", "둘", "셋", "우리", "당신", 
            "그", "그녀", "그들", "이것", "저것", "그것", "관련", "관계"
        }
        
        keywords = set()
        words = text.split()
        for word in words:
            clean_word = re.sub(r'[^\w\s]', '', word)
            if clean_word in GENERIC_KEYWORDS and clean_word not in RELATION_STOPWORDS:
                keywords.add(clean_word)
        return keywords
        

    
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
