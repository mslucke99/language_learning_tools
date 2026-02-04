"""
RelatedItemsPanel - Reusable UI component for displaying AI-suggested vocabulary and grammar.

This widget provides a consistent interface for:
1. Displaying flashcard suggestions (word + definition)
2. Displaying grammar pattern suggestions (title + explanation)
3. Adding suggestions to decks or the study collection

Usage:
    panel = RelatedItemsPanel(parent, db, study_manager)
    panel.pack(fill="both", expand=True)
    panel.populate(suggestions_dict)  # {'flashcards': [...], 'grammar': [...]}
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional, Callable, Dict, List, Any

class RelatedItemsPanel(ttk.Frame):
    """
    A reusable panel for displaying and managing AI-generated study suggestions.
    
    Supports two types of suggestions:
    - flashcards: [{word, definition}, ...]
    - grammar: [{title, explanation}, ...]
    """
    
    def __init__(self, parent, db, study_manager, 
                 show_deck_choice: bool = True,
                 on_item_added: Optional[Callable] = None):
        """
        Initialize the RelatedItemsPanel.
        
        Args:
            parent: Parent tkinter widget
            db: FlashcardDatabase instance
            study_manager: StudyManager instance for language settings
            show_deck_choice: If True, ask user whether to add to deck or vocabulary list
            on_item_added: Optional callback invoked after an item is successfully added
        """
        super().__init__(parent)
        self.db = db
        self.study_manager = study_manager
        self.show_deck_choice = show_deck_choice
        self.on_item_added = on_item_added
        
        # Container for suggestion widgets
        self.content_frame = ttk.Frame(self)
        self.content_frame.pack(fill="both", expand=True)
        
        # Show placeholder initially
        self._show_placeholder()
    
    def _show_placeholder(self, message: str = "AI suggestions will appear here..."):
        """Display a placeholder message when no suggestions are available."""
        self.clear()
        ttk.Label(
            self.content_frame, 
            text=message, 
            font=("Arial", 10, "italic"), 
            foreground="gray"
        ).pack(pady=20)
    
    def clear(self):
        """Clear all suggestions from the panel."""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def populate(self, suggestions: Dict[str, List[Dict[str, Any]]]):
        """
        Populate the panel with suggestions.
        
        Args:
            suggestions: Dict with optional 'flashcards' and 'grammar' keys.
                flashcards: List of {word: str, definition: str}
                grammar: List of {title: str, explanation: str}
        """
        self.clear()
        
        if not suggestions:
            self._show_placeholder("No suggestions available.")
            return
        
        flashcards = suggestions.get('flashcards', [])
        grammar = suggestions.get('grammar', [])
        
        if not flashcards and not grammar:
            self._show_placeholder("No specific suggestions found.")
            return
        
        # Scrollable container
        canvas = tk.Canvas(self.content_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Render flashcards
        if flashcards:
            self._render_flashcards(scrollable_frame, flashcards)
        
        # Render grammar
        if grammar:
            self._render_grammar(scrollable_frame, grammar, has_flashcards=bool(flashcards))
    
    def _render_flashcards(self, parent: ttk.Frame, flashcards: List[Dict[str, str]]):
        """Render the vocabulary/flashcard suggestions section."""
        ttk.Label(
            parent, 
            text="📚 Vocabulary Suggestions", 
            font=("Arial", 10, "bold")
        ).pack(anchor="w", pady=(10, 5), padx=5)
        
        for item in flashcards:
            frame = ttk.Frame(parent)
            frame.pack(fill="x", pady=2, padx=5)
            
            # Word label
            ttk.Label(
                frame, 
                text=f"• {item.get('word', 'Unknown')}", 
                font=("Arial", 10, "bold")
            ).pack(side="left")
            
            # Definition label
            definition = item.get('definition', '')
            if len(definition) > 60:
                definition = definition[:57] + "..."
            ttk.Label(
                frame, 
                text=f": {definition}", 
                font=("Arial", 9)
            ).pack(side="left", padx=5)
            
            # Context/Example label (new line)
            context = item.get('context', '')
            if context:
                ttk.Label(
                    frame,
                    text=f"  Context: \"{context}\"",
                    font=("Arial", 8, "italic"),
                    foreground="#555"
                ).pack(side="left", padx=5)
            
            # Add button
            ttk.Button(
                frame, 
                text="Add", 
                width=6,
                command=lambda i=item: self._add_flashcard(i)
            ).pack(side="right")
    
    def _render_grammar(self, parent: ttk.Frame, grammar: List[Dict[str, str]], 
                        has_flashcards: bool = False):
        """Render the grammar suggestions section."""
        ttk.Label(
            parent, 
            text="📖 Grammar Suggestions", 
            font=("Arial", 10, "bold")
        ).pack(anchor="w", pady=(20 if has_flashcards else 10, 5), padx=5)
        
        for item in grammar:
            frame = ttk.Frame(parent)
            frame.pack(fill="x", pady=2, padx=5)
            
            # Title label
            ttk.Label(
                frame, 
                text=f"• {item.get('title', 'Pattern')}", 
                font=("Arial", 10, "bold")
            ).pack(side="left")
            
            # Add button
            ttk.Button(
                frame, 
                text="Add", 
                width=6,
                command=lambda i=item: self._add_grammar(i)
            ).pack(side="right")
            
            # Explanation snippet
            explanation = item.get('explanation', '')
            if len(explanation) > 60:
                explanation = explanation[:57] + "..."
            ttk.Label(
                frame, 
                text=f"- {explanation}", 
                font=("Arial", 9, "italic")
            ).pack(side="left", padx=5)
    
    def _add_flashcard(self, item: Dict[str, str]):
        """Handle adding a flashcard suggestion."""
        word = item.get('word', '')
        definition = item.get('definition', '')
        
        if not word:
            messagebox.showwarning("Error", "Invalid suggestion: missing word")
            return
        
        try:
            if self.show_deck_choice:
                # Ask where to save
                choice = messagebox.askyesnocancel(
                    "Add Word",
                    f"Where should '{word}' be saved?\n\n"
                    "Yes: Flashcard Deck\n"
                    "No: Vocabulary List (Study Center)"
                )
                if choice is None:
                    return
                
                if choice:  # Yes -> Deck
                    self._add_to_deck(word, definition)
                else:  # No -> Vocabulary List
                    self._add_to_vocabulary(word, definition, context=item.get('context', ''))
            else:
                # Default to vocabulary list
                self._add_to_vocabulary(word, definition, context=item.get('context', ''))
            
            if self.on_item_added:
                self.on_item_added('flashcard', item)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add flashcard: {e}")
    
    def _add_to_deck(self, word: str, definition: str):
        """Add a flashcard to a user-selected deck."""
        # Import here to avoid circular imports
        from src.features.study_center.ui.dialogs import DeckPickerDialog
        
        deck_id = DeckPickerDialog(self.winfo_toplevel(), self.db).show()
        if not deck_id:
            return
        
        # Check for duplicate
        if hasattr(self.db, 'find_flashcard_in_deck'):
            existing = self.db.find_flashcard_in_deck(deck_id, word)
            if existing:
                if not messagebox.askyesno(
                    "Duplicate", 
                    f"Card '{word}' already exists in this deck. Add anyway?"
                ):
                    return
        
        self.db.add_flashcard(deck_id, word, definition)
        messagebox.showinfo("Saved", "Added flashcard to deck!")
    
    def _add_to_vocabulary(self, word: str, definition: str, context: str = ''):
        """Add a word to the vocabulary/study list."""
        # Check for existing
        existing = self.db.find_flashcard_by_question(word)
        if existing:
            if not messagebox.askyesno(
                "Duplicate",
                f"The word '{word}' might already exist in deck "
                f"'{existing[0]['deck_name']}'. Add anyway?"
            ):
                return
        
        # Add to imported content
        content_id = self.db.add_imported_content(
            'word', 
            word,
            url="AI Suggestion",
            title="Related Items",
            language=getattr(self.study_manager, 'study_language', '')
        )
        
        # Add definition
        self.study_manager.add_word_definition(
            content_id, 
            definition,
            definition_language=getattr(self.study_manager, 'native_language', 'native'),
            examples=[context] if context else []
        )
        
        messagebox.showinfo("Saved", f"Added '{word}' to your vocabulary list.")
    
    def _add_grammar(self, item: Dict[str, str]):
        """Handle adding a grammar suggestion."""
        title = item.get('title', '')
        explanation = item.get('explanation', '')
        
        if not title:
            messagebox.showwarning("Error", "Invalid suggestion: missing title")
            return
        
        try:
            self.db.add_grammar_entry(
                title,
                explanation,
                language=getattr(self.study_manager, 'study_language', ''),
                tags="auto-generated"
            )
            messagebox.showinfo("Saved", f"Added grammar pattern '{title}'.")
            
            if self.on_item_added:
                self.on_item_added('grammar', item)
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add grammar: {e}")


# Utility function for views that embed suggestions differently (e.g., chat)
def add_suggestion_to_storage(db, study_manager, item: Dict[str, str], 
                               type_name: str, source: str = "AI Suggestion") -> bool:
    """
    Utility function to add a suggestion to storage without UI prompts.
    
    Args:
        db: FlashcardDatabase instance
        study_manager: StudyManager instance
        item: The suggestion dict (word/definition or title/explanation)
        type_name: 'word' or 'grammar'
        source: Source label for the content
        
    Returns:
        True if saved successfully, False otherwise
    """
    try:
        if type_name == 'word':
            word = item.get('word', '')
            definition = item.get('definition', '')
            
            content_id = db.add_imported_content(
                'word',
                word,
                url=source,
                title=source,
                language=getattr(study_manager, 'study_language', '')
            )
            
            study_manager.add_word_definition(
                content_id,
                definition,
                definition_language=getattr(study_manager, 'native_language', 'native'),
                examples=[item.get('context', '')] if item.get('context') else []
            )
            return True
            
        elif type_name == 'grammar':
            db.add_grammar_entry(
                item.get('title', ''),
                item.get('explanation', ''),
                language=getattr(study_manager, 'study_language', ''),
                tags="auto-generated"
            )
            return True
            
    except Exception:
        return False
    
    return False
