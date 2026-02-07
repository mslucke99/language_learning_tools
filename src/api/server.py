"""
REST API Server for Language Learning Suite
Provides endpoints for browser extension and external integrations
"""

from flask import Flask, request, jsonify
from src.core.database import FlashcardDatabase
from src.services.llm_service import get_ai_client, is_ai_available
import json
from datetime import datetime
import sys
import io

# Ensure UTF-8 output on Windows for both stdout and stderr
def setup_encoding():
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
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# Health check
@app.route('/api/health', methods=['GET'])
def health():
    """Check if API is running."""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "ai_available": is_ai_available()
    })

# Deck endpoints
@app.route('/api/decks', methods=['GET'])
def get_decks():
    """Get all decks."""
    try:
        language = request.args.get('language')
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
def create_deck():
    """Create a new deck."""
    try:
        data = request.json
        name = data.get('name', '').strip()
        description = data.get('description', '').strip()
        language = data.get('language')
        
        if not name:
            return jsonify({"success": False, "error": "Deck name is required"}), 400
        
        deck_id = db.create_deck(name, description, language=language)
        if deck_id:
            return jsonify({"success": True, "deck_id": deck_id, "name": name})
        else:
            return jsonify({"success": False, "error": "Deck already exists"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/decks/<int:deck_id>', methods=['GET'])
def get_deck(deck_id):
    """Get deck details and statistics."""
    try:
        decks = db.get_all_decks() # TODO: Optimize to get single deck
        deck = next((d for d in decks if d['id'] == deck_id), None)
        
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
def get_cards(deck_id):
    """Get all cards in a deck."""
    try:
        cards = db.get_all_flashcards(deck_id)
        cards_data = [
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
def add_card(deck_id):
    """Add a flashcard to a deck."""
    try:
        data = request.json
        question = data.get('question', '').strip()
        answer = data.get('answer', '').strip()
        
        if not question or not answer:
            return jsonify({"success": False, "error": "Question and answer are required"}), 400
        
        card_id = db.add_flashcard(deck_id, question, answer)
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
def add_cards_batch(deck_id):
    """Add multiple flashcards at once (useful for browser extension)."""
    try:
        data = request.json
        cards = data.get('cards', [])
        
        if not cards:
            return jsonify({"success": False, "error": "No cards provided"}), 400
        
        added = []
        failed = []
        
        for card in cards:
            question = card.get('question', '').strip()
            answer = card.get('answer', '').strip()
            
            if question and answer:
                card_id = db.add_flashcard(deck_id, question, answer)
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
def get_due_cards(deck_id):
    """Get cards due for review."""
    try:
        due_cards = db.get_due_flashcards(deck_id)
        cards_data = [
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
def get_stats(deck_id):
    """Get deck statistics."""
    try:
        stats = db.get_deck_statistics(deck_id)
        cards = db.get_all_flashcards(deck_id)
        
        reviewed_count = sum(1 for c in cards if c.total_reviews > 0)
        avg_easiness = sum(c.easiness for c in cards) / len(cards) if cards else 0.0
        avg_interval = sum(c.interval for c in cards) / len(cards) if cards else 0.0
        
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
def ai_status():
    """Check AI availability."""
    return jsonify({
        "available": is_ai_available(),
        "timestamp": datetime.now().isoformat()
    })

# Legacy Ollama aliases
@app.route('/api/ollama/status', methods=['GET'])
def ollama_status():
    return ai_status()

@app.route('/api/ai/define', methods=['POST'])
def define_word():
    """Get word definition from AI with language context."""
    try:
        if not is_ai_available():
            return jsonify({"success": False, "error": "AI Service not available"}), 503
        
        data = request.json
        word = data.get('word', '').strip()
        language = data.get('language', 'english').strip()
        explain_in = data.get('explain_in', 'english').strip()
        
        if not word:
            return jsonify({"success": False, "error": "Word is required"}), 400
        
        client = get_ai_client()
        
        # Create language-aware prompt
        prompt = f"Define the {language} word '{word}' in {explain_in}. Be concise."
        definition = client.generate_response(prompt)
        
        if definition:
            return jsonify({"success": True, "word": word, "definition": definition, "language": language})
        else:
            return jsonify({"success": False, "error": "Could not define word"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/ollama/define', methods=['POST'])
def define_word_legacy():
    return define_word()

@app.route('/api/ai/explain', methods=['POST'])
def explain_grammar_api():
    """Get grammar explanation from AI with language context."""
    try:
        if not is_ai_available():
            return jsonify({"success": False, "error": "AI Service not available"}), 503
        
        data = request.json
        topic = data.get('topic', '').strip()
        language = data.get('language', 'english').strip()
        explain_in = data.get('explain_in', 'english').strip()
        
        if not topic:
            return jsonify({"success": False, "error": "Topic is required"}), 400
        
        client = get_ai_client()
        
        # Create language-aware prompt
        if language != explain_in:
            enhanced_topic = f"{topic}\n\nUse {explain_in} for your explanation."
        else:
            enhanced_topic = topic
        
        # Use 240 second timeout for larger models
        explanation = client.generate_response(enhanced_topic, timeout=240)

        if explanation:
            return jsonify({"success": True, "topic": topic, "explanation": explanation, "language": language})
        else:
            return jsonify({"success": False, "error": "Could not explain topic"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/ollama/explain', methods=['POST'])
def explain_grammar_api_legacy():
    return explain_grammar_api()

# Health check for browser extension
@app.route('/api/extension/ping', methods=['GET'])
def extension_ping():
    """Simple ping for browser extension to check if API is running."""
    return jsonify({"status": "connected"})

@app.route('/api/ai/models', methods=['GET'])
def get_models():
    """Get list of available models."""
    try:
        client = get_ai_client()
        models = client.get_available_models()
        current_model = client.model
        
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
def get_models_legacy():
    return get_models()

# ===== IMPORTED CONTENT ENDPOINTS =====

@app.route('/api/imported', methods=['GET'])
def get_imported_content():
    """Get imported content from browser extension."""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        content_type = request.args.get('type', None)
        language = request.args.get('language', None)
        
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
def add_imported_content():
    """Add imported content from browser extension."""
    try:
        print('\n[API] POST /api/imported called', flush=True)
        data = request.json
        print(f'[API] Request received', flush=True)
        
        content_type = data.get('content_type', 'word')
        content = data.get('content', '').strip()
        url = data.get('url', '').strip()
        
        # Safe logging without trying to print the actual Unicode content
        content_length = len(content)
        print(f'[API] Extracted: type={content_type}, content_length={content_length}, url_length={len(url)}', flush=True)
        
        if not content or not url:
            print('[API] ERROR: Missing content or URL', flush=True)
            return jsonify({"success": False, "error": "Content and URL are required"}), 400
        
        # Optional fields
        title = data.get('title', '').strip()
        context = data.get('context', '').strip()
        language = data.get('language', '').strip()
        tags = data.get('tags', '').strip()
        
        print('[API] Calling db.add_imported_content...', flush=True)
        content_id = db.add_imported_content(
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
def delete_imported_content(content_id):
    """Delete imported content."""
    try:
        success = db.delete_imported_content(content_id)
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
def mark_content_processed(content_id):
    """Mark imported content as processed."""
    try:
        success = db.mark_content_processed(content_id)
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
def get_imported_stats():
    """Get statistics about imported content."""
    try:
        language = request.args.get('language', None)
        stats = db.get_imported_content_stats(language=language)
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        print(f'[API] Error getting imported stats: {str(e)}', flush=True)
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
