import tkinter as tk
from tkinter import ttk, messagebox
from src.core.database import FlashcardDatabase

class DeckOverviewFrame(ttk.Frame):
    def __init__(self, parent, controller, db: FlashcardDatabase, deck_id: int):
        super().__init__(parent)
        self.controller = controller
        self.db = db
        self.deck_id = deck_id
        self.style = ttk.Style()
        self.style.configure("Large.TButton", font=("Arial", 12), padding=15)
        
        self.setup_ui()
        
    def setup_ui(self):
        deck_stats = self.db.get_deck_statistics(self.deck_id)
        decks = self.db.get_all_decks()
        # Find deck name safely
        deck_name = "Unknown Deck"
        for d in decks:
            if d["id"] == self.deck_id:
                deck_name = d["name"]
                break
        
        self.pack(fill="both", expand=True)
        
        # Title
        title = ttk.Label(self, text=f"Deck: {deck_name}", font=("Arial", 22, "bold"))
        title.pack(pady=20)
        
        # Statistics
        stats_frame = ttk.LabelFrame(self, text="Statistics", padding="15")
        stats_frame.pack(fill="x", pady=15, padx=20)
        
        stats_text = f"""Total Cards: {deck_stats['total_cards']}  |  Due Today: {deck_stats['due_cards']}
Total Reviews: {deck_stats['total_reviews']}  |  Accuracy: {deck_stats['overall_accuracy']:.1f}%"""
        
        ttk.Label(stats_frame, text=stats_text, font=("Arial", 11)).pack()
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=25, padx=20)
        
        review_btn = ttk.Button(btn_frame, text="Review Cards", command=self.start_review, style="Large.TButton")
        review_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        add_btn = ttk.Button(btn_frame, text="Add Card", command=self.add_card_dialog, style="Large.TButton")
        add_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        view_btn = ttk.Button(btn_frame, text="View All Cards", command=self.view_all_cards, style="Large.TButton")
        view_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        # Check logic for ollama later, for now conditional on controller
        if hasattr(self.controller, 'is_ollama_available') and self.controller.is_ollama_available():
            grammar_btn = ttk.Button(btn_frame, text="Grammar Help", command=self.show_grammar_help, style="Large.TButton")
            grammar_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        back_btn = ttk.Button(btn_frame, text="Back", command=self.go_back, style="Large.TButton")
        back_btn.pack(side="left", padx=10, fill="both", expand=True)

    def start_review(self):
        if hasattr(self.controller, 'start_review'):
            self.controller.start_review(self.deck_id)

    def view_all_cards(self):
        if hasattr(self.controller, 'view_all_cards'):
            self.controller.view_all_cards(self.deck_id)

    def go_back(self):
        if hasattr(self.controller, 'show_deck_selection'):
            self.controller.show_deck_selection()

    def add_card_dialog(self):
        """Show dialog to add a new card."""
        dialog = tk.Toplevel(self)
        dialog.title("Add Flashcard")
        dialog.geometry("400x300")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Question:", font=("Arial", 10)).pack(pady=5)
        question_text = tk.Text(dialog, height=3, width=40)
        question_text.pack(pady=5)
        
        warning_label = ttk.Label(dialog, text="", foreground="orange", font=("Arial", 9, "italic"))
        warning_label.pack()
        
        ttk.Label(dialog, text="Answer:", font=("Arial", 10)).pack(pady=5)
        answer_text = tk.Text(dialog, height=3, width=40)
        answer_text.pack(pady=5)
        
        def check_duplicate(event=None):
            question = question_text.get("1.0", "end").strip()
            if not question:
                warning_label.config(text="")
                return
            
            matches = self.db.find_flashcard_by_question(question)
            if matches:
                matching_decks = list(set([m['deck_name'] for m in matches]))
                warning_label.config(text=f"⚠️ Already in deck(s): {', '.join(matching_decks)}")
            else:
                warning_label.config(text="")
        
        question_text.bind("<KeyRelease>", check_duplicate)
        
        def save_card():
            question = question_text.get("1.0", "end").strip()
            answer = answer_text.get("1.0", "end").strip()
            
            if not question or not answer:
                messagebox.showerror("Error", "Please enter both question and answer")
                return
            
            # Check for duplicates again on save
            # Using controller.db or self.db (assuming it's valid)
            matches = self.db.find_flashcard_by_question(question)
            if matches:
                 matching_decks = list(set([m['deck_name'] for m in matches]))
                 msg = f"This word already exists in deck(s): {', '.join(matching_decks)}.\n\nAdd it anyway?"
                 if not messagebox.askyesno("Duplicate Word", msg):
                     return
            
            self.db.add_flashcard(self.deck_id, question, answer)
            messagebox.showinfo("Success", "Card added!")
            dialog.destroy()
            # Refresh stats
            self.refresh_stats()
            
        ttk.Button(dialog, text="Save", command=save_card).pack(pady=10)

    def refresh_stats(self):
        # Simply reload the whole UI for now
        for widget in self.winfo_children():
            widget.destroy()
        self.setup_ui()

    def show_grammar_help(self):
        # Delegate to controller if complex, or implement here if simple
        if hasattr(self.controller, 'show_grammar_help'):
             self.controller.show_grammar_help()
        else:
             # Basic implementation fallback?
             pass
