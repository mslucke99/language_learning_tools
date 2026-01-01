"""
Study GUI - Interface for studying imported words and sentences.
Allows users to add/edit definitions for words and view/generate explanations for sentences.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
from study_manager import StudyManager
from database import FlashcardDatabase
from ollama_integration import is_ollama_available
from datetime import datetime


class StudyGUI:
    """GUI for the study features."""
    
    def __init__(self, root, db: FlashcardDatabase, study_manager: StudyManager):
        """Initialize the Study GUI."""
        self.root = root
        self.db = db
        self.study_manager = study_manager
        self.ollama_available = is_ollama_available()
        
        # Setup styles
        self.style = ttk.Style()
        self.style.configure("TButton", font=("Arial", 10), padding=8)
        self.style.configure("Large.TButton", font=("Arial", 11), padding=12)
        self.style.configure("TLabel", font=("Arial", 10))
        self.style.configure("Title.TLabel", font=("Arial", 14, "bold"))
        self.style.configure("Subtitle.TLabel", font=("Arial", 12, "bold"))
        
        self.current_word_id = None
        self.current_sentence_id = None
    
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
        title = ttk.Label(frame, text="Study Center", style="Title.TLabel")
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
        
        # Main buttons frame
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x", pady=20)
        
        # Study words button
        words_btn = ttk.Button(
            btn_frame,
            text="📚 Study Words",
            command=self.show_words_view,
            style="Large.TButton"
        )
        words_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        # Study sentences button
        sentences_btn = ttk.Button(
            btn_frame,
            text="📖 Study Sentences",
            command=self.show_sentences_view,
            style="Large.TButton"
        )
        sentences_btn.pack(side="left", padx=10, fill="both", expand=True)

        # Grammar Book button
        grammar_btn = ttk.Button(
            btn_frame,
            text="📒 Grammar Book",
            command=self.show_grammar_book_view,
            style="Large.TButton"
        )
        grammar_btn.pack(side="left", padx=10, fill="both", expand=True)
        
        # Back button
        back_btn = ttk.Button(frame, text="← Back to Main Menu", command=self.on_close)
        back_btn.pack(pady=10)

    
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
        
        # 2. Main Content (Split View)
        paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
        paned_window.pack(fill="both", expand=True)
        
        # LEFT PANE: Word List
        left_pane = ttk.Frame(paned_window)
        paned_window.add(left_pane, weight=1)
        
        ttk.Label(left_pane, text="Select Word", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        list_scroll = ttk.Scrollbar(left_pane)
        list_scroll.pack(side="right", fill="y")
        
        self.words_listbox = tk.Listbox(left_pane, yscrollcommand=list_scroll.set, height=12, font=("Arial", 10))
        self.words_listbox.pack(side="left", fill="both", expand=True)
        list_scroll.config(command=self.words_listbox.yview)
        
        self.words_listbox.bind('<<ListboxSelect>>', self._on_word_selected)
        self._bind_mousewheel(self.words_listbox)
        
        # Populate List
        words = self.study_manager.get_imported_words()
        self.words_data = words
        if words:
            for word_data in words:
                status = "✓" if word_data['has_definition'] else "○"
                display = f"{status} {word_data['word']}"
                self.words_listbox.insert(tk.END, display)
        else:
            self.words_listbox.insert(tk.END, "(No words found)")
        
        # RIGHT PANE: Detail & Editor
        right_pane = ttk.Frame(paned_window, padding=(10, 0, 0, 0))
        paned_window.add(right_pane, weight=3)
        
        # Selected Word Display (Always Visible)
        self.word_label = ttk.Label(right_pane, text="(Select a word)", style="Subtitle.TLabel")
        self.word_label.pack(anchor="w", pady=(0, 10))
        
        # TABS for Details
        self.notebook = ttk.Notebook(right_pane)
        self.notebook.pack(fill="both", expand=True)
        
        # TAB 1: Definition
        tab_def = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_def, text="Definition")
        
        self.word_definition_text = scrolledtext.ScrolledText(tab_def, font=("Arial", 10), wrap="word")
        self.word_definition_text.pack(fill="both", expand=True, pady=(0, 10))
        self._bind_mousewheel(self.word_definition_text)
        
        # AI Actions Row
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
        
        # Examples Section
        ex_frame = ttk.LabelFrame(notes_paned, text="Examples", padding="5")
        notes_paned.add(ex_frame, weight=1)
        self.word_examples_text = scrolledtext.ScrolledText(ex_frame, height=5, font=("Arial", 10), wrap="word")
        self.word_examples_text.pack(fill="both", expand=True)
        self._bind_mousewheel(self.word_examples_text)
        
        # AI Button for Examples inside the frame
        if self.ollama_available:
             ttk.Button(ex_frame, text="💬 Generate Examples", command=lambda: self._generate_word_content('examples')).pack(anchor="e", pady=2)
        
        # Notes Section
        notes_frame = ttk.LabelFrame(notes_paned, text="My Notes", padding="5")
        notes_paned.add(notes_frame, weight=1)
        self.word_notes_text = scrolledtext.ScrolledText(notes_frame, height=5, font=("Arial", 10), wrap="word")
        self.word_notes_text.pack(fill="both", expand=True)
        self._bind_mousewheel(self.word_notes_text)
        
        ttk.Button(tab_notes, text="Save Changes", command=self._save_word_definition).pack(anchor="e", pady=5)
    
    def _on_word_selected(self, event):
        """Handle word selection from listbox."""
        selection = self.words_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        word_data = self.words_data[index]
        self.current_word_id = word_data['id']
        
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
        Generate word content (definition, explanation, or examples) using Ollama.
        
        Args:
            content_type: 'definition', 'explanation', or 'examples'
        """
        if not self.current_word_id:
            messagebox.showwarning("Warning", "Please select a word first")
            return
        
        # Show loading
        original_text = self.word_definition_text.get(1.0, tk.END)
        self.word_definition_text.delete(1.0, tk.END)
        
        type_display = {
            'definition': 'definition',
            'explanation': 'explanation',
            'examples': 'examples'
        }
        
        self.word_definition_text.insert(tk.END, f"🔄 Generating {type_display.get(content_type, content_type)}...")
        self.root.update()
        
        success, result = self.study_manager.generate_word_content(
            self.current_word_id,
            content_type=content_type,
            language='native'
        )
        
        self.word_definition_text.delete(1.0, tk.END)
        if success:
            self.word_definition_text.insert(tk.END, result)
        else:
            self.word_definition_text.insert(tk.END, original_text)
            messagebox.showerror("Error", result)
    
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
        
        # 2. Main Content (Split View)
        paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
        paned_window.pack(fill="both", expand=True)
        
        # LEFT PANE: Sentence List
        left_pane = ttk.Frame(paned_window)
        paned_window.add(left_pane, weight=1)
        
        ttk.Label(left_pane, text="Select Sentence", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        list_scroll = ttk.Scrollbar(left_pane)
        list_scroll.pack(side="right", fill="y")
        
        self.sentences_listbox = tk.Listbox(left_pane, font=("Arial", 9), yscrollcommand=list_scroll.set, width=30)
        self.sentences_listbox.pack(side="left", fill="both", expand=True)
        list_scroll.config(command=self.sentences_listbox.yview)
        
        self.sentences_listbox.bind('<<ListboxSelect>>', self._on_sentence_selected)
        self._bind_mousewheel(self.sentences_listbox)
        
        # Populate List
        sentences = self.study_manager.get_imported_sentences()
        self.sentences_data = sentences
        if sentences:
            for sent_data in sentences:
                status = "✓" if sent_data['has_explanation'] else "○"
                display = f"{status} {sent_data['sentence'][:40]}..."
                self.sentences_listbox.insert(tk.END, display)
        else:
            self.sentences_listbox.insert(tk.END, "(No sentences found)")
        
        # RIGHT PANE: Details & Editor
        right_pane = ttk.Frame(paned_window, padding=(10, 0, 0, 0))
        paned_window.add(right_pane, weight=3)
        
        # Target Sentence Display (Always Visible)
        target_frame = ttk.LabelFrame(right_pane, text="Target Sentence", padding="10")
        target_frame.pack(fill="x", pady=(0, 10))
        
        self.sentence_display_text = scrolledtext.ScrolledText(target_frame, height=3, font=("Arial", 11), wrap="word", state="disabled")
        self.sentence_display_text.pack(fill="both", expand=True)
        self._bind_mousewheel(self.sentence_display_text)
        
        # TABS for Details
        self.notebook = ttk.Notebook(right_pane)
        self.notebook.pack(fill="both", expand=True)
        
        # TAB 1: Explanation (AI)
        tab_explanation = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_explanation, text="AI Explanation")
        
        self.sentence_explanation_text = scrolledtext.ScrolledText(tab_explanation, font=("Arial", 10), wrap="word")
        self.sentence_explanation_text.pack(fill="both", expand=True, pady=(0, 10))
        self._bind_mousewheel(self.sentence_explanation_text)
        
        # AI Actions Row
        ai_action_frame = ttk.Frame(tab_explanation)
        ai_action_frame.pack(fill="x")
        
        if self.ollama_available:
            ttk.Button(ai_action_frame, text="✨ Generate/Regenerate Explanation", command=self._generate_sentence_explanation_multi).pack(side="left")
        
        ttk.Button(ai_action_frame, text="Save Changes", command=self._save_sentence_explanation).pack(side="right")

        # TAB 2: Notes & Grammar
        tab_notes = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_notes, text="My Notes & Grammar")
        
        # Split Notes into Grammar (Top) and Personal (Bottom) or Left/Right
        notes_paned = ttk.PanedWindow(tab_notes, orient="vertical")
        notes_paned.pack(fill="both", expand=True)
        
        # Grammar Note Section
        grammar_frame = ttk.LabelFrame(notes_paned, text="Grammar Notes", padding="5")
        notes_paned.add(grammar_frame, weight=1)
        self.sentence_grammar_text = scrolledtext.ScrolledText(grammar_frame, height=5, font=("Arial", 10), wrap="word")
        self.sentence_grammar_text.pack(fill="both", expand=True)
        self._bind_mousewheel(self.sentence_grammar_text)
        
        # Personal Note Section
        personal_frame = ttk.LabelFrame(notes_paned, text="Personal Notes", padding="5")
        notes_paned.add(personal_frame, weight=1)
        self.sentence_notes_text = scrolledtext.ScrolledText(personal_frame, height=5, font=("Arial", 10), wrap="word")
        self.sentence_notes_text.pack(fill="both", expand=True)
        self._bind_mousewheel(self.sentence_notes_text)
        
        ttk.Button(tab_notes, text="Save Notes", command=self._save_sentence_explanation).pack(anchor="e", pady=5)
        
        # TAB 3: Talk to AI (Follow-up)
        tab_chat = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(tab_chat, text="Ask AI")
        
        chat_history_frame = ttk.Frame(tab_chat)
        chat_history_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.followup_history_text = scrolledtext.ScrolledText(chat_history_frame, state="disabled", font=("Arial", 10), wrap="word")
        self.followup_history_text.pack(side="left", fill="both", expand=True)
        chat_scroll = ttk.Scrollbar(chat_history_frame, command=self.followup_history_text.yview)
        chat_scroll.pack(side="right", fill="y")
        self.followup_history_text.config(yscrollcommand=chat_scroll.set)
        self._bind_mousewheel(self.followup_history_text)
        
        input_frame = ttk.Frame(tab_chat)
        input_frame.pack(fill="x")
        
        self.followup_question_text = scrolledtext.ScrolledText(input_frame, height=3, font=("Arial", 10), wrap="word")
        self.followup_question_text.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self._bind_mousewheel(self.followup_question_text)
        
        ttk.Button(input_frame, text="Ask", command=self._ask_followup_question).pack(side="right")
        ttk.Button(tab_chat, text="Clear History", command=self._clear_followup_history).pack(anchor="w", pady=5)
        
        # TAB 4: Settings (Focus Areas)
        tab_settings = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(tab_settings, text="Settings")
        
        ttk.Label(tab_settings, text="Select Focus Areas for AI Generation:", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))
        
        self.focus_vars = {}
        for focus in ["grammar", "vocabulary", "context", "pronunciation", "all"]:
            self.focus_vars[focus] = tk.BooleanVar(value=(focus == 'all'))
            ttk.Checkbutton(tab_settings, text=focus.capitalize(), variable=self.focus_vars[focus]).pack(anchor="w", pady=2)
            
        self.current_sentence_explanation_id = None
    
    def _on_sentence_selected(self, event):
        """Handle sentence selection from listbox."""
        selection = self.sentences_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        sent_data = self.sentences_data[index]
        self.current_sentence_id = sent_data['id']
        
        # Update sentence display
        self.sentence_display_text.config(state="normal")
        self.sentence_display_text.delete(1.0, tk.END)
        self.sentence_display_text.insert(tk.END, sent_data['sentence'])
        self.sentence_display_text.config(state="disabled")
        
        # Load existing explanation
        explanation = self.study_manager.get_sentence_explanation(self.current_sentence_id)
        
        self.sentence_explanation_text.delete(1.0, tk.END)
        self.sentence_grammar_text.delete(1.0, tk.END)
        self.sentence_notes_text.delete(1.0, tk.END)
        
        # Reset checkboxes
        for focus in self.focus_vars:
            self.focus_vars[focus].set(False)
        
        # Clear follow-up question input and history
        self.followup_question_text.delete(1.0, tk.END)
        self.current_sentence_explanation_id = None
        
        if explanation:
            self.sentence_explanation_text.insert(tk.END, explanation['explanation'])
            self.sentence_grammar_text.insert(tk.END, explanation['grammar_notes'])
            self.sentence_notes_text.insert(tk.END, explanation['user_notes'])
            # Set checkbox for the focus area if stored
            if explanation.get('focus_area') and explanation['focus_area'] in self.focus_vars:
                self.focus_vars[explanation['focus_area']].set(True)
            
            # Store explanation ID for follow-ups
            self.current_sentence_explanation_id = explanation['id']
            
            # Load follow-up history
            self._load_followup_history()
        else:
            # Default to "all" if no explanation exists
            self.focus_vars['all'].set(True)
            # Clear follow-up history
            self.followup_history_text.config(state="normal")
            self.followup_history_text.delete(1.0, tk.END)
            self.followup_history_text.insert(tk.END, "(No explanation yet. Generate or enter an explanation first.)")
            self.followup_history_text.config(state="disabled")
    
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
        """Generate sentence explanation for multiple selected focus areas using Ollama."""
        if not self.current_sentence_id:
            messagebox.showwarning("Warning", "Please select a sentence first")
            return
        
        # Get selected focus areas from checkboxes
        selected_focus_areas = [focus for focus, var in self.focus_vars.items() if var.get()]
        
        if not selected_focus_areas:
            messagebox.showwarning("Warning", "Please select at least one focus area")
            return
        
        # Show loading
        original_text = self.sentence_explanation_text.get(1.0, tk.END)
        self.sentence_explanation_text.delete(1.0, tk.END)
        self.sentence_explanation_text.insert(tk.END, f"🔄 Generating explanations for {', '.join(selected_focus_areas)}...")
        self.root.update()
        
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
        
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)
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
        
        # 2. Main Content (Split View)
        paned_window = ttk.PanedWindow(main_frame, orient="horizontal")
        paned_window.pack(fill="both", expand=True)
        
        # LEFT PANE: Entry List
        left_pane = ttk.Frame(paned_window)
        paned_window.add(left_pane, weight=1)
        
        # Search Box
        search_frame = ttk.Frame(left_pane)
        search_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.grammar_search_var = tk.StringVar()
        self.grammar_search_var.trace("w", self._filter_grammar_entries)
        ttk.Entry(search_frame, textvariable=self.grammar_search_var).pack(side="left", fill="x", expand=True, padx=5)
        
        # List
        list_scroll = ttk.Scrollbar(left_pane)
        list_scroll.pack(side="right", fill="y")
        
        self.grammar_listbox = tk.Listbox(left_pane, font=("Arial", 10), yscrollcommand=list_scroll.set)
        self.grammar_listbox.pack(side="left", fill="both", expand=True)
        list_scroll.config(command=self.grammar_listbox.yview)
        
        self.grammar_listbox.bind('<<ListboxSelect>>', self._on_grammar_entry_selected)
        self._bind_mousewheel(self.grammar_listbox)
        
        # RIGHT PANE: Editor
        right_panel = ttk.LabelFrame(paned_window, text="Entry Editor", padding="15")
        paned_window.add(right_panel, weight=3)
        
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
        self._load_grammar_entries()
        
    def _load_grammar_entries(self):
        """Load grammar entries into listbox."""
        search = self.grammar_search_var.get()
        self.grammar_entries = self.study_manager.get_grammar_entries(search)
        
        self.grammar_listbox.delete(0, tk.END)
        for entry in self.grammar_entries:
            self.grammar_listbox.insert(tk.END, entry['title'])
            
    def _filter_grammar_entries(self, *args):
        """Filter entries based on search."""
        self._load_grammar_entries()
        
    def _on_grammar_entry_selected(self, event):
        """Handle selection of a grammar entry."""
        selection = self.grammar_listbox.curselection()
        if not selection:
            return
            
        index = selection[0]
        entry = self.grammar_entries[index]
        self.current_grammar_id = entry['id']
        
        self.grammar_title_var.set(entry['title'])
        self.grammar_tags_var.set(entry['tags'] or "")
        self.grammar_content_text.delete(1.0, tk.END)
        self.grammar_content_text.insert(tk.END, entry['content'])
        
    def _new_grammar_entry(self):
        """Clear editor for new entry."""
        self.current_grammar_id = None
        self.grammar_title_var.set("")
        self.grammar_tags_var.set("")
        self.grammar_content_text.delete(1.0, tk.END)
        self.grammar_listbox.selection_clear(0, tk.END)
        
    def _save_grammar_entry(self):
        """Save the current grammar entry."""
        title = self.grammar_title_var.get().strip()
        content = self.grammar_content_text.get(1.0, tk.END).strip()
        tags = self.grammar_tags_var.get().strip()
        
        if not title:
            messagebox.showwarning("Warning", "Title is required")
            return
            
        if not content:
            messagebox.showwarning("Warning", "Content is required")
            return
            
        if self.current_grammar_id:
            self.study_manager.update_grammar_entry(self.current_grammar_id, title, content, tags)
        else:
            self.study_manager.add_grammar_entry(title, content, tags)
            
        self._load_grammar_entries()
        self._new_grammar_entry()
        messagebox.showinfo("Success", "Entry saved!")
        
    def _delete_grammar_entry(self):
        """Delete the current grammar entry."""
        if not self.current_grammar_id:
            return
            
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this entry?"):
            self.study_manager.delete_grammar_entry(self.current_grammar_id)
            self._load_grammar_entries()
            self._new_grammar_entry()
            
    def _generate_grammar_explanation(self):
        """Generate grammar explanation using AI."""
        topic = self.grammar_title_var.get().strip()
        if not topic:
            messagebox.showwarning("Warning", "Please enter a title (topic) first")
            return
            
        self.grammar_content_text.delete(1.0, tk.END)
        self.grammar_content_text.insert(tk.END, "🔄 Generating explanation... Please wait.")
        self.root.update()
        
        success, content = self.study_manager.generate_grammar_explanation(topic)
        
        self.grammar_content_text.delete(1.0, tk.END)
        if success:
            self.grammar_content_text.insert(tk.END, content)
        else:
            self.grammar_content_text.insert(tk.END, f"Error: {content}")
            
            
    
    # ========== MANUAL ENTRY METHODS ==========

    def _add_manual_word_dialog(self):
        """Show dialog to manually add a word."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add New Word")
        dialog.geometry("400x350")
        
        ttk.Label(dialog, text="Add New Word", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Word
        ttk.Label(dialog, text="Word/Phrase (Target Language):").pack(anchor="w", padx=20)
        word_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=word_var, width=40).pack(padx=20, pady=(0, 10))
        
        # Definition
        ttk.Label(dialog, text="Definition (Optional):").pack(anchor="w", padx=20)
        def_var = tk.StringVar()
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

    
    def clear_window(self):
        """Clear all widgets from the window."""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def on_close(self):
        """Return to main menu."""
        self.root.quit()
