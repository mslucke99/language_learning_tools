#!/usr/bin/env python
"""
Detailed debug script for sentence splitting
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

def detailed_debug():
    miner = SentenceMiner(MockDatabase(), None)
    
    # Test case
    text = "Dr. Smith went to the U.S.A. He saw Mr. Jones."
    print(f"Testing: {repr(text)}")
    
    # Manually replicate the key parts of _split_paragraph to see what's happening
    
    # Normalize line endings
    text_norm = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Split into paragraphs on blank lines (always a boundary)
    paragraphs = regex.split(r'\n{2,}', text_norm)
    
    for para in paragraphs:
        if not para.strip():
            continue
            
        # Process each paragraph
        lines = [ln.strip() for ln in para.split('\n') if ln.strip()]
        
        # Merge wrapped lines within each paragraph
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
        
        merged = []
        if lines:
            current = lines[0]
            for next_line in lines[1:]:
                ends_sentence = bool(ENDS_SENTENCE_RE.search(current))
                starts_new    = bool(STARTS_NEW_SENTENCE_RE.match(next_line))
                
                if ends_sentence and starts_new:
                    merged.append(current)
                    current = next_line
                else:
                    current = current + ' ' + next_line
            merged.append(current)
        
        print(f"Merged lines: {merged}")
        
        # Process each merged block
        for block_idx, block in enumerate(merged):
            print(f"\nProcessing block {block_idx+1}: {repr(block)}")
            
            if not any(c in block for c in SENTENCE_TERMINATORS):
                print("  No terminators found")
                continue
            
            # Define the regex pattern
            SPLIT_PATTERN = regex.compile(
                r'(?<!\d)([.!?][\p{Pe}\p{Pf}"\']*)(?=\s*(?:' + SENTENCE_OPENERS + SENTENCE_STARTER + r')|\s*$)' +
                r'|([。！？])'
            )
            
            # Find all matches and their positions
            matches = list(SPLIT_PATTERN.finditer(block))
            print(f"  Found {len(matches)} matches:")
            for m_idx, match in enumerate(matches):
                print(f"    Match {m_idx+1}: {repr(match.group(0))} at {match.start()}-{match.end()}")
                # Show which groups matched
                for g_idx in range(len(match.groups())+1):
                    if match.group(g_idx) is not None:
                        print(f"      Group {g_idx}: {repr(match.group(g_idx))}")
            
            if not matches:
                print("  No matches, treating as one sentence")
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
                        print(f"    Added text part: {repr(sentence_part)}")
                
                # Add the matched delimiter (the terminator)
                sentence_part = match.group(0).strip()
                if sentence_part:
                    candidates.append(sentence_part)
                    print(f"    Added delimiter: {repr(sentence_part)}")
                    
                start = match.end()
            
            # Add remaining text after last match
            if start < len(block):
                sentence_part = block[start:].strip()
                if sentence_part:
                    candidates.append(sentence_part)
                    print(f"    Added final text part: {repr(sentence_part)}")
            
            print(f"  Raw candidates after split: {candidates}")
            
            # Now we need to merge text parts with their following delimiters
            merged_candidates = []
            i = 0
            while i < len(candidates):
                text_part = candidates[i]
                # Check if next item is a delimiter (punctuation)
                if i + 1 < len(candidates) and regex.match(r'^[.!?。！？]+[\p{Pe}\p{Pf}"\']*$', candidates[i + 1]):
                    # Merge text with its delimiter
                    merged = (text_part + candidates[i + 1]).strip()
                    if merged:
                        merged_candidates.append(merged)
                        print(f"    Merged '{text_part}' + '{candidates[i + 1]}' -> '{merged}'")
                    i += 2  # Skip both text and delimiter
                else:
                    # No following delimiter, just add the text part
                    if text_part:
                        merged_candidates.append(text_part)
                        print(f"    Added text part '{text_part}' (no following delimiter)")
                    i += 1
            
            print(f"  Candidates after delimiter merging: {merged_candidates}")
            
            # --- Step 3: Merge back abbreviations and very short fragments that were incorrectly split ---
            ABBREV_RE = regex.compile(
                r'\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|vs|etc|approx|dept|est|vol|pp|fig|'
                r'Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|'
                r'Mon|Tue|Wed|Thu|Fri|Sat|Sun)\.?',
                regex.IGNORECASE
            )
            
            final_sentences = []
            i = 0
            while i < len(merged_candidates):
                candidate = merged_candidates[i]
                
                # Check if this ends with an abbreviation and there's a next candidate
                is_abbreviation = (i + 1 < len(merged_candidates) and 
                                  ABBREV_RE.search(candidate) and 
                                  not candidate.endswith('..'))  # Avoid double dots
                
                # Also check if this is a very short fragment (likely part of abbreviated text like "U.", "S.", etc.)
                # Very short fragments ending with period are often incorrectly split abbreviations
                is_short_fragment = (len(candidate.strip()) <= 2 and 
                                    candidate.strip().endswith('.') and
                                    i + 1 < len(merged_candidates))
                
                print(f"    Checking candidate {i}: {repr(candidate)}")
                print(f"      Is abbreviation: {is_abbreviation}")
                if is_abbreviation:
                    print(f"      ABBREV_RE matched: {ABBREV_RE.search(candidate)}")
                print(f"      Is short fragment: {is_short_fragment}")
                print(f"      Has next candidate: {i + 1 < len(merged_candidates)}")
                if i + 1 < len(merged_candidates):
                    print(f"      Next candidate: {repr(merged_candidates[i + 1])}")
                
                if is_abbreviation or is_short_fragment:
                    # Merge with next candidate
                    merged = candidate + ' ' + merged_candidates[i + 1]
                    final_sentences.append(merged)
                    print(f"      -> MERGING with next: '{merged}'")
                    i += 2  # Skip both current and next items as they've been merged
                else:
                    final_sentences.append(candidate)
                    print(f"      -> Adding as-is: '{candidate}'")
                    i += 1  # Move to next item
            
            print(f"  Final sentences from this block: {final_sentences}")

if __name__ == "__main__":
    detailed_debug()