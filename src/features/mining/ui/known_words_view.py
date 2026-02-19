import tkinter as tk
from tkinter import ttk, messagebox
from src.core.localization import tr
from src.core.database import FlashcardDatabase

class KnownWordsView(ttk.Frame):
    def __init__(self, parent, db: FlashcardDatabase, lang_code="ko", on_change=None):
        super().__init__(parent)
        self.db = db
        self.lang_code = lang_code
        self.on_change = on_change
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        # Header / Stats
        self.stats_label = ttk.Label(self, text="Loading stats...", font=("Arial", 10))
        self.stats_label.pack(fill="x", padx=10, pady=5)
        
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(toolbar, text=tr("lbl_add_word", "Add Word:")).pack(side="left")
        self.entry_word = ttk.Entry(toolbar)
        self.entry_word.pack(side="left", padx=5)
        self.entry_word.bind("<Return>", self._add_manual_word)
        
        ttk.Button(toolbar, text="+", width=3, command=self._add_manual_word).pack(side="left")
        
        # Delete Button (Far Right)
        ttk.Button(toolbar, text="Delete", command=self._delete_selected).pack(side="right", padx=5)

        ttk.Label(toolbar, text=tr("lbl_search", "Search:")).pack(side="left", padx=(20, 5))
        self.entry_search = ttk.Entry(toolbar)
        self.entry_search.pack(side="left", fill="x", expand=True)
        self.entry_search.bind("<KeyRelease>", self._filter_list)

        # List
        # ... rest of setup_ui is fine ...
        cols = ("Word", "Source", "Date Added")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("Word", text="Word")
        self.tree.heading("Source", text="Source")
        self.tree.heading("Date Added", text="Date")
        
        self.tree.column("Word", width=150)
        self.tree.column("Source", width=100)
        self.tree.column("Date Added", width=150)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.pack(fill="both", expand=True, padx=10)
        
        # Context Menu
        self.tree.bind("<Button-3>", self._on_right_click)

    def refresh_list(self):
        # Update stats
        count = self.db.get_known_word_count(self.lang_code)
        self.stats_label.config(text=f"Total Known Words: {count}")
        
        # Update list
        self.all_words = self.db.get_all_known_words(self.lang_code)
        self._filter_list()

    def _filter_list(self, event=None):
        query = self.entry_search.get().lower()
        self.tree.delete(*self.tree.get_children())
        
        for w in self.all_words:
            if query in w['lemma'].lower():
                # Display only date part of added_at
                date_str = w['added_at'].split("T")[0] if "T" in w['added_at'] else w['added_at']
                self.tree.insert("", "end", values=(w['lemma'], w['source'], date_str), tags=(w['id'],))

    def _add_manual_word(self, event=None):
        word = self.entry_word.get().strip()
        if not word: return
        
        if self.db.add_known_word(word, self.lang_code, source="manual"):
            self.entry_word.delete(0, "end")
            self.refresh_list()
            if self.on_change: self.on_change()
        else:
            messagebox.showinfo("Info", "Word already mapped as known.", parent=self)

    def _on_right_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item: return
        self.tree.selection_set(item)
        
        menu = tk.Menu(self, tearoff=0)
        menu.add_command(label="Delete", command=self._delete_selected)
        menu.post(event.x_root, event.y_root)

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel: return
        
        item = sel[0]
        word_id = self.tree.item(item, "tags")[0]
        lemma = self.tree.item(item, "values")[0]
        
        if messagebox.askyesno("Confirm", f"Remove '{lemma}' from known words?", parent=self):
            self.db.delete_known_word(word_id)
            self.refresh_list()
            if self.on_change: self.on_change()
