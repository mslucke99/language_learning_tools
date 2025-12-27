"""
Ollama integration for grammar explanations and word definitions.
Provides AI-powered language learning assistance using local LLM.
"""

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

import json
from typing import Optional, Dict, List
import threading

class OllamaClient:
    """Client for interacting with local Ollama LLM."""
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = None):
        self.base_url = base_url
        self.available = False
        self.available_models = []
        self.model = None
        self._check_connection()
        
        # If model specified, use it. Otherwise use first available.
        if model and model in self.available_models:
            self.model = model
        elif self.available_models:
            self.model = self.available_models[0]
            print(f'[OLLAMA] Using model: {self.model}')
        else:
            print('[OLLAMA] No models available!')
    
    def _check_connection(self) -> bool:
        """Check if Ollama is running and accessible."""
        if not HAS_REQUESTS:
            print("Warning: requests library not installed. Ollama features disabled.")
            print("Install with: pip install requests")
            self.available = False
            return False
        
        try:
            print('[OLLAMA] Checking connection to', self.base_url, flush=True)
            response = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if response.status_code == 200:
                data = response.json()
                self.available_models = [m["name"] for m in data.get("models", [])]
                self.available = len(self.available_models) > 0
                print(f'[OLLAMA] Found {len(self.available_models)} models: {self.available_models}', flush=True)
                return True
        except Exception as e:
            print(f'[OLLAMA] Connection check failed: {str(e)}', flush=True)
            self.available = False
        return False
    
    def is_available(self) -> bool:
        """Check if Ollama is available."""
        return self.available
    
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        return self.available_models
    
    def set_model(self, model: str) -> bool:
        """Set the model to use."""
        if model in self.available_models:
            self.model = model
            return True
        return False
    
    def explain_grammar(self, grammar_topic: str, example: str = None, language: str = "Spanish", timeout: int = 120) -> Optional[str]:
        """
        Get grammar explanation from Ollama.
        
        Args:
            grammar_topic: The grammar concept to explain (e.g., "preterite tense", "subjunctive")
            example: Optional example sentence
            language: Target language
            timeout: Request timeout in seconds (default 120 for slower models like mistral)
        
        Returns:
            Grammar explanation or None if unavailable
        """
        if not self.available:
            return None
        
        if example:
            prompt = f"""Explain the {language} {grammar_topic} in simple terms. 
            
Example: {example}

Provide a clear, concise explanation suitable for language learners."""
        else:
            prompt = f"""Explain the {language} {grammar_topic} in simple terms.

Provide a clear, concise explanation with examples suitable for language learners."""
        
        try:
            return self._query_model(prompt, timeout=timeout)
        except Exception as e:
            print(f"Error getting grammar explanation: {e}")
            return None
    
    def define_word(self, word: str, language: str = "Spanish") -> Optional[Dict[str, str]]:
        """
        Get word definition and usage from Ollama.
        
        Args:
            word: The word to define
            language: Language of the word
        
        Returns:
            Dictionary with definition, usage, and examples
        """
        if not self.available:
            return None
        
        prompt = f"""Define the {language} word "{word}" in simple terms.

Provide:
1. Definition (1-2 sentences)
2. Part of speech
3. Example sentence
4. Similar words (synonyms)

Format as:
Definition: [your definition]
Part of speech: [noun/verb/adjective/etc]
Example: [example sentence]
Synonyms: [similar words]"""
        
        try:
            response = self._query_model(prompt)
            return self._parse_definition_response(response)
        except Exception as e:
            print(f"Error defining word: {e}")
            return None
    
    def suggest_difficult_words(self, text: str, difficulty_level: str = "intermediate", language: str = "Spanish") -> Optional[List[str]]:
        """
        Suggest words from text that user might not know.
        
        Args:
            text: Text to analyze
            difficulty_level: "beginner", "intermediate", or "advanced"
            language: Target language
        
        Returns:
            List of potentially difficult words
        """
        if not self.available:
            return None
        
        # Limit text length
        if len(text) > 1000:
            text = text[:1000]
        
        prompt = f"""Analyze this {language} text and identify {difficulty_level}-level vocabulary words that might be challenging.

Text: {text}

Return ONLY a comma-separated list of 5-10 words (no explanations or numbering).
Format: word1, word2, word3, etc"""
        
        try:
            response = self._query_model(prompt)
            # Parse response as comma-separated list
            words = [w.strip() for w in response.split(",")]
            # Filter empty strings and keep only valid words
            words = [w for w in words if w and len(w) > 2]
            return words[:10]  # Return max 10 words
        except Exception as e:
            print(f"Error suggesting words: {e}")
            return None
    
    def translate_with_context(self, phrase: str, language: str = "Spanish") -> Optional[str]:
        """
        Translate with contextual explanation.
        
        Args:
            phrase: Phrase to translate
            language: Source language
        
        Returns:
            Translation with context
        """
        if not self.available:
            return None
        
        prompt = f"""Translate this {language} phrase to English and explain why:

Phrase: {phrase}

Provide:
1. Direct translation
2. Idiomatic meaning (if different)
3. When/how to use it"""
        
        try:
            return self._query_model(prompt)
        except Exception as e:
            print(f"Error translating: {e}")
            return None
    
    def generate_response(self, prompt: str, timeout: int = 60) -> str:
        """
        Generate a response from the Ollama model given a prompt.
        Public method for querying the model.
        
        Args:
            prompt: The prompt to send to the model
            timeout: Request timeout in seconds (default 60 for slow hardware)
        
        Returns:
            Model response string or None if unavailable
        """
        return self._query_model(prompt, timeout)
    
    def _query_model(self, prompt: str, timeout: int = 60) -> str:
        """
        Query the Ollama model with a prompt.
        
        Args:
            prompt: The prompt to send
            timeout: Request timeout in seconds (default 60 for slow hardware)
        
        Returns:
            Model response
        """
        if not HAS_REQUESTS:
            return None
        
        if not self.model:
            print('[OLLAMA] No model available!', flush=True)
            return None
        
        try:
            print(f'[OLLAMA] Querying {self.model} with timeout {timeout}s...', flush=True)
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.7,
                },
                timeout=timeout
            )
            
            print(f'[OLLAMA] Response status: {response.status_code}', flush=True)
            
            if response.status_code == 200:
                data = response.json()
                result = data.get("response", "").strip()
                print(f'[OLLAMA] Got response: {len(result)} chars', flush=True)
                return result
            else:
                print(f'[OLLAMA] Error status {response.status_code}: {response.text}', flush=True)
                return None
        except requests.exceptions.Timeout:
            print(f'[OLLAMA] Request timed out after {timeout}s', flush=True)
            return None
        except Exception as e:
            print(f'[OLLAMA] Error querying model: {str(e)}', flush=True)
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_definition_response(self, response: str) -> Dict[str, str]:
        """Parse the definition response into structured data."""
        result = {
            "definition": "",
            "part_of_speech": "",
            "example": "",
            "synonyms": ""
        }
        
        if not response:
            return result
        
        lines = response.split("\n")
        for line in lines:
            if "Definition:" in line:
                result["definition"] = line.replace("Definition:", "").strip()
            elif "Part of speech:" in line:
                result["part_of_speech"] = line.replace("Part of speech:", "").strip()
            elif "Example:" in line:
                result["example"] = line.replace("Example:", "").strip()
            elif "Synonyms:" in line:
                result["synonyms"] = line.replace("Synonyms:", "").strip()
        
        return result
    
    def batch_define_words(self, words: List[str], language: str = "Spanish") -> Dict[str, Optional[Dict]]:
        """
        Define multiple words efficiently.
        
        Args:
            words: List of words to define
            language: Language of the words
        
        Returns:
            Dictionary of word -> definitions
        """
        results = {}
        for word in words[:10]:  # Limit to 10 words
            results[word] = self.define_word(word, language)
        return results


class OllamaThreadedQuery:
    """Helper for async Ollama queries to prevent UI blocking."""
    
    def __init__(self, client: OllamaClient):
        self.client = client
        self.result = None
        self.error = None
    
    def explain_grammar_async(self, grammar_topic: str, callback, example: str = None, language: str = "Spanish"):
        """Query grammar explanation in background thread."""
        def worker():
            try:
                self.result = self.client.explain_grammar(grammar_topic, example, language)
                callback(self.result)
            except Exception as e:
                self.error = str(e)
                callback(None)
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
    
    def suggest_words_async(self, text: str, callback, difficulty_level: str = "intermediate", language: str = "Spanish"):
        """Query word suggestions in background thread."""
        def worker():
            try:
                self.result = self.client.suggest_difficult_words(text, difficulty_level, language)
                callback(self.result)
            except Exception as e:
                self.error = str(e)
                callback(None)
        
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()


# Global client instance
_ollama_client: Optional[OllamaClient] = None

def get_ollama_client(base_url: str = "http://localhost:11434", model: str = "llama2") -> OllamaClient:
    """Get or create the global Ollama client."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient(base_url, model)
    return _ollama_client

def is_ollama_available() -> bool:
    """Check if Ollama is available."""
    client = get_ollama_client()
    return client.is_available()
