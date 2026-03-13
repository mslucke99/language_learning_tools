#!/usr/bin/env python3
"""Comprehensive test of the sentence import fix."""

import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.database import FlashcardDatabase
from src.features.study_center.logic.study_manager import StudyManager

print("\n" + "="*80)
print("COMPREHENSIVE IMPORT VERIFICATION TEST")
print("="*80)

db = FlashcardDatabase('flashcards.db')

# Test 1: Add a sentence via API simulation
print("\n[TEST 1] Adding test sentence via simulated API call...")
cursor = db.conn.cursor()
cursor.execute("""
    INSERT INTO imported_content 
    (content_type, content, url, title, language, created_at, tags)
    VALUES (?, ?, ?, ?, ?, datetime('now'), ?)
""", ('sentence', 'This is a test sentence added after the fix.', 'http://test.com', 'Test Page', '', 'test'))

db.conn.commit()
new_id = cursor.lastrowid
print(f"✓ Added sentence with ID: {new_id}")

# Test 2: Verify it shows up in raw database
print("\n[TEST 2] Raw database query...")
cursor.execute("""
    SELECT id, content, language FROM imported_content WHERE id = ?
""", (new_id,))
row = cursor.fetchone()
if row:
    print(f"✓ Found in DB: ID={row[0]}, language={repr(row[2])}")
else:
    print("✗ NOT found in database!")

# Test 3: Verify it shows up in study manager
print("\n[TEST 3] Study Manager retrieval...")
sm = StudyManager(db)
sentences = sm.get_imported_sentences()
found = False
for s in sentences:
    if s['id'] == new_id:
        print(f"✓ Found in study manager:")
        print(f"  - Content: {s['sentence']}")
        print(f"  - Language: {s['language']}")
        found = True
        break

if not found:
    print("✗ NOT found in study manager!")
    print("\nFirst 3 sentences:")
    for s in sentences[:3]:
        print(f"  - ID {s['id']}: {s['sentence'][:50]}")

# Test 4: Count totals
print("\n[TEST 4] Summary counts...")
cursor.execute("SELECT COUNT(*) FROM imported_content WHERE content_type = 'sentence'")
db_count = cursor.fetchone()[0]
mgr_count = len(sentences)

print(f"✓ Total in database: {db_count}")
print(f"✓ Total in study manager: {mgr_count}")
if db_count == mgr_count:
    print("✓ PERFECT MATCH!")
else:
    print(f"⚠️  MISMATCH: Expected {db_count}, got {mgr_count}")

print("\n" + "="*80)
print("FINAL VERDICT")
print("="*80)
if found and db_count == mgr_count:
    print("✅ FIX VERIFIED: All imported sentences are now visible!")
    print("   The issue was that the study manager was filtering by study_language")
    print("   when it should show ALL imported content regardless of language.")
else:
    print("❌ Fix verification failed")

print("="*80 + "\n")
