
from typing import List, Dict, Optional, Union, Tuple
from src.services.text.tokenizer_service import Token

class GrammarPattern:
    def __init__(self, name: str, pattern_id: str, tags: List[Union[str, Tuple[str, ...]]], lemmas: Optional[List[Optional[str]]] = None):
        self.name = name
        self.pattern_id = pattern_id
        self.tags = tags # List of prefixes or tuples of prefixes
        self.lemmas = lemmas # Sequence of required lemmas (None = any), same length as tags

class GrammarExtractor:
    def __init__(self):
        # Broad categories
        V = ('VV', 'VA', 'VX', 'VCP', 'VCN') # Any verb/adjective stem
        
        # Initial Catalog for Korean
        self.catalog = {
            "ko": [
                GrammarPattern("Possibility (-ㄹ 수 있다/없다)", "ko_can", 
                               [V, 'ETM', 'NNB', V], 
                               [None, None, '수', ('있', '없')]),
                GrammarPattern("Want (-고 싶다)", "ko_want",
                               [V, 'EC', 'VX'],
                               [None, '고', '싶']),
                GrammarPattern("Try (-아/어 보다)", "ko_try",
                               [V, 'EC', 'VX'],
                               [None, None, '보']),
                GrammarPattern("Doing for (-아/어 주다)", "ko_help",
                               [V, 'EC', 'VX'],
                               [None, None, '주']),
                GrammarPattern("Because (-기 때문에)", "ko_reason",
                               [V, 'ETN', 'NNB'],
                               [None, '기', '때문']),
            ]
        }

    def extract(self, tokens: List[Token], lang_code: str) -> List[str]:
        """
        Scan tokens for known grammar patterns.
        Returns a list of pattern names found.
        """
        if lang_code not in self.catalog:
            return []
            
        patterns = self.catalog[lang_code]
        found = []
        
        i = 0
        while i < len(tokens):
            for p in patterns:
                if self._matches(tokens, i, p):
                    if p.name not in found:
                        found.append(p.name)
            i += 1
            
        return found

    def _matches(self, tokens: List[Token], start_idx: int, pattern: GrammarPattern) -> bool:
        if start_idx + len(pattern.tags) > len(tokens):
            return False
            
        for j in range(len(pattern.tags)):
            t = tokens[start_idx + j]
            p_tag_spec = pattern.tags[j]
            p_lemma_spec = pattern.lemmas[j] if pattern.lemmas else None
            
            # 1. Check POS tag prefix
            tags_to_check = [p_tag_spec] if isinstance(p_tag_spec, str) else p_tag_spec
            tag_match = any(t.pos.startswith(prefix) for prefix in tags_to_check)
            if not tag_match:
                return False
                
            # 2. Check Lemma if required
            if p_lemma_spec:
                lemmas_to_check = [p_lemma_spec] if isinstance(p_lemma_spec, str) else p_lemma_spec
                lemma_match = False
                for target in lemmas_to_check:
                    # Direct match
                    if t.lemma == target:
                        lemma_match = True
                        break
                    # Root form match (if lemma is '있다', target '있' should match)
                    if t.lemma.endswith('다') and t.lemma[:-1] == target:
                        lemma_match = True
                        break
                
                if not lemma_match:
                    return False
                    
        return True
