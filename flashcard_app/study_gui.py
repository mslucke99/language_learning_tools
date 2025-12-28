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
        
        # Back button
        back_btn = ttk.Button(frame, text="← Back to Main Menu", command=self.on_close)
        back_btn.pack(pady=10)

    
    # ========== WORDS VIEW ==========
    
    def show_words_view(self):
        """Show the words study view."""
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        # Title
        title = ttk.Label(frame, text="Study Words", style="Title.TLabel")
        title.pack(pady=10)
        
        # Get words
        words = self.study_manager.get_imported_words()
        
        if not words:
            ttk.Label(frame, text="No words imported yet. Import words using the browser extension!").pack(pady=20)
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
        
        # Title
        title = ttk.Label(frame, text="Study Sentences", style="Title.TLabel")
        title.pack(pady=10)
        
        # Get sentences
        sentences = self.study_manager.get_imported_sentences()
        
        if not sentences:
            ttk.Label(frame, text="No sentences imported yet. Import sentences using the browser extension!").pack(pady=20)
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
        
        if explanation:
            self.sentence_explanation_text.insert(tk.END, explanation['explanation'])
            self.sentence_grammar_text.insert(tk.END, explanation['grammar_notes'])
            self.sentence_notes_text.insert(tk.END, explanation['user_notes'])
            # Set checkbox for the focus area if stored
            if explanation.get('focus_area') and explanation['focus_area'] in self.focus_vars:
                self.focus_vars[explanation['focus_area']].set(True)
        else:
            # Default to "all" if no explanation exists
            self.focus_vars['all'].set(True)
    
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
    
    
    # ========== UTILITY METHODS ==========

    
    def clear_window(self):
        """Clear all widgets from the window."""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def on_close(self):
        """Return to main menu."""
        self.root.quit()
