"""
REST API Server for Language Learning Suite
Provides endpoints for browser extension and external integrations
"""

from typing import Any, Dict, Optional, Tuple, Union
from flask import Flask, request, jsonify, Response
from src.core.database import FlashcardDatabase
from src.services.llm_service import get_ai_client, is_ai_available
import json
from datetime import datetime
import sys
import io

# Ensure UTF-8 output on Windows for both stdout and stderr
def setup_encoding() -> None:
    try:
        if sys.stdout.encoding != 'utf-8':
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
        if sys.stderr.encoding != 'utf-8':
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='backslashreplace')
    except Exception:
        pass # Fallback to default if wrapping fails

setup_encoding()

app = Flask(__name__)
db = FlashcardDatabase()

# CORS support for browser extension
@app.after_request
def add_cors_headers(response: Response) -> Response:
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Health check
@app.route('/api/health', methods=['GET'])
def health() -> Response:
    """Check if API is running."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "ai_available": is_ai_available()
    })

# Deck endpoints
@app.route('/api/decks', methods=['GET'])
def get_decks() -> Union[Response, Tuple[Response, int]]:
    """Get all decks."""
    try:
        language: Optional[str] = request.args.get('language')
        safe_lang = str(language).encode('ascii', 'backslashreplace').decode('ascii') if language else 'None'
        print(f'[API] GET /decks - fetching all decks (language={safe_lang})', flush=True)
        decks = db.get_all_decks(language=language)
        print(f'[API] Found {len(decks)} decks', flush=True)
        return jsonify({"success": True, "decks": decks})
    except Exception as e:
        print(f'[API] Error getting decks: {str(e)}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/decks', methods=['POST'])
def create_deck() -> Union[Response, Tuple[Response, int]]:
    """Create a new deck."""
    try:
        data: Optional[Dict[str, Any]] = request.json
        name: str = (data.get('name', '') if data else '').strip()
        description: str = (data.get('description', '') if data else '').strip()
        language: Optional[str] = data.get('language') if data else None
        
        if not name:
            return jsonify({"success": False, "error": "Deck name is required"}), 400
        
        deck_id: Optional[int] = db.create_deck(name, description, language=language)
        if deck_id:
            return jsonify({"success": True, "deck_id": deck_id, "name": name})
        else:
            return jsonify({"success": False, "error": "Deck already exists"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/decks/<int:deck_id>', methods=['GET'])
def get_deck(deck_id: int) -> Union[Response, Tuple[Response, int]]:
    """Get deck details and statistics."""
    try:
        decks = db.get_all_decks() # TODO: Optimize to get single deck
        deck: Optional[Dict[str, Any]] = next((d for d in decks if d['id'] == deck_id), None)
        
        if not deck:
            return jsonify({"success": False, "error": "Deck not found"}), 404
        
        stats = db.get_deck_statistics(deck_id)
        cards = db.get_all_flashcards(deck_id)
        
        return jsonify({
            "success": True,
            "deck": deck,
            "stats": stats,
            "card_count": len(cards)
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# Flashcard endpoints
@app.route('/api/decks/<int:deck_id>/cards', methods=['GET'])
def get_cards(deck_id: int) -> Union[Response, Tuple[Response, int]]:
    """Get all cards in a deck."""
    try:
        cards = db.get_all_flashcards(deck_id)
        cards_data: list[Dict[str, Any]] = [
            {
                "id": c.id,
                "question": c.question,
                "answer": c.answer,
                "accuracy": round(c.get_accuracy(), 1) if c.total_reviews > 0 else 0,
                "reviews": c.total_reviews,
                "easiness": c.easiness
            }
            for c in cards
        ]
        return jsonify({"success": True, "cards": cards_data})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/decks/<int:deck_id>/cards', methods=['POST'])
def add_card(deck_id: int) -> Union[Response, Tuple[Response, int]]:
    """Add a flashcard to a deck."""
    try:
        data: Optional[Dict[str, Any]] = request.json
        question: str = (data.get('question', '') if data else '').strip()
        answer: str = (data.get('answer', '') if data else '').strip()
        
        if not question or not answer:
            return jsonify({"success": False, "error": "Question and answer are required"}), 400
        
        card_id: Optional[int] = db.add_flashcard(deck_id, question, answer)
        if card_id:
            return jsonify({
                "success": True,
                "card_id": card_id,
                "message": "Flashcard added successfully"
            })
        else:
            return jsonify({"success": False, "error": "Failed to add card"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/decks/<int:deck_id>/cards/batch', methods=['POST'])
def add_cards_batch(deck_id: int) -> Union[Response, Tuple[Response, int]]:
    """Add multiple flashcards at once (useful for browser extension)."""
    try:
        data: Optional[Dict[str, Any]] = request.json
        cards: list[Dict[str, Any]] = (data.get('cards', []) if data else [])
        
        if not cards:
            return jsonify({"success": False, "error": "No cards provided"}), 400
        
        added: list[Dict[str, Any]] = []
        failed: list[str] = []
        
        for card in cards:
            question: str = card.get('question', '').strip()
            answer: str = card.get('answer', '').strip()
            
            if question and answer:
                card_id: Optional[int] = db.add_flashcard(deck_id, question, answer)
                if card_id:
                    added.append({"card_id": card_id, "question": question})
                else:
                    failed.append(question)
            else:
                failed.append(card.get('question', 'Unknown'))
        
        return jsonify({
            "success": True,
            "added": len(added),
            "failed": len(failed),
            "cards": added
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/decks/<int:deck_id>/due', methods=['GET'])
def get_due_cards(deck_id: int) -> Union[Response, Tuple[Response, int]]:
    """Get cards due for review."""
    try:
        due_cards = db.get_due_flashcards(deck_id)
        cards_data: list[Dict[str, Any]] = [
            {
                "id": c.id,
                "question": c.question,
                "answer": c.answer,
            }
            for c in due_cards
        ]
        return jsonify({
            "success": True,
            "due_count": len(cards_data),
            "cards": cards_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/decks/<int:deck_id>/stats', methods=['GET'])
def get_stats(deck_id: int) -> Union[Response, Tuple[Response, int]]:
    """Get deck statistics."""
    try:
        stats = db.get_deck_statistics(deck_id)
        cards = db.get_all_flashcards(deck_id)
        
        reviewed_count: int = sum(1 for c in cards if c.total_reviews > 0)
        avg_easiness: float = sum(c.easiness for c in cards) / len(cards) if cards else 0.0
        avg_interval: float = sum(c.interval for c in cards) / len(cards) if cards else 0.0
        
        return jsonify({
            "success": True,
            "stats": {
                **stats,
                "reviewed": reviewed_count,
                "avg_easiness": round(avg_easiness, 2),
                "avg_interval": round(avg_interval, 1)
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

# AI endpoints (Universal)
@app.route('/api/ai/status', methods=['GET'])
def ai_status() -> Response:
    """Check AI availability."""
    return jsonify({
        "available": is_ai_available(),
        "timestamp": datetime.now().isoformat()
    })

# Legacy Ollama aliases
@app.route('/api/ollama/status', methods=['GET'])
def ollama_status() -> Response:
    return ai_status()

@app.route('/api/ai/define', methods=['POST'])
def define_word() -> Union[Response, Tuple[Response, int]]:
    """Get word definition from AI with language context."""
    try:
        if not is_ai_available():
            return jsonify({"success": False, "error": "AI Service not available"}), 503
        
        data: Optional[Dict[str, Any]] = request.json
        word: str = (data.get('word', '') if data else '').strip()
        language: str = (data.get('language', 'english') if data else 'english').strip()
        explain_in: str = (data.get('explain_in', 'english') if data else 'english').strip()
        
        if not word:
            return jsonify({"success": False, "error": "Word is required"}), 400
        
        client = get_ai_client()
        
        # Create language-aware prompt
        prompt: str = f"Define the {language} word '{word}' in {explain_in}. Be concise."
        definition: Optional[str] = client.generate_response(prompt)
        
        if definition:
            return jsonify({"success": True, "word": word, "definition": definition, "language": language})
        else:
            return jsonify({"success": False, "error": "Could not define word"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/ollama/define', methods=['POST'])
def define_word_legacy() -> Union[Response, Tuple[Response, int]]:
    return define_word()

@app.route('/api/ai/explain', methods=['POST'])
def explain_grammar_api() -> Union[Response, Tuple[Response, int]]:
    """Get grammar explanation from AI with language context."""
    try:
        if not is_ai_available():
            return jsonify({"success": False, "error": "AI Service not available"}), 503
        
        data: Optional[Dict[str, Any]] = request.json
        topic: str = (data.get('topic', '') if data else '').strip()
        language: str = (data.get('language', 'english') if data else 'english').strip()
        explain_in: str = (data.get('explain_in', 'english') if data else 'english').strip()
        
        if not topic:
            return jsonify({"success": False, "error": "Topic is required"}), 400
        
        client = get_ai_client()
        
        # Create language-aware prompt
        if language != explain_in:
            enhanced_topic: str = f"{topic}\n\nUse {explain_in} for your explanation."
        else:
            enhanced_topic = topic
        
        # Use 240 second timeout for larger models
        explanation: Optional[str] = client.generate_response(enhanced_topic, timeout=240)

        if explanation:
            return jsonify({"success": True, "topic": topic, "explanation": explanation, "language": language})
        else:
            return jsonify({"success": False, "error": "Could not explain topic"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/ollama/explain', methods=['POST'])
def explain_grammar_api_legacy() -> Union[Response, Tuple[Response, int]]:
    return explain_grammar_api()

# Health check for browser extension
@app.route('/api/extension/ping', methods=['GET'])
def extension_ping() -> Response:
    """Simple ping for browser extension to check if API is running."""
    return jsonify({"status": "connected"})

@app.route('/api/ai/models', methods=['GET'])
def get_models() -> Union[Response, Tuple[Response, int]]:
    """Get list of available models."""
    try:
        client = get_ai_client()
        models: list[str] = client.get_available_models()
        current_model: str = client.model
        
        return jsonify({
            "success": True,
            "available": len(models) > 0,
            "models": models,
            "current_model": current_model,
            "ai_running": is_ai_available()
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "available": False,
            "ai_running": False
        }), 503

@app.route('/api/ollama/models', methods=['GET'])
def get_models_legacy() -> Union[Response, Tuple[Response, int]]:
    return get_models()

# ===== IMPORTED CONTENT ENDPOINTS =====

@app.route('/api/imported', methods=['GET'])
def get_imported_content() -> Union[Response, Tuple[Response, int]]:
    """Get imported content from browser extension."""
    try:
        limit: int = int(request.args.get('limit', 50))
        offset: int = int(request.args.get('offset', 0))
        content_type: Optional[str] = request.args.get('type', None)
        language: Optional[str] = request.args.get('language', None)
        
        if content_type:
            content = db.get_imported_content_by_type(content_type, language=language)
        else:
            content = db.get_imported_content(limit, offset, language=language)
        
        return jsonify({"success": True, "content": content})
    except Exception as e:
        # Safe logging of error
        err_msg = str(e).encode('ascii', 'backslashreplace').decode('ascii')
        print(f'[API] Error getting imported content: {err_msg}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/imported', methods=['POST'])
def add_imported_content() -> Union[Response, Tuple[Response, int]]:
    """Add imported content from browser extension."""
    try:
        print('\n[API] POST /api/imported called', flush=True)
        data: Optional[Dict[str, Any]] = request.json
        print(f'[API] Request received', flush=True)
        
        content_type: str = (data.get('content_type', 'word') if data else 'word')
        content: str = (data.get('content', '').strip() if data else '')
        url: str = (data.get('url', '').strip() if data else '')
        
        # Safe logging without trying to print the actual Unicode content
        content_length: int = len(content)
        print(f'[API] Extracted: type={content_type}, content_length={content_length}, url_length={len(url)}', flush=True)
        
        if not content or not url:
            print('[API] ERROR: Missing content or URL', flush=True)
            return jsonify({"success": False, "error": "Content and URL are required"}), 400
        
        # Optional fields
        title: str = (data.get('title', '').strip() if data else '')
        context: str = (data.get('context', '').strip() if data else '')
        language: str = (data.get('language', '').strip() if data else '')
        tags: str = (data.get('tags', '').strip() if data else '')
        
        print('[API] Calling db.add_imported_content...', flush=True)
        content_id: Optional[int] = db.add_imported_content(
            content_type=content_type,
            content=content,
            url=url,
            title=title,
            context=context,
            language=language,
            tags=tags
        )
        print(f'[API] SUCCESS! content_id={content_id}', flush=True)
        
        # Avoid putting Unicode in the success message if it might be logged
        return jsonify({
            "success": True, 
            "content_id": content_id,
            "message": f"Imported {content_type} successfully"
        })
    except Exception as e:
        err_msg = str(e).encode('ascii', 'backslashreplace').decode('ascii')
        print(f'[API] ERROR: {err_msg}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/imported/<int:content_id>', methods=['DELETE'])
def delete_imported_content(content_id: int) -> Union[Response, Tuple[Response, int]]:
    """Delete imported content."""
    try:
        success: bool = db.delete_imported_content(content_id)
        if success:
            return jsonify({"success": True, "message": "Content deleted"})
        else:
            return jsonify({"success": False, "error": "Content not found"}), 404
    except Exception as e:
        print(f'[API] Error deleting imported content: {str(e)}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/imported/<int:content_id>/processed', methods=['PUT'])
def mark_content_processed(content_id: int) -> Union[Response, Tuple[Response, int]]:
    """Mark imported content as processed."""
    try:
        success: bool = db.mark_content_processed(content_id)
        if success:
            return jsonify({"success": True, "message": "Content marked as processed"})
        else:
            return jsonify({"success": False, "error": "Content not found"}), 404
    except Exception as e:
        print(f'[API] Error marking content processed: {str(e)}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/imported/stats', methods=['GET'])
def get_imported_stats() -> Union[Response, Tuple[Response, int]]:
    """Get statistics about imported content."""
    try:
        language: Optional[str] = request.args.get('language', None)
        stats = db.get_imported_content_stats(language=language)
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        print(f'[API] Error getting imported stats: {str(e)}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/sentences/score', methods=['POST'])
def score_sentences() -> Union[Response, Tuple[Response, int]]:
    """
    Score sentence difficulty. Body: {"sentences": ["...", ...], "language": "en"}.
    Returns list of {sentence, difficulty_score, confidence, category, bottleneck_word, unknown_count}.
    """
    try:
        data: Optional[Dict[str, Any]] = request.json or {}
        sentences: list[str] = data.get('sentences', []) if data else []
        language: str = data.get('language', 'en') if data else 'en'
        if not sentences:
            return jsonify({"success": False, "error": "sentences list required"}), 400
        from src.services.text.tokenizer_service import TokenizerService
        from src.services.text.sentence_difficulty import (
            SentenceDifficultyScorer,
            UserProfile,
            make_tokenizer_adapter_from_tokenizer_service,
            make_recall_provider_from_db,
        )
        from src.services.text.difficulty_resources import load_resource_bundle

        tokenizer = TokenizerService()
        adapter = make_tokenizer_adapter_from_tokenizer_service(tokenizer)
        resources = load_resource_bundle(
            language, db.db_path, load_frequency=True, load_graded=False, load_quantiles=False
        )
        profile = UserProfile(claimed_level="B1", language=language)
        recall_provider = make_recall_provider_from_db(db)
        scorer = SentenceDifficultyScorer(
            tokenizer_adapter=adapter,
            resources=resources,
            user_profile=profile,
            recall_provider=recall_provider,
        )
        results = scorer.score_batch(sentences, lang_code=language)
        out: list[Dict[str, Any]] = [
            {
                "sentence": r.sentence,
                "difficulty_score": r.difficulty_score,
                "confidence": r.confidence,
                "category": r.difficulty_category,
                "bottleneck_word": r.bottleneck_word,
                "unknown_count": r.unknown_count,
            }
            for r in results
        ]
        return jsonify({"success": True, "scores": out})
    except Exception as e:
        print(f'[API] Error scoring sentences: {str(e)}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == '__main__':
    print("Starting Language Learning Suite API Server...")
    print("API running on http://0.0.0.0:5000")
    print("Available endpoints:")
    print("  GET  /api/health")
    print("  GET  /api/decks")
    print("  POST /api/decks")
    print("  GET  /api/decks/<id>")
    print("  GET  /api/decks/<id>/cards")
    print("  POST /api/decks/<id>/cards")
    print("  POST /api/decks/<id>/cards/batch")
    print("  GET  /api/decks/<id>/due")
    print("  GET  /api/decks/<id>/stats")
    print("  GET  /api/ollama/status")
    print("  GET  /api/ollama/models")
    print("  POST /api/ollama/define")
    print("  POST /api/ollama/explain")
    print("  GET  /api/imported")
    print("  POST /api/imported")
    print("  DELETE /api/imported/<id>")
    print("  PUT /api/imported/<id>/processed")
    print("  GET /api/imported/stats")
    print("\nPress Ctrl+C to stop")
    
    # Use 0.0.0.0 to bind to all interfaces and threaded=True for concurrent requests
    # Browser extension will connect via localhost:5000
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
