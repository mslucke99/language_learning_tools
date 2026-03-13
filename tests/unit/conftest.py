import pytest
from src.services.text.difficulty_resources import FrequencyList, ResourceBundle
from src.services.text.sentence_difficulty import UserProfile

@pytest.fixture
def tokenizer_adapter():
    def adapter(text: str, lang_code: str):
        import re
        return [w.lower() for w in re.findall(r"\w+", text) if w]
    return adapter

@pytest.fixture
def empty_resources():
    return ResourceBundle(language="en", frequency_list=None, graded_list=None)

@pytest.fixture
def resources_with_frequency():
    freq = FrequencyList(
        {"the": 1, "cat": 2, "sat": 3, "on": 4, "mat": 5},
        10,
    )
    return ResourceBundle(language="en", frequency_list=freq, graded_list=None)

@pytest.fixture
def user_profile():
    return UserProfile(claimed_level="B1", language="en")
