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
        
        # Settings button
        settings_btn = ttk.Button(
            btn_frame,
            text="⚙️ Settings",
            command=self.show_settings,
            style="Large.TButton"
        )
        settings_btn.pack(side="left", padx=10, fill="both", expand=True)
        
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
        
        # Word detail frame
        detail_frame = ttk.LabelFrame(frame, text="Word Definition Editor", padding="15")
        detail_frame.pack(fill="both", expand=True, pady=10)
        
        # Word label
        self.word_label = ttk.Label(detail_frame, text="(Select a word)", style="Subtitle.TLabel")
        self.word_label.pack(pady=5)
        
        # Definition text
        ttk.Label(detail_frame, text="Definition (Native Language):", font=("Arial", 9)).pack(anchor="w", pady=(10, 0))
        self.word_definition_text = scrolledtext.ScrolledText(detail_frame, height=6, font=("Arial", 10), wrap="word")
        self.word_definition_text.pack(fill="both", expand=True, pady=5)
        
        # Examples
        ttk.Label(detail_frame, text="Examples (one per line):", font=("Arial", 9)).pack(anchor="w")
        self.word_examples_text = scrolledtext.ScrolledText(detail_frame, height=4, font=("Arial", 9), wrap="word")
        self.word_examples_text.pack(fill="both", expand=True, pady=5)
        
        # Notes
        ttk.Label(detail_frame, text="Notes:", font=("Arial", 9)).pack(anchor="w")
        self.word_notes_text = scrolledtext.ScrolledText(detail_frame, height=3, font=("Arial", 9), wrap="word")
        self.word_notes_text.pack(fill="both", expand=True, pady=5)
        
        # Action buttons
        action_frame = ttk.Frame(detail_frame)
        action_frame.pack(fill="x", pady=10)
        
        ttk.Button(action_frame, text="Save Definition", command=self._save_word_definition).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Clear", command=self._clear_word_form).pack(side="left", padx=5)
        
        if self.ollama_available:
            ttk.Button(
                action_frame,
                text="🤖 Generate Definition",
                command=self._generate_word_definition
            ).pack(side="left", padx=5)
        
        # Navigation
        nav_frame = ttk.Frame(frame)
        nav_frame.pack(fill="x", pady=10)
        
        ttk.Button(nav_frame, text="← Back", command=self.show_study_center).pack(side="left", padx=5)
    
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
        """Generate word definition using Ollama."""
        if not self.current_word_id:
            messagebox.showwarning("Warning", "Please select a word first")
            return
        
        # Show loading
        original_text = self.word_definition_text.get(1.0, tk.END)
        self.word_definition_text.delete(1.0, tk.END)
        self.word_definition_text.insert(tk.END, "🔄 Generating definition...")
        self.root.update()
        
        success, result = self.study_manager.generate_word_definition(
            self.current_word_id,
            language='native',
            use_simplified=False
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
        
        # Sentence detail frame
        detail_frame = ttk.LabelFrame(frame, text="Sentence Explanation Editor", padding="15")
        detail_frame.pack(fill="both", expand=True, pady=10)
        
        # Sentence display (read-only)
        ttk.Label(detail_frame, text="Current Sentence:", font=("Arial", 9, "bold")).pack(anchor="w", pady=(0, 5))
        self.sentence_display_text = scrolledtext.ScrolledText(detail_frame, height=3, font=("Arial", 11), wrap="word", state="disabled")
        self.sentence_display_text.pack(fill="x", pady=(0, 10))
        
        # Focus area selection
        focus_frame = ttk.Frame(detail_frame)
        focus_frame.pack(fill="x", pady=10)
        
        ttk.Label(focus_frame, text="Explanation Focus:").pack(side="left", padx=5)
        self.focus_var = tk.StringVar(value="all")
        for focus in ["all", "grammar", "vocabulary", "context"]:
            ttk.Radiobutton(focus_frame, text=focus, variable=self.focus_var, value=focus).pack(side="left", padx=5)
        
        # Explanation text
        ttk.Label(detail_frame, text="Explanation (Native Language):", font=("Arial", 9)).pack(anchor="w", pady=(10, 0))
        self.sentence_explanation_text = scrolledtext.ScrolledText(detail_frame, height=7, font=("Arial", 10), wrap="word")
        self.sentence_explanation_text.pack(fill="both", expand=True, pady=5)
        
        # Grammar notes
        ttk.Label(detail_frame, text="Grammar Notes:", font=("Arial", 9)).pack(anchor="w")
        self.sentence_grammar_text = scrolledtext.ScrolledText(detail_frame, height=3, font=("Arial", 9), wrap="word")
        self.sentence_grammar_text.pack(fill="both", expand=True, pady=5)
        
        # User notes
        ttk.Label(detail_frame, text="Personal Notes:", font=("Arial", 9)).pack(anchor="w")
        self.sentence_notes_text = scrolledtext.ScrolledText(detail_frame, height=3, font=("Arial", 9), wrap="word")
        self.sentence_notes_text.pack(fill="both", expand=True, pady=5)
        
        # Action buttons
        action_frame = ttk.Frame(detail_frame)
        action_frame.pack(fill="x", pady=10)
        
        ttk.Button(action_frame, text="Save Explanation", command=self._save_sentence_explanation).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Clear", command=self._clear_sentence_form).pack(side="left", padx=5)
        
        if self.ollama_available:
            ttk.Button(
                action_frame,
                text="🤖 Generate Explanation",
                command=self._generate_sentence_explanation
            ).pack(side="left", padx=5)
        
        # Navigation
        nav_frame = ttk.Frame(frame)
        nav_frame.pack(fill="x", pady=10)
        
        ttk.Button(nav_frame, text="← Back", command=self.show_study_center).pack(side="left", padx=5)
    
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
        
        if explanation:
            self.sentence_explanation_text.insert(tk.END, explanation['explanation'])
            self.sentence_grammar_text.insert(tk.END, explanation['grammar_notes'])
            self.sentence_notes_text.insert(tk.END, explanation['user_notes'])
            self.focus_var.set(explanation['focus_area'])
    
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
        focus = self.focus_var.get()
        
        try:
            self.study_manager.add_sentence_explanation(
                self.current_sentence_id,
                explanation,
                explanation_language='native',
                focus_area=focus,
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
        """Generate sentence explanation using Ollama."""
        if not self.current_sentence_id:
            messagebox.showwarning("Warning", "Please select a sentence first")
            return
        
        # Show loading
        original_text = self.sentence_explanation_text.get(1.0, tk.END)
        self.sentence_explanation_text.delete(1.0, tk.END)
        self.sentence_explanation_text.insert(tk.END, "🔄 Generating explanation...")
        self.root.update()
        
        focus = self.focus_var.get()
        success, result = self.study_manager.generate_sentence_explanation(
            self.current_sentence_id,
            language='native',
            focus_area=focus
        )
        
        self.sentence_explanation_text.delete(1.0, tk.END)
        if success:
            self.sentence_explanation_text.insert(tk.END, result)
        else:
            self.sentence_explanation_text.insert(tk.END, original_text)
            messagebox.showerror("Error", result)
    
    # ========== SETTINGS ==========
    
    def show_settings(self):
        """Show settings screen."""
        self.clear_window()
        
        frame = ttk.Frame(self.root, padding="20")
        frame.pack(fill="both", expand=True)
        
        # Title
        title = ttk.Label(frame, text="Study Settings", style="Title.TLabel")
        title.pack(pady=20)
        
        # Settings content
        settings_frame = ttk.LabelFrame(frame, text="Language Preferences", padding="15")
        settings_frame.pack(fill="x", pady=10)
        
        # Native language
        ttk.Label(settings_frame, text="Your Native Language:", font=("Arial", 10)).pack(anchor="w", pady=5)
        native_lang_var = tk.StringVar(value=self.study_manager.native_language)
        native_entry = ttk.Entry(settings_frame, textvariable=native_lang_var, width=30)
        native_entry.pack(anchor="w", pady=5)
        
        # Study language
        ttk.Label(settings_frame, text="Language You're Studying:", font=("Arial", 10)).pack(anchor="w", pady=5)
        study_lang_var = tk.StringVar(value=self.study_manager.study_language)
        study_entry = ttk.Entry(settings_frame, textvariable=study_lang_var, width=30)
        study_entry.pack(anchor="w", pady=5)
        
        # Preference frame
        pref_frame = ttk.LabelFrame(frame, text="Output Language Preferences", padding="15")
        pref_frame.pack(fill="x", pady=10)
        
        def_native_var = tk.BooleanVar(value=self.study_manager.prefer_native_definitions)
        ttk.Checkbutton(
            pref_frame,
            text="Prefer native language for word definitions",
            variable=def_native_var
        ).pack(anchor="w", pady=5)
        
        exp_native_var = tk.BooleanVar(value=self.study_manager.prefer_native_explanations)
        ttk.Checkbutton(
            pref_frame,
            text="Prefer native language for sentence explanations",
            variable=exp_native_var
        ).pack(anchor="w", pady=5)
        
        # Save button
        def save_settings():
            self.study_manager.set_native_language(native_lang_var.get())
            self.study_manager.set_study_language(study_lang_var.get())
            self.study_manager.set_definition_language_preference(def_native_var.get())
            self.study_manager.set_explanation_language_preference(exp_native_var.get())
            messagebox.showinfo("Success", "Settings saved!")
            self.show_study_center()
        
        ttk.Button(frame, text="Save Settings", command=save_settings).pack(pady=20)
        ttk.Button(frame, text="← Back", command=self.show_study_center).pack()
    
    # ========== UTILITY METHODS ==========
    
    def clear_window(self):
        """Clear all widgets from the window."""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def on_close(self):
        """Return to main menu."""
        self.root.quit()
