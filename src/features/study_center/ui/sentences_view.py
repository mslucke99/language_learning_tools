import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from src.features.study_center.logic.study_manager import StudyManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header, bind_mousewheel
from src.features.study_center.ui.dialogs import ManageCollectionsDialog, MoveItemDialog

class SentencesViewFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, db: FlashcardDatabase, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        self.embedded = embedded
        self.ollama_available = study_manager.ollama_client is not None
        
        self.current_sentence_id = None
        self.current_sentence_explanation_id = None # Track for follow-ups
        self.sentences_data = []
        self.active_tasks = {}
        self.focus_vars = {}
        
        self.setup_ui()
        self._check_queue_status()

    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(
                self, 
                "Study Sentences", 
                back_cmd=self.go_back,
                action_text="+ Add Sentence",
                action_cmd=self._add_manual_sentence_dialog
            )
        else:
            toolbar = ttk.Frame(self)
            toolbar.pack(fill="x", padx=10, pady=5)
            ttk.Button(toolbar, text="+ Add New Sentence", command=self._add_manual_sentence_dialog).pack(side="right")
        
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        
        paned_window = ttk.PanedWindow(container, orient="horizontal")
        paned_window.pack(fill="both", expand=True)
        
        # LEFT PANE: Sentence Tree
        left_pane = ttk.Frame(paned_window)
        paned_window.add(left_pane, weight=1)
        ttk.Label(left_pane, text="Folders & Sentences", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        ctrl_frame = ttk.Frame(left_pane)
        ctrl_frame.pack(fill="x", pady=(0, 5))
        self.sent_search_var = tk.StringVar()
        search_entry = ttk.Entry(ctrl_frame, textvariable=self.sent_search_var)
        search_entry.pack(fill="x", pady=(0, 2))
        search_entry.bind("<KeyRelease>", lambda e: self._update_sentences_view())
        
        status_frame = ttk.Frame(ctrl_frame)
        status_frame.pack(fill="x")
        ttk.Label(status_frame, text="Status:").pack(side="left")
        self.sent_status_var = tk.StringVar(value="All")
        status_filter = ttk.Combobox(status_frame, textvariable=self.sent_status_var, values=["All", "Processed", "Unprocessed"], state="readonly", width=12)
        status_filter.pack(side="left", padx=5)
        status_filter.bind("<<ComboboxSelected>>", lambda e: self._update_sentences_view())
        
        tree_frame = ttk.Frame(left_pane)
        tree_frame.pack(fill="both", expand=True)
        list_scroll = ttk.Scrollbar(tree_frame)
        self.sentences_tree = ttk.Treeview(tree_frame, show="tree", yscrollcommand=list_scroll.set)
        self.sentences_tree.pack(side="left", fill="both", expand=True)
        list_scroll.pack(side="right", fill="y")
        list_scroll.config(command=self.sentences_tree.yview)
        self.sentences_tree.bind('<<TreeviewSelect>>', self._on_sentence_selected)
        
        tree_btns = ttk.Frame(left_pane)
        tree_btns.pack(fill="x", pady=5)
        ttk.Button(tree_btns, text="📁 New Folder", command=lambda: ManageCollectionsDialog(self, self.db, 'sentence', self._update_sentences_view)).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(tree_btns, text="📂 Move Item", command=lambda: self._move_item_dialog()).pack(side="left", padx=2, fill="x", expand=True)
        
        # RIGHT PANE: Detail & Editor
        right_pane = ttk.Frame(paned_window, padding=(10, 0, 0, 0))
        paned_window.add(right_pane, weight=3)
        
        target_frame = ttk.LabelFrame(right_pane, text="Target Sentence", padding="10")
        target_frame.pack(fill="x", pady=(0, 10))
        self.sentence_display_text = scrolledtext.ScrolledText(target_frame, height=3, font=("Arial", 11), wrap="word", state="disabled")
        self.sentence_display_text.pack(fill="both", expand=True)
        
        self.notebook = ttk.Notebook(right_pane)
        self.notebook.pack(fill="both", expand=True)
        
        # Tab 1: AI Explanation
        tab_explanation = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_explanation, text="AI Explanation")
        self.sentence_explanation_text = scrolledtext.ScrolledText(tab_explanation, font=("Arial", 10), wrap="word")
        self.sentence_explanation_text.pack(fill="both", expand=True, pady=(0, 10))
        
        ai_action_frame = ttk.Frame(tab_explanation)
        ai_action_frame.pack(fill="x")
        if self.ollama_available:
            ttk.Button(ai_action_frame, text="💬 Explain", command=self._generate_sentence_explanation).pack(side="left", padx=2)
        ttk.Button(ai_action_frame, text="Save", command=self._save_sentence_explanation).pack(side="right")
        
        # Tab 2: Grammar Notes
        tab_grammar = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_grammar, text="Grammar Notes")
        self.sentence_grammar_text = scrolledtext.ScrolledText(tab_grammar, font=("Arial", 10), wrap="word")
        self.sentence_grammar_text.pack(fill="both", expand=True)
        
        # Tab 3: Personal Notes
        tab_notes = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_notes, text="Personal Notes")
        self.sentence_notes_text = scrolledtext.ScrolledText(tab_notes, font=("Arial", 10), wrap="word")
        self.sentence_notes_text.pack(fill="both", expand=True)
        
        # Tab 4: Follow-up Chat
        tab_chat = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_chat, text="Follow-up Chat")
        self.followup_history_text = scrolledtext.ScrolledText(tab_chat, font=("Arial", 10), wrap="word", state="disabled")
        self.followup_history_text.pack(fill="both", expand=True, pady=(0, 10))
        input_frame = ttk.Frame(tab_chat)
        input_frame.pack(fill="x")
        self.followup_question_text = tk.Text(input_frame, height=2, font=("Arial", 10))
        self.followup_question_text.pack(fill="x", side="left", expand=True, padx=(0, 5))
        ttk.Button(input_frame, text="Ask", command=self._ask_followup_question).pack(side="right")
        
        # Tab 5: Settings
        tab_settings = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(tab_settings, text="Settings")
        ttk.Label(tab_settings, text="Select Focus Areas:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))
        self.focus_vars = {}
        for focus in ["grammar", "vocabulary", "context", "pronunciation", "all"]:
            self.focus_vars[focus] = tk.BooleanVar(value=(focus == 'all'))
            ttk.Checkbutton(tab_settings, text=focus.capitalize(), variable=self.focus_vars[focus]).pack(anchor="w", pady=2)

        # Initial Load
        self.sentences_data = self.study_manager.get_imported_sentences()
        self._update_sentences_view()
        
        if self.ollama_available:
             ttk.Button(left_pane, text="⚡ Batch Explain", command=self._start_batch_sentences).pack(fill="x", pady=5)

    def go_back(self):
        if hasattr(self.controller, 'show_study_dashboard'):
            self.controller.show_study_dashboard()

    def _update_sentences_view(self):
        search_query = self.sent_search_var.get().lower().strip()
        status_filter = self.sent_status_var.get()
        
        for item in self.sentences_tree.get_children():
            self.sentences_tree.delete(item)
            
        colls = self.db.get_collections('sentence')
        sentences = self.sentences_data
        
        filtered_sents = []
        for s in sentences:
            match = True
            if search_query and search_query not in s['sentence'].lower(): match = False
            if status_filter == "Processed" and not s['has_explanation']: match = False
            if status_filter == "Unprocessed" and s['has_explanation']: match = False
            if match: filtered_sents.append(s)
            
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
                node = self.sentences_tree.insert(parent, "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)
                folder_nodes[f"coll_{c['id']}"] = node
                remaining.pop(i)
        
        for c in remaining: self.sentences_tree.insert("", "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)
        
        uncategorized_node = None
        for s in filtered_sents:
            parent = ""
            if s['collection_id'] and f"coll_{s['collection_id']}" in folder_nodes: parent = f"coll_{s['collection_id']}"
            else:
                if not uncategorized_node: uncategorized_node = self.sentences_tree.insert("", "end", text="📦 Uncategorized", open=True)
                parent = uncategorized_node
            status = "✓" if s['has_explanation'] else "○"
            snippet = s['sentence'][:30] + ("..." if len(s['sentence']) > 30 else "")
            self.sentences_tree.insert(parent, "end", iid=f"sent_{s['id']}", text=f"{status} {snippet}")

    def _on_sentence_selected(self, event):
        selection = self.sentences_tree.selection()
        if not selection: return
        iid = selection[0]
        if not iid.startswith("sent_"): return
        
        sent_id = int(iid.split("_")[1])
        self.current_sentence_id = sent_id
        
        sent_data = next((s for s in self.sentences_data if s['id'] == sent_id), None)
        if not sent_data: return
        
        self.sentence_display_text.config(state="normal")
        self.sentence_display_text.delete(1.0, tk.END)
        self.sentence_display_text.insert(tk.END, sent_data['sentence'])
        self.sentence_display_text.config(state="disabled")
        
        explanation = self.study_manager.get_sentence_explanation(self.current_sentence_id)
        
        self.sentence_explanation_text.delete(1.0, tk.END)
        self.sentence_grammar_text.delete(1.0, tk.END)
        self.sentence_notes_text.delete(1.0, tk.END)
        self.followup_question_text.delete(1.0, tk.END)
        self.current_sentence_explanation_id = None
        
        if explanation:
            self.sentence_explanation_text.insert(tk.END, explanation['explanation'])
            self.sentence_grammar_text.insert(tk.END, explanation['grammar_notes'])
            self.sentence_notes_text.insert(tk.END, explanation['user_notes'])
            self.current_sentence_explanation_id = explanation['id']
            self._load_followup_history()
        else:
            self.followup_history_text.config(state="normal")
            self.followup_history_text.delete(1.0, tk.END)
            self.followup_history_text.insert(tk.END, "(No explanation yet)")
            self.followup_history_text.config(state="disabled")

    def _generate_sentence_explanation(self):
        if not self.current_sentence_id:
             messagebox.showwarning("Warning", "Please select a sentence first")
             return
             
        selected_focus = [f for f, v in self.focus_vars.items() if v.get()]
        if not selected_focus: selected_focus = ['all']
        
        self.sentence_explanation_text.delete(1.0, tk.END)
        self.sentence_explanation_text.insert(tk.END, f"⏳ Task Queued: Generating explanations for {', '.join(selected_focus)}...")
        
        task_id = self.study_manager.queue_generation_task(
            'sentence_explanation',
            self.current_sentence_id,
            language='native',
            focus_areas=selected_focus
        )
        
        self.active_tasks[task_id] = {
            'type': 'sentence_explanation',
            'item_id': self.current_sentence_id
        }

    def _save_sentence_explanation(self):
        if not self.current_sentence_id: return
        
        exp = self.sentence_explanation_text.get(1.0, tk.END).strip()
        gram = self.sentence_grammar_text.get(1.0, tk.END).strip()
        notes = self.sentence_notes_text.get(1.0, tk.END).strip()
        
        selected_focus = [f for f, v in self.focus_vars.items() if v.get()]
        primary = selected_focus[0] if selected_focus else 'all'
        
        try:
            self.study_manager.add_sentence_explanation(
                self.current_sentence_id,
                exp,
                explanation_language='native',
                focus_area=primary,
                grammar_notes=gram,
                user_notes=notes
            )
            messagebox.showinfo("Success", "Explanation saved!")
            self.sentences_data = self.study_manager.get_imported_sentences() # Refresh
            self._update_sentences_view()
            
            # Update current explanation ID if it was new
            explanation = self.study_manager.get_sentence_explanation(self.current_sentence_id)
            if explanation:
                 self.current_sentence_explanation_id = explanation['id']
                 
        except Exception as e:
            messagebox.showerror("Error", f"Failed: {e}")

    def _check_queue_status(self):
        completed = []
        for task_id in list(self.active_tasks.keys()):
            status = self.study_manager.get_task_status(task_id)
            if status['status'] in ['completed', 'failed']:
                 completed.append(task_id)
                 if status['status'] == 'completed' and self.active_tasks[task_id]['item_id'] == self.current_sentence_id:
                      self._on_sentence_selected(None)
                      messagebox.showinfo("Complete", "Explanation ready!")
                 elif status['status'] == 'failed':
                      messagebox.showerror("Error", status.get("error"))
                      
        for t in completed: del self.active_tasks[t]
        self.after(1000, self._check_queue_status)

    def _add_manual_sentence_dialog(self):
        dialog = tk.Toplevel(self)
        dialog.title("Add Sentence")
        dialog.geometry("500x300")
        
        ttk.Label(dialog, text="Sentence:", font=("Arial", 10)).pack(pady=5)
        sent_text = scrolledtext.ScrolledText(dialog, height=5)
        sent_text.pack(pady=5, padx=10, fill="x")
        
        def save():
            s = sent_text.get(1.0, tk.END).strip()
            if s:
                self.study_manager.add_manual_sentence(s, "")
                self.sentences_data = self.study_manager.get_imported_sentences()
                self._update_sentences_view()
                dialog.destroy()
        
        ttk.Button(dialog, text="Save", command=save).pack(pady=10)

    def _move_item_dialog(self):
        if not self.current_sentence_id:
             messagebox.showwarning("Warning", "Select a sentence first")
             return
        MoveItemDialog(self, self.db, 'sentence', self.current_sentence_id, self._update_sentences_view)

    def _ask_followup_question(self):
        if not self.current_sentence_explanation_id:
             messagebox.showwarning("Warning", "Save explanation first")
             return
             
        q = self.followup_question_text.get(1.0, tk.END).strip()
        if not q: return
        
        self.followup_history_text.config(state="normal")
        self.followup_history_text.insert(tk.END, f"\nQ: {q}\n... Thinking ...\n")
        self.followup_history_text.config(state="disabled")
        self.update() # Force redraw
        
        success, ans = self.study_manager.ask_grammar_followup(self.current_sentence_explanation_id, q)
        
        self.followup_history_text.config(state="normal")
        # Remove thinking? Simplified: just append answer
        if success:
             self.followup_history_text.insert(tk.END, f"A: {ans}\n")
        else:
             self.followup_history_text.insert(tk.END, f"Error: {ans}\n")
        self.followup_history_text.see(tk.END)
        self.followup_history_text.config(state="disabled")
        self.followup_question_text.delete(1.0, tk.END)

    def _load_followup_history(self):
         if not self.current_sentence_explanation_id: return
         followups = self.db.get_grammar_followups(self.current_sentence_explanation_id)
         self.followup_history_text.config(state="normal")
         self.followup_history_text.delete(1.0, tk.END)
         for f in followups:
              self.followup_history_text.insert(tk.END, f"Q: {f['question']}\nA: {f['answer']}\n\n")
         self.followup_history_text.config(state="disabled")
         
    def _start_batch_sentences(self):
         pass
