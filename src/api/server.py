"""
REST API Server for Language Learning Suite
Provides endpoints for browser extension and external integrations
"""

from flask import Flask, request, jsonify
from src.core.database import FlashcardDatabase
from src.services.llm_service import get_ollama_client, is_ollama_available
import json
from datetime import datetime

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
        "ollama_available": is_ollama_available()
    })

# Deck endpoints
@app.route('/api/decks', methods=['GET'])
def get_decks():
    """Get all decks."""
    try:
        print('[API] GET /decks - fetching all decks', flush=True)
        decks = db.get_all_decks()
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
        
        if not name:
            return jsonify({"success": False, "error": "Deck name is required"}), 400
        
        deck_id = db.create_deck(name, description)
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
        decks = db.get_all_decks()
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

# Ollama AI endpoints (for browser extension)
@app.route('/api/ollama/status', methods=['GET'])
def ollama_status():
    """Check Ollama availability."""
    return jsonify({
        "available": is_ollama_available(),
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/ollama/define', methods=['POST'])
def define_word():
    """Get word definition from Ollama with language context."""
    try:
        if not is_ollama_available():
            return jsonify({"success": False, "error": "Ollama not available"}), 503
        
        data = request.json
        word = data.get('word', '').strip()
        language = data.get('language', 'english').strip()
        explain_in = data.get('explain_in', 'english').strip()
        
        if not word:
            return jsonify({"success": False, "error": "Word is required"}), 400
        
        client = get_ollama_client()
        
        # Create language-aware prompt
        prompt = f"Define the {language} word '{word}' in {explain_in}. Be concise."
        definition = client.explain_grammar(prompt)
        
        if definition:
            return jsonify({"success": True, "word": word, "definition": definition, "language": language})
        else:
            return jsonify({"success": False, "error": "Could not define word"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/ollama/explain', methods=['POST'])
def explain_grammar_api():
    """Get grammar explanation from Ollama with language context."""
    try:
        print('[OLLAMA] POST /ollama/explain - checking availability', flush=True)
        
        if not is_ollama_available():
            print('[OLLAMA] Ollama not available', flush=True)
            return jsonify({"success": False, "error": "Ollama not available"}), 503
        
        data = request.json
        print(f'[OLLAMA] Request data: {data}', flush=True)
        
        topic = data.get('topic', '').strip()
        language = data.get('language', 'english').strip()
        explain_in = data.get('explain_in', 'english').strip()
        
        print(f'[OLLAMA] topic={topic}, language={language}, explain_in={explain_in}', flush=True)
        
        if not topic:
            print('[OLLAMA] Topic is empty', flush=True)
            return jsonify({"success": False, "error": "Topic is required"}), 400
        
        client = get_ollama_client()
        
        # Create language-aware prompt
        if language != explain_in:
            enhanced_topic = f"{topic}\n\nUse {explain_in} for your explanation."
        else:
            enhanced_topic = topic
        
        print(f'[OLLAMA] Calling explain_grammar with enhanced_topic...', flush=True)
        # Use 240 second timeout for larger models like mistral (may take 30-60+ seconds on slow hardware)
        explanation = client.explain_grammar(enhanced_topic, timeout=240)

        if explanation:
            print(f'[OLLAMA] Got explanation, returning success', flush=True)
            return jsonify({"success": True, "topic": topic, "explanation": explanation, "language": language})
        else:
            print('[OLLAMA] explain_grammar returned empty', flush=True)
            return jsonify({"success": False, "error": "Could not explain topic"}), 400
    except Exception as e:
        print(f'[OLLAMA] Exception: {str(e)}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400

# Health check for browser extension
@app.route('/api/extension/ping', methods=['GET'])
def extension_ping():
    """Simple ping for browser extension to check if API is running."""
    return jsonify({"status": "connected"})

# Get available Ollama models
@app.route('/api/ollama/models', methods=['GET'])
def get_models():
    """Get list of available Ollama models."""
    try:
        print('[OLLAMA] GET /ollama/models - fetching available models', flush=True)
        client = get_ollama_client()
        models = client.get_available_models()
        current_model = client.model
        
        print(f'[OLLAMA] Found {len(models)} models, current model: {current_model}', flush=True)
        
        return jsonify({
            "success": True,
            "available": len(models) > 0,
            "models": models,
            "current_model": current_model,
            "ollama_running": is_ollama_available()
        })
    except Exception as e:
        print(f'[OLLAMA] Error getting models: {str(e)}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": str(e),
            "available": False,
            "ollama_running": False
        }), 503

# ===== IMPORTED CONTENT ENDPOINTS =====

@app.route('/api/imported', methods=['GET'])
def get_imported_content():
    """Get imported content from browser extension."""
    try:
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))
        content_type = request.args.get('type', None)
        
        if content_type:
            content = db.get_imported_content_by_type(content_type)
        else:
            content = db.get_imported_content(limit, offset)
        
        return jsonify({"success": True, "content": content})
    except Exception as e:
        print(f'[API] Error getting imported content: {str(e)}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/imported', methods=['POST'])
def add_imported_content():
    """Add imported content from browser extension."""
    try:
        print('\n[API] POST /api/imported called', flush=True)
        data = request.json
        print(f'[API] Request JSON: {data}', flush=True)
        
        content_type = data.get('content_type', 'word')
        content = data.get('content', '').strip()
        url = data.get('url', '').strip()
        
        print(f'[API] Extracted: type={content_type}, content={content[:50]}, url={url}', flush=True)
        
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
        
        return jsonify({
            "success": True, 
            "content_id": content_id,
            "message": f"Imported {content_type}: {content[:50]}..."
        })
    except Exception as e:
        print(f'[API] ERROR: {str(e)}', flush=True)
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
        stats = db.get_imported_content_stats()
        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        print(f'[API] Error getting imported stats: {str(e)}', flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == '__main__':
    print("Starting Language Learning Suite API Server...")
    print("API running on http://localhost:5000")
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
    
    app.run(host='localhost', port=5000, debug=False)
