"""
Script to seed the database with sample story templates.

This script creates sample templates for three genres:
- Mystery
- Adventure  
- Fantasy

Run this script to populate the story_templates table with initial content.
"""

import sys
import os
import sqlite3
import json
from dataclasses import dataclass
from typing import List, Dict, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import StoryTemplate directly to avoid database import issues
@dataclass
class StoryTemplate:
    """Represents a story template node."""
    id: Optional[int]
    genre: str
    node_id: str
    template_text: str
    suggested_vocab: List[Dict[str, str]]
    choices: List[Dict[str, str]]
    metadata: Dict[str, any]


def create_mystery_templates():
    """Create mystery genre templates."""
    
    templates = [
        # Start node
        StoryTemplate(
            id=None,
            genre="mystery",
            node_id="start",
            template_text="You wake up in a dark {LOCATION:room}. The door is locked. You notice a {OBJECT:window} and a {OBJECT:desk}.",
            suggested_vocab=[
                {"word": "어두운", "translation": "dark", "context": "The room is 어두운."},
                {"word": "잠기다", "translation": "to be locked", "context": "The door is 잠기다."}
            ],
            choices=[
                {"id": 1, "text": "Look out the {OBJECT:window}", "description": "Investigate the window", "next_node": "window"},
                {"id": 2, "text": "Search the {OBJECT:desk}", "description": "Check the desk", "next_node": "desk"}
            ],
            metadata={"difficulty": "beginner", "location": "room"}
        ),
        
        # Window path
        StoryTemplate(
            id=None,
            genre="mystery",
            node_id="window",
            template_text="You look out the window. Outside, you see a {LOCATION:garden}. There's a {OBJECT:key} on the windowsill.",
            suggested_vocab=[
                {"word": "창문", "translation": "window", "context": "Look through the 창문."},
                {"word": "열쇠", "translation": "key", "context": "You found a 열쇠."}
            ],
            choices=[
                {"id": 1, "text": "Take the {OBJECT:key}", "description": "Pick up the key", "next_node": "take_key"},
                {"id": 2, "text": "Go back and check the {OBJECT:desk}", "description": "Return to desk", "next_node": "desk"}
            ],
            metadata={"difficulty": "beginner", "location": "window"}
        ),
        
        # Desk path
        StoryTemplate(
            id=None,
            genre="mystery",
            node_id="desk",
            template_text="You search the desk. Inside a drawer, you find a {OBJECT:note} and a {OBJECT:photo}. The note has strange writing.",
            suggested_vocab=[
                {"word": "서랍", "translation": "drawer", "context": "Open the 서랍."},
                {"word": "메모", "translation": "note", "context": "Read the 메모."}
            ],
            choices=[
                {"id": 1, "text": "Read the {OBJECT:note}", "description": "Examine the note", "next_node": "read_note"},
                {"id": 2, "text": "Look at the {OBJECT:photo}", "description": "Study the photo", "next_node": "photo"}
            ],
            metadata={"difficulty": "beginner", "location": "desk"}
        ),
    ]
    
    return templates


def create_adventure_templates():
    """Create adventure genre templates."""
    
    templates = [
        # Start node
        StoryTemplate(
            id=None,
            genre="adventure",
            node_id="start",
            template_text="You stand at the edge of a vast {LOCATION:forest}. A {OBJECT:path} leads into the trees. You hear a {SOUND:noise} in the distance.",
            suggested_vocab=[
                {"word": "숲", "translation": "forest", "context": "Enter the 숲."},
                {"word": "길", "translation": "path", "context": "Follow the 길."}
            ],
            choices=[
                {"id": 1, "text": "Follow the {OBJECT:path}", "description": "Take the path", "next_node": "path"},
                {"id": 2, "text": "Investigate the {SOUND:noise}", "description": "Check the sound", "next_node": "noise"}
            ],
            metadata={"difficulty": "beginner", "location": "forest_edge"}
        ),
        
        # Path node
        StoryTemplate(
            id=None,
            genre="adventure",
            node_id="path",
            template_text="The path leads to a {LOCATION:clearing}. In the center, there's a {OBJECT:stone} with ancient markings. A {PERSON:traveler} approaches you.",
            suggested_vocab=[
                {"word": "돌", "translation": "stone", "context": "Touch the 돌."},
                {"word": "여행자", "translation": "traveler", "context": "Meet the 여행자."}
            ],
            choices=[
                {"id": 1, "text": "Examine the {OBJECT:stone}", "description": "Study the stone", "next_node": "stone"},
                {"id": 2, "text": "Talk to the {PERSON:traveler}", "description": "Speak with traveler", "next_node": "traveler"}
            ],
            metadata={"difficulty": "beginner", "location": "clearing"}
        ),
        
        # Noise node
        StoryTemplate(
            id=None,
            genre="adventure",
            node_id="noise",
            template_text="You discover a {ANIMAL:creature} trapped in a {OBJECT:net}. It looks at you with {EMOTION:hopeful} eyes.",
            suggested_vocab=[
                {"word": "동물", "translation": "animal", "context": "Help the 동물."},
                {"word": "그물", "translation": "net", "context": "Cut the 그물."}
            ],
            choices=[
                {"id": 1, "text": "Free the {ANIMAL:creature}", "description": "Help the creature", "next_node": "free_creature"},
                {"id": 2, "text": "Leave and return to the {OBJECT:path}", "description": "Go back", "next_node": "path"}
            ],
            metadata={"difficulty": "beginner", "location": "forest"}
        ),
    ]
    
    return templates


def create_fantasy_templates():
    """Create fantasy genre templates."""
    
    templates = [
        # Start node
        StoryTemplate(
            id=None,
            genre="fantasy",
            node_id="start",
            template_text="You arrive at a {LOCATION:castle} surrounded by {WEATHER:mist}. The {OBJECT:gate} is guarded by a {PERSON:knight}.",
            suggested_vocab=[
                {"word": "성", "translation": "castle", "context": "Enter the 성."},
                {"word": "안개", "translation": "mist", "context": "Walk through the 안개."}
            ],
            choices=[
                {"id": 1, "text": "Approach the {PERSON:knight}", "description": "Talk to the guard", "next_node": "knight"},
                {"id": 2, "text": "Find another {OBJECT:entrance}", "description": "Look for another way", "next_node": "side_entrance"}
            ],
            metadata={"difficulty": "beginner", "location": "castle_gate"}
        ),
        
        # Knight node
        StoryTemplate(
            id=None,
            genre="fantasy",
            node_id="knight",
            template_text="The knight asks for a {OBJECT:password}. You notice a {OBJECT:scroll} attached to their {OBJECT:belt}.",
            suggested_vocab=[
                {"word": "기사", "translation": "knight", "context": "Speak to the 기사."},
                {"word": "암호", "translation": "password", "context": "Say the 암호."}
            ],
            choices=[
                {"id": 1, "text": "Try to guess the {OBJECT:password}", "description": "Attempt password", "next_node": "password"},
                {"id": 2, "text": "Ask about the {OBJECT:scroll}", "description": "Inquire about scroll", "next_node": "scroll"}
            ],
            metadata={"difficulty": "beginner", "location": "castle_gate"}
        ),
        
        # Side entrance node
        StoryTemplate(
            id=None,
            genre="fantasy",
            node_id="side_entrance",
            template_text="You find a hidden {OBJECT:door} covered in {PLANT:vines}. Through a crack, you see a {LOCATION:garden} with glowing {OBJECT:flowers}.",
            suggested_vocab=[
                {"word": "문", "translation": "door", "context": "Open the 문."},
                {"word": "정원", "translation": "garden", "context": "Enter the 정원."}
            ],
            choices=[
                {"id": 1, "text": "Push open the {OBJECT:door}", "description": "Enter through door", "next_node": "garden"},
                {"id": 2, "text": "Return to the {PERSON:knight}", "description": "Go back to main gate", "next_node": "knight"}
            ],
            metadata={"difficulty": "beginner", "location": "side_path"}
        ),
    ]
    
    return templates


def seed_templates(db_path: str = None):
    """
    Seed the database with sample story templates.
    
    Args:
        db_path: Optional path to database file
    """
    # Use default database path if not provided
    if db_path is None:
        db_path = os.path.join(os.path.dirname(__file__), '../../../flashcards.db')
    
    # Connect directly to database
    conn = sqlite3.connect(db_path)
    
    print("Seeding story templates...")
    
    # Create templates for each genre
    mystery_templates = create_mystery_templates()
    adventure_templates = create_adventure_templates()
    fantasy_templates = create_fantasy_templates()
    
    all_templates = mystery_templates + adventure_templates + fantasy_templates
    
    # Save templates to database
    cursor = conn.cursor()
    
    for template in all_templates:
        # Check if template already exists
        cursor.execute("""
            SELECT id FROM story_templates
            WHERE genre = ? AND node_id = ?
        """, (template.genre, template.node_id))
        
        existing = cursor.fetchone()
        
        if existing:
            print(f"  Skipping {template.genre}/{template.node_id} (already exists)")
            continue
        
        # Insert template
        cursor.execute("""
            INSERT INTO story_templates (genre, node_id, template_text, suggested_vocab, choices, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            template.genre,
            template.node_id,
            template.template_text,
            json.dumps(template.suggested_vocab),
            json.dumps(template.choices),
            json.dumps(template.metadata)
        ))
        
        print(f"  Created {template.genre}/{template.node_id}")
    
    conn.commit()
    
    print(f"\nSeeded {len(all_templates)} templates across 3 genres")
    print("Genres: mystery, adventure, fantasy")
    
    conn.close()


if __name__ == "__main__":
    # Use default database path
    seed_templates()
    print("\nTemplate seeding complete!")
