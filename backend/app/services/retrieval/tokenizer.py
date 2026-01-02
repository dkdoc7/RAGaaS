"""
Korean Tokenizer Utility using Kiwi morphological analyzer.

Provides two tokenization modes:
- 'strict': Nouns only (NNG, NNP, NR, NP, SL) - for precise keyword matching
- 'extended': Nouns + Verbs + Adjectives + original words - for broader matching
"""

from typing import List, Literal

# Global Kiwi instance (lazy initialization)
_kiwi = None

def _get_kiwi():
    """Lazy initialization of Kiwi to avoid repeated imports."""
    global _kiwi
    if _kiwi is None:
        try:
            from kiwipiepy import Kiwi
            _kiwi = Kiwi()
            
            # Load User Dictionary if exists
            import os
            # Assuming CWD is backend root, or check relative to file
            # Try backend root first
            dic_path = "user_dic.txt"
            if not os.path.exists(dic_path):
                # Try relative to this file
                dic_path = os.path.join(os.path.dirname(__file__), "../../../user_dic.txt")
            
            if os.path.exists(dic_path):
                try:
                    _kiwi.load_user_dictionary(dic_path)
                    print(f"[Tokenizer] Loaded user dictionary from {dic_path}")
                except Exception as e:
                    print(f"[Tokenizer] Failed to load user dictionary: {e}")
                    
        except ImportError:
            print("Warning: Kiwi (kiwipiepy) not found. Will use simple whitespace tokenizer.")
            _kiwi = False  # Use False to indicate unavailable
    return _kiwi


def korean_tokenize(
    text: str,
    mode: Literal['strict', 'extended'] = 'strict',
    include_original_words: bool = False,
    min_length: int = 1
) -> List[str]:
    """
    Tokenize Korean text using Kiwi morphological analyzer.
    
    Args:
        text: Input text to tokenize
        mode: Tokenization mode
            - 'strict': Nouns only (NNG, NNP, NR, NP, SL)
            - 'extended': Nouns + Verbs + Adjectives (NNG, NNP, NR, NP, SL, VV, VA)
        include_original_words: If True, also include original words with particles stripped
                                (useful for proper nouns that Kiwi may not recognize)
        min_length: Minimum token length to include (default 1)
    
    Returns:
        List of extracted tokens
    """
    kiwi = _get_kiwi()
    
    if not kiwi:
        # Fallback to simple whitespace split
        return text.lower().split()
    
    tokens = []
    result = kiwi.analyze(text)
    
    if not result:
        return text.lower().split()
    
    # Define which POS tags to include based on mode
    if mode == 'strict':
        # Nouns only - for precise matching (BM25 standalone)
        allowed_tags = {'NNG', 'NNP', 'NR', 'NP', 'SL'}
    else:  # 'extended'
        # Nouns + Verbs + Adjectives - for broader matching (Hybrid)
        allowed_tags = {'NNG', 'NNP', 'NR', 'NP', 'SL', 'VV', 'VA'}
    
    # Extract tokens from morphological analysis
    best_analysis = result[0][0]
    for token in best_analysis:
        if token.tag in allowed_tags:
            if len(token.form) >= min_length:
                tokens.append(token.form)
    
    # Optionally include original words with particles stripped
    if include_original_words:
        # Common Korean particles (조사) to strip
        particles = '은는이가을를의에서로와과도만'
        for word in text.split():
            # Strip trailing particles
            clean_word = word.rstrip(particles)
            # Also try stripping question marks and other punctuation
            clean_word = clean_word.rstrip('?!.,')
            if len(clean_word) >= min_length and clean_word not in tokens:
                tokens.append(clean_word)
    
    if not tokens:
        # Fallback to simple split if no tokens extracted
        return text.lower().split()
    
    return tokens


def tokenize_for_bm25(text: str, is_query: bool = False) -> List[str]:
    """
    Tokenizer optimized for BM25 standalone search.
    Uses strict mode (nouns only) for precise keyword matching.
    Does NOT include original words - keeps it clean.
    
    Args:
        text: Input text to tokenize
        is_query: Unused for BM25, kept for API compatibility
    """
    return korean_tokenize(
        text,
        mode='strict',
        include_original_words=False,  # BM25 uses clean nouns only
        min_length=2
    )


def tokenize_for_hybrid(text: str, is_query: bool = False) -> List[str]:
    """
    Tokenizer optimized for Hybrid (ANN + BM25) search.
    Uses extended mode (nouns + verbs + adjectives) for broader matching.
    
    Args:
        text: Input text to tokenize
        is_query: If True, also includes original words for better proper noun handling
    """
    return korean_tokenize(
        text,
        mode='extended',
        include_original_words=is_query,
        min_length=2
    )
