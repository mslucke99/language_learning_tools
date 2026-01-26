import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
import threading
import re
from database import FlashcardDatabase
from spaced_repetition import get_due_flashcards, get_next_review_date
from flashcard import Flashcard
from datetime import datetime
from ollama_integration import get_ollama_client, is_ollama_available, OllamaThreadedQuery
from study_manager import StudyManager
from study_gui import StudyGUI
from import_export import ImportExportManager

class FlashcardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Language Learning Suite")
        self.root.geometry("1000x700")
        self.root.configure(bg="#f0f0f0")
        
        self.db = FlashcardDatabase()
        self.ollama_client = get_ollama_client()
        self.ollama_available = is_ollama_available()
        
        # Initialize managers
        self.study_manager = StudyManager(self.db, self.ollama_client)
        self.io_manager = ImportExportManager(self.db, self.study_manager)
        self.study_gui = StudyGUI(self.root, self.db, self.study_manager, self.io_manager)
        
        # Pre-load Ollama model in background if enabled
        if self.ollama_available and self.study_manager.get_preload_on_startup():
            self._preload_ollama_background()
        
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
        
        # Main container with a scrollbar
        container = ttk.Frame(self.root)
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, padding="20")
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Ensure the scrollable frame expands to the canvas width
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Title and status
        title_frame = ttk.Frame(scrollable_frame)
        title_frame.pack(fill="x", pady=(0, 20))
        
        title = ttk.Label(title_frame, text="Language Learning Suite", font=("Arial", 28, "bold"))
        title.pack(side="left")
        
        if self.ollama_available:
            ollama_status = ttk.Label(title_frame, text="✓ Ollama Connected", foreground="green", font=("Arial", 10, "bold"))
        else:
            ollama_status = ttk.Label(title_frame, text="⚠ Ollama Offline", foreground="red", font=("Arial", 10))
        ollama_status.pack(side="right", padx=10)
        
        # TOP ACTION BUTTONS
        top_btn_frame = ttk.Frame(scrollable_frame)
        top_btn_frame.pack(fill="x", pady=(0, 20))
        
        create_btn = ttk.Button(top_btn_frame, text="Create New Deck", command=self.create_deck_dialog, style="Large.TButton")
        create_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        study_btn = ttk.Button(top_btn_frame, text="🎓 Study Center", command=self.open_study_center, style="Large.TButton")
        study_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        settings_btn = ttk.Button(top_btn_frame, text="⚙️ Settings", command=self.show_settings, style="Large.TButton")
        settings_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        # Deck list section
        list_label = ttk.Label(scrollable_frame, text="Your Decks:", font=("Arial", 13, "bold"))
        list_label.pack(pady=(0, 10), anchor="w")
        
        # Treeview for decks
        tree_frame = ttk.Frame(scrollable_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.decks_tree = ttk.Treeview(tree_frame, columns=("Total", "Due"), height=10)
        self.decks_tree.column("#0", width=350)
        self.decks_tree.column("Total", width=120)
        self.decks_tree.column("Due", width=120)
        self.decks_tree.heading("#0", text="Deck Name / Folder")
        self.decks_tree.heading("Total", text="Total Cards")
        self.decks_tree.heading("Due", text="Due Today")
        
        tree_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.decks_tree.yview)
        self.decks_tree.configure(yscrollcommand=tree_scroll.set)
        
        self.decks_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.pack(side="right", fill="y")
        
        # DECK ACTIONS
        deck_action_frame = ttk.Frame(scrollable_frame)
        deck_action_frame.pack(fill="x", pady=20)
        
        open_btn = ttk.Button(deck_action_frame, text="Open Deck", command=self.open_deck, style="Large.TButton")
        open_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        stats_btn = ttk.Button(deck_action_frame, text="View Statistics", command=self.view_deck_stats, style="Large.TButton")
        stats_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        delete_btn = ttk.Button(deck_action_frame, text="Delete Deck", command=self.delete_deck, style="Large.TButton")
        delete_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        # FOLDER ACTIONS
        coll_frame = ttk.LabelFrame(scrollable_frame, text="Folder Management", padding=10)
        coll_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(coll_frame, text="📁 Manage Folders", command=self.manage_collections_dialog).pack(side="left", padx=10)
        ttk.Button(coll_frame, text="📂 Move Selected Deck to Folder", command=self.move_deck_to_collection_dialog).pack(side="left", padx=10)
        
        # IMPORT/EXPORT SECTION
        io_frame = ttk.LabelFrame(scrollable_frame, text="Data Management", padding=10)
        io_frame.pack(fill="x", pady=(0, 20))
        
        btn_grid = ttk.Frame(io_frame)
        btn_grid.pack(fill="x")
        
        ttk.Button(btn_grid, text="📥 Import Deck from CSV", command=self._import_deck_csv).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(btn_grid, text="📤 Export Selected Deck (CSV)", command=self._export_deck_csv).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(btn_grid, text="💾 Full Backup (JSON)", command=self._full_backup_json).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(btn_grid, text="🔄 Full Restore (JSON)", command=self._full_restore_json).pack(side="left", padx=5, fill="x", expand=True)
        
        self.refresh_decks()
        
        self.refresh_decks()
    
    def refresh_decks(self):
        """Refresh the decks list with nesting by collection."""
        for item in self.decks_tree.get_children():
            self.decks_tree.delete(item)
        
        collections = self.db.get_collections('deck')
        decks = self.db.get_all_decks()
        
        # Map collection IDs to Treeview nodes
        coll_nodes = {}
        for coll in collections:
            node = self.decks_tree.insert("", "end", text=f"📁 {coll['name']}", values=("", ""), open=True)
            coll_nodes[coll['id']] = node
            
        # Add a node for Uncategorized decks if there are any
        uncategorized_node = None
        
        for deck in decks:
            parent = ""
            if deck["collection_id"] in coll_nodes:
                parent = coll_nodes[deck["collection_id"]]
            else:
                if uncategorized_node is None:
                    uncategorized_node = self.decks_tree.insert("", "end", text="📦 Uncategorized", values=("", ""), open=True)
                parent = uncategorized_node
                
            self.decks_tree.insert(
                parent, "end", iid=f"deck_{deck['id']}", text=deck["name"],
                values=(deck["total_cards"], deck["due_cards"])
            )
    
    def manage_collections_dialog(self):
        """Show dialog to manage folders (collections)."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Manage Folders")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Folders:", font=("Arial", 10, "bold")).pack(pady=5)
        
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=20)
        
        coll_listbox = tk.Listbox(list_frame)
        coll_listbox.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(list_frame, command=coll_listbox.yview)
        scroll.pack(side="right", fill="y")
        coll_listbox.config(yscrollcommand=scroll.set)
        
        def refresh_colls():
            coll_listbox.delete(0, tk.END)
            for c in self.db.get_collections('deck'):
                coll_listbox.insert("end", f"{c['name']} (ID: {c['id']})")
                
        refresh_colls()
        
        # New folder
        new_frame = ttk.Frame(dialog)
        new_frame.pack(fill="x", pady=10, padx=20)
        
        name_entry = ttk.Entry(new_frame)
        name_entry.pack(side="left", fill="x", expand=True)
        
        def add_coll():
            name = name_entry.get().strip()
            if name:
                self.db.create_collection(name, 'deck')
                name_entry.delete(0, tk.END)
                refresh_colls()
                self.refresh_decks()
                
        ttk.Button(new_frame, text="Add Folder", command=add_coll).pack(side="right")
        
        def delete_coll():
            sel = coll_listbox.curselection()
            if sel:
                item = coll_listbox.get(sel[0])
                coll_id = int(item.split("ID: ")[1].rstrip(")"))
                if messagebox.askyesno("Confirm", f"Delete folder? Decks inside will be uncategorized."):
                    self.db.delete_collection(coll_id)
                    refresh_colls()
                    self.refresh_decks()
                    
        ttk.Button(dialog, text="Delete Selected Folder", command=delete_coll).pack(pady=5)

    def move_deck_to_collection_dialog(self):
        """Move selected deck to a folder."""
        selection = self.decks_tree.selection()
        if not selection or not selection[0].startswith("deck_"):
            messagebox.showwarning("Warning", "Please select a deck to move")
            return
            
        deck_id = int(selection[0].split("_")[1])
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Move to Folder")
        dialog.geometry("300x150")
        
        ttk.Label(dialog, text="Select Folder:").pack(pady=10)
        
        collections = self.db.get_collections('deck')
        options = ["None (Uncategorized)"] + [c['name'] for c in collections]
        coll_map = {c['name']: c['id'] for c in collections}
        
        sel_var = tk.StringVar(value=options[0])
        combo = ttk.Combobox(dialog, textvariable=sel_var, values=options, state="readonly")
        combo.pack(pady=5)
        
        def save_move():
            coll_name = sel_var.get()
            coll_id = coll_map.get(coll_name) # None for "None"
            self.db.assign_to_collection('deck', deck_id, coll_id)
            messagebox.showinfo("Success", "Deck moved!")
            dialog.destroy()
            self.refresh_decks()
            
        ttk.Button(dialog, text="Move", command=save_move).pack(pady=10)

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
        
        iid = selection[0]
        if not iid.startswith("deck_"):
             messagebox.showwarning("Warning", "Please select a deck, not a folder")
             return
             
        self.current_deck_id = int(iid.split("_")[1])
        self.show_deck_menu()
    
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
            matches = self.db.find_flashcard_by_question(question)
            if matches:
                matching_decks = list(set([m['deck_name'] for m in matches]))
                msg = f"This word already exists in deck(s): {', '.join(matching_decks)}.\n\nAdd it anyway?"
                if not messagebox.askyesno("Duplicate Word", msg):
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
        
        self.current_all_flashcards = self.db.get_all_flashcards(self.current_deck_id)
        
        if not self.current_all_flashcards:
            ttk.Label(frame, text="No cards in this deck", font=("Arial", 12)).pack(pady=20)
        else:
            # Controls Frame (Search & Sort)
            controls_frame = ttk.Frame(frame)
            controls_frame.pack(fill="x", pady=(0, 10))
            
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
            self.cards_tree = ttk.Treeview(frame, columns=("Accuracy", "Next Review"), height=15)
            self.cards_tree.column("#0", width=300)
            self.cards_tree.column("Accuracy", width=150)
            self.cards_tree.column("Next Review", width=200)
            self.cards_tree.heading("#0", text="Question")
            self.cards_tree.heading("Accuracy", text="Accuracy")
            self.cards_tree.heading("Next Review", text="Next Review Date")
            self.cards_tree.pack(fill="both", expand=True, pady=10)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.cards_tree.yview)
            scrollbar.pack(side="right", fill="y")
            self.cards_tree.configure(yscroll=scrollbar.set)
            
            # Action Buttons
            action_frame = ttk.Frame(frame)
            action_frame.pack(fill="x", pady=10)
            
            ttk.Button(action_frame, text="Edit Selected", command=self.edit_selected_card).pack(side="left", padx=5)
            ttk.Button(action_frame, text="Delete Selected", command=self.delete_selected_card_from_list).pack(side="left", padx=5)
        
        ttk.Button(frame, text="Back", command=self.show_deck_menu).pack(pady=10)
        
        if self.current_all_flashcards:
            self._filter_and_sort_cards()

    def _filter_and_sort_cards(self):
        """Filter and sort flashcards in the Treeview."""
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
        """Edit the selected card from the list."""
        selection = self.cards_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a card to edit")
            return
        
        index = int(selection[0])
        flashcard = self.filtered_cards[index]
        
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Flashcard")
        dialog.geometry("400x350")
        dialog.transient(self.root)
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
            self.current_all_flashcards = self.db.get_all_flashcards(self.current_deck_id)
            self._filter_and_sort_cards()
            
        ttk.Button(dialog, text="Save Changes", command=save_changes).pack(pady=10)

    def delete_selected_card_from_list(self):
        """Delete the selected card from the list."""
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
            self.current_all_flashcards = self.db.get_all_flashcards(self.current_deck_id)
            self._filter_and_sort_cards()

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
        
        # Pre-load setting
        preload_var = tk.BooleanVar(value=self.study_manager.get_preload_on_startup())
        preload_checkbox = ttk.Checkbutton(ollama_frame, text="Pre-load model on startup", variable=preload_var)
        preload_checkbox.pack(anchor="w", pady=(15, 5))
        ttk.Label(ollama_frame, text="  Ensures near-instant response for first query (uses background RAM/VRAM)", font=("Arial", 9)).pack(anchor="w")
        
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
            self.study_manager.set_preload_on_startup(preload_var.get())
            
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

    def _preload_ollama_background(self):
        """Start a background thread to pre-load the Ollama model."""
        def preload_worker():
            try:
                # Use the configured model from study manager
                model = self.study_manager.get_ollama_model()
                if model:
                    self.ollama_client.preload_model(model)
            except Exception as e:
                print(f"Background pre-load error: {e}")
        
        thread = threading.Thread(target=preload_worker, daemon=True)
        thread.start()

    def _export_deck_csv(self):
        """Export the selected deck to CSV."""
        selection = self.decks_tree.selection()
        if not selection or not selection[0].startswith("deck_"):
            messagebox.showwarning("Warning", "Please select a deck to export.")
            return
            
        deck_id = int(selection[0].split("_")[1])
        deck_name = self.decks_tree.item(selection[0])['text']
        
        # Sanitize filename
        safe_name = re.sub(r'[\\/*?:"<>|]', "", deck_name)
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
            initialfile=f"{safe_name}_export.csv",
            title="Export Deck to CSV (Anki Compatible)"
        )
        
        if file_path:
            try:
                if self.io_manager.export_deck_to_csv(deck_id, file_path):
                    messagebox.showinfo("Success", f"Deck '{deck_name}' exported successfully!")
                else:
                    messagebox.showerror("Error", "Failed to export deck. It might be empty or a file error occurred.")
            except Exception as e:
                import traceback
                traceback.print_exc()
                messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def _import_deck_csv(self):
        """Import a deck from CSV."""
        file_path = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv")],
            title="Import Deck from CSV"
        )
        
        if file_path:
            # Ask for a deck name
            deck_name = simpledialog.askstring("Import Deck", "Enter name for the new deck:")
            if not deck_name:
                return
                
            deck_id = self.db.create_deck(deck_name)
            if not deck_id:
                messagebox.showerror("Error", "Could not create deck (name may already exist).")
                return
                
            count = self.io_manager.import_deck_from_csv(deck_id, file_path)
            if count >= 0:
                self.refresh_decks()
                messagebox.showinfo("Success", f"Imported {count} cards into '{deck_name}'!")
            else:
                messagebox.showerror("Error", "Failed to import cards from CSV.")

    def _full_backup_json(self):
        """Create a full JSON backup of the database."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"learning_suite_backup_{datetime.now().strftime('%Y%m%d')}.json",
            title="Save Full Backup"
        )
        
        if file_path:
            if self.io_manager.full_backup_to_json(file_path):
                messagebox.showinfo("Success", "Full backup created successfully!")
            else:
                messagebox.showerror("Error", "Failed to create backup.")

    def _full_restore_json(self):
        """Restore the entire database from a JSON backup."""
        if not messagebox.askyesno("Confirm Restore", 
                                   "WARNING: This will delete ALL existing data and replace it with the backup content.\n\nAre you sure you want to proceed?"):
            return
            
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")],
            title="Select Backup File to Restore"
        )
        
        if file_path:
            if self.io_manager.full_restore_from_json(file_path):
                self.refresh_decks()
                messagebox.showinfo("Success", "Database restored successfully!")
            else:
                messagebox.showerror("Error", "Failed to restore database. The file might be invalid.")


def main():
    root = tk.Tk()
    app = FlashcardApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
