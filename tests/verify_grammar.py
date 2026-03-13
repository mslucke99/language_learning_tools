
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from services.text.sentence_miner import SentenceMiner
from services.text.tokenizer_service import TokenizerService

class MockDB:
    def get_all_known_words(self, lang): return []

def test_grammar_extraction():
    miner = SentenceMiner(MockDB(), TokenizerService())
    
    with open("tests/grammar_results.txt", "w", encoding="utf-8") as f:
        # 1. Test "Can" pattern: -ㄹ 수 있다
        f.write("--- Testing 'Can' Pattern ---\n")
        text1 = "할 수 있어요."
        res1 = miner.analyze_text(text1, 'ko')
        s1 = res1.sentences[0]
        f.write(f"Sentence: [{s1.text}]\n")
        f.write(f"Tokens: {[(t.text, t.pos, t.lemma) for t in s1.tokens]}\n")
        f.write(f"Grammar: {s1.grammar_patterns}\n\n")
        
        # 2. Test "Want" pattern: -고 싶다
        f.write("--- Testing 'Want' Pattern ---\n")
        text2 = "먹고 싶어요."
        res2 = miner.analyze_text(text2, 'ko')
        s2 = res2.sentences[0]
        f.write(f"Sentence: [{s2.text}]\n")
        f.write(f"Tokens: {[(t.text, t.pos, t.lemma) for t in s2.tokens]}\n")
        f.write(f"Grammar: {s2.grammar_patterns}\n\n")

        # 3. Test "Because" pattern: -기 때문에
        f.write("--- Testing 'Because' Pattern ---\n")
        text3 = "춥기 때문에 안 가요."
        res3 = miner.analyze_text(text3, 'ko')
        s3 = res3.sentences[0]
        f.write(f"Sentence: [{s3.text}]\n")
        f.write(f"Tokens: {[(t.text, t.pos, t.lemma) for t in s3.tokens]}\n")
        f.write(f"Grammar: {s3.grammar_patterns}\n\n")

if __name__ == "__main__":
    test_grammar_extraction()

if __name__ == "__main__":
    test_grammar_extraction()
