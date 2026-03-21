"""Collections View for managing sentence collections."""
import tkinter as tk
from tkinter import ttk, messagebox
from src.features.study_center.logic.study_manager import StudyManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header
from src.core.localization import tr


class CollectionsView(ttk.Frame):
    """View for managing sentence collections with tabs for different types."""
    
    def __init__(self, parent, controller, study_manager: StudyManager, db: FlashcardDatabase, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        self.embedded = embedded
        self.collections_data = []
        self.setup_ui()
        self.refresh_all_collections()
    
    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(
                self,
                tr("sentence_collections", "Sentence Collections"),
                back_cmd=self.go_back
            )
        else:
            header = ttk.Frame(self)
            header.pack(fill="x", padx=10, pady=5)
            ttk.Label(header, text=tr("sentence_collections", "Sentence Collections"), 
                     font=("Arial", 14, "bold")).pack(side="left")
        
        # Toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(fill="x", padx=10, pady=5)
        ttk.Button(toolbar, text=tr("btn_new_collection", "+ New Collection"), 
                  command=self._show_create_dialog).pack(side="left", padx=2)
        ttk.Button(toolbar, text=tr("btn_refresh", "🔄 Refresh"), 
                  command=self.refresh_all_collections).pack(side="left", padx=2)
        
        # Collections notebook with tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Tab 1: My Collections
        self.my_collections_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.my_collections_tab, text=tr("tab_my_collections", "📁 My Collections"))
        self._create_collection_list(self.my_collections_tab, "manual")
        
        # Tab 2: Grammar Patterns
        self.grammar_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.grammar_tab, text=tr("tab_grammar_patterns", "📝 Grammar Patterns"))
        self._create_collection_list(self.grammar_tab, "grammar_pattern")
        
        # Tab 3: Topics
        self.topics_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.topics_tab, text=tr("tab_topics", "🏷️ Topics"))
        self._create_collection_list(self.topics_tab, "topic")
        
        # Tab 4: Difficulty Ladders
        self.ladders_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.ladders_tab, text=tr("tab_ladders", "📊 Difficulty Ladders"))
        self._create_ladder_list(self.ladders_tab)
    
    def _create_collection_list(self, parent, collection_type):
        """Create a scrollable list of collections."""
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.collections_tree = ttk.Treeview(list_frame, yscrollcommand=scrollbar.set, 
                                              columns=("name", "sentences", "avg_difficulty"), 
                                              show="headings")
        self.collections_tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.collections_tree.yview)
        
        self.collections_tree.heading("name", text=tr("col_name", "Name"))
        self.collections_tree.heading("sentences", text=tr("col_sentences", "Sentences"))
        self.collections_tree.heading("avg_difficulty", text=tr("col_avg_difficulty", "Avg Difficulty"))
        
        self.collections_tree.column("name", width=200)
        self.collections_tree.column("sentences", width=80)
        self.collections_tree.column("avg_difficulty", width=100)
        
        self.collections_tree.bind("<Double-1>", self._on_collection_double_click)
        
        # Buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text=tr("btn_view_sentences", "View Sentences"), 
                  command=self._view_collection_sentences).pack(side="left", padx=2)
        ttk.Button(btn_frame, text=tr("btn_delete", "Delete"), 
                  command=self._delete_collection).pack(side="left", padx=2)
        
        self.current_list_type = collection_type
    
    def _create_ladder_list(self, parent):
        """Create a list specifically for difficulty ladders with visualization."""
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.ladders_tree = ttk.Treeview(list_frame, yscrollcommand=scrollbar.set,
                                         columns=("name", "steps", "difficulty_range"), 
                                         show="headings")
        self.ladders_tree.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.ladders_tree.yview)
        
        self.ladders_tree.heading("name", text=tr("col_name", "Name"))
        self.ladders_tree.heading("steps", text=tr("col_steps", "Steps"))
        self.ladders_tree.heading("difficulty_range", text=tr("col_difficulty_range", "Difficulty Range"))
        
        self.ladders_tree.column("name", width=200)
        self.ladders_tree.column("steps", width=80)
        self.ladders_tree.column("difficulty_range", width=150)
        
        self.ladders_tree.bind("<Double-1>", self._on_ladder_double_click)
        
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill="x", pady=5)
        ttk.Button(btn_frame, text=tr("btn_view_ladder", "View Ladder"), 
                  command=self._view_ladder).pack(side="left", padx=2)
    
    def refresh_all_collections(self):
        """Load all collections by type."""
        self.collections_data = self.db.get_sentence_collections()
        self._render_collections()
        self._render_ladders()
    
    def _render_collections(self):
        """Render collections in the tree view."""
        for item in self.collections_tree.get_children():
            self.collections_tree.delete(item)
        
        for coll in self.collections_data:
            if coll['collection_type'] != self.current_list_type:
                continue
            
            sentence_count = self.db.get_collection_sentence_count(coll['id'])
            avg_diff = self._get_collection_avg_difficulty(coll['id'])
            diff_str = f"{avg_diff:.2f}" if avg_diff is not None else "-"
            
            self.collections_tree.insert("", "end", iid=f"coll_{coll['id']}", 
                                         values=(coll['name'], sentence_count, diff_str))
    
    def _render_ladders(self):
        """Render difficulty ladders."""
        for item in self.ladders_tree.get_children():
            self.ladders_tree.delete(item)
        
        for coll in self.collections_data:
            if coll['collection_type'] != 'difficulty_ladder':
                continue
            
            sentence_count = self.db.get_collection_sentence_count(coll['id'])
            metadata = coll.get('metadata', {})
            diff_range = metadata.get('difficulty_range', '-')
            
            self.ladders_tree.insert("", "end", iid=f"ladder_{coll['id']}",
                                     values=(coll['name'], sentence_count, diff_range))
    
    def _get_collection_avg_difficulty(self, collection_id):
        """Get average difficulty for a collection."""
        try:
            cursor = self.db.db.cursor()
            cursor.execute("""
                SELECT AVG(ic.difficulty_score) 
                FROM sentence_collection_items sci
                JOIN imported_content ic ON sci.imported_content_id = ic.id
                WHERE sci.collection_id = ?
            """, (collection_id,))
            result = cursor.fetchone()
            return result[0] if result and result[0] is not None else None
        except Exception:
            return None
    
    def _show_create_dialog(self):
        """Show dialog to create a new collection."""
        dialog = tk.Toplevel(self)
        dialog.title(tr("dlg_new_collection", "New Collection"))
        dialog.geometry("400x250")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text=tr("lbl_name", "Name:"), padding=5).grid(row=0, column=0, sticky="w")
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=40)
        name_entry.grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text=tr("lbl_description", "Description:"), padding=5).grid(row=1, column=0, sticky="nw")
        desc_text = tk.Text(dialog, height=4, width=30)
        desc_text.grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(dialog, text=tr("lbl_type", "Type:"), padding=5).grid(row=2, column=0, sticky="w")
        type_var = tk.StringVar(value="manual")
        type_combo = ttk.Combobox(dialog, textvariable=type_var, 
                                  values=["manual", "grammar_pattern", "topic", "difficulty_ladder"],
                                  state="readonly", width=20)
        type_combo.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning(tr("msg_warning", "Warning"), tr("msg_name_required", "Name is required"))
                return
            if len(name) > 100:
                messagebox.showwarning(tr("msg_warning", "Warning"), tr("msg_name_too_long", "Name must be 100 characters or less"))
                return
            
            desc = desc_text.get(1.0, tk.END).strip()
            coll_type = type_var.get()
            
            try:
                self.db.create_sentence_collection(name, desc, coll_type, "en", {})
                messagebox.showinfo(tr("msg_success", "Success"), tr("msg_collection_created", "Collection created!"))
                dialog.destroy()
                self.refresh_all_collections()
            except Exception as e:
                messagebox.showerror(tr("msg_error", "Error"), str(e))
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text=tr("btn_save", "Save"), command=save).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("btn_cancel", "Cancel"), command=dialog.destroy).pack(side="left", padx=5)
    
    def _on_collection_double_click(self, event):
        self._view_collection_sentences()
    
    def _on_ladder_double_click(self, event):
        self._view_ladder()
    
    def _view_collection_sentences(self):
        """View sentences in the selected collection."""
        selection = self.collections_tree.selection()
        if not selection:
            messagebox.showwarning(tr("msg_warning", "Warning"), tr("msg_select_collection", "Please select a collection"))
            return
        
        coll_id = int(selection[0].split("_")[1])
        # TODO: Show collection detail view
        messagebox.showinfo(tr("msg_info", "Info"), f"View sentences for collection {coll_id}")
    
    def _view_ladder(self):
        """View the selected difficulty ladder."""
        selection = self.ladders_tree.selection()
        if not selection:
            messagebox.showwarning(tr("msg_warning", "Warning"), tr("msg_select_ladder", "Please select a ladder"))
            return
        
        ladder_id = int(selection[0].split("_")[1])
        # TODO: Show DifficultyLadderView
        messagebox.showinfo(tr("msg_info", "Info"), f"View difficulty ladder {ladder_id}")
    
    def _delete_collection(self):
        """Delete the selected collection."""
        selection = self.collections_tree.selection()
        if not selection:
            messagebox.showwarning(tr("msg_warning", "Warning"), tr("msg_select_collection", "Please select a collection"))
            return
        
        if not messagebox.askyesno(tr("lbl_confirm_delete", "Confirm Delete"), 
                                   tr("msg_delete_collection_prompt", "Are you sure you want to delete this collection?")):
            return
        
        coll_id = int(selection[0].split("_")[1])
        try:
            self.db.delete_sentence_collection(coll_id)
            messagebox.showinfo(tr("msg_success", "Success"), tr("msg_deleted", "Collection deleted."))
            self.refresh_all_collections()
        except Exception as e:
            messagebox.showerror(tr("msg_error", "Error"), str(e))
    
    def go_back(self):
        if hasattr(self.controller, 'show_study_dashboard'):
            self.controller.show_study_dashboard()
    
    def on_show(self):
        """Refresh when view becomes visible."""
        self.refresh_all_collections()