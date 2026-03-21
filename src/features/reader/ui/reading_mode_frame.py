"""
Reading Mode UI Frame for Tkinter GUI.

Provides a user-friendly interface for importing, browsing, and reading content
with AI-powered assistance including word lookups, sentence explanations, and
vocabulary extraction.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import os
import re
from typing import Optional, Dict, List
from datetime import datetime

from src.core.database import FlashcardDatabase
from src.core.localization import tr
from src.features.reader.content_manager import ContentManager
from src.features.reader.reading_assistant import ReadingAssistant
from src.features.reader.analytics_engine import AnalyticsEngine
from src.features.reader.library import ReadingLibrary
from src.features.reader.annotations import AnnotationManager
from src.features.mining.ui.mining_view import SentenceMiningView
from src.features.reader.embedding_worker import EmbeddingWorker
from src.services.dictionary.dictionary_manager import DictionaryEngine


class ReadingModeFrame(ttk.Frame):
    """Main frame for the Reading Mode feature."""
    
    def __init__(self, parent, controller, study_manager, db: FlashcardDatabase, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        self.embedded = embedded
        
        # Initialize reading mode components
        self.content_manager = ContentManager(db)
        self.reading_assistant = ReadingAssistant(study_manager, db)
        self.analytics_engine = AnalyticsEngine(db)
        self.library = ReadingLibrary(db)
        self.annotation_manager = AnnotationManager(db)
        
        # Local Dictionary Engine
        self.dict_engine = DictionaryEngine()
        
        # Background worker for sentence embeddings
        self.embedding_worker = EmbeddingWorker(db)
        self.embedding_worker.start()
        
        # State
        self.current_session_id = None
        self.current_content = None
        
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the main UI with tabs for different reading mode features."""
        # Main Header with Back Button (Global for all tabs)
        from src.core.ui_utils import setup_standard_header
        self.main_header = setup_standard_header(
            self, tr("lbl_reading_mode", "Reading Mode"), 
            back_cmd=self._go_back_to_dashboard
        )
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Tab 1: Import Content
        self.import_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.import_tab, text=tr("btn_import", "📥 Import Content"))
        self._setup_import_tab()
        
        # Tab 2: Reading Library
        self.library_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.library_tab, text=tr("lbl_library", "📚 My Library"))
        self._setup_library_tab()
        
        # Tab 3: Active Reading Session
        self.reading_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.reading_tab, text=tr("lbl_reading", "📖 Read"))
        self._setup_reading_tab()
        
        # Tab 4: Sentence Mining
        self.mining_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.mining_tab, text=tr("lbl_mining", "⛏️ Mine Sentences"))
        
        # Sub-header for Mining Tab
        mining_header = ttk.Frame(self.mining_tab)
        mining_header.pack(fill="x", padx=5, pady=5)
        ttk.Button(mining_header, text=tr("btn_back", "← Back to Library"), 
                  command=lambda: self.notebook.select(1)).pack(side="left", padx=5)
        
        self.mining_view = SentenceMiningView(self.mining_tab, self.db, self.study_manager, embedded=True)
        self.mining_view.pack(fill="both", expand=True)
        
        # Tab 5: Statistics
        self.stats_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_tab, text=tr("lbl_statistics", "📊 Statistics"))
        self._setup_stats_tab()
    
    def _setup_import_tab(self):
        """Set up the import content tab."""
        # Title
        ttk.Label(self.import_tab, text=tr("msg_import_content", "Import Content for Reading"), 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Legal disclaimer
        disclaimer_frame = ttk.LabelFrame(self.import_tab, text=tr("lbl_legal", "⚖️ Legal Notice"), padding=10)
        disclaimer_frame.pack(fill="x", padx=10, pady=10)
        
        disclaimer_text = tr("msg_reading_legal", 
            "You are responsible for ensuring you have legal rights to import and use any content. "
            "This includes:\n"
            "✓ Content you created yourself\n"
            "✓ Public domain works\n"
            "✓ Content with explicit permission\n"
            "✗ Copyrighted material without permission\n"
            "✗ Commercial use of imported content")
        
        ttk.Label(disclaimer_frame, text=disclaimer_text, wraplength=600, justify="left").pack()
        
        # Import options
        options_frame = ttk.LabelFrame(self.import_tab, text=tr("lbl_import_options", "Import Options"), padding=10)
        options_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Paste content
        ttk.Label(options_frame, text=tr("lbl_paste_content", "Paste Content:"), font=("Arial", 11, "bold")).pack(anchor="w", pady=(10, 5))
        
        paste_frame = ttk.Frame(options_frame)
        paste_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        ttk.Label(paste_frame, text=tr("lbl_title", "Title:")).grid(row=0, column=0, sticky="w", pady=5)
        self.paste_title_var = tk.StringVar()
        ttk.Entry(paste_frame, textvariable=self.paste_title_var, width=40).grid(row=0, column=1, sticky="ew", padx=5)
        
        ttk.Label(paste_frame, text=tr("lbl_content", "Content:")).grid(row=1, column=0, sticky="nw", pady=5)
        self.paste_content_text = scrolledtext.ScrolledText(paste_frame, height=8, width=50)
        self.paste_content_text.grid(row=1, column=1, sticky="nsew", padx=5)
        
        paste_frame.columnconfigure(1, weight=1)
        paste_frame.rowconfigure(1, weight=1)
        
        ttk.Button(paste_frame, text=tr("btn_import", "Import from Paste"), 
                  command=self._import_from_paste).grid(row=2, column=1, sticky="e", pady=10)
        
        # File import
        ttk.Label(options_frame, text=tr("lbl_import_file", "Import from File:"), 
                 font=("Arial", 11, "bold")).pack(anchor="w", pady=(20, 5))
        
        file_frame = ttk.Frame(options_frame)
        file_frame.pack(fill="x", padx=10, pady=5)
        
        self.file_path_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path_var, state="readonly", width=40).pack(side="left", fill="x", expand=True)
        ttk.Button(file_frame, text=tr("btn_browse", "Browse..."), 
                  command=self._browse_file).pack(side="left", padx=5)
        
        ttk.Button(file_frame, text=tr("btn_import", "Import File"), 
                  command=self._import_from_file).pack(side="left", padx=5)
        
        # Attestation checkbox
        self.attestation_var = tk.BooleanVar()
        ttk.Checkbutton(options_frame, text=tr("msg_legal_attestation", 
            "I confirm I have legal rights to import and use this content"),
            variable=self.attestation_var).pack(anchor="w", padx=10, pady=10)
    
    def _setup_library_tab(self):
        """Set up the reading library tab."""
        ttk.Label(self.library_tab, text=tr("lbl_reading_library", "Your Reading Library"), 
                 font=("Arial", 14, "bold")).pack(pady=10)
        
        # Filter frame
        filter_frame = ttk.LabelFrame(self.library_tab, text=tr("lbl_filter", "Filter"), padding=10)
        filter_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(filter_frame, text=tr("lbl_status", "Status:")).pack(side="left", padx=5)
        self.status_var = tk.StringVar(value="all")
        ttk.Combobox(filter_frame, textvariable=self.status_var, 
                    values=["all", "in_progress", "completed", "not_started"],
                    state="readonly", width=15).pack(side="left", padx=5)
        
        ttk.Label(filter_frame, text=tr("lbl_difficulty", "Difficulty:")).pack(side="left", padx=5)
        self.difficulty_var = tk.StringVar(value="all")
        ttk.Combobox(filter_frame, textvariable=self.difficulty_var,
                    values=["all", "easy", "medium", "hard"],
                    state="readonly", width=15).pack(side="left", padx=5)
        
        ttk.Button(filter_frame, text=tr("btn_refresh", "Refresh"), 
                  command=self._refresh_library).pack(side="left", padx=5)
        
        # Library list
        list_frame = ttk.Frame(self.library_tab)
        list_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Create treeview for sessions
        columns = ("title", "progress", "difficulty", "last_read")
        self.library_tree = ttk.Treeview(list_frame, columns=columns, height=15)
        self.library_tree.column("#0", width=0, stretch=tk.NO)
        self.library_tree.column("title", anchor=tk.W, width=250)
        self.library_tree.column("progress", anchor=tk.CENTER, width=100)
        self.library_tree.column("difficulty", anchor=tk.CENTER, width=100)
        self.library_tree.column("last_read", anchor=tk.CENTER, width=150)
        
        self.library_tree.heading("#0", text="", anchor=tk.W)
        self.library_tree.heading("title", text=tr("lbl_title", "Title"), anchor=tk.W)
        self.library_tree.heading("progress", text=tr("lbl_progress", "Progress"), anchor=tk.CENTER)
        self.library_tree.heading("difficulty", text=tr("lbl_difficulty", "Difficulty"), anchor=tk.CENTER)
        self.library_tree.heading("last_read", text=tr("lbl_last_read", "Last Read"), anchor=tk.CENTER)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.library_tree.yview)
        self.library_tree.configure(yscroll=scrollbar.set)
        
        self.library_tree.pack(side=tk.LEFT, fill="both", expand=True)
        scrollbar.pack(side=tk.RIGHT, fill="y")
        
        # Bind double-click to open session
        self.library_tree.bind("<Double-1>", self._on_library_item_double_click)
        
        # Action buttons
        button_frame = ttk.Frame(self.library_tab)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(button_frame, text=tr("btn_read", "📖 Read"), 
                  command=self._open_selected_session).pack(side="left", padx=5)
        ttk.Button(button_frame, text=tr("btn_delete", "🗑️ Delete"), 
                  command=self._delete_selected_session).pack(side="left", padx=5)
        ttk.Button(button_frame, text=tr("btn_export", "📤 Export Vocabulary"), 
                  command=self._export_vocabulary).pack(side="left", padx=5)
        
        self._refresh_library()
    
    def _setup_reading_tab(self):
        """Set up the active reading session tab."""
        # Header with back button - make it prominent at top left
        header_frame = ttk.Frame(self.reading_tab)
        header_frame.pack(fill="x", padx=5, pady=5, side="top")
        
        # Back button - prominent at top left
        back_button = ttk.Button(header_frame, text=tr("btn_back", "← Back to Library"), 
                                command=self._back_to_library)
        back_button.pack(side="left", padx=5, pady=5)
        
        ttk.Label(header_frame, text=tr("lbl_active_reading", "Active Reading Session"), 
                 font=("Arial", 14, "bold")).pack(side="left", padx=20)
        
        # Session info
        info_frame = ttk.LabelFrame(self.reading_tab, text=tr("lbl_session_info", "Session Info"), padding=10)
        info_frame.pack(fill="x", padx=10, pady=10)
        
        self.session_title_label = ttk.Label(info_frame, text=tr("msg_no_session", "No active session"))
        self.session_title_label.pack(anchor="w")
        
        self.session_progress_label = ttk.Label(info_frame, text="")
        self.session_progress_label.pack(anchor="w")
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(info_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=5)
        
        # Content display
        content_frame = ttk.LabelFrame(self.reading_tab, text=tr("lbl_content", "Content"), padding=10)
        content_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.content_display = scrolledtext.ScrolledText(content_frame, height=15, width=80, state="disabled")
        self.content_display.pack(fill="both", expand=True)
        
        # Bind scroll events to track progress
        self.content_display.bind("<MouseWheel>", self._on_content_scroll)
        self.content_display.bind("<Button-4>", self._on_content_scroll)  # Linux scroll up
        self.content_display.bind("<Button-5>", self._on_content_scroll)  # Linux scroll down
        
        # Reading tools
        tools_frame = ttk.LabelFrame(self.reading_tab, text=tr("lbl_reading_tools", "Reading Tools"), padding=10)
        tools_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(tools_frame, text=tr("lbl_word_lookup", "Word Lookup:")).pack(side="left", padx=5)
        self.lookup_word_var = tk.StringVar()
        ttk.Entry(tools_frame, textvariable=self.lookup_word_var, width=20).pack(side="left", padx=5)
        ttk.Button(tools_frame, text=tr("btn_define", "Define"), 
                  command=self._lookup_word).pack(side="left", padx=5)
        
        ttk.Button(tools_frame, text=tr("btn_add_bookmark", "🔖 Bookmark"), 
                  command=self._add_bookmark).pack(side="left", padx=5)
        ttk.Button(tools_frame, text=tr("btn_add_note", "📝 Note"), 
                  command=self._add_note).pack(side="left", padx=5)
        
        # Statistics
        stats_frame = ttk.LabelFrame(self.reading_tab, text=tr("lbl_session_stats", "Session Statistics"), padding=10)
        stats_frame.pack(fill="x", padx=10, pady=10)
        
        self.stats_display_label = ttk.Label(stats_frame, text="")
        self.stats_display_label.pack(anchor="w")
    
    def _setup_stats_tab(self):
        """Set up the statistics tab."""
        # Header for Stats Tab
        stats_header = ttk.Frame(self.stats_tab)
        stats_header.pack(fill="x", padx=5, pady=5)
        ttk.Button(stats_header, text=tr("btn_back", "← Back to Library"), 
                  command=lambda: self.notebook.select(1)).pack(side="left", padx=5)
                  
        ttk.Label(stats_header, text=tr("lbl_reading_statistics", "Reading Statistics"), 
                 font=("Arial", 14, "bold")).pack(side="left", padx=20)
        
        # Aggregate stats
        stats_frame = ttk.LabelFrame(self.stats_tab, text=tr("lbl_overall_stats", "Overall Statistics"), padding=10)
        stats_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.stats_text = scrolledtext.ScrolledText(stats_frame, height=20, width=80, state="disabled")
        self.stats_text.pack(fill="both", expand=True)
        
        ttk.Button(self.stats_tab, text=tr("btn_refresh", "Refresh"), 
                  command=self._refresh_stats).pack(pady=10)
        
        self._refresh_stats()
    
    # --- Import Methods ---
    
    def _import_from_paste(self):
        """Import content from pasted text."""
        title = self.paste_title_var.get().strip()
        content = self.paste_content_text.get("1.0", "end-1c").strip()
        
        if not title:
            messagebox.showwarning(tr("title_warning", "Warning"), tr("msg_enter_title", "Please enter a title"))
            return
        
        if not content:
            messagebox.showwarning(tr("title_warning", "Warning"), tr("msg_enter_content", "Please enter content"))
            return
        
        if not self.attestation_var.get():
            messagebox.showwarning(tr("title_warning", "Warning"), 
                                  tr("msg_confirm_legal", "Please confirm you have legal rights to this content"))
            return
        
        try:
            language = self.study_manager.study_language
            session_id = self.content_manager.import_from_paste(
                content=content,
                title=title,
                language=language,
                user_attestation=True
            )
            
            messagebox.showinfo(tr("title_success", "Success"), 
                               tr("msg_content_imported", "Content imported successfully!"))
            
            # Clear form
            self.paste_title_var.set("")
            self.paste_content_text.delete("1.0", "end")
            self.attestation_var.set(False)
            
            # Refresh library
            self._refresh_library()
            
        except Exception as e:
            messagebox.showerror(tr("title_error", "Error"), 
                                tr("msg_import_failed", "Failed to import content: {error}", error=str(e)))
    
    def _browse_file(self):
        """Browse for a file to import."""
        filename = filedialog.askopenfilename(
            title=tr("title_select_file", "Select a file to import"),
            filetypes=[
                (tr("lbl_all_supported", "All Supported Files"), "*.txt *.md *.html *.htm *.epub *.pdf *.docx"),
                (tr("lbl_text_files", "Text Files"), "*.txt *.md"),
                ("HTML", "*.html *.htm"),
                ("EPUB", "*.epub"),
                ("PDF", "*.pdf"),
                ("Word", "*.docx"),
                (tr("lbl_all_files", "All Files"), "*.*")
            ]
        )
        if filename:
            self.file_path_var.set(filename)
    
    def _import_from_file(self):
        """Import content from a file."""
        file_path = self.file_path_var.get().strip()
        
        if not file_path:
            messagebox.showwarning(tr("title_warning", "Warning"), tr("msg_select_file", "Please select a file"))
            return
        
        if not self.attestation_var.get():
            messagebox.showwarning(tr("title_warning", "Warning"), 
                                  tr("msg_confirm_legal", "Please confirm you have legal rights to this content"))
            return
        
        try:
            title = os.path.splitext(os.path.basename(file_path))[0]
            language = self.study_manager.study_language
            
            session_id = self.content_manager.import_from_file(
                file_path=file_path,
                title=title,
                language=language,
                user_attestation=True
            )
            
            messagebox.showinfo(tr("title_success", "Success"), 
                               tr("msg_content_imported", "Content imported successfully!"))
            
            # Clear form
            self.file_path_var.set("")
            self.attestation_var.set(False)
            
            # Refresh library
            self._refresh_library()
            
        except Exception as e:
            messagebox.showerror(tr("title_error", "Error"), 
                                tr("msg_import_failed", "Failed to import content: {error}", error=str(e)))
    
    # --- Library Methods ---
    
    def _refresh_library(self):
        """Refresh the reading library display."""
        try:
            # Clear existing items
            for item in self.library_tree.get_children():
                self.library_tree.delete(item)
            
            # Get user ID (use 1 as default for now)
            user_id = 1
            
            # Get all sessions
            sessions = self.library.get_all_sessions(user_id)
            
            # Filter by status and difficulty
            status_filter = self.status_var.get()
            difficulty_filter = self.difficulty_var.get()
            
            for session in sessions:
                # Apply filters
                if status_filter != "all":
                    completion = session.get('completion_percentage', 0)
                    if status_filter == "completed" and completion < 100:
                        continue
                    elif status_filter == "in_progress" and (completion == 0 or completion == 100):
                        continue
                    elif status_filter == "not_started" and completion > 0:
                        continue
                
                if difficulty_filter != "all" and session.get('difficulty_rating') != difficulty_filter:
                    continue
                
                # Format data
                title = session.get('title', 'Untitled')
                progress = f"{session.get('completion_percentage', 0):.0f}%"
                difficulty = session.get('difficulty_rating', 'unknown')
                last_read = session.get('last_read_at', 'Never')
                
                # Add to tree
                self.library_tree.insert("", "end", values=(title, progress, difficulty, last_read))
        
        except Exception as e:
            messagebox.showerror(tr("title_error", "Error"), 
                                tr("msg_refresh_failed", "Failed to refresh library: {error}", error=str(e)))
    
    def _on_library_item_double_click(self, event):
        """Handle double-click on library item."""
        self._open_selected_session()
    
    def _open_selected_session(self):
        """Open the selected reading session."""
        selection = self.library_tree.selection()
        if not selection:
            messagebox.showwarning(tr("title_warning", "Warning"), tr("msg_select_session", "Please select a session"))
            return
        
        try:
            # Get session info from tree
            item = selection[0]
            values = self.library_tree.item(item, "values")
            title = values[0] if values else None
            
            if not title:
                messagebox.showerror(tr("title_error", "Error"), "Could not retrieve session information")
                return
            
            # Find the session ID by title
            user_id = 1
            sessions = self.library.get_all_sessions(user_id)
            session_id = None
            
            for session in sessions:
                if session.get('title') == title:
                    session_id = session.get('id')
                    break
            
            if not session_id:
                messagebox.showerror(tr("title_error", "Error"), 
                                    tr("msg_session_not_found", "Session not found in database"))
                return
            
            # Load the session content
            self.current_session_id = session_id
            session = self.content_manager.get_reading_session(session_id, user_id)
            
            if not session:
                messagebox.showerror(tr("title_error", "Error"), 
                                    tr("msg_session_load_failed", "Failed to load session"))
                return
            
            # Store current content
            self.current_content = session
            
            # Update session info display
            self.session_title_label.config(
                text=f"Title: {session.get('title', 'Untitled')}"
            )
            
            completion = session.get('completion_percentage', 0)
            self.session_progress_label.config(
                text=f"Progress: {completion:.0f}% | Words: {session.get('word_count', 0)} | Difficulty: {session.get('difficulty_rating', 'unknown')}"
            )
            
            # Populate Mining tab first so known words are loaded
            self.mining_view.process_text(session.get('content', ''))
            
            # Display content interactively in Read tab
            self._render_interactive_content(session.get('content', ''))
            
            # Update statistics
            self._update_session_stats(session_id)
            
            # Initialize progress bar with current progress
            completion = session.get('completion_percentage', 0)
            self.progress_var.set(completion)
            
            # Switch to reading tab
            self.notebook.select(2)  # Reading tab index
            
        except Exception as e:
            messagebox.showerror(tr("title_error", "Error"), 
                                tr("msg_session_load_failed", "Failed to load session: {error}", error=str(e)))
    
    def _delete_selected_session(self):
        """Delete the selected reading session."""
        selection = self.library_tree.selection()
        if not selection:
            messagebox.showwarning(tr("title_warning", "Warning"), tr("msg_select_session", "Please select a session"))
            return
        
        if messagebox.askyesno(tr("title_confirm", "Confirm"), 
                              tr("msg_confirm_delete", "Are you sure you want to delete this session?")):
            try:
                # Get session info from tree
                item = selection[0]
                values = self.library_tree.item(item, "values")
                title = values[0] if values else None
                
                if not title:
                    return
                
                # Find the session ID by title
                user_id = 1
                sessions = self.library.get_all_sessions(user_id)
                session_id = None
                
                for session in sessions:
                    if session.get('title') == title:
                        session_id = session.get('id')
                        break
                
                if session_id:
                    self.content_manager.delete_reading_session(session_id)
                
                self._refresh_library()
                messagebox.showinfo(tr("title_success", "Success"), tr("msg_deleted", "Session deleted"))
            except Exception as e:
                messagebox.showerror(tr("title_error", "Error"), 
                                    tr("msg_delete_failed", "Failed to delete session: {error}", error=str(e)))
    
    def _export_vocabulary(self):
        """Export vocabulary from selected session."""
        selection = self.library_tree.selection()
        if not selection:
            messagebox.showwarning(tr("title_warning", "Warning"), tr("msg_select_session", "Please select a session"))
            return
        
        messagebox.showinfo(tr("title_info", "Info"), 
                           tr("msg_export_vocab", "Vocabulary export feature coming soon!"))
    
    # --- Reading Methods ---
    
    def _lookup_word(self):
        """Look up a word definition."""
        word = self.lookup_word_var.get().strip()
        if not word:
            messagebox.showwarning(tr("title_warning", "Warning"), tr("msg_enter_word", "Please enter a word"))
            return
        
        try:
            # Get definition from reading assistant
            definition = self.reading_assistant.get_word_definition(
                word=word,
                sentence_context="",
                paragraph_context="",
                language=self.study_manager.study_language
            )
            
            messagebox.showinfo(tr("title_definition", "Definition"), 
                               f"{word}\n\n{definition.get('definition', 'No definition found')}")
        except Exception as e:
            messagebox.showerror(tr("title_error", "Error"), 
                                tr("msg_lookup_failed", "Failed to look up word: {error}", error=str(e)))
    
    def _add_bookmark(self):
        """Add a bookmark to the current position."""
        messagebox.showinfo(tr("title_info", "Info"), tr("msg_bookmark_added", "Bookmark added!"))
    
    def _add_note(self):
        """Add a note to the current position."""
        messagebox.showinfo(tr("title_info", "Info"), tr("msg_note_added", "Note added!"))
    
    def _back_to_library(self):
        """Return to the library tab and save progress."""
        if self.current_session_id:
            try:
                # Save current progress before switching tabs
                self._save_reading_progress()
            except Exception as e:
                messagebox.showerror(tr("title_error", "Error"), 
                                    tr("msg_save_progress_failed", "Failed to save progress: {error}", error=str(e)))
        
        # Switch back to library tab
        self.notebook.select(1)  # Library tab index

    def _go_back_to_dashboard(self):
        """Clean up and return to the main dashboard."""
        if hasattr(self.controller, 'show_home'):
            self._save_reading_progress()
            self.controller.show_home()

    def _render_interactive_content(self, content: str):
        """Render text with clickable words and sentences, applying dynamic styling if enabled."""
        from src.core.config import config
        
        self.content_display.config(state="normal")
        self.content_display.delete("1.0", "end")
        
        # Map IDs to actual text data
        self._interactive_map = {
            'words': {},
            'sentences': {}
        }
        
        # Configure tags
        self.content_display.tag_configure("clickable", foreground="black")
        if config.enable_dynamic_styling:
            self.content_display.tag_configure("known_word", foreground="green")
            self.content_display.tag_configure("unknown_word", foreground="#D4AF37") # Gold
            
            # Difficulty Highlighting Tags (Subtle backgrounds)
            self.content_display.tag_configure("i0", background="#e8f5e9")      # Very subtle green
            self.content_display.tag_configure("i1", background="#fff3e0")      # Very subtle orange
            self.content_display.tag_configure("i2plus", background="#ffebee")  # Very subtle red
            
        self.content_display.tag_configure("word_hover", background="lightblue")
        self.content_display.tag_configure("sentence_hover", background="#f0f0f0")
        
        # Bind events
        self.content_display.tag_bind("clickable", "<Button-1>", self._on_text_click)
        self.content_display.tag_bind("clickable", "<Enter>", self._on_text_enter)
        self.content_display.tag_bind("clickable", "<Leave>", self._on_text_leave)
        
        known_words = set()
        ignored_words = set()
        if config.enable_dynamic_styling and hasattr(self.mining_view, 'miner'):
            # Use the miner's helpers to get the word sets for the current language
            lang = self.mining_view.lang_code
            known_words = self.mining_view.miner._load_known_vocabulary(lang)
            ignored_words = self.mining_view.miner._load_ignored_vocabulary(lang)
            
        # Get sentences from parser to find boundaries
        sentences = self.content_manager.parser.segment_sentences(content)
        
        # This is a simplified regex approach that handles basic word boundaries
        # and non-word characters (spaces, punctuation).
        word_pattern = re.compile(r'(\w+)|([^\w]+)', re.UNICODE)
        
        sentence_idx = 0
        word_idx = 0
        
        # Use simple string search to track sentence spans for the whole text
        # Since segment_sentences strips whitespace, we match loosely
        current_sentence = sentences[sentence_idx] if sentences else None
        sentence_accum = ""
        
        for match in word_pattern.finditer(content):
            word = match.group(1)
            non_word = match.group(2)
            
            tags = ["clickable"]
            
            if current_sentence:
                sentence_tag = f"sen_{sentence_idx}"
                tags.append(sentence_tag)
                self._interactive_map['sentences'][sentence_tag] = current_sentence
                
                # Sentence Difficulty Highlighting
                diff_tag = None
                if config.enable_dynamic_styling and hasattr(self.mining_view, 'mining_result') and self.mining_view.mining_result:
                    matching_s = next((s for s in self.mining_view.mining_result.sentences if s.text.strip() == current_sentence.strip()), None)
                    if matching_s:
                        if matching_s.level == 0:
                            diff_tag = "i0"
                        elif matching_s.level == 1:
                            diff_tag = "i1"
                        else:
                            diff_tag = "i2plus"
                
                if word:
                    word_tag = f"wrd_{word_idx}"
                    tags.append(word_tag)
                    self._interactive_map['words'][word_tag] = word
                    word_idx += 1
                    
                    if config.enable_dynamic_styling:
                        word_lower = word.lower()
                        # Check if it's a number/punctuation or in the known/ignored sets
                        is_non_word = not any(c.isalpha() for c in word)
                        
                        if word_lower in known_words or word_lower in ignored_words or is_non_word:
                            tags.append("known_word")
                        else:
                            tags.append("unknown_word")
                    
                    if diff_tag:
                        tags.append(diff_tag)
                        
                    self.content_display.insert("end", word, tuple(tags))
                    sentence_accum += word
                elif non_word:
                    if diff_tag:
                        tags.append(diff_tag)
                    self.content_display.insert("end", non_word, tuple(tags))
                    sentence_accum += non_word
                
            # Check if we've completed the current sentence
            if current_sentence and current_sentence.strip() in sentence_accum.strip():
                sentence_idx += 1
                current_sentence = sentences[sentence_idx] if sentence_idx < len(sentences) else None
                sentence_accum = ""
                
        self.content_display.config(state="disabled")

    def _on_text_enter(self, event):
        """Highlight word or sentence on hover."""
        index = self.content_display.index(f"@{event.x},{event.y}")
        tags = self.content_display.tag_names(index)
        
        # Highlight word
        for tag in tags:
            if tag.startswith("wrd_"):
                self.content_display.tag_add("word_hover", f"{tag}.first", f"{tag}.last")
                break

    def _on_text_leave(self, event):
        """Remove highlight on leave."""
        self.content_display.tag_remove("word_hover", "1.0", "end")

    def _on_text_click(self, event):
        """Handle clicking a word or sentence."""
        index = self.content_display.index(f"@{event.x},{event.y}")
        tags = self.content_display.tag_names(index)
        
        clicked_word = None
        clicked_word_tag = None
        clicked_sentence = None
        
        for tag in tags:
            if tag.startswith("wrd_"):
                clicked_word = self._interactive_map['words'].get(tag)
                clicked_word_tag = tag
            elif tag.startswith("sen_"):
                clicked_sentence = self._interactive_map['sentences'].get(tag)
                
        if clicked_word:
            self._show_interactive_popup(event.x_root, event.y_root, clicked_word, clicked_sentence, clicked_word_tag)

    def _show_interactive_popup(self, x, y, word, sentence, word_tag):
        """Show an inline popup for word definition and study actions."""
        popup = tk.Menu(self, tearoff=0)
        
        # 1. Local dictionary lookup (Fast)
        lang_code = self.study_manager.study_language
        try:
            results = self.dict_engine.lookup(word.lower(), lang_code)
            if results:
                # Use the first definition for the summary line
                first_res = results[0]
                def_text = first_res['definitions'][0] if first_res['definitions'] else "No definition found"
                if len(def_text) > 40:
                    def_text = def_text[:37] + "..."
                popup.add_command(label=f"📖 {word}: {def_text}", state="disabled")
            else:
                # Fallback to ReadingAssistant (may use LLM)
                definition = self.reading_assistant.get_word_definition(
                    word=word,
                    sentence_context=sentence or "",
                    paragraph_context="",
                    language=lang_code
                )
                def_text = definition.get('definition', 'No definition found')
                if len(def_text) > 40:
                    def_text = def_text[:37] + "..."
                popup.add_command(label=f"📖 {word} (fallback): {def_text}", state="disabled")
        except Exception as e:
            print(f"Lookup error: {e}")
            
        popup.add_separator()

        # 2. Vocabulary Actions
        popup.add_command(
            label="✓ Mark as Known", 
            command=lambda: self._add_specific_item_to_study(word, "mark_known")
        )
        popup.add_command(
            label="➕ Add Word to Study", 
            command=lambda: self._add_specific_item_to_study(word, "word", context=sentence)
        )
        
        # 3. Sentence Actions
        if sentence:
            popup.add_separator()
            popup.add_command(
                label="➕ Add Sentence to Study", 
                command=lambda: self._add_specific_item_to_study(sentence, "sentence")
            )
            
        popup.tk_popup(x, y)

    def _add_specific_item_to_study(self, item, item_type, context=None):
        """Add a word or sentence to the study manager or mark as known."""
        lang_code = self.study_manager.study_language
        
        try:
            if item_type == "mark_known":
                self.db.add_known_word(item, lang_code, source="reading_mode")
                if hasattr(self.controller, 'show_status'):
                    self.controller.show_status(f"Marked '{item}' as known.")
                
            elif item_type == "word":
                self.db.add_imported_content(
                    content_type="word",
                    content=item,
                    url="reading_mode",
                    title="Reading Mode Import",
                    language=lang_code,
                    context=context or ""
                )
                if hasattr(self.controller, 'show_status'):
                    self.controller.show_status(f"Added '{item}' to Study Center.")
                
            elif item_type == "sentence":
                self.db.add_imported_content(
                    content_type="sentence",
                    content=item,
                    url="reading_mode",
                    title="Reading Mode Import",
                    language=lang_code,
                    tags="reading"
                )
                if hasattr(self.controller, 'show_status'):
                    self.controller.show_status("Sentence added to Study Center.")

            # Update styling if needed
            if item_type in ["mark_known", "word"]:
                # Notify mining view to refresh known set
                if hasattr(self, 'mining_view'):
                    self.mining_view.update_mining_levels()
                
                # Re-render interactive content to update tags/styling
                # Note: self.content_display is the widget name
                content = self.content_display.get("1.0", "end-1c")
                
                # Keep scroll position
                yview = self.content_display.yview()
                self._render_interactive_content(content)
                self.content_display.yview_moveto(yview[0])

        except Exception as e:
            messagebox.showerror("Error", f"Failed to perform action: {e}")
    
    def _save_reading_progress(self):
        """Save the current reading progress to the database."""
        if not self.current_session_id:
            return
        
        try:
            # Calculate progress based on scroll position
            content_length = len(self.content_display.get("1.0", "end-1c"))
            if content_length == 0:
                completion_percentage = 0.0
            else:
                # Get current scroll position
                scroll_position = self.content_display.yview()[0]
                completion_percentage = min(100.0, scroll_position * 100.0)
            
            # Update progress in database
            user_id = 1  # TODO: Get from current user context
            self.content_manager.update_reading_progress(
                session_id=self.current_session_id,
                current_position=0,  # Character position tracking can be enhanced later
                completion_percentage=completion_percentage,
                time_spent_seconds=0  # Time tracking can be enhanced with session timer
            )
        except Exception as e:
            # Log error but don't fail - progress saving is non-critical
            print(f"Warning: Failed to save reading progress: {e}")
    
    def _on_content_scroll(self, event=None):
        """Handle content scroll events to update progress bar."""
        if not self.current_session_id or not self.current_content:
            return
        
        try:
            # Get scroll position (0.0 to 1.0)
            scroll_position = self.content_display.yview()[0]
            
            # Calculate completion percentage
            completion_percentage = min(100.0, scroll_position * 100.0)
            
            # Update progress bar
            self.progress_var.set(completion_percentage)
            
            # Update progress label
            self.session_progress_label.config(
                text=f"Progress: {completion_percentage:.0f}% | Words: {self.current_content.get('word_count', 0)} | Difficulty: {self.current_content.get('difficulty_rating', 'unknown')}"
            )
        except Exception as e:
            print(f"Warning: Failed to update progress display: {e}")
    
    # --- Statistics Methods ---
    
    def _update_session_stats(self, session_id):
        """Update session statistics display."""
        try:
            stats = self.analytics_engine.get_session_statistics(session_id)
            
            stats_text = f"""
Session Statistics
==================

Time Spent: {stats.get('time_spent_seconds', 0) // 60} minutes
Words Read: {stats.get('words_read', 0)}
Reading Speed: {stats.get('wpm', 0):.0f} WPM
Lookups: {stats.get('lookup_count', 0)}
Comprehension: {stats.get('comprehension_score', 0):.0%}
Completion: {stats.get('completion_percentage', 0):.0f}%
            """
            
            self.stats_display_label.config(text=stats_text)
        except Exception as e:
            self.stats_display_label.config(text=f"Error loading stats: {str(e)}")
    
    def _refresh_stats(self):
        """Refresh the statistics display."""
        try:
            user_id = 1
            stats = self.analytics_engine.get_aggregate_statistics(user_id)
            
            stats_text = f"""
Reading Statistics
==================

Total Sessions: {stats.get('total_sessions', 0)}
Total Reading Time: {stats.get('total_time_seconds', 0) // 60} minutes
Average WPM: {stats.get('average_wpm', 0):.0f}
Total Words Learned: {stats.get('total_words_learned', 0)}

Current Streak: {stats.get('current_streak', 0)} days
Longest Streak: {stats.get('longest_streak', 0)} days
            """
            
            self.stats_text.config(state="normal")
            self.stats_text.delete("1.0", "end")
            self.stats_text.insert("1.0", stats_text)
            self.stats_text.config(state="disabled")
        
        except Exception as e:
            self.stats_text.config(state="normal")
            self.stats_text.delete("1.0", "end")
            self.stats_text.insert("1.0", f"Error loading statistics: {str(e)}")
            self.stats_text.config(state="disabled")
    
    def on_show(self):
        """Called when frame is shown."""
        self._refresh_library()
        self._refresh_stats()
        if hasattr(self, 'mining_view'):
            self.mining_view.on_show()
    
    def on_hide(self):
        """Called when frame is hidden."""
        if hasattr(self, 'embedding_worker'):
            self.embedding_worker.stop()
