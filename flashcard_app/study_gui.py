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
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        # Title Frame
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill="x", pady=10)
        
        ttk.Label(title_frame, text="Study Words", style="Title.TLabel").pack(side="left")
        ttk.Button(title_frame, text="+ Add Word", command=self._add_manual_word_dialog).pack(side="right")
        
        # Get words
        words = self.study_manager.get_imported_words()
        
        if not words:
            ttk.Label(frame, text="No words yet. Import via extension or add manually above!").pack(pady=20)
            ttk.Button(frame, text="← Back", command=self.show_study_center).pack()
            return
        
        # Words listbox
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, pady=10)
        
        ttk.Label(list_frame, text="Select a word to view/edit definition:", font=("Arial", 10)).pack(anchor="w")
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.words_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=12, font=("Arial", 10))
        self.words_listbox.pack(side="left", fill="both", expand=True)
        self.words_listbox.bind('<<ListboxSelect>>', self._on_word_selected)
        scrollbar.config(command=self.words_listbox.yview)
        
        # Populate listbox
        for word_data in words:
            status = "✓" if word_data['has_definition'] else "○"
            display = f"{status} {word_data['word']}"
            self.words_listbox.insert(tk.END, display)
        
        self.words_data = words
        
        # Word detail frame (with scrolling)
        detail_frame = ttk.LabelFrame(frame, text="Word Definition Editor", padding="10")
        detail_frame.pack(fill="both", expand=True, pady=5)
        
        # Create a scrollable frame for the content
        canvas = tk.Canvas(detail_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(detail_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Word label
        self.word_label = ttk.Label(scrollable_frame, text="(Select a word)", style="Subtitle.TLabel")
        self.word_label.pack(pady=3)
        
        # Top section - Definition only
        ttk.Label(scrollable_frame, text="Definition:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 0))
        self.word_definition_text = scrolledtext.ScrolledText(scrollable_frame, height=5, font=("Arial", 10), wrap="word")
        self.word_definition_text.pack(fill="both", pady=3)
        
        # Bottom section - Side by side: Examples (left) and Notes (right)
        bottom_frame = ttk.Frame(scrollable_frame)
        bottom_frame.pack(fill="both", expand=True, pady=3)
        
        # Left side - Examples
        left_frame = ttk.LabelFrame(bottom_frame, text="Examples:", padding="5")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 3))
        
        self.word_examples_text = scrolledtext.ScrolledText(left_frame, height=3, font=("Arial", 9), wrap="word")
        self.word_examples_text.pack(fill="both", expand=True)
        
        # Right side - Notes
        right_frame = ttk.LabelFrame(bottom_frame, text="Notes:", padding="5")
        right_frame.pack(side="right", fill="both", expand=True, padx=(3, 0))
        
        self.word_notes_text = scrolledtext.ScrolledText(right_frame, height=3, font=("Arial", 9), wrap="word")
        self.word_notes_text.pack(fill="both", expand=True)
        
        # Generation and action buttons in scrollable area
        if self.ollama_available:
            gen_frame = ttk.LabelFrame(scrollable_frame, text="Generate Content:", padding="5")
            gen_frame.pack(fill="x", pady=5)
            
            ttk.Button(
                gen_frame,
                text="📋 Definition",
                command=lambda: self._generate_word_content('definition')
            ).pack(side="left", padx=3, pady=3)
            
            ttk.Button(
                gen_frame,
                text="📝 Explanation",
                command=lambda: self._generate_word_content('explanation')
            ).pack(side="left", padx=3, pady=3)
            
            ttk.Button(
                gen_frame,
                text="💬 Examples",
                command=lambda: self._generate_word_content('examples')
            ).pack(side="left", padx=3, pady=3)
        
        # Action buttons
        action_frame = ttk.Frame(scrollable_frame)
        action_frame.pack(fill="x", pady=8)
        
        ttk.Button(action_frame, text="Save", command=self._save_word_definition).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Clear", command=self._clear_word_form).pack(side="left", padx=5)
        
        # Navigation - outside scrollable area for easy access
        nav_frame = ttk.Frame(frame)
        nav_frame.pack(fill="x", pady=10, side="bottom")
        
        ttk.Button(nav_frame, text="← Back to Study Center", command=self.show_study_center).pack(side="left", padx=5)
    
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
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        # Title Frame
        title_frame = ttk.Frame(frame)
        title_frame.pack(fill="x", pady=10)
        
        ttk.Label(title_frame, text="Study Sentences", style="Title.TLabel").pack(side="left")
        ttk.Button(title_frame, text="+ Add Sentence", command=self._add_manual_sentence_dialog).pack(side="right")
        
        # Get sentences
        sentences = self.study_manager.get_imported_sentences()
        
        if not sentences:
            ttk.Label(frame, text="No sentences yet. Import via extension or add manually above!").pack(pady=20)
            ttk.Button(frame, text="← Back", command=self.show_study_center).pack()
            return
        
        # Sentences listbox
        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, pady=10)
        
        ttk.Label(list_frame, text="Select a sentence to view/edit explanation:", font=("Arial", 10)).pack(anchor="w")
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.sentences_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=10, font=("Arial", 9))
        self.sentences_listbox.pack(side="left", fill="both", expand=True)
        self.sentences_listbox.bind('<<ListboxSelect>>', self._on_sentence_selected)
        scrollbar.config(command=self.sentences_listbox.yview)
        
        # Populate listbox
        for sent_data in sentences:
            status = "✓" if sent_data['has_explanation'] else "○"
            display = f"{status} {sent_data['sentence'][:70]}..."
            self.sentences_listbox.insert(tk.END, display)
        
        self.sentences_data = sentences
        
        # Sentence detail frame (with scrolling)
        detail_frame = ttk.LabelFrame(frame, text="Sentence Explanation Editor", padding="10")
        detail_frame.pack(fill="both", expand=True, pady=5)
        
        # Create a scrollable frame for the content
        canvas = tk.Canvas(detail_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(detail_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Sentence display (read-only) - more compact
        ttk.Label(scrollable_frame, text="Sentence:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 3))
        self.sentence_display_text = scrolledtext.ScrolledText(scrollable_frame, height=2, font=("Arial", 10), wrap="word", state="disabled")
        self.sentence_display_text.pack(fill="x", pady=(0, 8))
        
        # Focus area selection (checkboxes) - compact
        focus_frame = ttk.LabelFrame(scrollable_frame, text="Select Focus Areas:", padding="5")
        focus_frame.pack(fill="x", pady=5)
        
        # Initialize checkbox variables
        self.focus_vars = {}
        self.focus_checkboxes = {}
        
        # Add checkboxes for each focus area
        for focus in ["grammar", "vocabulary", "context", "pronunciation", "all"]:
            self.focus_vars[focus] = tk.BooleanVar(value=False)
            checkbox = ttk.Checkbutton(
                focus_frame,
                text=focus.capitalize(),
                variable=self.focus_vars[focus]
            )
            checkbox.pack(side="left", padx=5)
            self.focus_checkboxes[focus] = checkbox
        
        # Set "all" checked by default
        self.focus_vars['all'].set(True)
        
        # Top section - Explanation only
        ttk.Label(scrollable_frame, text="Explanation:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(5, 0))
        self.sentence_explanation_text = scrolledtext.ScrolledText(scrollable_frame, height=5, font=("Arial", 10), wrap="word")
        self.sentence_explanation_text.pack(fill="both", pady=3)
        
        # Bottom section - Side by side: Grammar Notes (left) and Personal Notes (right)
        bottom_frame = ttk.Frame(scrollable_frame)
        bottom_frame.pack(fill="both", expand=True, pady=3)
        
        # Left side - Grammar notes
        left_frame = ttk.LabelFrame(bottom_frame, text="Grammar Notes:", padding="5")
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 3))
        
        self.sentence_grammar_text = scrolledtext.ScrolledText(left_frame, height=3, font=("Arial", 9), wrap="word")
        self.sentence_grammar_text.pack(fill="both", expand=True)
        
        # Right side - Personal notes
        right_frame = ttk.LabelFrame(bottom_frame, text="Personal Notes:", padding="5")
        right_frame.pack(side="right", fill="both", expand=True, padx=(3, 0))
        
        self.sentence_notes_text = scrolledtext.ScrolledText(right_frame, height=3, font=("Arial", 9), wrap="word")
        self.sentence_notes_text.pack(fill="both", expand=True)
        
        # Action buttons in scrollable area
        action_frame = ttk.Frame(scrollable_frame)
        action_frame.pack(fill="x", pady=10)
        
        if self.ollama_available:
            ttk.Button(
                action_frame,
                text="🤖 Generate Explanations",
                command=self._generate_sentence_explanation_multi
            ).pack(side="left", padx=5)
        
        ttk.Button(action_frame, text="Save", command=self._save_sentence_explanation).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Clear", command=self._clear_sentence_form).pack(side="left", padx=5)
        
        # Follow-up Questions Section
        followup_frame = ttk.LabelFrame(scrollable_frame, text="💬 Ask Follow-up Questions", padding="10")
        followup_frame.pack(fill="both", expand=True, pady=10)
        
        # Question input
        ttk.Label(followup_frame, text="Ask a question about this sentence:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 3))
        
        question_input_frame = ttk.Frame(followup_frame)
        question_input_frame.pack(fill="x", pady=(0, 5))
        
        self.followup_question_text = scrolledtext.ScrolledText(question_input_frame, height=2, font=("Arial", 10), wrap="word")
        self.followup_question_text.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        ask_btn = ttk.Button(question_input_frame, text="Ask", command=self._ask_followup_question)
        ask_btn.pack(side="right")
        
        # Follow-up history display
        ttk.Label(followup_frame, text="Conversation History:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(10, 3))
        
        self.followup_history_text = scrolledtext.ScrolledText(followup_frame, height=8, font=("Arial", 9), wrap="word", state="disabled")
        self.followup_history_text.pack(fill="both", expand=True, pady=(0, 5))
        
        # Clear history button
        clear_history_btn = ttk.Button(followup_frame, text="Clear History", command=self._clear_followup_history)
        clear_history_btn.pack(anchor="w")
        
        # Store current sentence explanation ID
        self.current_sentence_explanation_id = None
        
        # Navigation - outside scrollable area for easy access
        nav_frame = ttk.Frame(frame)
        nav_frame.pack(fill="x", pady=10, side="bottom")
        
        ttk.Button(nav_frame, text="← Back to Study Center", command=self.show_study_center).pack(side="left", padx=5)
    
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
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        title = ttk.Label(header_frame, text="📒 Grammar Book", style="Title.TLabel")
        title.pack(side="left")
        
        # Content Area - split into list (left) and editor (right)
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True)
        
        # Left Panel: List and Search
        left_panel = ttk.Frame(content_frame, width=300)
        left_panel.pack(side="left", fill="y", padx=(0, 10))
        
        # Search box
        search_frame = ttk.Frame(left_panel)
        search_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.grammar_search_var = tk.StringVar()
        self.grammar_search_var.trace("w", self._filter_grammar_entries)
        search_entry = ttk.Entry(search_frame, textvariable=self.grammar_search_var)
        search_entry.pack(side="left", fill="x", expand=True, padx=5)
        
        # Entries list
        list_frame = ttk.Frame(left_panel)
        list_frame.pack(fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        self.grammar_listbox = tk.Listbox(list_frame, font=("Arial", 10), yscrollcommand=scrollbar.set)
        self.grammar_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.grammar_listbox.yview)
        
        self.grammar_listbox.bind('<<ListboxSelect>>', self._on_grammar_entry_selected)
        
        # New Entry Button
        ttk.Button(left_panel, text="+ New Entry", command=self._new_grammar_entry).pack(fill="x", pady=10)
        
        # Right Panel: Editor
        right_panel = ttk.LabelFrame(content_frame, text="Entry Editor", padding="15")
        right_panel.pack(side="left", fill="both", expand=True)
        
        # Title Input
        title_input_frame = ttk.Frame(right_panel)
        title_input_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(title_input_frame, text="Title:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.grammar_title_var = tk.StringVar()
        ttk.Entry(title_input_frame, textvariable=self.grammar_title_var, font=("Arial", 11)).pack(fill="x", pady=5)
        
        # Tags Input
        tags_input_frame = ttk.Frame(right_panel)
        tags_input_frame.pack(fill="x", pady=(0, 10))
        ttk.Label(tags_input_frame, text="Tags (comma separated):").pack(anchor="w")
        self.grammar_tags_var = tk.StringVar()
        ttk.Entry(tags_input_frame, textvariable=self.grammar_tags_var).pack(fill="x", pady=5)
        
        # AI Generation Button
        if self.ollama_available:
            ai_frame = ttk.Frame(right_panel)
            ai_frame.pack(fill="x", pady=(0, 10))
            ttk.Button(ai_frame, text="✨ Generate Explanation from Title", command=self._generate_grammar_explanation).pack(anchor="w")
        
        # Content Editor
        ttk.Label(right_panel, text="Content:", font=("Arial", 10, "bold")).pack(anchor="w")
        self.grammar_content_text = scrolledtext.ScrolledText(right_panel, font=("Arial", 10), height=15)
        self.grammar_content_text.pack(fill="both", expand=True, pady=5)
        
        # Action Buttons
        action_frame = ttk.Frame(right_panel)
        action_frame.pack(fill="x", pady=10)
        
        ttk.Button(action_frame, text="Save Entry", command=self._save_grammar_entry, style="Large.TButton").pack(side="left", padx=5)
        ttk.Button(action_frame, text="Delete", command=self._delete_grammar_entry).pack(side="left", padx=5)
        
        # Navigation
        nav_frame = ttk.Frame(main_frame)
        nav_frame.pack(fill="x", pady=10, side="bottom")
        ttk.Button(nav_frame, text="← Back to Study Center", command=self.show_study_center).pack(side="left")
        
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
