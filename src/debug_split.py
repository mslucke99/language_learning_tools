#!/usr/bin/env python
"""
Debug script for sentence splitting
"""
import sys
import os
import regex

# Add the root directory (parent of src) to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from services.text.sentence_miner import SentenceMiner
from core.database import FlashcardDatabase

# Mock database for testing
class MockDatabase:
    def get_all_known_words(self, lang_code):
        return []  # Empty for testing
    
    def get_all_ignored_words(self, lang_code):
        return []  # Empty for testing

def debug_split():
    miner = SentenceMiner(MockDatabase(), None)
    
    # Test cases
    test_cases = [
        "Dr. Smith went to the U.S.A. He saw Mr. Jones.",
        "Price is $3.99. That's expensive."
    ]
    
    # Constants from the function
    SENTENCE_TERMINATORS = '.!?。！？'
    SENTENCE_STARTER = r'[\p{L}\p{Nl}]'
    SENTENCE_OPENERS = r'["\'\(\[\p{Pi}\p{Ps}]*'
    SENTENCE_ENDERS = r'[\p{Pe}\p{Pf}"\']*'
    
    ENDS_SENTENCE_RE = regex.compile(
        r'[' + regex.escape(SENTENCE_TERMINATORS) + r']' + SENTENCE_ENDERS + r'\s*$'
    )
    
    STARTS_NEW_SENTENCE_RE = regex.compile(
        r'^\s*' + SENTENCE_OPENERS + SENTENCE_STARTER
    )
    
    ABBREV_RE = regex.compile(
        r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|approx|dept|est|vol|pp|fig|'
        r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|'
        r'Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?',
        regex.IGNORECASE
    )
    
    for i, text in enumerate(test_cases):
        print(f"\n{'='*20} Test Case {i+1} {'='*20}")
        print(f"Text: {repr(text)}")
        
        # Normalize line endings
        text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
        print(f"After normalization: {repr(text_norm)}")
        
        # Split into paragraphs on blank lines (always a boundary)
        paragraphs = regex.split(r'\n{2,}', text_norm)
        print(f"Paragraphs: {paragraphs}")
        
        for j, para in enumerate(paragraphs):
            if not para.strip():
                continue
            print(f"\n--- Paragraph {j+1}: {repr(para)} ---")
            
            # Process each paragraph
            lines = [ln.strip() for ln in para.split('\n') if ln.strip()]
            print(f"Lines: {lines}")
            
            if not lines:
                continue
                
            # Merge wrapped lines within each paragraph
            merged: list[str] = []
            current = lines[0]
            print(f"Starting with: {repr(current)}")
            
            for k, next_line in enumerate(lines[1:]):
                ends_sentence = bool(ENDS_SENTENCE_RE.search(current))
                starts_new    = bool(STARTS_NEW_SENTENCE_RE.match(next_line))
                
                print(f"  Checking line {k+1}: {repr(next_line)}")
                print(f"    Current ends with sentence terminator: {ends_sentence}")
                print(f"    Next line starts with sentence starter: {starts_new}")
                
                if ends_sentence and starts_new:
                    print(f"    -> MERGE: Adding '{current}' to merged, starting new with '{next_line}'")
                    merged.append(current)
                    current = next_line
                else:
                    print(f"    -> NO MERGE: Appending '{next_line}' to current")
                    current = current + ' ' + next_line
                    
            merged.append(current)
            print(f"Merged lines: {merged}")
            
            # --- 4. Split each merged block on inline sentence terminators ---
            for block_idx, block in enumerate(merged):
                print(f"\n  Processing block {block_idx+1}: {repr(block)}")
                
                if not any(c in block for c in SENTENCE_TERMINATORS):
                    print(f"    No terminators found, treating as one sentence")
                    continue
                
                # Show what the regex pattern looks like
                SPLIT_PATTERN_STR = (
                    r'(?<!\d)([.!?][\p{Pe}\p{Pf}"\']*)(?=\s*(?:' + SENTENCE_OPENERS + SENTENCE_STARTER + r')|\s*$)' +
                    r'|([。！？])'
                )
                print(f"    Split pattern: {SPLIT_PATTERN_STR}")
                
                SPLIT_PATTERN = regex.compile(SPLIT_PATTERN_STR)
                
                # Find all matches
                matches = list(SPLIT_PATTERN.finditer(block))
                print(f"    Found {len(matches)} matches:")
                for m_idx, match in enumerate(matches):
                    print(f"      Match {m+1}: {repr(match.group(0))} at position {match.start()}-{match.end()}")
                    for g_idx in range(len(match.groups())+1):
                        if match.group(g_idx) is not None:
                            print(f"        Group {g_idx}: {repr(match.group(g_idx))}")
                
                if not matches:
                    print(f"    No matches, treating as one sentence")
                    continue
                    
                # Split the block based on match positions
                candidates = []
                start = 0
                for match_idx, match in enumerate(matches):
                    # Add text before the match
                    if start < match.start():
                        sentence_part = block[start:match.start()].strip()
                        if sentence_part:
                            candidates.append(sentence_part)
                            print(f"      Added text part {len(candidates)}: {repr(sentence_part)}")
                    
                    # Add the matched delimiter (the terminator)
                    sentence_part = match.group(0).strip()
                    if sentence_part:
                        candidates.append(sentence_part)
                        print(f"      Added delimiter {len(candidates)}: {repr(sentence_part)}")
                        
                    start = match.end()
                
                # Add remaining text after last match
                if start < len(block):
                    sentence_part = block[start:].strip()
                    if sentence_part:
                        candidates.append(sentence_part)
                        print(f"      Added final text part {len(candidates)}: {repr(sentence_part)}")
                
                print(f"    Raw candidates: {candidates}")
                
                # Now we need to merge text parts with their following delimiters
                merged_candidates = []
                idx = 0
                while idx < len(candidates):
                    text_part = candidates[idx]
                    # Check if next item is a delimiter (punctuation)
                    if idx + 1 < len(candidates) and regex.match(r'^[.!?。！？]+[\p{Pe}\p{Pf}"\']*$', candidates[idx + 1]):
                        # Merge text with its delimiter
                        merged = (text_part + candidates[idx + 1]).strip()
                        if merged:
                            merged_candidates.append(merged)
                            print(f"      Merged '{text_part}' + '{candidates[idx + 1]}' -> '{merged}'")
                        idx += 2  # Skip both text and delimiter
                    else:
                        # No following delimiter, just add the text part
                        if text_part:
                            merged_candidates.append(text_part)
                            print(f"      Added text part '{text_part}' (no following delimiter)")
                        idx += 1
                
                print(f"    After delimiter merging: {merged_candidates}")

if __name__ == "__main__":
    debug_split()