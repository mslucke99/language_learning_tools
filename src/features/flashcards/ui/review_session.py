import tkinter as tk
from tkinter import ttk, messagebox
from src.core.database import FlashcardDatabase
from src.features.flashcards.logic.spaced_repetition import get_due_flashcards

class ReviewSessionFrame(ttk.Frame):
    def __init__(self, parent, controller, db: FlashcardDatabase, deck_id: int):
        super().__init__(parent)
        self.controller = controller
        self.db = db
        self.deck_id = deck_id
        self.style = ttk.Style()
        self.style.configure("Large.TButton", font=("Arial", 12), padding=15)
        
        self.current_flashcards = []
        self.current_index = 0
        self.answer_revealed = False
        
        self.start_review()
        
    def start_review(self):
        """Start reviewing cards."""
        due_cards = self.db.get_due_flashcards(self.deck_id)
        
        if not due_cards:
            self.show_no_cards_message()
            return
        
        self.current_flashcards = due_cards
        self.current_index = 0
        self.answer_revealed = False
        self.show_review_card()

    def show_no_cards_message(self):
        self.clear_content()
        ttk.Label(self, text="No cards due for review!", font=("Arial", 16)).pack(pady=50)
        ttk.Button(self, text="Back to Deck", command=self.go_back, style="Large.TButton").pack(pady=20)
        
    def show_review_card(self):
        """Show the current card during review."""
        self.clear_content()
        
        if self.current_index >= len(self.current_flashcards):
            self.finish_review()
            return
        
        flashcard = self.current_flashcards[self.current_index]
        
        # Progress
        progress_text = f"Card {self.current_index + 1} of {len(self.current_flashcards)}"
        ttk.Label(self, text=progress_text, font=("Arial", 11, "bold")).pack(pady=10)
        
        # Progress bar
        progress = ttk.Progressbar(self, length=500, mode="determinate", 
                                   value=(self.current_index / len(self.current_flashcards)) * 100)
        progress.pack(pady=10)
        
        # Question
        ttk.Label(self, text="Question:", font=("Arial", 13, "bold")).pack(pady=15)
        question_frame = ttk.Frame(self, relief="sunken", borderwidth=2)
        question_frame.pack(fill="x", padx=20, pady=10)
        question_label = ttk.Label(question_frame, text=flashcard.question, wraplength=700, justify="center", font=("Arial", 12))
        question_label.pack(pady=25, padx=20)
        
        # Answer (hidden initially)
        answer_frame = ttk.LabelFrame(self, text="Answer", padding="15")
        answer_frame.pack(fill="x", padx=20, pady=15)
        
        if self.answer_revealed:
            answer_text = flashcard.answer
            state = "disabled"
            self.show_rating_buttons()
        else:
            answer_text = "[Click 'Reveal Answer' to see]"
        
        self.answer_label = ttk.Label(answer_frame, text=answer_text,
                                wraplength=650, justify="center", font=("Arial", 12, "italic"))
        self.answer_label.pack(pady=20, padx=20)
        
        if not self.answer_revealed:
            # Reveal button
            self.show_answer_button = ttk.Button(self, text="Reveal Answer", command=self.reveal_answer, style="Large.TButton")
            self.show_answer_button.pack(pady=15, fill="x", ipady=10)

    def reveal_answer(self):
        self.answer_revealed = True
        flashcard = self.current_flashcards[self.current_index]
        self.answer_label.config(text=flashcard.answer, font=("Arial", 12))
        self.show_answer_button.pack_forget() # Remove reveal button
        self.show_rating_buttons()

    def show_rating_buttons(self):
        rating_frame = ttk.LabelFrame(self, text="How well did you remember this?", padding="15")
        rating_frame.pack(fill="x", padx=20, pady=15)
        
        # Create rating buttons in a more organized way
        button_container = ttk.Frame(rating_frame)
        button_container.pack(fill="both", expand=True)
        
        ratings = [
            (0, "0 - Blank"),
            (1, "1 - Poor"),
            (2, "2 - Hard"),
            (3, "3 - OK"),
            (4, "4 - Good"),
            (5, "5 - Perfect")
        ]
        
        for quality, label in ratings:
            btn = ttk.Button(button_container, text=label, 
                           command=lambda q=quality: self.submit_rating(q), 
                           style="Large.TButton")
            btn.pack(side="left", padx=3, fill="both", expand=True, ipady=8)

    def submit_rating(self, quality):
        flashcard = self.current_flashcards[self.current_index]
        flashcard.mark_reviewed(quality)
        self.db.update_flashcard(flashcard)
        self.current_index += 1
        self.answer_revealed = False
        self.show_review_card()

    def finish_review(self):
        """Show review completion screen."""
        self.clear_content()
        
        ttk.Label(self, text="Review Complete!", font=("Arial", 24, "bold")).pack(pady=20)
        ttk.Label(self, text=f"You reviewed {len(self.current_flashcards)} cards", 
                 font=("Arial", 14)).pack(pady=10)
        
        ttk.Button(self, text="Back to Deck", command=self.go_back, style="Large.TButton").pack(pady=20)

    def go_back(self):
        if hasattr(self.controller, 'show_deck_menu'):
            self.controller.show_deck_menu(self.deck_id)

    def clear_content(self):
        """Clear all widgets from the frame."""
        for widget in self.winfo_children():
            widget.destroy()
