import csv
import json
import os
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional

class ImportExportManager:
    def __init__(self, db, study_manager):
        self.db = db
        self.study_manager = study_manager

    # ========== FLASHCARD EXPORT/IMPORT (CSV - Anki Compatible) ==========

    def export_deck_to_csv(self, deck_id: int, file_path: str) -> bool:
        """Export flashcards from a deck to a CSV file."""
        try:
            cards = self.db.get_all_flashcards(deck_id)
            if not cards:
                return False

            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Anki usually expects Front, Back
                for card in cards:
                    writer.writerow([card.question, card.answer])
            return True
        except Exception as e:
            print(f"Export error: {e}")
            traceback.print_exc()
            return False

    def import_deck_from_csv(self, deck_id: int, file_path: str) -> int:
        """Import flashcards from a CSV file into a deck. Returns count of imported cards."""
        try:
            count = 0
            with open(file_path, mode='r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 2:
                        question, answer = row[0], row[1]
                        if question.strip() and answer.strip():
                            self.db.add_flashcard(deck_id, question, answer)
                            count += 1
            return count
        except Exception as e:
            print(f"Import error: {e}")
            traceback.print_exc()
            return -1

    # ========== STUDY ITEMS EXPORT (JSON) ==========

    def export_study_items_to_json(self, item_type: str, file_path: str) -> bool:
        """Export study items (words, sentences, grammar) to JSON."""
        try:
            data = []
            if item_type == 'word':
                # Get all words with their definitions
                words = self.study_manager.get_imported_words()
                for w in words:
                    # Get full details including all definitions
                    defs = self.study_manager.get_all_word_definitions(w['id'])
                    w['definitions'] = defs
                    data.append(w)
            elif item_type == 'sentence':
                sentences = self.study_manager.get_imported_sentences()
                for s in sentences:
                    exps = self.study_manager.get_all_sentence_explanations(s['id'])
                    s['explanations'] = exps
                    # Also get followups for each explanation
                    for exp in exps:
                        exp['followups'] = self.db.get_grammar_followups(exp['id'])
                    data.append(s)
            elif item_type == 'grammar':
                entries = self.db.get_grammar_entries()
                data = entries
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Export study items error: {e}")
            traceback.print_exc()
            return False

    # ========== FULL DATABASE BACKUP (JSON) ==========

    def full_backup_to_json(self, file_path: str) -> bool:
        """Export the entire database content to a JSON file."""
        try:
            backup = {
                'timestamp': datetime.now().isoformat(),
                'version': '1.0',
                'collections': self.db.get_collections('deck') + self.db.get_collections('word') + 
                               self.db.get_collections('sentence') + self.db.get_collections('grammar'),
                'decks': [],
                'imported_content': [],
                'grammar_book': self.db.get_grammar_entries()
            }

            # Decks and cards
            decks = self.db.get_all_decks()
            for d in decks:
                cards = self.db.get_all_flashcards(d['id'])
                d['cards'] = [
                    {
                        'question': c.question,
                        'answer': c.answer,
                        'last_reviewed': c.last_reviewed.isoformat() if c.last_reviewed else None,
                        'stats': {
                            'easiness': c.easiness,
                            'interval': c.interval,
                            'repetitions': c.repetitions,
                            'total_reviews': c.total_reviews,
                            'correct_reviews': c.correct_reviews
                        }
                    } for c in cards
                ]
                backup['decks'].append(d)

            # Words & Sentences with all nested data
            # Using shared imported_content table
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT * FROM imported_content")
            cols = [desc[0] for desc in cursor.description]
            content_rows = [dict(zip(cols, row)) for row in cursor.fetchall()]
            
            for item in content_rows:
                if item['content_type'] == 'word':
                    item['definitions'] = self.study_manager.get_all_word_definitions(item['id'])
                elif item['content_type'] == 'sentence':
                    exps = self.study_manager.get_all_sentence_explanations(item['id'])
                    for exp in exps:
                        exp['followups'] = self.db.get_grammar_followups(exp['id'])
                    item['explanations'] = exps
                backup['imported_content'].append(item)

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(backup, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Full backup error: {e}")
            import traceback
            traceback.print_exc()
            return False
    def full_restore_from_json(self, file_path: str) -> bool:
        """Restore the database from a JSON backup file. WARNING: This clears existing data!"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Simple version check
            if 'decks' not in data or 'imported_content' not in data:
                return False
                
            cursor = self.db.conn.cursor()
            
            # 1. Clear existing tables (Ordered by dependency)
            tables = ['grammar_followups', 'sentence_explanations', 'word_definitions', 
                      'flashcards', 'decks', 'imported_content', 'grammar_book_entries', 'collections']
            for table in tables:
                cursor.execute(f"DELETE FROM {table}")
            
            # 2. Restore Collections (Hierarchy)
            # Map old IDs to new IDs to maintain hierarchy
            coll_map = {} # old_id -> new_id
            for c in data.get('collections', []):
                new_id = self.db.create_collection(c['name'], c['type'], None) # Parent fixed later
                coll_map[c['id']] = new_id
            
            # Update parent IDs
            for c in data.get('collections', []):
                if c.get('parent_id') and c['parent_id'] in coll_map:
                    cursor.execute("UPDATE collections SET parent_id = ? WHERE id = ?", 
                                 (coll_map[c['parent_id']], coll_map[c['id']]))

            # 3. Restore Decks & Flashcards
            for d in data.get('decks', []):
                coll_id = coll_map.get(d.get('collection_id'))
                cursor.execute(
                    "INSERT INTO decks (name, description, created_at, collection_id) VALUES (?, ?, ?, ?)",
                    (d['name'], d['description'], d['created_at'], coll_id)
                )
                new_deck_id = cursor.lastrowid
                
                for c in d.get('cards', []):
                    stats = c.get('stats', {})
                    cursor.execute("""
                        INSERT INTO flashcards (deck_id, question, answer, last_reviewed, 
                                              easiness, interval, repetitions, total_reviews, correct_reviews)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_deck_id, c['question'], c['answer'], c['last_reviewed'],
                          stats.get('easiness', 2.5), stats.get('interval', 1),
                          stats.get('repetitions', 0), stats.get('total_reviews', 0),
                          stats.get('correct_reviews', 0)))

            # 4. Restore Imported Content (Words/Sentences)
            content_map = {} # old_id -> new_id
            for item in data.get('imported_content', []):
                coll_id = coll_map.get(item.get('collection_id'))
                cursor.execute("""
                    INSERT INTO imported_content (content_type, content, context, title, url, language, created_at, processed, tags, collection_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (item['content_type'], item['content'], item['context'], item['title'], 
                      item['url'], item['language'], item['created_at'], item['processed'], item['tags'], coll_id))
                new_item_id = cursor.lastrowid
                content_map[item['id']] = new_item_id
                
                # Definitions
                for wd in item.get('definitions', []):
                    cursor.execute("""
                        INSERT INTO word_definitions (imported_content_id, word, definition, definition_language, 
                                                    source, created_at, last_updated, examples, notes, difficulty_level)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_item_id, wd['word'], wd['definition'], wd['language'],
                          wd['source'], wd['created_at'], wd['last_updated'], 
                          json.dumps(wd['examples']), wd['notes'], wd['difficulty_level']))
                
                # Explanations
                for se in item.get('explanations', []):
                    cursor.execute("""
                        INSERT INTO sentence_explanations (imported_content_id, sentence, explanation, 
                                                          explanation_language, source, focus_area, created_at, 
                                                          last_updated, grammar_notes, user_notes)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_item_id, se['sentence'], se['explanation'], se['language'],
                          se['source'], se['focus_area'], se['created_at'],
                          se['last_updated'], se['grammar_notes'], se['user_notes']))
                    new_exp_id = cursor.lastrowid
                    
                    # Followups
                    for fup in se.get('followups', []):
                        cursor.execute("""
                            INSERT INTO grammar_followups (sentence_explanation_id, question, answer, context, created_at)
                            VALUES (?, ?, ?, ?, ?)
                        """, (new_exp_id, fup['question'], fup['answer'], fup['context'], fup['created_at']))

            # 5. Restore Grammar Book
            for g in data.get('grammar_book', []):
                coll_id = coll_map.get(g.get('collection_id'))
                cursor.execute("""
                    INSERT INTO grammar_book_entries (title, content, language, tags, created_at, updated_at, collection_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (g['title'], g['content'], g['language'], g['tags'], 
                      g['created_at'], g['updated_at'], coll_id))

            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Full restore error: {e}")
            import traceback
            traceback.print_exc()
            self.db.conn.rollback()
            return False

    def close(self):
        self.db.close()
