import tkinter as tk
from tkinter import ttk, messagebox
from src.core.database import FlashcardDatabase
from src.features.flashcards.logic.spaced_repetition import get_next_review_date

class CardListFrame(ttk.Frame):
    def __init__(self, parent, controller, db: FlashcardDatabase, deck_id: int):
        super().__init__(parent)
        self.controller = controller
        self.db = db
        self.deck_id = deck_id
        
        self.setup_ui()
        
    def setup_ui(self):
        title = ttk.Label(self, text="All Cards in Deck", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        self.current_all_flashcards = self.db.get_all_flashcards(self.deck_id)
        
        if not self.current_all_flashcards:
            ttk.Label(self, text="No cards in this deck", font=("Arial", 12)).pack(pady=20)
        else:
            # Controls Frame (Search & Sort)
            controls_frame = ttk.Frame(self)
            controls_frame.pack(fill="x", pady=(0, 10), padx=20)
            
            ttk.Label(controls_frame, text="Search:").pack(side="left", padx=(0, 5))
            self.card_search_var = tk.StringVar()
            search_entry = ttk.Entry(controls_frame, textvariable=self.card_search_var, width=30)
            search_entry.pack(side="left", padx=(0, 20))
            search_entry.bind("<KeyRelease>", lambda e: self._filter_and_sort_cards())
            
            ttk.Label(controls_frame, text="Sort By:").pack(side="left", padx=(0, 5))
            self.card_sort_var = tk.StringVar(value="Newest First")
            sort_options = ["Newest First", "Oldest First", "A-Z (Question)", "Accuracy (Low)", "Accuracy (High)"]
            sort_dropdown = ttk.Combobox(controls_frame, textvariable=self.card_sort_var, values=sort_options, state="readonly", width=15)
            sort_dropdown.pack(side="left")
            sort_dropdown.bind("<<ComboboxSelected>>", lambda e: self._filter_and_sort_cards())
            
            # Treeview for cards
            self.cards_tree = ttk.Treeview(self, columns=("Accuracy", "Next Review"), height=15)
            self.cards_tree.column("#0", width=300)
            self.cards_tree.column("Accuracy", width=150)
            self.cards_tree.column("Next Review", width=200)
            self.cards_tree.heading("#0", text="Question")
            self.cards_tree.heading("Accuracy", text="Accuracy")
            self.cards_tree.heading("Next Review", text="Next Review Date")
            self.cards_tree.pack(fill="both", expand=True, pady=10, padx=20)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.cards_tree.yview)
            scrollbar.pack(side="right", fill="y")
            self.cards_tree.configure(yscroll=scrollbar.set)
            
            # Action Buttons
            action_frame = ttk.Frame(self)
            action_frame.pack(fill="x", pady=10, padx=20)
            
            ttk.Button(action_frame, text="Edit Selected", command=self.edit_selected_card).pack(side="left", padx=5)
            ttk.Button(action_frame, text="Delete Selected", command=self.delete_selected_card_from_list).pack(side="left", padx=5)
        
        ttk.Button(self, text="Back", command=self.go_back).pack(pady=10)
        
        if self.current_all_flashcards:
            self._filter_and_sort_cards()

    def go_back(self):
        if hasattr(self.controller, 'show_deck_menu'):
            self.controller.show_deck_menu(self.deck_id)

    def _filter_and_sort_cards(self):
        search_query = self.card_search_var.get().lower().strip()
        sort_by = self.card_sort_var.get()
        
        # Filter
        filtered = self.current_all_flashcards
        if search_query:
            filtered = [fc for fc in filtered if search_query in fc.question.lower() or search_query in fc.answer.lower()]
            
        # Sort
        if sort_by == "Newest First":
            filtered = sorted(filtered, key=lambda x: x.id, reverse=True)
        elif sort_by == "Oldest First":
            filtered = sorted(filtered, key=lambda x: x.id)
        elif sort_by == "A-Z (Question)":
            filtered = sorted(filtered, key=lambda x: x.question.lower())
        elif sort_by == "Accuracy (Low)":
            filtered = sorted(filtered, key=lambda x: x.get_accuracy())
        elif sort_by == "Accuracy (High)":
            filtered = sorted(filtered, key=lambda x: x.get_accuracy(), reverse=True)
            
        # Update Treeview
        for item in self.cards_tree.get_children():
            self.cards_tree.delete(item)
            
        self.filtered_cards = filtered
        
        for i, fc in enumerate(filtered):
            accuracy = f"{fc.get_accuracy():.1f}%" if fc.total_reviews > 0 else "N/A"
            next_review = get_next_review_date(fc).strftime("%Y-%m-%d %H:%M") if fc.last_reviewed else "Today"
            self.cards_tree.insert("", "end", iid=str(i), text=fc.question, values=(accuracy, next_review))

    def edit_selected_card(self):
        selection = self.cards_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a card to edit")
            return
        
        index = int(selection[0])
        flashcard = self.filtered_cards[index]
        
        dialog = tk.Toplevel(self)
        dialog.title("Edit Flashcard")
        dialog.geometry("400x350")
        dialog.grab_set()
        
        ttk.Label(dialog, text="Question:", font=("Arial", 10)).pack(pady=5)
        question_text = tk.Text(dialog, height=4, width=40)
        question_text.pack(pady=5)
        question_text.insert("1.0", flashcard.question)
        
        ttk.Label(dialog, text="Answer:", font=("Arial", 10)).pack(pady=5)
        answer_text = tk.Text(dialog, height=4, width=40)
        answer_text.pack(pady=5)
        answer_text.insert("1.0", flashcard.answer)
        
        def save_changes():
            new_question = question_text.get("1.0", "end").strip()
            new_answer = answer_text.get("1.0", "end").strip()
            
            if not new_question or not new_answer:
                messagebox.showerror("Error", "Both question and answer are required")
                return
            
            flashcard.question = new_question
            flashcard.answer = new_answer
            self.db.update_flashcard(flashcard)
            
            messagebox.showinfo("Success", "Card updated!")
            dialog.destroy()
            
            # Refresh data and view
            self.current_all_flashcards = self.db.get_all_flashcards(self.deck_id)
            self._filter_and_sort_cards()
            
        ttk.Button(dialog, text="Save Changes", command=save_changes).pack(pady=10)

    def delete_selected_card_from_list(self):
        selection = self.cards_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a card to delete")
            return
        
        index = int(selection[0])
        flashcard = self.filtered_cards[index]
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this card?"):
            self.db.delete_flashcard(flashcard.id)
            messagebox.showinfo("Success", "Card deleted!")
            
            # Refresh data and view
            self.current_all_flashcards = self.db.get_all_flashcards(self.deck_id)
            self._filter_and_sort_cards()
