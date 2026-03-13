
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.services.text.sentence_difficulty import (
    SentenceDifficultyScorer, UserProfile, 
    make_tokenizer_adapter_from_tokenizer_service, 
    make_recall_provider_from_db
)
from src.services.text.tokenizer_service import TokenizerService
from src.services.text.difficulty_resources import ResourceBundle, FrequencyList

class MockDB:
    def __init__(self, known_words):
        self.known_words = [{"lemma": w} for w in known_words]
    def get_all_known_words(self, lang):
        return self.known_words

def run_diagnostic():
    tokenizer = TokenizerService()
    adapter = make_tokenizer_adapter_from_tokenizer_service(tokenizer)
    
    # 1. Setup Resources
    # Simulate a frequency list where common words have low ranks
    freq_data = {
        "안녕하세요": 1,
        "하": 2, # 하다
        "저": 10,
        "는": 5,
        "이것": 50,
        "은": 6,
        "사과": 500,
        "학교": 300,
        "친구": 400,
        "비": 1000,
        "집": 200,
        "고양이": 1500,
    }
    freq = FrequencyList(freq_data, 10000)
    resources = ResourceBundle(language="ko", frequency_list=freq)
    
    # 2. Setup Profile (B1 Learner)
    profile = UserProfile(claimed_level="B1", language="ko")
    
    # 3. Setup Scorer
    # User knows "안녕하세요" and "저"
    db = MockDB(["안녕하세요", "저", "는", "이것", "은"])
    recall_provider = make_recall_provider_from_db(db)
    
    scorer = SentenceDifficultyScorer(adapter, resources, profile, recall_provider)
    
    test_sentences = [
        "안녕하세요.", # Fully known -> Mastered/Review
        "이것은 사과입니다.", # Partly known, one "fairly common" unknown (사과) -> Review/Sweet Spot
        "저는 어제 학교에 가서 친구를 만났지만 비가 와서 일찍 집에 왔어요.", # Complex
        "고양이.", # Unknown but short
        "퀀텀 점프.", # Technical/Rare
    ]
    
    print(f"{'Text':<40} | {'Score':<7} | {'Category':<15} | {'MinRec':<7}")
    print("-" * 75)
    
    for sent in test_sentences:
        res = scorer.score_sentence(sent, "ko")
        print(f"{sent[:39]:<40} | {res.difficulty_score:<7} | {res.difficulty_category:<15} | {res.features['min_recall']:<7}")

if __name__ == "__main__":
    run_diagnostic()
