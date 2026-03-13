
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.text.sentence_miner import SentenceMiner
from services.text.tokenizer_service import TokenizerService

class MockDB:
    def get_all_known_words(self, lang): return []

def test_morphology():
    miner = SentenceMiner(MockDB(), TokenizerService())
    
    # 1. Test Korean Particles
    print("--- Testing Korean Particles ---")
    text = "사과는 있다."
    # '사과' (NNG) -> unknown
    # '는' (JX) -> ignored
    # '있' (VV) -> '있다' (lemma), unknown
    # '.' (SF) -> ignored
    
    result = miner.analyze_text(text, 'ko')
    s = result.sentences[0]
    print(f"Sentence: [{s.text}]")
    print(f"Unknown Tokens: {[t.text for t in s.unknown_words]}")
    print(f"Unknown Lemmas: {[t.lemma for t in s.unknown_words]}")
    print(f"Level: {s.level} (Expected: 2)")
    
    # 2. Test Verb Recovery
    print("\n--- Testing Verb Recovery ---")
    text_verb = "먹었다."
    # '먹' (VV) -> '먹다' (lemma)
    # '었' (EP) -> ignored
    # '다' (EF) -> ignored
    
    result_verb = miner.analyze_text(text_verb, 'ko')
    s_verb = result_verb.sentences[0]
    print(f"Sentence: [{s_verb.text}]")
    unknown_lemmas = [t.lemma for t in s_verb.unknown_words]
    print(f"Unknown Lemmas: {unknown_lemmas}")
    print(f"Level: {s_verb.level} (Expected: 1)")
    
    # 3. Test Numbers (previously fixed)
    print("\n--- Testing Numbers (should still be ignored) ---")
    text_num = "2024년"
    # '2024' (SN) -> ignored
    # '년' (NNB) -> unknown
    
    result_num = miner.analyze_text(text_num, 'ko')
    s_num = result_num.sentences[0]
    print(f"Sentence: [{s_num.text}]")
    print(f"Unknown Lemmas: {[t.lemma for t in s_num.unknown_words]}")
    print(f"Level: {s_num.level} (Expected: 1)")

if __name__ == "__main__":
    test_morphology()
