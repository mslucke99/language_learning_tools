"""
Study GUI - Interface for studying imported words and sentences.
Allows users to add/edit definitions for words and view/generate explanations for sentences.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext, filedialog
from study_manager import StudyManager
from database import FlashcardDatabase
from ollama_integration import is_ollama_available
from datetime import datetime
import re
from quiz_manager import QuizManager
from localization import tr


class StudyGUI:
    """GUI for the study features."""
    
    def __init__(self, root, db: FlashcardDatabase, study_manager: StudyManager, io_manager):
        """Initialize the Study GUI."""
        self.root = root
        self.db = db
        self.study_manager = study_manager
        self.io_manager = io_manager
        self.ollama_available = is_ollama_available()
        timeout = study_manager.request_timeout if study_manager else 30
        self.quiz_manager = QuizManager(db, study_manager.ollama_client if study_manager else None, timeout=timeout)
        
        # Setup styles
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10), padding=8)
        self.style.configure("Large.TButton", font=("Arial", 11), padding=12)
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("Title.TLabel", font=("Arial", 14, "bold"))
        self.style.configure("Subtitle.TLabel", font=("Arial", 12, "bold"))
        
        self.current_word_id = None
        self.current_sentence_id = None
        
        # Background Task Tracking
        self.active_tasks = {} # task_id -> {type, item_id}
        self.cached_suggestions = {} # (type, item_id) -> suggestions dict
        self.current_status_label = None # Widget to update with status
        self._check_queue_status()
        
    def _check_queue_status(self):
        """Poll the task queue status and update UI."""
        status = self.study_manager.get_queue_status()
        queued = status['queued']
        
        # Update status label if it exists
        if self.current_status_label and self.current_status_label.winfo_exists():
            if queued > 0:
                self.current_status_label.config(text=f"⏳ Processing: {queued} items queued...")
            else:
                self.current_status_label.config(text="")
        
        # Check for completed tasks that affect current view
        completed_tasks = []
        for task_id in list(self.active_tasks.keys()):
            info = self.active_tasks[task_id]
            task_status = self.study_manager.get_task_status(task_id)
            if task_status['status'] in ['completed', 'failed']:
                completed_tasks.append(task_id)
                self._handle_completed_task(task_id, task_status)
        
        # Remove completed
        for task_id in completed_tasks:
            del self.active_tasks[task_id]
            
        # Schedule next check
        self.root.after(1000, self._check_queue_status)
        
    def _handle_completed_task(self, task_id, status):
        """Handle a completed task."""
        task_type = status.get('type')
        item_id = status.get('item_id')
        result = status.get('result')
        
        if status['status'] == 'failed':
            messagebox.showerror("Task Failed", f"Task {task_id} failed: {status.get('error')}")
            return

        # Cache suggestions
        suggestions = status.get('suggestions', {})
        if suggestions:
            if task_type in ['definition', 'explanation', 'examples']:
                cache_key = ('word', item_id)
            elif task_type == 'sentence_explanation':
                cache_key = ('sentence', item_id)
            elif task_type == 'grammar_explanation':
                cache_key = ('grammar', item_id)
            else:
                cache_key = (task_type, item_id)
            
            if cache_key not in self.cached_suggestions:
                self.cached_suggestions[cache_key] = {'flashcards': [], 'grammar': []}
            
            # Append new suggestions
            self.cached_suggestions[cache_key]['flashcards'].extend(suggestions.get('flashcards', []))
            self.cached_suggestions[cache_key]['grammar'].extend(suggestions.get('grammar', []))

        # Refresh UI if we are looking at this item
        if task_type in ['definition', 'explanation', 'examples'] and self.current_word_id == item_id:
            # We are likely in words view
            if hasattr(self, 'words_listbox') and self.words_listbox.winfo_exists(): 
                self._on_word_selected(None) # Reload content
                messagebox.showinfo("Complete", "Word generation complete!")
                
        elif task_type == 'sentence_explanation' and self.current_sentence_id == item_id:
            # We are likely in sentence view
            if hasattr(self, 'sentences_listbox') and self.sentences_listbox.winfo_exists():
                self._on_sentence_selected(None) # Reload content
                messagebox.showinfo("Complete", "Sentence explanation ready!")
                
        elif task_type == 'grammar_explanation' and self.current_grammar_id == item_id:
            # We are in grammar view
            if hasattr(self, 'grammar_listbox') and self.grammar_listbox.winfo_exists():
                self._on_grammar_entry_selected(None) # Reload content
                messagebox.showinfo("Complete", "Grammar explanation updated!")
    
    def _setup_standard_header(self, parent, title, back_cmd=None, action_text=None, action_cmd=None):
        """Create a standard header with Back button, Title, and optional Action button."""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Left: Back Button
        if back_cmd:
            ttk.Button(header_frame, text="← Back", command=back_cmd).pack(side="left", padx=(0, 10))
            
        # Center: Title
        ttk.Label(header_frame, text=title, style="Title.TLabel").pack(side="left", fill="x", expand=True)
        
        # Right: Action Button (e.g., "+ Add Item")
        if action_text and action_cmd:
            ttk.Button(header_frame, text=action_text, command=action_cmd).pack(side="right")
            
        return header_frame

    def _bind_mousewheel(self, widget):
        """Bind mousewheel events to a widget recursively."""
        # Windows uses <MouseWheel>, Linux uses <Button-4>/<Button-5>
        def _on_mousewheel(event):
            widget.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind to the widget itself
        widget.bind_all("<MouseWheel>", _on_mousewheel)
        # Note: In a complex app bind_all can be risky if multiple scroll areas exist.
        # Better approach for focused scrolling:
        widget.bind("<Enter>", lambda e: widget.bind_all("<MouseWheel>", _on_mousewheel))
        widget.bind("<Leave>", lambda e: widget.unbind_all("<MouseWheel>"))
    
    def show_study_center(self):
        """Show the main study center screen."""
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        # Title
        title = ttk.Label(frame, text=tr("study_center"), style="Title.TLabel")
        title.pack(pady=20)
        
        # Stats frame
        stats_frame = ttk.LabelFrame(frame, text="Progress Overview", padding="15")
        stats_frame.pack(fill="x", pady=15)
        
        stats = self.study_manager.get_study_statistics()
        
        # Create stat displays
        stats_content = f"""
Words: {stats['words_with_definitions']}/{stats['total_words']} with definitions ({stats['words_percentage']:.1f}%)
Sentences: {stats['sentences_with_explanations']}/{stats['total_sentences']} with explanations ({stats['sentences_percentage']:.1f}%)

Study Languages:
  Native: {self.study_manager.native_language}
  Target: {self.study_manager.study_language}
        """
        
        stats_label = ttk.Label(stats_frame, text=stats_content, justify="left", font=("Courier", 10))
        stats_label.pack()

        # Language Selection
        lang_frame = ttk.Frame(frame)
        lang_frame.pack(fill="x", pady=10)
        
        ttk.Label(lang_frame, text=tr("lbl_language"), font=("Arial", 10, "bold")).pack(side="left", padx=5)
        
        self.study_lang_var = tk.StringVar(value=self.study_manager.study_language)
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.study_lang_var, 
                                 values=["Spanish", "French", "German", "Japanese", "Korean", "Mandarin", "Italian", "Portuguese", "Russian", "Arabic", "Biblical Greek"],
                                 width=15, state="readonly")
        lang_combo.pack(side="left", padx=5)
        lang_combo.bind("<<ComboboxSelected>>", self._on_study_language_changed)
        
        # Main buttons frame
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=20)
        
        # Study words button
        words_btn = ttk.Button(
            btn_frame,
            text=tr("btn_study_words"),
            command=self.show_words_view,
            style="Large.TButton"
        )
        words_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        # Study sentences button
        sentences_btn = ttk.Button(
            btn_frame,
            text=tr("btn_study_sentences"),
            command=self.show_sentences_view,
            style="Large.TButton"
        )
        sentences_btn.pack(side="left", padx=10, fill="both", expand=True)

        # Grammar Book button
        grammar_btn = ttk.Button(
            btn_frame,
            text=tr("btn_grammar_book"),
            command=self.show_grammar_book_view,
            style="Large.TButton"
        )
        grammar_btn.pack(side="left", padx=10, fill="both", expand=True)

        # Writing Composition Lab button
        writing_btn = ttk.Button(
            btn_frame,
            text=tr("btn_writing_lab"),
            command=self.show_writing_lab_view,
            style="Large.TButton"
        )
        writing_btn.pack(side="left", padx=10, fill="both", expand=True)

        # Chat with AI button
        chat_btn = ttk.Button(
            btn_frame,
            text=tr("btn_chat"),
            command=self.show_chat_dashboard,
            style="Large.TButton"
        )
        chat_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        # Quiz button
        quiz_btn = ttk.Button(
            btn_frame,
            text=tr("btn_quiz"),
            command=self.show_quiz_setup,
            style="Large.TButton"
        )
        quiz_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        # Back button
        back_btn = ttk.Button(frame, text=tr("btn_main_menu"), command=self.on_close)
        back_btn.pack(pady=10)
        
        # Status Label (Global)
        self.current_status_label = ttk.Label(frame, text="", font=("Arial", 10, "italic"), foreground="blue")
        self.current_status_label.pack(pady=5)

        # Disclaimer
        disclaimer_label = ttk.Label(frame, text=tr("msg_disclaimer"), font=("Arial", 8), foreground="gray", wraplength=600, justify="center")
        disclaimer_label.pack(side="bottom", pady=20)
        
        # Test UI Language Switcher (Korean/English)
        test_lang_frame = ttk.Frame(frame)
        test_lang_frame.pack(side="bottom", pady=5)
        ttk.Label(test_lang_frame, text="Switch UI (Test):", font=("Arial", 8)).pack(side="left")
        ttk.Button(test_lang_frame, text="EN", width=3, command=lambda: self._switch_ui_locale('en')).pack(side="left", padx=2)
        ttk.Button(test_lang_frame, text="KO", width=3, command=lambda: self._switch_ui_locale('ko')).pack(side="left", padx=2)

    def _switch_ui_locale(self, lang_code):
        """Switch UI language and refresh."""
        from localization import set_locale
        set_locale(lang_code)
        self.show_study_center()

    def _on_study_language_changed(self, event):
        """Handle study language change."""
        new_lang = self.study_lang_var.get()
        if new_lang != self.study_manager.study_language:
            self.study_manager.set_study_language(new_lang)
            messagebox.showinfo("Language Changed", f"Switched study language to {new_lang}")
            self.show_study_center() # Refresh stats

    
    # ========== WORDS VIEW ==========
    
    def show_words_view(self):
        """Show the words study view."""
        self.clear_window()
        
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill="both", expand=True)
        
        # 1. Custom Header
        self._setup_standard_header(
            main_frame,
            "Study Words",
            back_cmd=self.show_study_center,
            action_text="+ Add Word",
            action_cmd=self._add_manual_word_dialog
        )
        
        # 2. Main Content (Integrated View)
        # Wrap everything in a scrollable frame for stability
        container = ttk.Frame(main_frame)
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_content = ttk.Frame(canvas, padding="5")
        
        scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        paned_window = ttk.PanedWindow(scrollable_content, orient="horizontal")
        paned_window.pack(fill="both", expand=True)
        
        # LEFT PANE: Word Tree (Integrated)
        left_pane = ttk.Frame(paned_window)
        paned_window.add(left_pane, weight=1)
        
        ttk.Label(left_pane, text="Folders & Words", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        # Search & Status controls
        ctrl_frame = ttk.Frame(left_pane)
        ctrl_frame.pack(fill="x", pady=(0, 5))
        
        self.word_search_var = tk.StringVar()
        search_entry = ttk.Entry(ctrl_frame, textvariable=self.word_search_var)
        search_entry.pack(fill="x", pady=(0, 2))
        search_entry.bind("<KeyRelease>", lambda e: self._update_words_view())
        
        status_frame = ttk.Frame(ctrl_frame)
        status_frame.pack(fill="x")
        ttk.Label(status_frame, text="Status:").pack(side="left")
        self.word_status_var = tk.StringVar(value="All")
        status_filter = ttk.Combobox(status_frame, textvariable=self.word_status_var, values=["All", "Processed", "Unprocessed"], state="readonly", width=12)
        status_filter.pack(side="left", padx=5)
        status_filter.bind("<<ComboboxSelected>>", lambda e: self._update_words_view())
        
        # Treeview Scrollbar
        tree_frame = ttk.Frame(left_pane)
        tree_frame.pack(fill="both", expand=True)
        
        list_scroll = ttk.Scrollbar(tree_frame)
        self.words_tree = ttk.Treeview(tree_frame, show="tree", yscrollcommand=list_scroll.set)
        self.words_tree.pack(side="left", fill="both", expand=True)
        list_scroll.pack(side="right", fill="y")
        list_scroll.config(command=self.words_tree.yview)
        
        self.words_tree.bind('<<TreeviewSelect>>', self._on_word_selected)
        
        # Action Buttons below Tree
        tree_btns = ttk.Frame(left_pane)
        tree_btns.pack(fill="x", pady=5)
        ttk.Button(tree_btns, text="📁 New Folder", command=lambda: self._manage_study_colls('word')).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(tree_btns, text="📂 Move Item", command=lambda: self._move_item_to_coll('word')).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(tree_btns, text="📤 Export JSON", command=lambda: self._export_study_items('word')).pack(side="left", padx=2, fill="x", expand=True)
        
        # RIGHT PANE: Detail & Editor
        right_pane = ttk.Frame(paned_window, padding=(10, 0, 0, 0))
        paned_window.add(right_pane, weight=3)
        
        # Header Row (Label + Status)
        header_row = ttk.Frame(right_pane)
        header_row.pack(fill="x", pady=(0, 10))
        
        # Selected Word Display
        self.word_label = ttk.Label(header_row, text="(Select a word)", style="Subtitle.TLabel")
        self.word_label.pack(side="left")
        
        # Status Label
        self.current_status_label = ttk.Label(header_row, text="", font=("Arial", 9, "italic"), foreground="blue")
        self.current_status_label.pack(side="right")
        
        # TABS for Details
        self.notebook = ttk.Notebook(right_pane)
        self.notebook.pack(fill="both", expand=True)
        
        # TAB 1: Definition
        tab_def = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_def, text="Definition")
        self.word_definition_text = scrolledtext.ScrolledText(tab_def, font=("Arial", 10), wrap="word")
        self.word_definition_text.pack(fill="both", expand=True, pady=(0, 10))
        self._bind_mousewheel(self.word_definition_text)
        
        ai_action_frame = ttk.Frame(tab_def)
        ai_action_frame.pack(fill="x")
        if self.ollama_available:
            ttk.Button(ai_action_frame, text="📋 Generate Definition", command=lambda: self._generate_word_content('definition')).pack(side="left", padx=2)
            ttk.Button(ai_action_frame, text="📝 Generate Explanation", command=lambda: self._generate_word_content('explanation')).pack(side="left", padx=2)
        ttk.Button(ai_action_frame, text="Save", command=self._save_word_definition).pack(side="right")
        
        # TAB 2: Examples & Notes
        tab_notes = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_notes, text="Examples & Notes")
        notes_paned = ttk.PanedWindow(tab_notes, orient="vertical")
        notes_paned.pack(fill="both", expand=True)
        ex_frame = ttk.LabelFrame(notes_paned, text="Examples", padding="5")
        notes_paned.add(ex_frame, weight=1)
        self.word_examples_text = scrolledtext.ScrolledText(ex_frame, height=5, font=("Arial", 10), wrap="word")
        self.word_examples_text.pack(fill="both", expand=True)
        if self.ollama_available:
             ttk.Button(ex_frame, text="💬 Generate Examples", command=lambda: self._generate_word_content('examples')).pack(anchor="e", pady=2)
        notes_frame = ttk.LabelFrame(notes_paned, text="My Notes", padding="5")
        notes_paned.add(notes_frame, weight=1)
        self.word_notes_text = scrolledtext.ScrolledText(notes_frame, height=5, font=("Arial", 10), wrap="word")
        self.word_notes_text.pack(fill="both", expand=True)
        ttk.Button(tab_notes, text="Save Changes", command=self._save_word_definition).pack(anchor="e", pady=5)
        
        # TAB 3: Related Items
        tab_related = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_related, text="Related Items")
        self.related_items_frame = ttk.Frame(tab_related)
        self.related_items_frame.pack(fill="both", expand=True)
        ttk.Label(self.related_items_frame, text="AI Suggestions will appear here...", font=("Arial", 10, "italic"), foreground="gray").pack(pady=20)
        
        # Populate Tree
        self.words_data = self.study_manager.get_imported_words()
        self._update_words_view()
        
        if self.ollama_available:
            ttk.Button(left_pane, text="⚡ Batch Define (Missing)", command=self._start_batch_words).pack(fill="x", pady=5)

    def _update_words_view(self):
        """Update the words treeview with folders and items."""
        if not hasattr(self, 'words_tree') or not self.words_tree.winfo_exists():
            return
            
        search_query = self.word_search_var.get().lower().strip()
        status_filter = self.word_status_var.get()
        
        # Clear tree
        for item in self.words_tree.get_children():
            self.words_tree.delete(item)
            
        # Get data
        colls = self.db.get_collections('word')
        words = self.words_data
        
        # Filter words
        filtered_words = []
        for w in words:
            match = True
            if search_query and search_query not in w['word'].lower(): match = False
            if status_filter == "Processed" and not w['has_definition']: match = False
            if status_filter == "Unprocessed" and w['has_definition']: match = False
            if match: filtered_words.append(w)
        
        self.filtered_words_data = filtered_words
        
        # Map folders
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
                node = self.words_tree.insert(parent, "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)
                folder_nodes[f"coll_{c['id']}"] = node
                remaining.pop(i)
        
        for c in remaining: self.words_tree.insert("", "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)

        # Insert Words
        uncategorized_node = None
        for w in filtered_words:
            parent = ""
            if w['collection_id'] and f"coll_{w['collection_id']}" in folder_nodes: parent = f"coll_{w['collection_id']}"
            else:
                if not uncategorized_node: uncategorized_node = self.words_tree.insert("", "end", text="📦 Uncategorized", open=True)
                parent = uncategorized_node
            status = "✓" if w['has_definition'] else "○"
            self.words_tree.insert(parent, "end", iid=f"word_{w['id']}", text=f"{status} {w['word']}")
    
    def _on_word_selected(self, event):
        """Handle word selection from treeview."""
        selection = self.words_tree.selection()
        if not selection:
            return
        
        iid = selection[0]
        if not iid.startswith("word_"):
            return # Folders don't have details
            
        word_id = int(iid.split("_")[1])
        self.current_word_id = word_id
        
        # Find data
        word_data = next((w for w in self.words_data if w['id'] == word_id), None)
        if not word_data: return
        
        # Update label
        self.word_label.config(text=f"Word: {word_data['word']}")
        
        # Load existing definition
        definition = self.study_manager.get_word_definition(self.current_word_id)
        
        self.word_definition_text.delete(1.0, tk.END)
        self.word_examples_text.delete(1.0, tk.END)
        self.word_notes_text.delete(1.0, tk.END)
        
        if definition:
            self.word_definition_text.insert(tk.END, definition['definition'])
            if definition['examples']:
                self.word_examples_text.insert(tk.END, "\n".join(definition['examples']))
            self.word_notes_text.insert(tk.END, definition['notes'])
            
        # Update Related Items Tab
        self._update_related_items_tab('word', self.current_word_id)
    
    def _save_word_definition(self):
        """Save the word definition."""
        if not self.current_word_id:
            messagebox.showwarning("Warning", "Please select a word first")
            return
        
        definition = self.word_definition_text.get(1.0, tk.END).strip()
        if not definition:
            messagebox.showwarning("Warning", "Please enter a definition")
            return
        
        examples_text = self.word_examples_text.get(1.0, tk.END).strip()
        examples = [e.strip() for e in examples_text.split('\n') if e.strip()] if examples_text else []
        
        notes = self.word_notes_text.get(1.0, tk.END).strip()
        
        try:
            self.study_manager.add_word_definition(
                self.current_word_id,
                definition,
                definition_language='native',
                examples=examples,
                notes=notes
            )
            messagebox.showinfo("Success", "Definition saved!")
            self.show_words_view()  # Refresh
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def _clear_word_form(self):
        """Clear the word form."""
        self.word_definition_text.delete(1.0, tk.END)
        self.word_examples_text.delete(1.0, tk.END)
        self.word_notes_text.delete(1.0, tk.END)
    
    def _generate_word_definition(self):
        """Generate word definition using Ollama (legacy compatibility)."""
        self._generate_word_content('definition')
    
    def _generate_word_content(self, content_type: str):
        """
        Generate word content (definition, explanation, or examples) using Ollama asynchronously.
        
        Args:
            content_type: 'definition', 'explanation', or 'examples'
        """
        if not self.current_word_id:
            messagebox.showwarning("Warning", "Please select a word first")
            return
        
        # Show loading/queued state
        self.word_definition_text.delete(1.0, tk.END)
        self.word_definition_text.insert(tk.END, f"⏳ Task Queued: Generating {content_type}...")
        
        # Queue the task
        task_id = self.study_manager.queue_generation_task(
            content_type,
            self.current_word_id,
            language='native'
        )
        
        # Track active task for this view
        self.active_tasks[task_id] = {
            'type': content_type,
            'item_id': self.current_word_id
        }
        
        # Poke the status checker
        self._check_queue_status()
    
    
    # ========== SUGGESTIONS MANAGEMENT ==========
    
    def _update_related_items_tab(self, item_type, item_id):
        """Update the Related Items tab with cached suggestions."""
        if not hasattr(self, 'related_items_frame'):
            return
            
        # Clear existing
        for widget in self.related_items_frame.winfo_children():
            widget.destroy()
            
        # Get suggestions
        key = (item_type, item_id)
        suggestions = self.cached_suggestions.get(key)
        
        if not suggestions or (not suggestions['flashcards'] and not suggestions['grammar']):
            ttk.Label(self.related_items_frame, text="No suggestions available.\nGenerate content using AI to see related items.", 
                     font=("Arial", 10, "italic"), foreground="gray", justify="center").pack(pady=20)
            return
            
        # Render Flashcards
        if suggestions['flashcards']:
            ttk.Label(self.related_items_frame, text="Related Words (Flashcards)", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 5))
            for fc in suggestions['flashcards']:
                f = ttk.Frame(self.related_items_frame, padding=5, relief="solid", borderwidth=1)
                f.pack(fill="x", pady=2, padx=5)
                
                info = ttk.Frame(f)
                info.pack(side="left", fill="x", expand=True)
                ttk.Label(info, text=fc['word'], font=("Arial", 10, "bold")).pack(anchor="w")
                ttk.Label(info, text=fc['definition'], font=("Arial", 9), wraplength=300).pack(anchor="w")
                
                # Check if already in a deck
                matches = self.db.find_flashcard_by_question(fc['word'])
                if matches:
                    decks = list(set([m['deck_name'] for m in matches]))
                    ttk.Label(f, text=f"✓ In {', '.join(decks)}", foreground="green", font=("Arial", 8, "italic")).pack(side="right", padx=5)
                
                ttk.Button(f, text="+ Add", width=6, 
                          command=lambda w=fc['word'], d=fc['definition']: self._add_suggested_flashcard(w, d)).pack(side="right")
                          
        # Render Grammar
        if suggestions['grammar']:
            ttk.Label(self.related_items_frame, text="Related Grammar", font=("Arial", 10, "bold")).pack(anchor="w", pady=(15, 5))
            for gp in suggestions['grammar']:
                f = ttk.Frame(self.related_items_frame, padding=5, relief="solid", borderwidth=1)
                f.pack(fill="x", pady=2, padx=5)
                
                info = ttk.Frame(f)
                info.pack(side="left", fill="x", expand=True)
                ttk.Label(info, text=gp['title'], font=("Arial", 10, "bold")).pack(anchor="w")
                ttk.Label(info, text=gp['explanation'], font=("Arial", 9), wraplength=300).pack(anchor="w")
                
                ttk.Button(f, text="+ Add", width=6, 
                          command=lambda t=gp['title'], e=gp['explanation']: self._add_suggested_grammar(t, e)).pack(side="right")

    def _add_suggested_flashcard(self, word, definition):
        """Open add dialog for suggested word."""
        self._add_manual_word_dialog(initial_word=word, initial_def=definition)
        
    def _add_suggested_grammar(self, title, explanation):
        """Add suggested grammar entry."""
        if messagebox.askyesno("Add Grammar", f"Add '{title}' to Grammar Book?"):
            self.study_manager.add_grammar_entry(title, explanation, tags="ai_suggestion")
            messagebox.showinfo("Success", "Grammar entry added!")
            # Optional: Refresh? No need unless we have a grammar list visible.
            
    # ========== SENTENCES VIEW ==========
    
    def show_sentences_view(self):
        """Show the sentences study view."""
        self.clear_window()
        
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill="both", expand=True)
        
        # 1. Custom Header
        self._setup_standard_header(
            main_frame, 
            "Study Sentences", 
            back_cmd=self.show_study_center,
            action_text="+ Add Sentence",
            action_cmd=self._add_manual_sentence_dialog
        )
        
        # 2. Main Content (Integrated View)
        container = ttk.Frame(main_frame)
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_content = ttk.Frame(canvas, padding="5")
        
        scrollable_content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_canvas_configure(event): canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        paned_window = ttk.PanedWindow(scrollable_content, orient="horizontal")
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
        ttk.Button(tree_btns, text="📁 New Folder", command=lambda: self._manage_study_colls('sentence')).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(tree_btns, text="📂 Move Item", command=lambda: self._move_item_to_coll('sentence')).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(tree_btns, text="📤 Export JSON", command=lambda: self._export_study_items('sentence')).pack(side="left", padx=2, fill="x", expand=True)
        
        # RIGHT PANE: Detail & Editor
        right_pane = ttk.Frame(paned_window, padding=(10, 0, 0, 0))
        paned_window.add(right_pane, weight=3)
        
        status_row = ttk.Frame(right_pane)
        status_row.pack(fill="x", pady=(0, 5))
        self.current_status_label = ttk.Label(status_row, text="", font=("Arial", 9, "italic"), foreground="blue")
        self.current_status_label.pack(side="right")
        
        target_frame = ttk.LabelFrame(right_pane, text="Target Sentence", padding="10")
        target_frame.pack(fill="x", pady=(0, 10))
        self.sentence_display_text = scrolledtext.ScrolledText(target_frame, height=3, font=("Arial", 11), wrap="word", state="disabled")
        self.sentence_display_text.pack(fill="both", expand=True)
        
        self.notebook = ttk.Notebook(right_pane)
        self.notebook.pack(fill="both", expand=True)
        
        # Tabs
        tab_explanation = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_explanation, text="AI Explanation")
        self.sentence_explanation_text = scrolledtext.ScrolledText(tab_explanation, font=("Arial", 10), wrap="word")
        self.sentence_explanation_text.pack(fill="both", expand=True, pady=(0, 10))
        
        ai_action_frame = ttk.Frame(tab_explanation)
        ai_action_frame.pack(fill="x")
        if self.ollama_available:
            ttk.Button(ai_action_frame, text="💬 Explain", command=self._generate_sentence_explanation_multi).pack(side="left", padx=2)
        ttk.Button(ai_action_frame, text="Save", command=self._save_sentence_explanation).pack(side="right")
        
        tab_grammar = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_grammar, text="Grammar Notes")
        self.sentence_grammar_text = scrolledtext.ScrolledText(tab_grammar, font=("Arial", 10), wrap="word")
        self.sentence_grammar_text.pack(fill="both", expand=True)
        ttk.Button(tab_grammar, text="Save", command=self._save_sentence_explanation).pack(anchor="e", pady=5)
        
        tab_notes = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_notes, text="Personal Notes")
        self.sentence_notes_text = scrolledtext.ScrolledText(tab_notes, font=("Arial", 10), wrap="word")
        self.sentence_notes_text.pack(fill="both", expand=True)
        ttk.Button(tab_notes, text="Save", command=self._save_sentence_explanation).pack(anchor="e", pady=5)

        tab_chat = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_chat, text="Follow-up Chat")
        self.followup_history_text = scrolledtext.ScrolledText(tab_chat, font=("Arial", 10), wrap="word", state="disabled")
        self.followup_history_text.pack(fill="both", expand=True, pady=(0, 10))
        input_frame = ttk.Frame(tab_chat)
        input_frame.pack(fill="x")
        self.followup_question_text = tk.Text(input_frame, height=2, font=("Arial", 10))
        self.followup_question_text.pack(fill="x", side="left", expand=True, padx=(0, 5))
        ttk.Button(input_frame, text="Ask", command=self._ask_followup_question).pack(side="right")
        
        tab_related = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_related, text="Related Items")
        self.related_items_frame = ttk.Frame(tab_related)
        self.related_items_frame.pack(fill="both", expand=True)
        
        tab_settings = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(tab_settings, text="Settings")
        ttk.Label(tab_settings, text="Select Focus Areas:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))
        self.focus_vars = {}
        for focus in ["grammar", "vocabulary", "context", "pronunciation", "all"]:
            self.focus_vars[focus] = tk.BooleanVar(value=(focus == 'all'))
            ttk.Checkbutton(tab_settings, text=focus.capitalize(), variable=self.focus_vars[focus]).pack(anchor="w", pady=2)

        # Populate
        self.sentences_data = self.study_manager.get_imported_sentences()
        self._update_sentences_view()
        if self.ollama_available:
            ttk.Button(left_pane, text="⚡ Batch Explain", command=self._start_batch_sentences).pack(fill="x", pady=5)

    def _update_sentences_view(self):
        """Update the sentences treeview with folders and items."""
        if not hasattr(self, 'sentences_tree') or not self.sentences_tree.winfo_exists():
            return
            
        search_query = self.sent_search_var.get().lower().strip()
        status_filter = self.sent_status_var.get()
        
        # Clear tree
        for item in self.sentences_tree.get_children():
            self.sentences_tree.delete(item)
            
        # Get data
        colls = self.db.get_collections('sentence')
        sentences = self.sentences_data
        
        # Filter sentences
        filtered_sents = []
        for s in sentences:
            match = True
            if search_query and search_query not in s['sentence'].lower():
                match = False
            if status_filter == "Processed" and not s['has_explanation']:
                match = False
            if status_filter == "Unprocessed" and s['has_explanation']:
                match = False
            if match:
                filtered_sents.append(s)
        
        self.filtered_sentences_data = filtered_sents
        
        # Map folders
        folder_nodes = {}
        remaining = list(colls)
        max_iters = 5
        while remaining and max_iters > 0:
            max_iters -= 1
            for i in range(len(remaining)-1, -1, -1):
                c = remaining[i]
                parent = ""
                if c['parent_id'] and f"coll_{c['parent_id']}" in folder_nodes:
                    parent = f"coll_{c['parent_id']}"
                elif c['parent_id'] is None:
                    parent = ""
                else: continue
                
                node = self.sentences_tree.insert(parent, "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)
                folder_nodes[f"coll_{c['id']}"] = node
                remaining.pop(i)
        
        # Insert any orphaned folders to root
        for c in remaining:
            self.sentences_tree.insert("", "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)

        # Insert Sentences
        uncategorized_node = None
        for s in filtered_sents:
            parent = ""
            if s['collection_id'] and f"coll_{s['collection_id']}" in folder_nodes:
                parent = f"coll_{s['collection_id']}"
            else:
                if not uncategorized_node:
                    uncategorized_node = self.sentences_tree.insert("", "end", text="📦 Uncategorized", open=True)
                parent = uncategorized_node
            
            status = "✓" if s['has_explanation'] else "○"
            snippet = s['sentence'][:30] + ("..." if len(s['sentence']) > 30 else "")
            self.sentences_tree.insert(parent, "end", iid=f"sent_{s['id']}", text=f"{status} {snippet}")

    def _on_sentence_selected(self, event):
        """Handle sentence selection from treeview."""
        selection = self.sentences_tree.selection()
        if not selection: return
        iid = selection[0]
        if not iid.startswith("sent_"): return
            
        sent_id = int(iid.split("_")[1])
        self.current_sentence_id = sent_id
        
        sent_data = next((s for s in self.sentences_data if s['id'] == sent_id), None)
        if not sent_data: return
        
        # Update widgets instead of re-creating them
        if hasattr(self, 'sentence_display_text'):
            self.sentence_display_text.config(state="normal")
            self.sentence_display_text.delete(1.0, tk.END)
            self.sentence_display_text.insert(tk.END, sent_data['sentence'])
            self.sentence_display_text.config(state="disabled")
        
        explanation = self.study_manager.get_sentence_explanation(self.current_sentence_id)
        
        self.sentence_explanation_text.delete(1.0, tk.END)
        self.sentence_grammar_text.delete(1.0, tk.END)
        self.sentence_notes_text.delete(1.0, tk.END)
        for focus in self.focus_vars: self.focus_vars[focus].set(False)
        self.followup_question_text.delete(1.0, tk.END)
        self.current_sentence_explanation_id = None
        
        if explanation:
            self.sentence_explanation_text.insert(tk.END, explanation['explanation'])
            self.sentence_grammar_text.insert(tk.END, explanation['grammar_notes'])
            self.sentence_notes_text.insert(tk.END, explanation['user_notes'])
            if explanation.get('focus_area') and explanation['focus_area'] in self.focus_vars:
                self.focus_vars[explanation['focus_area']].set(True)
            self.current_sentence_explanation_id = explanation['id']
            self._load_followup_history()
        else:
            self.focus_vars['all'].set(True)
            self.followup_history_text.config(state="normal")
            self.followup_history_text.delete(1.0, tk.END)
            self.followup_history_text.insert(tk.END, "(No explanation yet. Generate or enter an explanation first.)")
            self.followup_history_text.config(state="disabled")
            
        self._update_related_items_tab('sentence', self.current_sentence_id)
    
    def _save_sentence_explanation(self):
        """Save the sentence explanation."""
        if not self.current_sentence_id:
            messagebox.showwarning("Warning", "Please select a sentence first")
            return
        
        explanation = self.sentence_explanation_text.get(1.0, tk.END).strip()
        if not explanation:
            messagebox.showwarning("Warning", "Please enter an explanation")
            return
        
        grammar_notes = self.sentence_grammar_text.get(1.0, tk.END).strip()
        user_notes = self.sentence_notes_text.get(1.0, tk.END).strip()
        
        # Get selected focus areas from checkboxes
        selected_focus_areas = [focus for focus, var in self.focus_vars.items() if var.get()]
        
        if not selected_focus_areas:
            messagebox.showwarning("Warning", "Please select at least one focus area")
            return
        
        # Use the first selected focus area as primary
        primary_focus = selected_focus_areas[0]
        
        try:
            self.study_manager.add_sentence_explanation(
                self.current_sentence_id,
                explanation,
                explanation_language='native',
                focus_area=primary_focus,
                grammar_notes=grammar_notes,
                user_notes=user_notes
            )
            messagebox.showinfo("Success", "Explanation saved!")
            self.show_sentences_view()  # Refresh
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save: {str(e)}")
    
    def _clear_sentence_form(self):
        """Clear the sentence form."""
        self.sentence_explanation_text.delete(1.0, tk.END)
        self.sentence_grammar_text.delete(1.0, tk.END)
        self.sentence_notes_text.delete(1.0, tk.END)
    
    def _generate_sentence_explanation(self):
        """Generate sentence explanation using Ollama (legacy - single focus area)."""
        if not self.current_sentence_id:
            messagebox.showwarning("Warning", "Please select a sentence first")
            return
        
        # Show loading
        original_text = self.sentence_explanation_text.get(1.0, tk.END)
        self.sentence_explanation_text.delete(1.0, tk.END)
        self.sentence_explanation_text.insert(tk.END, "🔄 Generating explanation...")
        self.root.update()
        
        # Get selected focus areas
        selected_focus_areas = [focus for focus, var in self.focus_vars.items() if var.get()]
        if not selected_focus_areas:
            selected_focus_areas = ['all']
        
        success, result = self.study_manager.generate_sentence_explanation(
            self.current_sentence_id,
            language='native',
            focus_areas=selected_focus_areas
        )
        
        self.sentence_explanation_text.delete(1.0, tk.END)
        if success:
            self.sentence_explanation_text.insert(tk.END, result)
        else:
            self.sentence_explanation_text.insert(tk.END, original_text)
            messagebox.showerror("Error", result)
    
    def _generate_sentence_explanation_multi(self):
        """Generate sentence explanation for multiple selected focus areas using Ollama asynchronously."""
        if not self.current_sentence_id:
            messagebox.showwarning("Warning", "Please select a sentence first")
            return
        
        # Get selected focus areas from checkboxes
        selected_focus_areas = [focus for focus, var in self.focus_vars.items() if var.get()]
        
        if not selected_focus_areas:
            messagebox.showwarning("Warning", "Please select at least one focus area")
            return
        
        # Show loading/queued
        self.sentence_explanation_text.delete(1.0, tk.END)
        self.sentence_explanation_text.insert(tk.END, f"⏳ Task Queued: Generating explanations for {', '.join(selected_focus_areas)}...")
        
        # Queue task
        task_id = self.study_manager.queue_generation_task(
            'sentence_explanation',
            self.current_sentence_id,
            language='native',
            focus_areas=selected_focus_areas
        )
        
        # Track active task
        self.active_tasks[task_id] = {
            'type': 'sentence_explanation',
            'item_id': self.current_sentence_id
        }
        
        # Poke status checker
        self._check_queue_status()
    
    # ========== FOLLOW-UP QUESTIONS ==========
    
    def _ask_followup_question(self):
        """Ask a follow-up question about the current sentence."""
        if not self.current_sentence_explanation_id:
            messagebox.showwarning("Warning", "Please save an explanation first before asking follow-up questions")
            return
        
        question = self.followup_question_text.get(1.0, tk.END).strip()
        if not question:
            messagebox.showwarning("Warning", "Please enter a question")
            return
        
        # Show loading in history
        self.followup_history_text.config(state="normal")
        self.followup_history_text.insert(tk.END, f"\n\n🤔 Q: {question}\n🔄 Generating answer...\n")
        self.followup_history_text.see(tk.END)
        self.followup_history_text.config(state="disabled")
        self.root.update()
        
        # Ask the question
        success, answer = self.study_manager.ask_grammar_followup(
            self.current_sentence_explanation_id,
            question
        )
        
        # Update history with answer
        self.followup_history_text.config(state="normal")
        # Remove loading message
        content = self.followup_history_text.get(1.0, tk.END)
        content = content.replace("🔄 Generating answer...\n", "")
        self.followup_history_text.delete(1.0, tk.END)
        self.followup_history_text.insert(1.0, content)
        
        if success:
            self.followup_history_text.insert(tk.END, f"💡 A: {answer}\n")
        else:
            self.followup_history_text.insert(tk.END, f"❌ Error: {answer}\n")
        
        self.followup_history_text.see(tk.END)
        self.followup_history_text.config(state="disabled")
        
        # Clear question input
        self.followup_question_text.delete(1.0, tk.END)
        
        if not success:
            messagebox.showerror("Error", answer)
    
    def _load_followup_history(self):
        """Load and display follow-up history for the current sentence."""
        if not self.current_sentence_explanation_id:
            return
        
        followups = self.db.get_grammar_followups(self.current_sentence_explanation_id)
        
        self.followup_history_text.config(state="normal")
        self.followup_history_text.delete(1.0, tk.END)
        
        if not followups:
            self.followup_history_text.insert(tk.END, "(No follow-up questions yet. Ask a question above!)")
        else:
            for i, followup in enumerate(followups, 1):
                self.followup_history_text.insert(tk.END, f"🤔 Q{i}: {followup['question']}\n")
                self.followup_history_text.insert(tk.END, f"💡 A{i}: {followup['answer']}\n\n")
        
        self.followup_history_text.config(state="disabled")
    
    def _clear_followup_history(self):
        """Clear all follow-up questions for the current sentence."""
        if not self.current_sentence_explanation_id:
            messagebox.showwarning("Warning", "No sentence selected")
            return
        
        if messagebox.askyesno("Clear History", "Clear all follow-up questions for this sentence?"):
            self.db.clear_grammar_followups(self.current_sentence_explanation_id)
            self._load_followup_history()
            messagebox.showinfo("Success", "Follow-up history cleared")
    
    
    
    # ========== GRAMMAR BOOK VIEW ==========
    
    def show_grammar_book_view(self):
        """Show the grammar book view."""
        self.clear_window()
        
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill="both", expand=True)
        
        # 1. Custom Header
        self._setup_standard_header(
            main_frame,
            "Grammar Book",
            back_cmd=self.show_study_center,
            action_text="+ New Entry",
            action_cmd=self._new_grammar_entry
        )
        
        # 2. Main Content (Integrated View)
        container = ttk.Frame(main_frame)
        container.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_content = ttk.Frame(canvas, padding="5")
        
        scrollable_content.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_content, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        def _on_canvas_configure(event):
            canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        paned_window = ttk.PanedWindow(scrollable_content, orient="horizontal")
        paned_window.pack(fill="both", expand=True)
        
        # LEFT PANE: Grammar Tree (Integrated)
        left_pane = ttk.Frame(paned_window)
        paned_window.add(left_pane, weight=1)
        
        ttk.Label(left_pane, text="Folders & Entries", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        # Search & Sort controls
        ctrl_frame = ttk.Frame(left_pane)
        ctrl_frame.pack(fill="x", pady=(0, 5))
        
        self.grammar_search_var = tk.StringVar()
        self.grammar_search_var.trace("w", self._filter_grammar_entries)
        ttk.Entry(ctrl_frame, textvariable=self.grammar_search_var, width=15).pack(fill="x", pady=(0, 2))
        
        sort_frame = ttk.Frame(ctrl_frame)
        sort_frame.pack(fill="x")
        ttk.Label(sort_frame, text="Sort:").pack(side="left")
        self.grammar_sort_var = tk.StringVar(value="Updated")
        sort_dropdown = ttk.Combobox(sort_frame, textvariable=self.grammar_sort_var, values=["Updated", "A-Z"], state="readonly", width=10)
        sort_dropdown.pack(side="left", padx=5)
        sort_dropdown.bind("<<ComboboxSelected>>", lambda e: self._update_grammar_view())
        
        # Treeview Scrollbar
        tree_frame = ttk.Frame(left_pane)
        tree_frame.pack(fill="both", expand=True)
        
        list_scroll = ttk.Scrollbar(tree_frame)
        self.grammar_tree = ttk.Treeview(tree_frame, show="tree", yscrollcommand=list_scroll.set)
        self.grammar_tree.pack(side="left", fill="both", expand=True)
        list_scroll.pack(side="right", fill="y")
        list_scroll.config(command=self.grammar_tree.yview)
        
        self.grammar_tree.bind('<<TreeviewSelect>>', self._on_grammar_entry_selected)
        
        # Action Buttons below Tree
        tree_btns = ttk.Frame(left_pane)
        tree_btns.pack(fill="x", pady=5)
        ttk.Button(tree_btns, text="📁 New Folder", command=lambda: self._manage_study_colls('grammar')).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(tree_btns, text="📂 Move Item", command=lambda: self._move_item_to_coll('grammar')).pack(side="left", padx=2, fill="x", expand=True)
        ttk.Button(tree_btns, text="📤 Export JSON", command=lambda: self._export_study_items('grammar')).pack(side="left", padx=2, fill="x", expand=True)
        
        # Populate Tree
        self._update_grammar_view()
        
        # RIGHT PANE: Editor
        right_panel = ttk.LabelFrame(paned_window, text="Entry Editor", padding="15")
        paned_window.add(right_panel, weight=3)
        
        # Status Label
        status_frame = ttk.Frame(right_panel)
        status_frame.pack(fill="x", pady=(0, 10))
        self.current_status_label = ttk.Label(status_frame, text="", font=("Arial", 9, "italic"), foreground="blue")
        self.current_status_label.pack(side="right")
        
        # Title Input
        title_frame = ttk.Frame(right_panel)
        title_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(title_frame, text="Title:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.grammar_title_var = tk.StringVar()
        ttk.Entry(title_frame, textvariable=self.grammar_title_var, font=("Arial", 11)).pack(fill="x", pady=(2, 0))
        
        # Tags Input
        tags_frame = ttk.Frame(right_panel)
        tags_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(tags_frame, text="Tags (comma separated):").pack(anchor="w")
        self.grammar_tags_var = tk.StringVar()
        ttk.Entry(tags_frame, textvariable=self.grammar_tags_var).pack(fill="x", pady=(2, 0))
        
        # AI Generation Button
        if self.ollama_available:
            ttk.Button(right_panel, text="✨ Generate Explanation from Title", command=self._generate_grammar_explanation).pack(anchor="w", pady=(0, 10))
        
        # Content Editor
        ttk.Label(right_panel, text="Content:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.grammar_content_text = scrolledtext.ScrolledText(right_panel, font=("Arial", 10))
        self.grammar_content_text.pack(fill="both", expand=True, pady=5)
        self._bind_mousewheel(self.grammar_content_text)
        
        # Action Buttons
        action_frame = ttk.Frame(right_panel)
        action_frame.pack(fill="x", pady=10)
        
        ttk.Button(action_frame, text="Save Entry", command=self._save_grammar_entry, style="Large.TButton").pack(side="left", padx=5)
        ttk.Button(action_frame, text="Delete", command=self._delete_grammar_entry).pack(side="left", padx=5)
        
        # Load entries
        self.current_grammar_id = None
        self._update_grammar_view()
        
    def _update_grammar_view(self):
        """Update the grammar treeview with folders and items."""
        if not hasattr(self, 'grammar_tree') or not self.grammar_tree.winfo_exists():
            return
            
        search = self.grammar_search_var.get()
        sort_by = self.grammar_sort_var.get()
        
        # Clear tree
        for item in self.grammar_tree.get_children():
            self.grammar_tree.delete(item)
            
        entries = self.study_manager.get_grammar_entries(search)
        colls = self.db.get_collections('grammar')
        
        # In-memory sorting
        if sort_by == "A-Z":
            entries = sorted(entries, key=lambda x: x['title'].lower())
        else:
            entries = sorted(entries, key=lambda x: x['updated_at'], reverse=True)
            
        self.grammar_entries = entries
        
        # Map folders
        folder_nodes = {}
        remaining = list(colls)
        max_iters = 5
        while remaining and max_iters > 0:
            max_iters -= 1
            for i in range(len(remaining)-1, -1, -1):
                c = remaining[i]
                parent = ""
                if c['parent_id'] and f"coll_{c['parent_id']}" in folder_nodes:
                    parent = f"coll_{c['parent_id']}"
                elif c['parent_id'] is None: parent = ""
                else: continue
                
                node = self.grammar_tree.insert(parent, "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)
                folder_nodes[f"coll_{c['id']}"] = node
                remaining.pop(i)
        
        for c in remaining:
            self.grammar_tree.insert("", "end", iid=f"coll_{c['id']}", text=f"📁 {c['name']}", open=True)

        # Insert Entries
        uncategorized_node = None
        for e in entries:
            parent = ""
            if e['collection_id'] and f"coll_{e['collection_id']}" in folder_nodes:
                parent = f"coll_{e['collection_id']}"
            else:
                if not uncategorized_node:
                    uncategorized_node = self.grammar_tree.insert("", "end", text="📦 Uncategorized", open=True)
                parent = uncategorized_node
            
            self.grammar_tree.insert(parent, "end", iid=f"gram_{e['id']}", text=f"📒 {e['title']}")

    def _on_grammar_coll_selected(self, event):
        """Handle selection in grammar folder tree."""
        # This method is no longer directly used for filtering, as _update_grammar_view handles the tree population.
        # However, it might be useful for future folder-specific actions.
        selection = self.grammar_tree.selection()
        if selection:
            res = selection[0]
            if res.startswith("coll_"):
                self.current_grammar_coll_id = int(res.split("_")[1])
            else:
                self.current_grammar_coll_id = res # "uncategorized" or "all" if we had those nodes
            # self._update_grammar_view() # No need to re-filter the view based on collection selection, the tree shows all.
                                        # This method might be repurposed for folder actions later.
            
    def _filter_grammar_entries(self, *args):
        """Filter entries based on search."""
        self._update_grammar_view()
        
    def _on_grammar_entry_selected(self, event):
        """Handle grammar entry selection from treeview."""
        selection = self.grammar_tree.selection()
        if not selection: return
        
        iid = selection[0]
        if not iid.startswith("gram_"): return
            
        gram_id = int(iid.split("_")[1])
        entry = next((e for e in self.grammar_entries if e['id'] == gram_id), None)
        if not entry: return
        
        self.current_grammar_id = entry['id']
        
        # Update editor fields
        self.grammar_title_var.set(entry['title'])
        self.grammar_tags_var.set(entry['tags'] or "")
        
        self.grammar_content_text.delete(1.0, tk.END)
        self.grammar_content_text.insert(tk.END, entry['content'])
        
        # Set status
        from datetime import datetime
        updated = datetime.fromisoformat(entry['updated_at']).strftime("%Y-%m-%d %H:%M")
        self.current_status_label.config(text=f"Last updated: {updated}")
        
    def _new_grammar_entry(self):
        """Clear editor for new entry."""
        self.current_grammar_id = None
        self.grammar_title_var.set("")
        self.grammar_tags_var.set("")
        self.grammar_content_text.delete(1.0, tk.END)
        self.grammar_tree.selection_remove(self.grammar_tree.selection()) # Clear treeview selection
        self.current_status_label.config(text="") # Clear status
        
    def _save_grammar_entry(self):
        """Save the current grammar entry."""
        title = self.grammar_title_var.get().strip()
        content = self.grammar_content_text.get(1.0, tk.END).strip()
        tags = self.grammar_tags_var.get().strip()
        
        if not title:
            messagebox.showwarning("Warning", "Title is required")
            return
            
        # Allow saving without content (e.g., for AI generation prep)
        
        if self.current_grammar_id:
            self.study_manager.update_grammar_entry(self.current_grammar_id, title, content, tags)
        else:
            self.current_grammar_id = self.study_manager.add_grammar_entry(title, content, tags)
            
        self._load_grammar_entries()
        
        # We don't call _new_grammar_entry() here because we want to keep editing the entry
        # or proceed to AI generation if that was the intent.
        
        msg = "Entry saved!" if content else "Entry created (Title only). You can now generate content!"
        messagebox.showinfo("Success", msg)
        
    def _delete_grammar_entry(self):
        """Delete the current grammar entry."""
        if not self.current_grammar_id:
            return
            
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this entry?"):
            self.study_manager.delete_grammar_entry(self.current_grammar_id)
            self._load_grammar_entries()
            self._new_grammar_entry()
            
    def _generate_grammar_explanation(self):
        """Generate grammar explanation using AI asynchronously."""
        if not self.current_grammar_id:
            # Auto-save if it's a new entry (requires title)
            topic = self.grammar_title_var.get().strip()
            if not topic:
                messagebox.showwarning("Warning", "Please enter a title (topic) first")
                return
            
            # Save to get an ID
            self._save_grammar_entry()
            
            # Check if save was successful (ID should be set now)
            if not self.current_grammar_id:
                return
            
        # Show loading/queued
        self.grammar_content_text.delete(1.0, tk.END)
        self.grammar_content_text.insert(tk.END, "⏳ Task Queued: Generating grammar explanation...")
        
        # Queue task
        task_id = self.study_manager.queue_generation_task(
            'grammar_explanation',
            self.current_grammar_id
        )
        
        # Track active task
        self.active_tasks[task_id] = {
            'type': 'grammar_explanation',
            'item_id': self.current_grammar_id
        }
        
        # Poke status checker
        self._check_queue_status()
            
            
    
    # ========== MANUAL ENTRY METHODS ==========

    def _add_manual_word_dialog(self, initial_word=None, initial_def=None):
        """Show dialog to manually add a word."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Word")
        dialog.geometry("400x350")
        
        ttk.Label(dialog, text="Add New Word", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Word
        ttk.Label(dialog, text="Word/Phrase (Target Language):").pack(anchor="w", padx=20)
        word_var = tk.StringVar(value=initial_word if initial_word else "")
        word_entry = ttk.Entry(dialog, textvariable=word_var, width=40)
        word_entry.pack(padx=20, pady=(0, 5))
        
        warning_label = ttk.Label(dialog, text="", foreground="orange", font=("Arial", 9, "italic"))
        warning_label.pack()
        
        def check_duplicate(*args):
            word = word_var.get().strip()
            if not word:
                warning_label.config(text="")
                return
            
            matches = self.db.find_flashcard_by_question(word)
            if matches:
                decks = list(set([m['deck_name'] for m in matches]))
                warning_label.config(text=f"⚠️ Already in deck(s): {', '.join(decks)}")
            else:
                warning_label.config(text="")
        
        word_var.trace("w", check_duplicate)
        if initial_word:
            check_duplicate()
        
        # Definition
        ttk.Label(dialog, text="Definition (Optional):").pack(anchor="w", padx=20)
        def_var = tk.StringVar(value=initial_def if initial_def else "")
        ttk.Entry(dialog, textvariable=def_var, width=40).pack(padx=20, pady=(0, 10))
        
        # Context
        ttk.Label(dialog, text="Context Sentence (Optional):").pack(anchor="w", padx=20)
        context_text = scrolledtext.ScrolledText(dialog, height=3, width=40, font=("Arial", 10))
        context_text.pack(padx=20, pady=(0, 20))
        
        def save():
            word = word_var.get().strip()
            definition = def_var.get().strip()
            context = context_text.get(1.0, tk.END).strip()
            
            if not word:
                messagebox.showerror("Error", "Word is required")
                return
                
            # Final duplicate check
            matches = self.db.find_flashcard_by_question(word)
            if matches:
                decks = list(set([m['deck_name'] for m in matches]))
                msg = f"'{word}' already exists in deck(s): {', '.join(decks)}.\n\nAdd it anyway?"
                if not messagebox.askyesno("Duplicate Word", msg):
                    return
            
            if not word:
                messagebox.showwarning("Required", "Please enter a word or phrase.")
                return
                
            success, message = self.study_manager.add_manual_word(word, context, definition)
            if success:
                messagebox.showinfo("Success", "Word added successfully!")
                dialog.destroy()
                self.show_words_view() # Refresh view
            else:
                messagebox.showerror("Error", message)
        
        ttk.Button(dialog, text="Save Word", command=save, style="Large.TButton").pack(pady=10)

    def _add_manual_sentence_dialog(self):
        """Show dialog to manually add a sentence."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Sentence")
        dialog.geometry("500x400")
        
        ttk.Label(dialog, text="Add New Sentence", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Sentence
        ttk.Label(dialog, text="Sentence (Target Language):").pack(anchor="w", padx=20)
        sent_text = scrolledtext.ScrolledText(dialog, height=5, width=50, font=("Arial", 10))
        sent_text.pack(padx=20, pady=(0, 15))
        
        # Notes
        ttk.Label(dialog, text="Notes (Optional):").pack(anchor="w", padx=20)
        notes_text = scrolledtext.ScrolledText(dialog, height=3, width=50, font=("Arial", 10))
        notes_text.pack(padx=20, pady=(0, 20))
        
        def save():
            sentence = sent_text.get(1.0, tk.END).strip()
            notes = notes_text.get(1.0, tk.END).strip()
            
            if not sentence:
                messagebox.showwarning("Required", "Please enter a sentence.")
                return
                
            success, message = self.study_manager.add_manual_sentence(sentence, notes)
            if success:
                messagebox.showinfo("Success", "Sentence added successfully!")
                dialog.destroy()
                self.show_sentences_view() # Refresh view
            else:
                messagebox.showerror("Error", message)
        
        ttk.Button(dialog, text="Save Sentence", command=save, style="Large.TButton").pack(pady=10)

    # ========== UTILITY METHODS ==========

    
    def _start_batch_words(self):
        """Start batch generation for missing word definitions."""
        if not messagebox.askyesno("Batch Process", "Generate definitions for all words that don't have one?"):
            return
            
        count = self.study_manager.batch_generate_words()
        if count > 0:
            messagebox.showinfo("Batch Started", f"Queued {count} words for generation.\nYou can continue using the app while they process.")
            self._check_queue_status()
        else:
            messagebox.showinfo("Batch Process", "No words found missing definitions.")

    def _start_batch_sentences(self):
        """Start batch generation for missing sentence explanations."""
        if not messagebox.askyesno("Batch Process", "Generate explanations for all sentences that don't have one?"):
            return
            
        count = self.study_manager.batch_generate_sentences()
        if count > 0:
            messagebox.showinfo("Batch Started", f"Queued {count} sentences for explanation.\nYou can continue using the app while they process.")
            self._check_queue_status()
        else:
            messagebox.showinfo("Batch Process", "No sentences found missing explanations.")

    # ========== STUDY COLLECTIONS MANAGEMENT ==========
    
    def _manage_study_colls(self, type_name):
        """Show dialog to manage folders for words/sentences/grammar."""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Manage {type_name.capitalize()} Folders")
        dialog.geometry("400x400")
        ttk.Label(dialog, text="Create New Folder:", font=("Arial", 10, "bold")).pack(pady=5)
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var, width=30).pack(pady=5)
        ttk.Label(dialog, text="Parent Folder (Optional):").pack(pady=5)
        colls = self.db.get_collections(type_name)
        options = ["None"] + [c['name'] for c in colls]
        coll_map = {c['name']: c['id'] for c in colls}
        parent_var = tk.StringVar(value="None")
        parent_combo = ttk.Combobox(dialog, textvariable=parent_var, values=options, state="readonly")
        parent_combo.pack(pady=5)
        
        def add_coll():
            name = name_var.get().strip()
            if name:
                parent_name = parent_var.get()
                p_id = coll_map.get(parent_name)
                self.db.create_collection(name, type_name, p_id)
                refresh_map = {'word': self._update_words_view, 'sentence': self._update_sentences_view, 'grammar': self._update_grammar_view}
                if type_name in refresh_map: refresh_map[type_name]()
                messagebox.showinfo("Success", "Folder created!")
                dialog.destroy()
        ttk.Button(dialog, text="Create", command=add_coll).pack(pady=10)
        ttk.Separator(dialog, orient="horizontal").pack(fill="x", pady=10)
        ttk.Label(dialog, text="Existing Folders:", font=("Arial", 10, "bold")).pack(pady=5)
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=20)
        lb = tk.Listbox(list_frame)
        lb.pack(side="left", fill="both", expand=True)
        for c in colls: lb.insert("end", f"{c['name']} (ID: {c['id']})")
        def delete_coll():
            sel = lb.curselection()
            if sel:
                item = lb.get(sel[0]); cid = int(item.split("ID: ")[1].rstrip(")"))
                if messagebox.askyesno("Confirm", "Delete folder?"):
                    self.db.delete_collection(cid)
                    refresh_map = {'word': self._update_words_view, 'sentence': self._update_sentences_view, 'grammar': self._update_grammar_view}
                    if type_name in refresh_map: refresh_map[type_name]()
                    dialog.destroy()
        ttk.Button(dialog, text="Delete Selected", command=delete_coll).pack(pady=10)

    def _move_item_to_coll(self, type_name):
        """Move selected item to a folder."""
        item_id = None
        tree = getattr(self, f"{type_name}s_tree" if type_name != 'grammar' else "grammar_tree", None)
        if not tree: return
        
        sel = tree.selection()
        if not sel:
            messagebox.showwarning("Warning", f"Please select a {type_name} first")
            return
            
        iid = sel[0]
        prefix = "word_" if type_name == 'word' else "sent_" if type_name == 'sentence' else "gram_"
        if not iid.startswith(prefix):
            messagebox.showwarning("Warning", "Please select an item, not a folder")
            return
        item_id = int(iid.split("_")[1])
            
        dialog = tk.Toplevel(self.root)
        dialog.title("Move to Folder")
        dialog.geometry("300x150")
        ttk.Label(dialog, text="Select Folder:").pack(pady=10)
        colls = self.db.get_collections(type_name)
        options = ["None (Uncategorized)"] + [c['name'] for c in colls]
        coll_map = {c['name']: c['id'] for c in colls}
        sel_var = tk.StringVar(value=options[0])
        combo = ttk.Combobox(dialog, textvariable=sel_var, values=options, state="readonly")
        combo.pack(pady=5)
        
        def save_move():
            coll_name = sel_var.get()
            coll_id = coll_map.get(coll_name)
            self.db.assign_to_collection(type_name, item_id, coll_id)
            refresh_map = {'word': self._update_words_view, 'sentence': self._update_sentences_view, 'grammar': self._update_grammar_view}
            if type_name in refresh_map: refresh_map[type_name]()
            messagebox.showinfo("Success", "Item moved!")
            dialog.destroy()
        ttk.Button(dialog, text="Move", command=save_move).pack(pady=10)

    def _export_study_items(self, item_type):
        """Export study items to JSON."""
        # Sanitize filename components
        timestamp = datetime.now().strftime('%Y%m%d')
        safe_type = re.sub(r'[\\/*?Internal:".<>|]', "", item_type)
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile=f"{safe_type}s_backup_{timestamp}.json",
            title=f"Export {item_type.capitalize()}s to JSON"
        )
        
        if file_path:
            try:
                if self.io_manager.export_study_items_to_json(item_type, file_path):
                    messagebox.showinfo("Success", f"All {item_type}s exported successfully!")
                else:
                    messagebox.showerror("Error", f"Failed to export {item_type}s.")
            except Exception as e:
                import traceback
                traceback.print_exc()
                messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    # ========== WRITING COMPOSITION LAB UI ==========

    def show_writing_lab_view(self):
        """Show the Writing Composition Lab view."""
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        
        # Header
        self._setup_standard_header(frame, "✍️ Writing Composition Lab", back_cmd=self.show_study_center)
        
        # Split view: Input (Top/Left) and Feedback (Bottom/Right)
        paned = tk.PanedWindow(frame, orient="vertical", sashrelief="raised", sashwidth=4)
        paned.pack(fill="both", expand=True, pady=10)
        
        # --- INPUT SECTION ---
        input_frame = ttk.Frame(paned)
        paned.add(input_frame, height=350)
        
        # Topic selection
        topic_header = ttk.Frame(input_frame)
        topic_header.pack(fill="x", pady=(0, 5))
        ttk.Label(topic_header, text="Topic & Background:", font=("Segoe UI", 12, "bold")).pack(side="left")
        
        topic_btn_frame = ttk.Frame(topic_header)
        topic_btn_frame.pack(side="right")
        ttk.Button(topic_btn_frame, text="🎲 AI Generate Topic", command=self._generate_writing_topic).pack(side="left", padx=5)
        
        self.topic_text = tk.Text(input_frame, height=4, font=("Segoe UI", 10), wrap="word")
        self.topic_text.pack(fill="x", pady=5)
        self.topic_text.insert("1.0", "Type your own topic here, or click 'AI Generate Topic'...")
        
        # Writing area
        ttk.Label(input_frame, text="Your Composition:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 5))
        self.writing_text = tk.Text(input_frame, font=("Segoe UI", 11), wrap="word", undo=True)
        self.writing_text.pack(fill="both", expand=True, pady=5)
        
        # Action buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=10)
        
        self.grade_btn = ttk.Button(btn_frame, text="🏆 Grade & Get Feedback", command=self._grade_writing, style="Accent.TButton")
        self.grade_btn.pack(side="right", padx=5)
        
        # --- FEEDBACK SECTION ---
        self.feedback_frame = ttk.Frame(paned)
        paned.add(self.feedback_frame)
        
        ttk.Label(self.feedback_frame, text="Feedback & Suggestions:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.feedback_display = scrolledtext.ScrolledText(self.feedback_frame, font=("Segoe UI", 10), wrap="word", state="disabled")
        self.feedback_display.pack(fill="both", expand=True, pady=5)
        
        # Suggestions bar (for adding to study lists)
        self.sugg_bar = ttk.Frame(self.feedback_frame)
        self.sugg_bar.pack(fill="x", pady=5)
        self.sugg_label = ttk.Label(self.sugg_bar, text="AI Suggestions: None", font=("Segoe UI", 9, "italic"))
        self.sugg_label.pack(side="left")

    def _generate_writing_topic(self):
        """Request a topic from AI."""
        self.topic_text.delete("1.0", "end")
        self.topic_text.insert("1.0", "Generating topic... please wait.")
        task_id = self.io_manager.study_manager.queue_generation_task('writing_topic', 0)
        self._check_writing_task(task_id, "topic")

    def _grade_writing(self):
        """Analyze and grade the user's writing."""
        topic = self.topic_text.get("1.0", "end").strip()
        writing = self.writing_text.get("1.0", "end").strip()
        
        if not writing or len(writing) < 10:
            messagebox.showwarning("Incomplete", "Please write a bit more before grading!")
            return
            
        self.feedback_display.configure(state="normal")
        self.feedback_display.delete("1.0", "end")
        self.feedback_display.insert("1.0", "Analyzing your writing... this may take a moment.")
        self.feedback_display.configure(state="disabled")
        self.grade_btn.configure(state="disabled")
        
        task_id = self.io_manager.study_manager.queue_generation_task('grade_writing', 0, user_writing=writing, topic=topic)
        self._check_writing_task(task_id, "grade")

    def _check_writing_task(self, task_id, task_type):
        """Poll for task completion."""
        status = self.io_manager.study_manager.get_task_status(task_id)
        if status['status'] == 'completed':
            if task_type == "topic":
                self.topic_text.delete("1.0", "end")
                self.topic_text.insert("1.0", status['result'])
            else:
                self._display_writing_feedback(status['result'], status.get('suggestions', {}))
                self.grade_btn.configure(state="normal")
        elif status['status'] == 'failed':
            error_msg = status.get('error', 'Unknown error')
            if task_type == "topic":
                self.topic_text.delete("1.0", "end")
                self.topic_text.insert("1.0", f"Error generating topic: {error_msg}")
            else:
                self.feedback_display.configure(state="normal")
                self.feedback_display.delete("1.0", "end")
                self.feedback_display.insert("1.0", f"Error grading writing: {error_msg}")
                self.feedback_display.configure(state="disabled")
                self.grade_btn.configure(state="normal")
        else:
            self.root.after(1000, lambda: self._check_writing_task(task_id, task_type))

    def _display_writing_feedback(self, feedback, suggestions):
        """Update the UI with results and suggestions."""
        self.feedback_display.configure(state="normal")
        self.feedback_display.delete("1.0", "end")
        self.feedback_display.insert("1.0", feedback)
        self.feedback_display.configure(state="disabled")
        
        # Clear suggestion buttons
        for widget in self.sugg_bar.winfo_children():
            widget.destroy()
            
        fc_count = len(suggestions.get('flashcards', []))
        gram_count = len(suggestions.get('grammar', []))
        
        if fc_count > 0 or gram_count > 0:
            msg = f"Suggestions: {fc_count} Words, {gram_count} Grammar Patterns"
            ttk.Label(self.sugg_bar, text=msg, font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            
            if fc_count > 0:
                ttk.Button(self.sugg_bar, text="➕ Add Words", 
                           command=lambda: self._add_suggestions(suggestions, 'word'),
                           style="Small.TButton").pack(side="left", padx=2)
            if gram_count > 0:
                ttk.Button(self.sugg_bar, text="➕ Add Grammar", 
                           command=lambda: self._add_suggestions(suggestions, 'grammar'),
                           style="Small.TButton").pack(side="left", padx=2)
        else:
            ttk.Label(self.sugg_bar, text="Suggestions: None found.", font=("Segoe UI", 9, "italic")).pack(side="left")

    def _add_suggestions(self, suggestions, type_name):
        """Batch add suggestions to the database."""
        db = self.io_manager.study_manager.db
        count = 0
        if type_name == 'word':
            for item in suggestions.get('flashcards', []):
                # We need to add to imported_content first, then definition
                content_id = db.add_imported_content(
                    'word', item['word'], url="Writing Lab Suggestion",
                    title="AI Suggestion", language=self.io_manager.study_manager.study_language
                )
                self.io_manager.study_manager.add_word_definition(
                    content_id, item['definition'], 
                    definition_language=self.io_manager.study_manager.native_language
                )
                count += 1
            messagebox.showinfo("Success", f"Added {count} words to your study list!")
        else:
            for item in suggestions.get('grammar', []):
                db.add_grammar_entry(
                    item['title'], item['explanation'], 
                    language=self.io_manager.study_manager.study_language
                )
                count += 1
            messagebox.showinfo("Success", f"Added {count} grammar patterns to your Grammar Book!")

    # ========== INTERACTIVE CHAT UI ==========

    def show_chat_dashboard(self):
        """Show the Chat Dashboard (Session List)."""
        self.clear_window()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        
        self._setup_standard_header(frame, "💬 Interactive Chat", back_cmd=self.show_study_center)
        
        # New Chat Controls
        ctrl_frame = ttk.Frame(frame)
        ctrl_frame.pack(fill="x", pady=10)
        
        ttk.Label(ctrl_frame, text="Start New Conversation:", font=("Segoe UI", 11)).pack(side="left")
        self.topic_entry = ttk.Entry(ctrl_frame, width=40)
        self.topic_entry.pack(side="left", padx=5)
        self.topic_entry.insert(0, "Ordering at a Cafe")
        
        ttk.Button(ctrl_frame, text="Start Chat", command=self._start_new_chat).pack(side="left")
        
        # Session List
        ttk.Label(frame, text="Recent Conversations:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(20, 5))
        
        # Scrollable list
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        sessions = self.io_manager.study_manager.get_chat_sessions()
        if not sessions:
            ttk.Label(scrollable_frame, text="No history yet. Start a new chat above!").pack(pady=20)
        
        for session in sessions:
            s_frame = ttk.Frame(scrollable_frame, relief="solid", borderwidth=1)
            s_frame.pack(fill="x", pady=5, padx=5)
            
            # Info
            info = f"{session['cur_topic']} ({session['study_language']})"
            date = session['last_updated'].split('T')[0]
            
            ttk.Label(s_frame, text=info, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=10)
            ttk.Label(s_frame, text=date, font=("Segoe UI", 9)).pack(side="left", padx=10)
            
            # Actions
            ttk.Button(s_frame, text="Continue", command=lambda s=session: self._open_chat_session(s['id'])).pack(side="right", padx=5)
            # Delete button could go here
            
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
    def _start_new_chat(self):
        """Create a session and open it."""
        topic = self.topic_entry.get().strip()
        if not topic:
            return
        session_id = self.io_manager.study_manager.create_chat_session(topic)
        self._open_chat_session(session_id)
        
    def _open_chat_session(self, session_id):
        """Open the Active Chat View."""
        self.active_session_id = session_id
        self.show_active_chat_view()
        
    def show_active_chat_view(self):
        """Display the active chat interface."""
        self.clear_window()
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)
        
        # Header
        session_info = next((s for s in self.io_manager.study_manager.get_chat_sessions() if s['id'] == self.active_session_id), None)
        title = f"💬 Chat: {session_info['cur_topic']}" if session_info else "Chat"
        self._setup_standard_header(frame, title, back_cmd=self.show_chat_dashboard)
        
        # Main Split: Chat (Left) vs Analysis Tabs (Right)
        paned = tk.PanedWindow(frame, orient="horizontal", sashrelief="raised", sashwidth=4)
        paned.pack(fill="both", expand=True, pady=5)
        
        # --- LEFT: CHAT AREA ---
        chat_frame = ttk.Frame(paned, width=600)
        paned.add(chat_frame)
        
        # Message History
        self.chat_display = scrolledtext.ScrolledText(chat_frame, state="disabled", wrap="word", font=("Segoe UI", 11))
        self.chat_display.pack(fill="both", expand=True, pady=(0, 10))
        self.chat_display.tag_config("user", foreground="#007ACC", justify="right")
        self.chat_display.tag_config("assistant", foreground="#2E7D32")
        self.chat_display.tag_config("system", foreground="gray", font=("Segoe UI", 9, "italic"))
        
        # Input Area
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill="x")
        
        self.chat_input = ttk.Entry(input_frame, font=("Segoe UI", 11))
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.chat_input.bind("<Return>", lambda e: self._send_message())
        
        self.send_btn = ttk.Button(input_frame, text="Send", command=self._send_message)
        self.send_btn.pack(side="right")
        
        # --- RIGHT: ANALYSIS TABS ---
        analysis_frame = ttk.Frame(paned, width=400)
        paned.add(analysis_frame)
        
        self.analysis_notebook = ttk.Notebook(analysis_frame)
        self.analysis_notebook.pack(fill="both", expand=True)
        
        # Tabs
        self.feedback_tab = scrolledtext.ScrolledText(self.analysis_notebook, wrap="word", font=("Segoe UI", 10))
        self.vocab_tab = scrolledtext.ScrolledText(self.analysis_notebook, wrap="word", font=("Segoe UI", 10))
        self.grammar_tab = scrolledtext.ScrolledText(self.analysis_notebook, wrap="word", font=("Segoe UI", 10))
        
        self.analysis_notebook.add(self.feedback_tab, text="Feedback")
        self.analysis_notebook.add(self.vocab_tab, text="Vocabulary")
        self.analysis_notebook.add(self.grammar_tab, text="Grammar")
        
        # Initial Load
        self._refresh_chat_history()
        
    def _refresh_chat_history(self):
        """Load messages from DB and render."""
        messages = self.io_manager.study_manager.get_chat_messages(self.active_session_id)
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == "user":
                self.chat_display.insert("end", f"You: {content}\n\n", "user")
            else:
                self.chat_display.insert("end", f"Tutor: {content}\n\n", "assistant")
                
            # Populate tabs with latest analysis (simple approach: show cumulative or latest)
            # User requested History for feedback => we can append formatted feedback
            if msg.get('analysis'):
                try:
                    import json
                    analysis = json.loads(msg['analysis'])
                    self._append_analysis(analysis)
                except:
                    pass
                    
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def _append_analysis(self, analysis):
        """Append analysis to tabs."""
        # Feedback
        if analysis.get('feedback'):
            self.feedback_tab.insert("end", f"--- New Feedback ---\n{analysis['feedback']}\n\n")
            self.feedback_tab.see("end")
            
        # Vocab (Parsing <flashcard> tags locally for display or using pre-parsed)
        if analysis.get('vocab_section'):
             self.vocab_tab.insert("end", f"{analysis['vocab_section']}\n\n")
             self.vocab_tab.see("end")
        
        # Grammar
        if analysis.get('grammar_section'):
             self.grammar_tab.insert("end", f"{analysis['grammar_section']}\n\n")
             self.grammar_tab.see("end")
             
    def _send_message(self):
        """Send message to AI."""
        msg = self.chat_input.get().strip()
        if not msg: 
            return
            
        self.chat_input.delete(0, "end")
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"You: {msg}\n\n", "user")
        self.chat_display.insert("end", "Tutor is typing...\n\n", "system")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
        
        # Get history for context
        current_msgs = self.io_manager.study_manager.get_chat_messages(self.active_session_id)
        
        # Queue task
        task_id = self.io_manager.study_manager.queue_generation_task(
            'chat_message', 
            0, # Item ID irrelevant here
            session_id=self.active_session_id,
            user_message=msg,
            current_history=current_msgs
        )
        self._check_chat_task(task_id)

    def _check_chat_task(self, task_id):
        """Poll for chat response."""
        status = self.io_manager.study_manager.get_task_status(task_id)
        if status['status'] == 'completed':
            # Remove "Tutor is typing..."
            self.chat_display.configure(state="normal")
            # Hacky delete last line: start of system tag to end
            # Better: just refresh full history
            self._refresh_chat_history()
            
        elif status['status'] == 'failed':
             self.chat_display.configure(state="normal")
             self.chat_display.insert("end", f"Error: {status.get('error')}\n\n", "system")
             self.chat_display.configure(state="disabled")
        else:
            self.root.after(500, lambda: self._check_chat_task(task_id))
    
    def clear_window(self):
        """Clear all widgets from the window."""
        for widget in self.root.winfo_children():
            widget.destroy()

    # ========== QUIZ UI ==========

    def show_quiz_setup(self):
        """Show quiz setup dialog."""
        self.clear_window()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        
        self._setup_standard_header(frame, "📝 Quiz Setup", back_cmd=self.show_study_center)
        
        # Source selection
        ttk.Label(frame, text="Select Source:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 5))
        
        source_frame = ttk.Frame(frame)
        source_frame.pack(fill="x", pady=5)
        
        self.quiz_source_type = tk.StringVar(value="deck")
        ttk.Radiobutton(source_frame, text="Flashcard Deck", variable=self.quiz_source_type, value="deck").pack(side="left", padx=10)
        ttk.Radiobutton(source_frame, text="Vocabulary Collection", variable=self.quiz_source_type, value="vocab").pack(side="left", padx=10)
        ttk.Radiobutton(source_frame, text="Grammar Collection", variable=self.quiz_source_type, value="grammar").pack(side="left", padx=10)
        
        # Specific source dropdown
        ttk.Label(frame, text="Choose specific item:", font=("Segoe UI", 11)).pack(anchor="w", pady=(15, 5))
        self.quiz_source_combo = ttk.Combobox(frame, state="readonly", width=50)
        self.quiz_source_combo.pack(fill="x", pady=5)
        
        # Update combo when radio changes
        self.quiz_source_type.trace_add("write", lambda *args: self._update_quiz_sources())
        self._update_quiz_sources()
        
        # Question count
        ttk.Label(frame, text="Number of Questions:", font=("Segoe UI", 11)).pack(anchor="w", pady=(15, 5))
        self.quiz_count_var = tk.IntVar(value=10)
        count_frame = ttk.Frame(frame)
        count_frame.pack(fill="x")
        ttk.Scale(count_frame, from_=5, to=50, variable=self.quiz_count_var, orient="horizontal").pack(side="left", fill="x", expand=True)
        ttk.Label(count_frame, textvariable=self.quiz_count_var, width=5).pack(side="right")
        
        # Difficulty
        ttk.Label(frame, text="Difficulty:", font=("Segoe UI", 11)).pack(anchor="w", pady=(15, 5))
        diff_frame = ttk.Frame(frame)
        diff_frame.pack(fill="x", pady=5)
        
        self.quiz_difficulty = tk.StringVar(value="medium")
        ttk.Radiobutton(diff_frame, text="Easy", variable=self.quiz_difficulty, value="easy").pack(side="left", padx=10)
        ttk.Radiobutton(diff_frame, text="Medium", variable=self.quiz_difficulty, value="medium").pack(side="left", padx=10)
        ttk.Radiobutton(diff_frame, text="Hard", variable=self.quiz_difficulty, value="hard").pack(side="left", padx=10)
        
        # Start button
        ttk.Button(frame, text="Start Quiz", command=self._start_quiz, style="Accent.TButton").pack(pady=20)
        
    def _update_quiz_sources(self):
        """Update source dropdown based on selection."""
        source_type = self.quiz_source_type.get()
        cursor = self.db.conn.cursor()
        
        if source_type == "deck":
            cursor.execute("SELECT id, name FROM decks ORDER BY name")
            items = [(f"{row[1]}", row[0]) for row in cursor.fetchall()]
        elif source_type == "vocab":
            cursor.execute("SELECT id, name FROM collections WHERE type = 'word' ORDER BY name")
            items = [(row[0], row[1]) for row in cursor.fetchall()]
        else:  # grammar
            cursor.execute("SELECT id, name FROM collections WHERE type = 'grammar' ORDER BY name")
            items = [(row[0], row[1]) for row in cursor.fetchall()]
        
        if not items:
            items = [("No items available", -1)]
            
        self.quiz_source_combo['values'] = [item[0] for item in items]
        self.quiz_source_ids = {item[0]: item[1] for item in items}
        if items:
            self.quiz_source_combo.current(0)
            
    def _start_quiz(self):
        """Generate quiz and start."""
        source_name = self.quiz_source_combo.get()
        source_id = self.quiz_source_ids.get(source_name, -1)
        
        if source_id == -1:
            messagebox.showwarning("No Source", "Please select a valid source.")
            return
            
        source_type = self.quiz_source_type.get()
        count = self.quiz_count_var.get()
        difficulty = self.quiz_difficulty.get()
        
        # Generate quiz
        session_id = self.quiz_manager.generate_quiz(source_type, source_id, count, difficulty)
        
        if session_id == -1:
            messagebox.showerror("Error", "No items found to quiz on.")
            return
            
        self.current_quiz_session = session_id
        self.show_quiz_view()
        
    def show_quiz_view(self):
        """Display quiz questions."""
        self.clear_window()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        
        # Get questions
        self.quiz_questions = self.quiz_manager.get_quiz_questions(self.current_quiz_session)
        self.current_question_index = 0
        
        # Header
        self._setup_standard_header(frame, "📝 Quiz", back_cmd=self.show_study_center)
        
        # Question counter
        self.question_counter_label = ttk.Label(frame, text="", font=("Segoe UI", 11))
        self.question_counter_label.pack(pady=10)
        
        # Question text
        self.question_label = ttk.Label(frame, text="", font=("Segoe UI", 13, "bold"), wraplength=600)
        self.question_label.pack(pady=20)
        
        # Answer choices
        self.quiz_answer = tk.StringVar()
        choices_frame = ttk.Frame(frame)
        choices_frame.pack(fill="both", expand=True, pady=20)
        
        self.choice_buttons = {}
        for letter in ['A', 'B', 'C', 'D']:
            btn_frame = ttk.Frame(choices_frame)
            btn_frame.pack(fill="x", pady=5)
            
            rb = ttk.Radiobutton(btn_frame, text="", variable=self.quiz_answer, value=letter)
            rb.pack(side="left", padx=5)
            self.choice_buttons[letter] = ttk.Label(btn_frame, text="", font=("Segoe UI", 11), wraplength=500)
            self.choice_buttons[letter].pack(side="left", fill="x", expand=True)
        
        # Next button
        self.next_button = ttk.Button(frame, text="Next", command=self._submit_quiz_answer, style="Accent.TButton")
        self.next_button.pack(pady=20)
        
        # Load first question
        self._load_quiz_question()
        
    def _load_quiz_question(self):
        """Load current question into UI."""
        if self.current_question_index >= len(self.quiz_questions):
            return
            
        q = self.quiz_questions[self.current_question_index]
        total = len(self.quiz_questions)
        
        self.question_counter_label.config(text=f"Question {self.current_question_index + 1} of {total}")
        self.question_label.config(text=q['question_text'])
        
        # Load choices
        for letter in ['A', 'B', 'C', 'D']:
            choice_text = q[f'choice_{letter.lower()}']
            self.choice_buttons[letter].config(text=choice_text)
        
        # Reset selection
        self.quiz_answer.set("")
        
        # Update button text
        if self.current_question_index == len(self.quiz_questions) - 1:
            self.next_button.config(text="Finish")
        else:
            self.next_button.config(text="Next")
            
    def _submit_quiz_answer(self):
        """Submit answer and move to next."""
        answer = self.quiz_answer.get()
        if not answer:
            messagebox.showwarning("No Answer", "Please select an answer.")
            return
            
        # Submit answer
        q = self.quiz_questions[self.current_question_index]
        self.quiz_manager.submit_answer(q['id'], answer)
        
        # Move to next
        self.current_question_index += 1
        
        if self.current_question_index < len(self.quiz_questions):
            self._load_quiz_question()
        else:
            # Quiz complete
            self.show_quiz_results()
            
    def show_quiz_results(self):
        """Show quiz results."""
        self.clear_window()
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill="both", expand=True)
        
        self._setup_standard_header(frame, "📝 Quiz Results", back_cmd=self.show_study_center)
        
        # Calculate score
        results = self.quiz_manager.calculate_score(self.current_quiz_session)
        
        # Score display
        score_frame = ttk.Frame(frame, relief="solid", borderwidth=2)
        score_frame.pack(fill="x", pady=20, padx=50)
        
        ttk.Label(score_frame, text=f"Score: {results['score']}%", font=("Segoe UI", 24, "bold")).pack(pady=20)
        ttk.Label(score_frame, text=f"{results['correct']} / {results['total']} correct", font=("Segoe UI", 14)).pack(pady=10)
        
        # Question review
        ttk.Label(frame, text="Review:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(20, 10))
        
        # Scrollable review
        review_frame = ttk.Frame(frame)
        review_frame.pack(fill="both", expand=True)
        
        canvas = tk.Canvas(review_frame)
        scrollbar = ttk.Scrollbar(review_frame, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)
        
        scrollable.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add questions
        questions = self.quiz_manager.get_quiz_questions(self.current_quiz_session)
        for i, q in enumerate(questions, 1):
            q_frame = ttk.Frame(scrollable, relief="groove", borderwidth=1)
            q_frame.pack(fill="x", pady=5, padx=5)
            
            # Status icon
            icon = "✓" if q['is_correct'] else "✗"
            color = "green" if q['is_correct'] else "red"
            
            ttk.Label(q_frame, text=f"{icon} Q{i}: {q['question_text']}", 
                     foreground=color, font=("Segoe UI", 10, "bold")).pack(anchor="w", padx=10, pady=5)
            
            ttk.Label(q_frame, text=f"Your answer: {q['user_answer']} - {q[f'choice_{q['user_answer'].lower()}']}",
                     font=("Segoe UI", 9)).pack(anchor="w", padx=20)
            
            if not q['is_correct']:
                ttk.Label(q_frame, text=f"Correct answer: {q['correct_answer']} - {q[f'choice_{q['correct_answer'].lower()}']}",
                         foreground="green", font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=2)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Action buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=20)
        ttk.Button(btn_frame, text="Take Another Quiz", command=self.show_quiz_setup).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Return to Study Center", command=self.show_study_center).pack(side="left", padx=5)

    def on_close(self):
        """Return to main menu."""
        self.root.quit()
