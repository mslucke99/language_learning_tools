import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
from database import FlashcardDatabase
from spaced_repetition import get_due_flashcards, get_next_review_date
from flashcard import Flashcard
from datetime import datetime
from ollama_integration import get_ollama_client, is_ollama_available, OllamaThreadedQuery
from study_manager import StudyManager
from study_gui import StudyGUI

class FlashcardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Language Learning Suite")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")
        
        self.db = FlashcardDatabase()
        self.ollama_client = get_ollama_client()
        self.ollama_available = is_ollama_available()
        
        # Initialize study manager
        self.study_manager = StudyManager(self.db, self.ollama_client)
        self.study_gui = StudyGUI(self.root, self.db, self.study_manager)
        
        self.current_deck_id = None
        self.current_flashcards = []
        self.current_index = 0
        self.reviewing = False
        self.answer_revealed = False
        
        # Style configuration with better button sizing
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure("TButton", font=("Arial", 11), padding=10)
        self.style.configure("Large.TButton", font=("Arial", 12), padding=15)
        self.style.configure("TLabel", font=("Arial", 10))
        
        self.show_deck_selection()
    
    def clear_window(self):
        """Clear all widgets from the window."""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_deck_selection(self):
        """Show the deck selection screen."""
        self.clear_window()
        self.reviewing = False
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        # Title and status
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill="x", pady=10)
        
        title = ttk.Label(title_frame, text="Language Learning Suite", font=("Arial", 28, "bold"))
        title.pack(side="left")
        
        # Ollama status indicator
        if self.ollama_available:
            ollama_status = ttk.Label(title_frame, text="✓ Ollama Connected", foreground="green", font=("Arial", 10, "bold"))
        else:
            ollama_status = ttk.Label(title_frame, text="⚠ Ollama Offline", foreground="red", font=("Arial", 10))
        ollama_status.pack(side="right", padx=10)
        
        # Create deck button - LARGER
        create_btn = ttk.Button(frame, text="Create New Deck", command=self.create_deck_dialog, style="Large.TButton")
        create_btn.pack(pady=15, fill="x", ipady=10)
        
        # Study Center button - NEW!
        study_btn = ttk.Button(frame, text="🎓 Study Center", command=self.open_study_center, style="Large.TButton")
        study_btn.pack(pady=15, fill="x", ipady=10)
        
        # Settings button
        settings_btn = ttk.Button(frame, text="⚙️ Settings", command=self.show_settings, style="Large.TButton")
        settings_btn.pack(pady=15, fill="x", ipady=10)
        
        # Deck list
        list_label = ttk.Label(frame, text="Your Decks:", font=("Arial", 13, "bold"))
        list_label.pack(pady=15)
        
        # Treeview for decks
        self.decks_tree = ttk.Treeview(frame, columns=("Total", "Due"), height=12)
        self.decks_tree.column("#0", width=400)
        self.decks_tree.column("Total", width=150)
        self.decks_tree.column("Due", width=150)
        self.decks_tree.heading("#0", text="Deck Name")
        self.decks_tree.heading("Total", text="Total Cards")
        self.decks_tree.heading("Due", text="Due Today")
        self.decks_tree.pack(fill="both", expand=True, pady=10)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.decks_tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.decks_tree.configure(yscroll=scrollbar.set)
        
        # Buttons frame - LARGER BUTTONS
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=20)
        
        open_btn = ttk.Button(btn_frame, text="Open Deck", command=self.open_deck, style="Large.TButton")
        open_btn.pack(side="left", padx=8, fill="both", expand=True)
        
        stats_btn = ttk.Button(btn_frame, text="View Statistics", command=self.view_deck_stats, style="Large.TButton")
        stats_btn.pack(side="left", padx=8, fill="both", expand=True)
        
        delete_btn = ttk.Button(btn_frame, text="Delete Deck", command=self.delete_deck, style="Large.TButton")
        delete_btn.pack(side="left", padx=8, fill="both", expand=True)
        
        self.refresh_decks()
    
    def refresh_decks(self):
        """Refresh the decks list."""
        for item in self.decks_tree.get_children():
            self.decks_tree.delete(item)
        
        decks = self.db.get_all_decks()
        for deck in decks:
            self.decks_tree.insert(
                "", "end", text=deck["name"],
                values=(deck["total_cards"], deck["due_cards"])
            )
    
    def create_deck_dialog(self):
        """Show dialog to create a new deck."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Create New Deck")
        dialog.geometry("300x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Deck Name:", font=("Arial", 10)).pack(pady=5)
        name_entry = ttk.Entry(dialog, width=30)
        name_entry.pack(pady=5)
        
        ttk.Label(dialog, text="Description (optional):", font=("Arial", 10)).pack(pady=5)
        desc_entry = ttk.Entry(dialog, width=30)
        desc_entry.pack(pady=5)
        
        def save_deck():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Please enter a deck name")
                return
            
            deck_id = self.db.create_deck(name, desc_entry.get())
            if deck_id is None:
                messagebox.showerror("Error", "A deck with that name already exists")
            else:
                messagebox.showinfo("Success", f"Deck '{name}' created!")
                dialog.destroy()
                self.refresh_decks()
        
        ttk.Button(dialog, text="Create", command=save_deck).pack(pady=10)
    
    def open_deck(self):
        """Open selected deck."""
        selection = self.decks_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a deck")
            return
        
        deck_name = self.decks_tree.item(selection[0])["text"]
        decks = self.db.get_all_decks()
        for deck in decks:
            if deck["name"] == deck_name:
                self.current_deck_id = deck["id"]
                self.show_deck_menu()
                break
    
    def show_deck_menu(self):
        """Show the deck management menu."""
        self.clear_window()
        
        deck_stats = self.db.get_deck_statistics(self.current_deck_id)
        decks = self.db.get_all_decks()
        deck_name = next(d["name"] for d in decks if d["id"] == self.current_deck_id)
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        # Title
        title = ttk.Label(frame, text=f"Deck: {deck_name}", font=("Arial", 22, "bold"))
        title.pack(pady=20)
        
        # Statistics
        stats_frame = ttk.LabelFrame(frame, text="Statistics", padding="15")
        stats_frame.pack(fill="x", pady=15)
        
        stats_text = f"""Total Cards: {deck_stats['total_cards']}  |  Due Today: {deck_stats['due_cards']}
Total Reviews: {deck_stats['total_reviews']}  |  Accuracy: {deck_stats['overall_accuracy']:.1f}%"""
        
        ttk.Label(stats_frame, text=stats_text, font=("Arial", 11)).pack()
        
        # Buttons - LARGER AND BETTER SPACED
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=25)
        
        review_btn = ttk.Button(btn_frame, text="Review Cards", command=self.start_review, style="Large.TButton")
        review_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        add_btn = ttk.Button(btn_frame, text="Add Card", command=self.add_card_dialog, style="Large.TButton")
        add_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        view_btn = ttk.Button(btn_frame, text="View All Cards", command=self.view_all_cards, style="Large.TButton")
        view_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        if self.ollama_available:
            grammar_btn = ttk.Button(btn_frame, text="Grammar Help", command=self.show_grammar_help, style="Large.TButton")
            grammar_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        back_btn = ttk.Button(btn_frame, text="Back", command=self.show_deck_selection, style="Large.TButton")
        back_btn.pack(side="left", padx=10, fill="both", expand=True)
    
    def add_card_dialog(self):
        """Show dialog to add a new card."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Flashcard")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Question:", font=("Arial", 10)).pack(pady=5)
        question_text = tk.Text(dialog, height=3, width=40)
        question_text.pack(pady=5)
        
        ttk.Label(dialog, text="Answer:", font=("Arial", 10)).pack(pady=5)
        answer_text = tk.Text(dialog, height=3, width=40)
        answer_text.pack(pady=5)
        
        def save_card():
            question = question_text.get("1.0", "end").strip()
            answer = answer_text.get("1.0", "end").strip()
            
            if not question or not answer:
                messagebox.showerror("Error", "Please enter both question and answer")
                return
            
            self.db.add_flashcard(self.current_deck_id, question, answer)
            messagebox.showinfo("Success", "Card added!")
            dialog.destroy()
            self.show_deck_menu()
        
        ttk.Button(dialog, text="Save", command=save_card).pack(pady=10)
    
    def view_all_cards(self):
        """View all cards in the deck."""
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        title = ttk.Label(frame, text="All Cards in Deck", font=("Arial", 16, "bold"))
        title.pack(pady=10)
        
        flashcards = self.db.get_all_flashcards(self.current_deck_id)
        
        if not flashcards:
            ttk.Label(frame, text="No cards in this deck", font=("Arial", 12)).pack(pady=20)
        else:
            # Treeview for cards
            tree = ttk.Treeview(frame, columns=("Accuracy", "Next Review"), height=20)
            tree.column("#0", width=300)
            tree.column("Accuracy", width=150)
            tree.column("Next Review", width=200)
            tree.heading("#0", text="Question")
            tree.heading("Accuracy", text="Accuracy")
            tree.heading("Next Review", text="Next Review Date")
            tree.pack(fill="both", expand=True, pady=10)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
            scrollbar.pack(side="right", fill="y")
            tree.configure(yscroll=scrollbar.set)
            
            for fc in flashcards:
                accuracy = f"{fc.get_accuracy():.1f}%" if fc.total_reviews > 0 else "N/A"
                next_review = get_next_review_date(fc).strftime("%Y-%m-%d %H:%M") if fc.last_reviewed else "Today"
                tree.insert("", "end", text=fc.question, values=(accuracy, next_review))
        
        ttk.Button(frame, text="Back", command=self.show_deck_menu).pack(pady=10)
    
    def start_review(self):
        """Start reviewing cards."""
        due_cards = self.db.get_due_flashcards(self.current_deck_id)
        
        if not due_cards:
            messagebox.showinfo("Info", "No cards due for review!")
            return
        
        self.current_flashcards = due_cards
        self.current_index = 0
        self.reviewing = True
        self.answer_revealed = False
        self.show_review_card()
    
    def show_review_card(self):
        """Show the current card during review."""
        self.clear_window()
        
        if self.current_index >= len(self.current_flashcards):
            self.finish_review()
            return
        
        flashcard = self.current_flashcards[self.current_index]
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        # Progress
        progress_text = f"Card {self.current_index + 1} of {len(self.current_flashcards)}"
        ttk.Label(frame, text=progress_text, font=("Arial", 11, "bold")).pack(pady=10)
        
        # Progress bar
        progress = ttk.Progressbar(frame, length=500, mode="determinate", 
                                   value=(self.current_index / len(self.current_flashcards)) * 100)
        progress.pack(pady=10)
        
        # Question
        ttk.Label(frame, text="Question:", font=("Arial", 13, "bold")).pack(pady=15)
        question_frame = ttk.Frame(frame, relief="sunken", borderwidth=2)
        question_frame.pack(fill="x", padx=20, pady=10)
        question_label = ttk.Label(question_frame, text=flashcard.question, wraplength=700, justify="center", font=("Arial", 12))
        question_label.pack(pady=25, padx=20)
        
        # Answer (hidden initially)
        answer_frame = ttk.LabelFrame(frame, text="Answer", padding="15")
        answer_frame.pack(fill="x", padx=20, pady=15)
        answer_label = ttk.Label(answer_frame, text="[Click 'Reveal Answer' to see]",
                                wraplength=650, justify="center", font=("Arial", 12, "italic"))
        answer_label.pack(pady=20, padx=20)
        
        # Reveal button - LARGER
        def reveal_answer():
            self.answer_revealed = True
            answer_label.config(text=flashcard.answer, font=("Arial", 12))
            show_answer_button.config(state="disabled")
            show_rating_buttons()
        
        show_answer_button = ttk.Button(frame, text="Reveal Answer", command=reveal_answer, style="Large.TButton")
        show_answer_button.pack(pady=15, fill="x", ipady=10)
        
        # Rating buttons
        def show_rating_buttons():
            rating_frame = ttk.LabelFrame(frame, text="How well did you remember this?", padding="15")
            rating_frame.pack(fill="x", padx=20, pady=15)
            
            def submit_rating(quality):
                flashcard.mark_reviewed(quality)
                self.db.update_flashcard(flashcard)
                self.current_index += 1
                self.answer_revealed = False
                self.show_review_card()
            
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
                               command=lambda q=quality: submit_rating(q), 
                               style="Large.TButton")
                btn.pack(side="left", padx=3, fill="both", expand=True, ipady=8)
    
    def finish_review(self):
        """Show review completion screen."""
        self.clear_window()
        self.reviewing = False
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Review Complete!", font=("Arial", 24, "bold")).pack(pady=20)
        ttk.Label(frame, text=f"You reviewed {len(self.current_flashcards)} cards", 
                 font=("Arial", 14)).pack(pady=10)
        
        ttk.Button(frame, text="Back to Deck", command=self.show_deck_menu).pack(pady=20)
    
    def view_deck_stats(self):
        """Show detailed statistics for selected deck."""
        selection = self.decks_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a deck")
            return
        
        deck_name = self.decks_tree.item(selection[0])["text"]
        decks = self.db.get_all_decks()
        deck = next(d for d in decks if d["name"] == deck_name)
        stats = self.db.get_deck_statistics(deck["id"])
        
        # Calculate reviewed count and averages from cards
        cards = self.db.get_all_flashcards(deck["id"])
        reviewed_count = sum(1 for c in cards if c.total_reviews > 0)
        avg_easiness = sum(c.easiness for c in cards) / len(cards) if cards else 0.0
        avg_interval = sum(c.interval for c in cards) / len(cards) if cards else 0.0
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Statistics - {deck_name}")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        stats_text = f"""
Deck: {deck_name}
Created: {deck['created_at']}

Total Cards: {stats['total_cards']}
New Cards: {stats['total_cards'] - reviewed_count}
Reviewed: {reviewed_count}
Due Today: {stats['due_cards']}

Total Reviews: {stats['total_reviews']}
Correct Reviews: {stats['correct_reviews']}
Overall Accuracy: {stats['overall_accuracy']:.1f}%

Average Easiness: {avg_easiness:.2f}
Average Interval: {avg_interval:.1f} days
        """
        
        ttk.Label(dialog, text=stats_text, font=("Courier", 10), justify="left").pack(padx=10, pady=10)
    
    def show_grammar_help(self):
        """Show grammar help using Ollama."""
        if not self.ollama_available:
            messagebox.showerror("Error", "Ollama is not available")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Grammar Help & Word Definitions")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Tab-like interface
        input_frame = ttk.LabelFrame(dialog, text="Search", padding="10")
        input_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(input_frame, text="Grammar Topic or Word:", font=("Arial", 10)).pack(anchor="w")
        search_entry = ttk.Entry(input_frame, width=50)
        search_entry.pack(fill="x", pady=5)
        
        ttk.Label(input_frame, text="Type: ", font=("Arial", 10)).pack(anchor="w")
        search_type = tk.StringVar(value="definition")
        type_frame = ttk.Frame(input_frame)
        type_frame.pack(anchor="w")
        ttk.Radiobutton(type_frame, text="Word Definition", variable=search_type, value="definition").pack(side="left", padx=5)
        ttk.Radiobutton(type_frame, text="Grammar Explanation", variable=search_type, value="grammar").pack(side="left", padx=5)
        
        # Results area
        results_frame = ttk.LabelFrame(dialog, text="Results", padding="10")
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        results_text = scrolledtext.ScrolledText(results_frame, height=20, width=70, font=("Arial", 10))
        results_text.pack(fill="both", expand=True)
        
        status_label = ttk.Label(dialog, text="Ready", font=("Arial", 9), foreground="blue")
        status_label.pack(pady=5)
        
        def search_callback(result):
            status_label.config(text="Ready", foreground="blue")
            if result:
                results_text.config(state="normal")
                results_text.delete("1.0", "end")
                results_text.insert("1.0", result)
                results_text.config(state="disabled")
            else:
                messagebox.showerror("Error", "Failed to get response from Ollama")
        
        def perform_search():
            query = search_entry.get().strip()
            if not query:
                messagebox.showwarning("Warning", "Please enter a search term")
                return
            
            status_label.config(text="Querying Ollama...", foreground="orange")
            dialog.update()
            
            query_helper = OllamaThreadedQuery(self.ollama_client)
            
            if search_type.get() == "definition":
                query_helper.suggest_words_async(query, search_callback, language="Spanish")
                # Actually get definition
                result = self.ollama_client.define_word(query, language="Spanish")
                if result:
                    formatted = f"Definition of '{query}':\n\n"
                    formatted += f"Definition: {result.get('definition', 'N/A')}\n"
                    formatted += f"Part of Speech: {result.get('part_of_speech', 'N/A')}\n"
                    formatted += f"Example: {result.get('example', 'N/A')}\n"
                    formatted += f"Synonyms: {result.get('synonyms', 'N/A')}"
                    search_callback(formatted)
            else:
                result = self.ollama_client.explain_grammar(query, language="Spanish")
                search_callback(result)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        search_btn = ttk.Button(btn_frame, text="Search", command=perform_search, style="Large.TButton")
        search_btn.pack(side="left", padx=5, fill="both", expand=True)
        
        close_btn = ttk.Button(btn_frame, text="Close", command=dialog.destroy, style="Large.TButton")
        close_btn.pack(side="left", padx=5, fill="both", expand=True)
    
    def suggest_difficult_words(self):
        """Suggest difficult words from article text."""
        if not self.ollama_available:
            messagebox.showerror("Error", "Ollama is not available")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Suggest Words to Learn")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Paste article text:", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=10)
        
        text_input = scrolledtext.ScrolledText(dialog, height=15, width=70, font=("Arial", 10))
        text_input.pack(fill="both", expand=True, padx=10, pady=5)
        
        status_label = ttk.Label(dialog, text="Ready", font=("Arial", 9), foreground="blue")
        status_label.pack(pady=5)
        
        def analyze_text():
            text = text_input.get("1.0", "end").strip()
            if not text or len(text) < 50:
                messagebox.showwarning("Warning", "Please enter at least 50 characters of text")
                return
            
            status_label.config(text="Analyzing with Ollama...", foreground="orange")
            dialog.update()
            
            words = self.ollama_client.suggest_difficult_words(text, difficulty_level="intermediate", language="Spanish")
            
            if words:
                status_label.config(text=f"Found {len(words)} words", foreground="green")
                # Show results
                result_dialog = tk.Toplevel(dialog)
                result_dialog.title("Suggested Words")
                result_dialog.geometry("400x300")
                
                ttk.Label(result_dialog, text="Words to add to deck:", font=("Arial", 11, "bold")).pack(anchor="w", padx=10, pady=10)
                
                words_frame = ttk.Frame(result_dialog)
                words_frame.pack(fill="both", expand=True, padx=10, pady=5)
                
                selected_words = {}
                for word in words:
                    var = tk.BooleanVar(value=True)
                    selected_words[word] = var
                    ttk.Checkbutton(words_frame, text=word, variable=var).pack(anchor="w", pady=3)
                
                def add_selected_words():
                    words_to_add = [w for w, v in selected_words.items() if v.get()]
                    if words_to_add:
                        # Create cards for selected words
                        for word in words_to_add:
                            definition = self.ollama_client.define_word(word, language="Spanish")
                            if definition:
                                question = f"What does '{word}' mean?"
                                answer = definition.get("definition", word)
                                self.db.add_flashcard(self.current_deck_id, question, answer)
                        
                        messagebox.showinfo("Success", f"Added {len(words_to_add)} cards to deck!")
                        dialog.destroy()
                        result_dialog.destroy()
                    else:
                        messagebox.showwarning("Warning", "Please select at least one word")
                
                ttk.Button(result_dialog, text="Add Selected Words", command=add_selected_words, style="Large.TButton").pack(fill="x", padx=10, pady=10, ipady=8)
            else:
                status_label.config(text="Error analyzing text", foreground="red")
                messagebox.showerror("Error", "Failed to get word suggestions")
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        analyze_btn = ttk.Button(btn_frame, text="Analyze Text", command=analyze_text, style="Large.TButton")
        analyze_btn.pack(side="left", padx=5, fill="both", expand=True)
        
        close_btn = ttk.Button(btn_frame, text="Close", command=dialog.destroy, style="Large.TButton")
        close_btn.pack(side="left", padx=5, fill="both", expand=True)
    
    def delete_deck(self):
        """Delete selected deck."""
        selection = self.decks_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a deck")
            return
        
        deck_name = self.decks_tree.item(selection[0])["text"]
        if messagebox.askyesno("Confirm", f"Delete deck '{deck_name}' and all its cards?"):
            decks = self.db.get_all_decks()
            deck_id = next(d["id"] for d in decks if d["name"] == deck_name)
            self.db.delete_deck(deck_id)
            messagebox.showinfo("Success", "Deck deleted!")
    
    
    def open_study_center(self):
        """Open the Study Center."""
        self.study_gui.on_close = self.show_deck_selection  # Set return callback
        self.study_gui.show_study_center()
    
    def show_settings(self):
        """Show the settings dialog."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Settings")
        dialog.geometry("600x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create notebook for tabs
        notebook = ttk.Notebook(dialog)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # ===== OLLAMA SETTINGS TAB =====
        ollama_frame = ttk.Frame(notebook, padding="20")
        notebook.add(ollama_frame, text="Ollama Settings")
        
        # Model selection
        ttk.Label(ollama_frame, text="Ollama Model:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        
        model_frame = ttk.Frame(ollama_frame)
        model_frame.pack(fill="x", pady=(0, 15))
        
        current_model = self.study_manager.get_ollama_model()
        available_models = self.study_manager.get_available_ollama_models()
        
        if not available_models:
            ttk.Label(model_frame, text="No models available. Is Ollama running?", foreground="red").pack(anchor="w")
            model_var = tk.StringVar(value="")
        else:
            model_var = tk.StringVar(value=current_model if current_model else available_models[0])
            model_dropdown = ttk.Combobox(model_frame, textvariable=model_var, values=available_models, state="readonly", width=40)
            model_dropdown.pack(anchor="w")
        
        # Timeout setting
        ttk.Label(ollama_frame, text="Request Timeout (seconds):", font=("Arial", 11, "bold")).pack(anchor="w", pady=(15, 5))
        
        timeout_frame = ttk.Frame(ollama_frame)
        timeout_frame.pack(fill="x", pady=(0, 15))
        
        current_timeout = self.study_manager.get_request_timeout()
        timeout_var = tk.IntVar(value=current_timeout)
        timeout_spinbox = ttk.Spinbox(timeout_frame, from_=30, to=600, textvariable=timeout_var, width=10)
        timeout_spinbox.pack(side="left")
        ttk.Label(timeout_frame, text="  (30-600 seconds, higher for slower hardware)", font=("Arial", 9)).pack(side="left")
        
        # Info label
        info_text = """
Ollama Settings:
• Model: Choose which Ollama model to use for AI features
• Timeout: How long to wait for AI responses (increase for slower systems)

Note: Changes take effect immediately after clicking Save.
        """
        info_label = ttk.Label(ollama_frame, text=info_text, font=("Arial", 9), foreground="gray", justify="left")
        info_label.pack(anchor="w", pady=(20, 0))
        
        # ===== LANGUAGE SETTINGS TAB =====
        lang_frame = ttk.Frame(notebook, padding="20")
        notebook.add(lang_frame, text="Language Preferences")
        
        # Native language
        ttk.Label(lang_frame, text="Native Language:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        native_var = tk.StringVar(value=self.study_manager.native_language)
        native_entry = ttk.Entry(lang_frame, textvariable=native_var, width=30)
        native_entry.pack(anchor="w", pady=(0, 15))
        
        # Study language
        ttk.Label(lang_frame, text="Study Language:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 5))
        study_var = tk.StringVar(value=self.study_manager.study_language)
        study_entry = ttk.Entry(lang_frame, textvariable=study_var, width=30)
        study_entry.pack(anchor="w", pady=(0, 15))
        
        # Definition language preference
        ttk.Label(lang_frame, text="Definition Language Preference:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(15, 5))
        def_pref_var = tk.BooleanVar(value=self.study_manager.prefer_native_definitions)
        ttk.Radiobutton(lang_frame, text="Native language (easier to understand)", variable=def_pref_var, value=True).pack(anchor="w")
        ttk.Radiobutton(lang_frame, text="Study language (immersive learning)", variable=def_pref_var, value=False).pack(anchor="w")
        
        # Explanation language preference
        ttk.Label(lang_frame, text="Explanation Language Preference:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(15, 5))
        exp_pref_var = tk.BooleanVar(value=self.study_manager.prefer_native_explanations)
        ttk.Radiobutton(lang_frame, text="Native language", variable=exp_pref_var, value=True).pack(anchor="w")
        ttk.Radiobutton(lang_frame, text="Study language", variable=exp_pref_var, value=False).pack(anchor="w")
        
        # ===== CUSTOM PROMPTS TAB =====
        prompts_frame = ttk.Frame(notebook, padding="20")
        notebook.add(prompts_frame, text="Custom Prompts (Advanced)")
        
        # Info label
        info_label = ttk.Label(
            prompts_frame,
            text="Customize AI prompts for advanced control. Leave blank to use defaults.\nUse {word}, {sentence}, {native_language}, {study_language} as placeholders.",
            font=("Arial", 9),
            foreground="gray",
            justify="left"
        )
        info_label.pack(anchor="w", pady=(0, 10))
        
        # Create scrollable frame for prompts
        canvas = tk.Canvas(prompts_frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(prompts_frame, orient="vertical", command=canvas.yview)
        scrollable_prompts = ttk.Frame(canvas)
        
        scrollable_prompts.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_prompts, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Word prompts
        word_prompts_frame = ttk.LabelFrame(scrollable_prompts, text="Word Prompts", padding="10")
        word_prompts_frame.pack(fill="x", pady=5)
        
        prompt_vars = {}
        
        # Definition prompt (native)
        ttk.Label(word_prompts_frame, text="Definition (Native Language):", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 2))
        current_def_native = self.study_manager.get_word_prompt('definition', 'native')
        prompt_vars['word_definition_native'] = tk.StringVar(value=current_def_native)
        def_native_entry = ttk.Entry(word_prompts_frame, textvariable=prompt_vars['word_definition_native'], width=70)
        def_native_entry.pack(anchor="w", pady=(0, 5))
        
        # Definition prompt (study)
        ttk.Label(word_prompts_frame, text="Definition (Study Language):", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 2))
        current_def_study = self.study_manager.get_word_prompt('definition', 'study')
        prompt_vars['word_definition_study'] = tk.StringVar(value=current_def_study)
        def_study_entry = ttk.Entry(word_prompts_frame, textvariable=prompt_vars['word_definition_study'], width=70)
        def_study_entry.pack(anchor="w", pady=(0, 5))
        
        # Examples prompt (native)
        ttk.Label(word_prompts_frame, text="Examples (Native Language):", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 2))
        current_ex_native = self.study_manager.get_word_prompt('examples', 'native')
        prompt_vars['word_examples_native'] = tk.StringVar(value=current_ex_native)
        ex_native_entry = ttk.Entry(word_prompts_frame, textvariable=prompt_vars['word_examples_native'], width=70)
        ex_native_entry.pack(anchor="w", pady=(0, 5))
        
        # Sentence prompts
        sentence_prompts_frame = ttk.LabelFrame(scrollable_prompts, text="Sentence Prompts", padding="10")
        sentence_prompts_frame.pack(fill="x", pady=5)
        
        # Grammar prompt
        ttk.Label(sentence_prompts_frame, text="Grammar Analysis:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 2))
        current_grammar = self.study_manager.get_sentence_prompt('grammar')
        prompt_vars['sentence_grammar'] = tk.StringVar(value=current_grammar)
        grammar_entry = ttk.Entry(sentence_prompts_frame, textvariable=prompt_vars['sentence_grammar'], width=70)
        grammar_entry.pack(anchor="w", pady=(0, 5))
        
        # Vocabulary prompt
        ttk.Label(sentence_prompts_frame, text="Vocabulary Analysis:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 2))
        current_vocab = self.study_manager.get_sentence_prompt('vocabulary')
        prompt_vars['sentence_vocabulary'] = tk.StringVar(value=current_vocab)
        vocab_entry = ttk.Entry(sentence_prompts_frame, textvariable=prompt_vars['sentence_vocabulary'], width=70)
        vocab_entry.pack(anchor="w", pady=(0, 5))
        
        # Comprehensive prompt
        ttk.Label(sentence_prompts_frame, text="Comprehensive Analysis:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 2))
        current_all = self.study_manager.get_sentence_prompt('all')
        prompt_vars['sentence_all'] = tk.StringVar(value=current_all)
        all_entry = ttk.Entry(sentence_prompts_frame, textvariable=prompt_vars['sentence_all'], width=70)
        all_entry.pack(anchor="w", pady=(0, 10))
        
        # Reset to defaults button
        def reset_prompts():
            if messagebox.askyesno("Reset Prompts", "Reset all prompts to defaults?"):
                from prompts import WORD_PROMPTS, SENTENCE_PROMPTS
                prompt_vars['word_definition_native'].set(WORD_PROMPTS['definition']['native_template'])
                prompt_vars['word_definition_study'].set(WORD_PROMPTS['definition']['study_template'])
                prompt_vars['word_examples_native'].set(WORD_PROMPTS['examples']['native_template'])
                prompt_vars['sentence_grammar'].set(SENTENCE_PROMPTS['grammar']['template'])
                prompt_vars['sentence_vocabulary'].set(SENTENCE_PROMPTS['vocabulary']['template'])
                prompt_vars['sentence_all'].set(SENTENCE_PROMPTS['all']['template'])
        
        reset_btn = ttk.Button(scrollable_prompts, text="Reset to Defaults", command=reset_prompts)
        reset_btn.pack(pady=10)
        
        # ===== SAVE/CANCEL BUTTONS =====
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        def save_settings():
            # Save Ollama settings
            if available_models and model_var.get():
                self.study_manager.set_ollama_model(model_var.get())
            self.study_manager.set_request_timeout(timeout_var.get())
            
            # Save language settings
            self.study_manager.set_native_language(native_var.get())
            self.study_manager.set_study_language(study_var.get())
            self.study_manager.set_definition_language_preference(def_pref_var.get())
            self.study_manager.set_explanation_language_preference(exp_pref_var.get())
            
            # Save custom prompts (only if they differ from defaults)
            from prompts import WORD_PROMPTS, SENTENCE_PROMPTS
            
            # Word prompts
            if prompt_vars['word_definition_native'].get() != WORD_PROMPTS['definition']['native_template']:
                self.study_manager.set_word_prompt('definition', 'native', prompt_vars['word_definition_native'].get())
            if prompt_vars['word_definition_study'].get() != WORD_PROMPTS['definition']['study_template']:
                self.study_manager.set_word_prompt('definition', 'study', prompt_vars['word_definition_study'].get())
            if prompt_vars['word_examples_native'].get() != WORD_PROMPTS['examples']['native_template']:
                self.study_manager.set_word_prompt('examples', 'native', prompt_vars['word_examples_native'].get())
            
            # Sentence prompts
            if prompt_vars['sentence_grammar'].get() != SENTENCE_PROMPTS['grammar']['template']:
                self.study_manager.set_sentence_prompt('grammar', prompt_vars['sentence_grammar'].get())
            if prompt_vars['sentence_vocabulary'].get() != SENTENCE_PROMPTS['vocabulary']['template']:
                self.study_manager.set_sentence_prompt('vocabulary', prompt_vars['sentence_vocabulary'].get())
            if prompt_vars['sentence_all'].get() != SENTENCE_PROMPTS['all']['template']:
                self.study_manager.set_sentence_prompt('all', prompt_vars['sentence_all'].get())
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            dialog.destroy()
            
            # Refresh the main screen to update Ollama status
            self.show_deck_selection()

        
        save_btn = ttk.Button(button_frame, text="Save", command=save_settings, style="Large.TButton")
        save_btn.pack(side="left", padx=5, fill="both", expand=True)
        
        cancel_btn = ttk.Button(button_frame, text="Cancel", command=dialog.destroy, style="Large.TButton")
        cancel_btn.pack(side="left", padx=5, fill="both", expand=True)


def main():
    root = tk.Tk()
    app = FlashcardApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
