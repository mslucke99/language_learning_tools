import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
from src.features.study_center.logic.study_manager import StudyManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header, bind_mousewheel
from src.features.study_center.ui.dialogs import ManageCollectionsDialog, MoveItemDialog
from src.core.localization import tr

class GrammarBookViewFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, db: FlashcardDatabase, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        self.embedded = embedded
        self.ai_available = study_manager.ai_available
        
        self.current_grammar_id = None
        self.grammar_entries = []
        self.active_tasks = {}
        
        self.setup_ui()
        self._check_queue_status()

    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(
                self,
                tr("header_grammar_book", "Grammar Book"),
                back_cmd=self.go_back,
                action_text=tr("btn_new_entry", "+ New Entry"),
                action_cmd=self._new_grammar_entry
            )
        else:
            toolbar = ttk.Frame(self)
            toolbar.pack(fill="x", padx=10, pady=5)
            ttk.Button(toolbar, text=tr("btn_new_entry", "+ New Grammar Entry"), command=self._new_grammar_entry).pack(side="right")
        
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        
        paned_window = ttk.PanedWindow(container, orient="horizontal")
        paned_window.pack(fill="both", expand=True)
        
        # LEFT PANE: Tree
        left_pane = ttk.Frame(paned_window)
        paned_window.add(left_pane, weight=1)
        ttk.Label(left_pane, text=tr("lbl_folders_entries", "Folders & Entries"), font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        ctrl_frame = ttk.Frame(left_pane)
        ctrl_frame.pack(fill="x", pady=(0, 5))
        self.grammar_search_var = tk.StringVar()
        self.grammar_search_var.trace("w", lambda *args: self._update_grammar_view())
        ttk.Entry(ctrl_frame, textvariable=self.grammar_search_var, width=15).pack(fill="x", pady=(0, 2))
        
        sort_frame = ttk.Frame(ctrl_frame)
        sort_frame.pack(fill="x")
        ttk.Label(sort_frame, text=tr("lbl_sort", "Sort:")).pack(side="left")
        self.grammar_sort_var = tk.StringVar(value=tr("opt_sort_updated", "Updated"))
        sort_dropdown = ttk.Combobox(sort_frame, textvariable=self.grammar_sort_var, 
                                     values=[tr("opt_sort_updated", "Updated"), tr("opt_sort_az", "A-Z")], 
                                     state="readonly", width=10)
        sort_dropdown.pack(side="left", padx=5)
        sort_dropdown.bind("<<ComboboxSelected>>", lambda e: self._update_grammar_view())
        
        tree_frame = ttk.Frame(left_pane)
        tree_frame.pack(fill="both", expand=True)
        list_scroll = ttk.Scrollbar(tree_frame)
        self.grammar_tree = ttk.Treeview(tree_frame, show="tree", yscrollcommand=list_scroll.set)
        self.grammar_tree.pack(side="left", fill="both", expand=True)
        list_scroll.pack(side="right", fill="y")
        list_scroll.config(command=self.grammar_tree.yview)
        self.grammar_tree.bind('<<TreeviewSelect>>', self._on_grammar_entry_selected)
        
        tree_btns = ttk.Frame(left_pane)
        tree_btns.pack(fill="x", pady=5)
        ttk.Button(tree_btns, text=tr("btn_new_folder", "📁 New Folder"), command=lambda: ManageCollectionsDialog(self, self.db, 'grammar', self._update_grammar_view)).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(tree_btns, text=tr("btn_move_item", "📂 Move Item"), command=lambda: self._move_item_dialog()).pack(side="left", padx=2, fill="x", expand=True)
        
        # RIGHT PANE: Editor
        right_panel = ttk.LabelFrame(paned_window, text=tr("lbl_entry_editor", "Entry Editor"), padding="15")
        paned_window.add(right_panel, weight=3)
        
        # Status
        status_frame = ttk.Frame(right_panel)
        status_frame.pack(fill="x", pady=(0, 10))
        self.current_status_label = ttk.Label(status_frame, text="", font=("Arial", 9, "italic"), foreground="blue")
        self.current_status_label.pack(side="right")
        
        # Title
        title_frame = ttk.Frame(right_panel)
        title_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(title_frame, text=tr("lbl_title_field", "Title:"), font=("Arial", 10, "bold")).pack(anchor="w")
        self.grammar_title_var = tk.StringVar()
        ttk.Entry(title_frame, textvariable=self.grammar_title_var, font=("Arial", 11)).pack(fill="x", pady=(2, 0))
        
        # Tags
        tags_frame = ttk.Frame(right_panel)
        tags_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(tags_frame, text=tr("lbl_tags_field", "Tags (comma separated):")).pack(anchor="w")
        self.grammar_tags_var = tk.StringVar()
        ttk.Entry(tags_frame, textvariable=self.grammar_tags_var).pack(fill="x", pady=(2, 0))
        
        # Proficiency
        prof_frame = ttk.Frame(right_panel)
        prof_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(prof_frame, text="Mastery Status:").pack(side="left")
        self.grammar_prof_var = tk.StringVar(value="0 - New")
        prof_cb = ttk.Combobox(prof_frame, textvariable=self.grammar_prof_var, 
                     values=["0 - New", "1 - Learning", "2 - Mastered"], state="readonly", width=15)
        prof_cb.pack(side="left", padx=5)
        
        if self.ai_available:
            ttk.Button(right_panel, text="✨ Generate Explanation from Title", command=self._generate_grammar_explanation).pack(anchor="w", pady=(0, 10))
            
        ttk.Label(right_panel, text="Content:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.grammar_content_text = scrolledtext.ScrolledText(right_panel, font=("Arial", 10))
        self.grammar_content_text.pack(fill="both", expand=True, pady=5)
        bind_mousewheel(self.grammar_content_text)
        
        action_frame = ttk.Frame(right_panel)
        action_frame.pack(fill="x", pady=10)
        ttk.Button(action_frame, text="Save Entry", command=self._save_grammar_entry, style="Large.TButton").pack(side="left", padx=5)
        ttk.Button(action_frame, text="Delete", command=self._delete_grammar_entry).pack(side="left", padx=5)
        
        self._update_grammar_view()

    def go_back(self):
        if hasattr(self.controller, 'show_study_dashboard'):
            self.controller.show_study_dashboard()

    def _update_grammar_view(self):
        # Preservation
        scroll_pos = self.grammar_tree.yview()
        selected_iid = self.grammar_tree.selection()

        search = self.grammar_search_var.get()
        sort_by = self.grammar_sort_var.get()
        
        for item in self.grammar_tree.get_children():
            self.grammar_tree.delete(item)
            
        entries = self.study_manager.get_grammar_entries(search)
        colls = self.db.get_collections('grammar')
        
        if sort_by == "A-Z":
            entries = sorted(entries, key=lambda x: x['title'].lower())
        else:
            entries = sorted(entries, key=lambda x: x['updated_at'], reverse=True)
        
        self.grammar_entries = entries
        
        folder_nodes = {}
        remaining = list(colls)
        max_iters = 5
        while remaining and max_iters > 0:
            max_iters -= 1
            for i in range(len(remaining)-1, -1, -1):
                c = remaining[i]
                parent = ""
                if c['parent_id'] and f"coll_{c['parent_id']}" in folder_nodes: parent = f"coll_{c['parent_id']}"
                elif c['parent_id'] is None: parent = ""
                else: continue
                node = self.grammar_tree.insert(parent, "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)
                folder_nodes[f"coll_{c['id']}"] = node
                remaining.pop(i)
        
        for c in remaining: self.grammar_tree.insert("", "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)
        
        uncategorized_node = None
        for e in entries:
            parent = ""
            if e['collection_id'] and f"coll_{e['collection_id']}" in folder_nodes: parent = f"coll_{e['collection_id']}"
            else:
                if not uncategorized_node: uncategorized_node = self.grammar_tree.insert("", "end", text="📦 Uncategorized", open=True)
                parent = uncategorized_node
            self.grammar_tree.insert(parent, "end", iid=f"gram_{e['id']}", text=f"{self._get_prof_icon(e.get('proficiency',0))} {e['title']}")

        # Restore
        try:
            self.grammar_tree.yview_moveto(scroll_pos[0])
            if selected_iid:
                if self.grammar_tree.exists(selected_iid[0]):
                    self.grammar_tree.selection_set(selected_iid[0])
                    self.grammar_tree.see(selected_iid[0])
        except: pass

    def _on_grammar_entry_selected(self, event):
        selection = self.grammar_tree.selection()
        if not selection: return
        iid = selection[0]
        if not iid.startswith("gram_"): return
        
        gram_id = int(iid.split("_")[1])
        entry = next((e for e in self.grammar_entries if e['id'] == gram_id), None)
        if not entry: return
        
        self.current_grammar_id = entry['id']
        self.grammar_title_var.set(entry['title'])
        self.grammar_tags_var.set(entry['tags'] or "")
        prof = entry.get('proficiency', 0)
        prof_map = {0: "0 - New", 1: "1 - Learning", 2: "2 - Mastered"}
        self.grammar_prof_var.set(prof_map.get(prof, "0 - New"))
        self.grammar_content_text.delete(1.0, tk.END)
        self.grammar_content_text.insert(tk.END, entry['content'])
        self.current_status_label.config(text=f"Last updated: {entry['updated_at']}")

    def _get_prof_icon(self, proficiency):
        if proficiency == 2: return "✅"
        if proficiency == 1: return "🔨"
        return "📒"

    def _new_grammar_entry(self):
        self.current_grammar_id = None
        self.grammar_title_var.set("")
        self.grammar_tags_var.set("")
        self.grammar_prof_var.set("0 - New")
        self.grammar_content_text.delete(1.0, tk.END)
        self.grammar_tree.selection_remove(self.grammar_tree.selection())
        self.current_status_label.config(text="")

    def _save_grammar_entry(self):
        title = self.grammar_title_var.get().strip()
        content = self.grammar_content_text.get(1.0, tk.END).strip()
        tags = self.grammar_tags_var.get().strip()
        prof_str = self.grammar_prof_var.get()
        proficiency = int(prof_str.split(" - ")[0])
        
        if not title:
            messagebox.showwarning("Warning", "Title is required")
            return
            
        if self.current_grammar_id:
            self.study_manager.update_grammar_entry(self.current_grammar_id, title, content, tags, proficiency)
        else:
            self.current_grammar_id = self.study_manager.add_grammar_entry(title, content, tags, proficiency)
        
        self._update_grammar_view()
        messagebox.showinfo("Success", "Entry saved!")

    def _delete_grammar_entry(self):
        if not self.current_grammar_id: return
        if messagebox.askyesno(tr("lbl_confirm_delete", "Confirm Delete"), tr("msg_confirm_delete_prompt", "Are you sure you want to delete this item?")):
            self.study_manager.delete_grammar_entry(self.current_grammar_id)
            self._update_grammar_view()
            self._new_grammar_entry()

    def on_show(self):
        """Lifecycle hook: Refresh view."""
        self._update_grammar_view()

    def on_hide(self):
        """Lifecycle hook."""
        pass

    def _generate_grammar_explanation(self):
        topic = self.grammar_title_var.get().strip()
        if not topic:
             messagebox.showwarning("Warning", "Title required")
             return
        
        # Save first if new
        if not self.current_grammar_id:
             self._save_grammar_entry()
             if not self.current_grammar_id: return
             
        self.grammar_content_text.delete(1.0, tk.END)
        self.grammar_content_text.insert(tk.END, "⏳ Task Queued: Generating grammar explanation...")
        
        task_id = self.study_manager.queue_generation_task('grammar_explanation', self.current_grammar_id)
        self.active_tasks[task_id] = {'type': 'grammar_explanation', 'item_id': self.current_grammar_id}

    def _check_queue_status(self):
        completed = []
        for task_id in list(self.active_tasks.keys()):
             status = self.study_manager.get_task_status(task_id)
             if status['status'] in ['completed', 'failed']:
                  completed.append(task_id)
                  if status['status'] == 'completed' and self.active_tasks[task_id]['item_id'] == self.current_grammar_id:
                       self._on_grammar_entry_selected(None)
                       messagebox.showinfo("Complete", "Explanation ready!")
                  elif status['status'] == 'failed':
                       messagebox.showerror("Error", status.get("error"))
        for t in completed: self.active_tasks.pop(t, None)
        self.after(1000, self._check_queue_status)
        
    def _move_item_dialog(self):
        if not self.current_grammar_id:
            messagebox.showwarning("Warning", "Select entry first")
            return
        MoveItemDialog(self, self.db, 'grammar', self.current_grammar_id, self._update_grammar_view)
