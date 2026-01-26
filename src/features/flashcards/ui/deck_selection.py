import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from src.core.database import FlashcardDatabase
from src.features.flashcards.logic.spaced_repetition import get_due_flashcards, get_next_review_date
from src.core.ui_utils import setup_standard_header

class DeckSelectionFrame(ttk.Frame):
    def __init__(self, parent, controller, db: FlashcardDatabase):
        super().__init__(parent)
        self.controller = controller
        self.db = db
        self.style = ttk.Style()
        self.style.configure("Large.TButton", font=("Arial", 12), padding=15)
        
        self.setup_ui()
        
    def setup_ui(self):
        # Header with Back button
        setup_standard_header(self, "Flashcard Decks", back_cmd=self.go_back)

        # Create canvas and scrollbar for the frame
        canvas = tk.Canvas(self, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.content_frame = ttk.Frame(canvas, padding="20")
        
        self.content_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.content_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Ensure the scrollable frame expands to the canvas width
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Action Buttons (New Deck)
        top_btn_frame = ttk.Frame(self.content_frame)
        top_btn_frame.pack(fill="x", pady=(0, 20))
        
        create_btn = ttk.Button(top_btn_frame, text="Create New Deck", command=self.create_deck_dialog, style="Large.TButton")
        create_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        # Deck List
        list_label = ttk.Label(self.content_frame, text="Your Decks:", font=("Arial", 13, "bold"))
        list_label.pack(pady=(0, 10), anchor="w")
        
        tree_frame = ttk.Frame(self.content_frame)
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
        
        # Deck Actions
        deck_action_frame = ttk.Frame(self.content_frame)
        deck_action_frame.pack(fill="x", pady=20)
        
        open_btn = ttk.Button(deck_action_frame, text="Open Deck", command=self.open_deck, style="Large.TButton")
        open_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        stats_btn = ttk.Button(deck_action_frame, text="View Statistics", command=self.view_deck_stats, style="Large.TButton")
        stats_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        delete_btn = ttk.Button(deck_action_frame, text="Delete Deck", command=self.delete_deck, style="Large.TButton")
        delete_btn.grid(row=0, column=3, padx=5, sticky="ew")
        
        deck_action_frame.columnconfigure((0,1,3), weight=1)

        # Folder Management
        coll_frame = ttk.LabelFrame(self.content_frame, text="Folder Management", padding=10)
        coll_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Button(coll_frame, text="📁 Manage Folders", command=self.manage_collections_dialog).pack(side="left", padx=10)
        ttk.Button(coll_frame, text="📂 Move Selected Deck to Folder", command=self.move_deck_to_collection_dialog).pack(side="left", padx=10)

        # Import/Export (Deck specific)
        io_frame = ttk.LabelFrame(self.content_frame, text="Import / Export", padding=10)
        io_frame.pack(fill="x", pady=(0, 20))
        
        btn_grid = ttk.Frame(io_frame)
        btn_grid.pack(fill="x")
        
        ttk.Button(btn_grid, text="📥 Import Deck from CSV", command=self._import_deck_csv).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(btn_grid, text="📤 Export Selected Deck (CSV)", command=self._export_deck_csv).pack(side="left", padx=5, fill="x", expand=True)
        
        self.refresh_decks()

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()

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
             
        deck_id = int(iid.split("_")[1])
        if hasattr(self.controller, 'show_deck_menu'):
            self.controller.show_deck_menu(deck_id)

    def create_deck_dialog(self):
        """Show dialog to create a new deck."""
        dialog = tk.Toplevel(self)
        dialog.title("Create New Deck")
        dialog.geometry("300x200")
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

    def delete_deck(self):
        """Delete selected deck."""
        selection = self.decks_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a deck to delete")
            return
        
        iid = selection[0]
        if not iid.startswith("deck_"): return

        deck_id = int(iid.split("_")[1])
        deck_name = self.decks_tree.item(iid)["text"]
        
        if messagebox.askyesno("Confirm Delete", f"Are you sure you want to delete deck '{deck_name}'?"):
            self.db.delete_deck(deck_id)
            self.refresh_decks()

    def view_deck_stats(self):
        """Show detailed statistics for selected deck."""
        selection = self.decks_tree.selection()
        if not selection or not selection[0].startswith("deck_"): return
             
        deck_name = self.decks_tree.item(selection[0])["text"]
        deck_id = int(selection[0].split("_")[1])
        
        decks = self.db.get_all_decks()
        stats = self.db.get_deck_statistics(deck_id)
        
        cards = self.db.get_all_flashcards(deck_id)
        reviewed_count = sum(1 for c in cards if c.total_reviews > 0)
        
        avg_easiness = sum(c.easiness for c in cards) / len(cards) if cards else 0.0
        avg_interval = sum(c.interval for c in cards) / len(cards) if cards else 0.0
        
        dialog = tk.Toplevel(self)
        dialog.title(f"Statistics - {deck_name}")
        dialog.geometry("400x350")
        
        stats_text = f'''
Deck: {deck_name}

Total Cards: {stats['total_cards']}
New Cards: {stats['total_cards'] - reviewed_count}
Reviewed: {reviewed_count}
Due Today: {stats['due_cards']}

Total Reviews: {stats['total_reviews']}
Correct Reviews: {stats['correct_reviews']}
Overall Accuracy: {stats['overall_accuracy']:.1f}%

Average Easiness: {avg_easiness:.2f}
Average Interval: {avg_interval:.1f} days
        '''
        
        ttk.Label(dialog, text=stats_text, font=("Courier", 10), justify="left").pack(padx=10, pady=10)

    def manage_collections_dialog(self):
        """Show dialog to manage folders (collections)."""
        dialog = tk.Toplevel(self)
        dialog.title("Manage Folders")
        dialog.geometry("400x350")
        
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        coll_listbox = tk.Listbox(list_frame)
        coll_listbox.pack(side="left", fill="both", expand=True)
        
        def refresh_colls():
            coll_listbox.delete(0, tk.END)
            for c in self.db.get_collections('deck'):
                coll_listbox.insert("end", f"{c['name']} (ID: {c['id']})")
                
        refresh_colls()
        
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

    def move_deck_to_collection_dialog(self):
        """Move selected deck to a folder."""
        selection = self.decks_tree.selection()
        if not selection or not selection[0].startswith("deck_"): return
        deck_id = int(selection[0].split("_")[1])
        
        dialog = tk.Toplevel(self)
        dialog.title("Move to Folder")
        dialog.geometry("300x150")
        
        collections = self.db.get_collections('deck')
        options = ["None (Uncategorized)"] + [c['name'] for c in collections]
        coll_map = {c['name']: c['id'] for c in collections}
        
        sel_var = tk.StringVar(value=options[0])
        combo = ttk.Combobox(dialog, textvariable=sel_var, values=options, state="readonly")
        combo.pack(pady=10)
        
        def save_move():
            coll_id = coll_map.get(sel_var.get())
            self.db.assign_to_collection('deck', deck_id, coll_id)
            dialog.destroy()
            self.refresh_decks()
            
        ttk.Button(dialog, text="Move", command=save_move).pack(pady=10)

    def _import_deck_csv(self):
        selection = self.decks_tree.selection()
        if not selection or not selection[0].startswith("deck_"): return
        deck_id = int(selection[0].split("_")[1])
        file_path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if file_path and hasattr(self.controller, 'io_manager'):
             count = self.controller.io_manager.import_deck_from_csv(deck_id, file_path)
             if count >= 0:
                 messagebox.showinfo("Success", f"Imported {count} cards!")
                 self.refresh_decks()

    def _export_deck_csv(self):
        selection = self.decks_tree.selection()
        if not selection or not selection[0].startswith("deck_"): return
        deck_id = int(selection[0].split("_")[1])
        file_path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV Files", "*.csv")])
        if file_path and hasattr(self.controller, 'io_manager'):
             if self.controller.io_manager.export_deck_to_csv(deck_id, file_path):
                 messagebox.showinfo("Success", "Export successful!")
