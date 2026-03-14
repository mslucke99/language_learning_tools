"""
Adventure Graded Reader UI Frame for Tkinter.

Provides the user interface for the Adventure Graded Reader feature,
including session management, story display, and choice selection.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import logging
from typing import Optional
from datetime import datetime

from ..session_manager import StorySessionManager
from ..story_generator import StoryGenerator
from ..models import GenerationMode, StorySession, StoryContext
from ...core.database import FlashcardDatabase


logger = logging.getLogger(__name__)


class AdventureReaderFrame(ttk.Frame):
    """Main frame for Adventure Graded Reader feature."""
    
    def __init__(self, parent, controller, study_manager, db: FlashcardDatabase):
        """Initialize the Adventure Reader frame."""
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        self.session_manager = StorySessionManager(db)
        self.current_session: Optional[StorySession] = None
        self.current_view = None
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the main UI layout."""
        for widget in self.winfo_children():
            widget.destroy()
        self.show_main_menu()
    
    def show_main_menu(self):
        """Display the main menu with options."""
        self._clear_current_view()
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=20)
        ttk.Label(header_frame, text=" Story Mode", font=("Arial", 24, "bold")).pack()
        ttk.Label(header_frame, text="Choose Your Own Adventure", font=("Arial", 12, "italic")).pack()
        menu_frame = ttk.Frame(self)
        menu_frame.pack(fill="both", expand=True, padx=20, pady=20)
        ttk.Button(menu_frame, text=" Start New Story", command=self.show_session_setup, style="Large.TButton").pack(fill="x", pady=10)
        ttk.Button(menu_frame, text=" Resume Story", command=self.show_resume_menu, style="Large.TButton").pack(fill="x", pady=10)
        back_frame = ttk.Frame(self)
        back_frame.pack(fill="x", padx=20, pady=20)
        ttk.Button(back_frame, text=" Back to Home", command=self.controller.show_home).pack(side="left")
        self.current_view = "main_menu"
    
    def show_session_setup(self):
        """Display session setup dialog for starting a new story."""
        self._clear_current_view()
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=20)
        ttk.Label(header_frame, text="Start New Story", font=("Arial", 20, "bold")).pack()
        form_frame = ttk.Frame(self)
        form_frame.pack(fill="both", expand=True, padx=20, pady=20)
        ttk.Label(form_frame, text="Select Genre:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(10, 5))
        try:
            generator = StoryGenerator(GenerationMode.TEMPLATE, self.db)
            genres = generator.get_available_genres()
        except Exception as e:
            logger.error(f"Failed to get genres: {e}")
            genres = ["Mystery", "Adventure", "Fantasy"]
        self.genre_var = tk.StringVar(value=genres[0] if genres else "")
        genre_frame = ttk.Frame(form_frame)
        genre_frame.pack(fill="x", pady=10)
        for genre in genres:
            ttk.Radiobutton(genre_frame, text=genre.capitalize(), variable=self.genre_var, value=genre).pack(anchor="w", pady=5)
        ttk.Label(form_frame, text="Generation Mode:", font=("Arial", 12, "bold")).pack(anchor="w", pady=(20, 5))
        self.mode_var = tk.StringVar(value="template")
        mode_frame = ttk.Frame(form_frame)
        mode_frame.pack(fill="x", pady=10)
        ttk.Radiobutton(mode_frame, text="Template (Fast, Offline)", variable=self.mode_var, value="template").pack(anchor="w", pady=5)
        ttk.Radiobutton(mode_frame, text="AI Generated (High Quality, Requires API)", variable=self.mode_var, value="llm").pack(anchor="w", pady=5)
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", padx=20, pady=20)
        ttk.Button(button_frame, text="Start Story", command=self._start_new_story).pack(side="left", padx=5)
        ttk.Button(button_frame, text=" Back", command=self.show_main_menu).pack(side="left", padx=5)
        self.current_view = "session_setup"
    
    def _start_new_story(self):
        """Create a new story session and start reading."""
        try:
            genre = self.genre_var.get()
            mode_str = self.mode_var.get()
            mode = GenerationMode.LLM if mode_str == "llm" else GenerationMode.TEMPLATE
            from ..vocabulary_service import VocabularyService
            vocab_service = VocabularyService(self.db)
            known_words = vocab_service.get_known_words(self.study_manager.study_language)
            if not known_words:
                messagebox.showwarning("Insufficient Vocabulary", "You need to have some known words in your vocabulary to start a story.\n\nPlease add words to your flashcard decks first.")
                return
            session = self.session_manager.create_session(language=self.study_manager.study_language, genre=genre, generation_mode=mode, known_words=known_words)
            self.current_session = session
            self.show_reading_view()
        except Exception as e:
            logger.error(f"Failed to start new story: {e}")
            messagebox.showerror("Error", f"Failed to start story: {str(e)}")
    
    def show_resume_menu(self):
        """Display list of saved sessions to resume."""
        self._clear_current_view()
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=20)
        ttk.Label(header_frame, text="Resume Story", font=("Arial", 20, "bold")).pack()
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT id, genre, created_at, last_updated FROM story_sessions WHERE language = ? ORDER BY last_updated DESC", (self.study_manager.study_language,))
            sessions = cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to load sessions: {e}")
            sessions = []
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=20, pady=20)
        if not sessions:
            ttk.Label(list_frame, text="No saved stories yet.", font=("Arial", 12)).pack(pady=20)
        else:
            for session_id, genre, created_at, last_updated in sessions:
                session_button_frame = ttk.Frame(list_frame)
                session_button_frame.pack(fill="x", pady=5)
                session_text = f" {genre.capitalize()} - Last played: {last_updated}"
                ttk.Button(session_button_frame, text=session_text, command=lambda sid=session_id: self._resume_session(sid)).pack(fill="x", side="left", expand=True)
                ttk.Button(session_button_frame, text="", command=lambda sid=session_id: self._delete_session(sid), width=3).pack(side="left", padx=5)
        back_frame = ttk.Frame(self)
        back_frame.pack(fill="x", padx=20, pady=20)
        ttk.Button(back_frame, text=" Back", command=self.show_main_menu).pack(side="left")
    
    def _resume_session(self, session_id: int):
        """Resume a saved story session."""
        try:
            self.current_session = self.session_manager.load_session(session_id)
            self.show_reading_view()
        except Exception as e:
            logger.error(f"Failed to resume session: {e}")
            messagebox.showerror("Error", f"Failed to resume story: {str(e)}")
    
    def _delete_session(self, session_id: int):
        """Delete a saved story session."""
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this story?"):
            try:
                self.session_manager.delete_session(session_id)
                self.show_resume_menu()
            except Exception as e:
                logger.error(f"Failed to delete session: {e}")
                messagebox.showerror("Error", f"Failed to delete story: {str(e)}")
    
    def show_reading_view(self):
        """Display the story reading interface."""
        if not self.current_session:
            messagebox.showerror("Error", "No active session")
            self.show_main_menu()
            return
        self._clear_current_view()
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        canvas = tk.Canvas(main_frame, bg="white", highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        try:
            history = self.session_manager.get_session_history(self.current_session.id)
            if history:
                current_passage = history[-1]
            else:
                from ..vocabulary_service import VocabularyService
                vocab_service = VocabularyService(self.db)
                known_words = vocab_service.get_known_words(self.current_session.language)
                from ..models import VocabularyConstraints
                constraints = VocabularyConstraints(known_words=known_words, min_coverage=0.90, max_new_words=2)
                generator = StoryGenerator(self.current_session.generation_mode, self.db)
                current_passage = generator.generate_passage(self.current_session.story_context, constraints)
            ttk.Label(scrollable_frame, text=f" {self.current_session.genre.capitalize()}", font=("Arial", 16, "bold")).pack(anchor="w", pady=(0, 10))
            passage_text = tk.Text(scrollable_frame, height=12, width=60, wrap="word", font=("Arial", 11), bg="white", relief="flat")
            passage_text.pack(fill="both", expand=True, pady=10)
            passage_text.insert("1.0", current_passage.text)
            passage_text.config(state="disabled")
            if current_passage.new_words:
                ttk.Label(scrollable_frame, text=" New Words:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 5))
                for new_word in current_passage.new_words:
                    word_frame = ttk.Frame(scrollable_frame)
                    word_frame.pack(fill="x", pady=3)
                    ttk.Label(word_frame, text=f" {new_word.word}", font=("Arial", 10, "bold")).pack(side="left", padx=(10, 5))
                    ttk.Label(word_frame, text=new_word.definition, font=("Arial", 10), foreground="gray").pack(side="left")
            if current_passage.choices:
                ttk.Label(scrollable_frame, text=" What do you do?", font=("Arial", 10, "bold")).pack(anchor="w", pady=(15, 10))
                for choice in current_passage.choices:
                    ttk.Button(scrollable_frame, text=f" {choice.text}", command=lambda cid=choice.id: self._make_choice(cid)).pack(fill="x", pady=5)
        except Exception as e:
            logger.error(f"Failed to display reading view: {e}")
            ttk.Label(scrollable_frame, text=f"Error loading story: {str(e)}", font=("Arial", 11), foreground="red").pack(pady=20)
        nav_frame = ttk.Frame(self)
        nav_frame.pack(fill="x", padx=20, pady=20)
        ttk.Button(nav_frame, text=" Save & Exit", command=self._save_and_exit).pack(side="left", padx=5)
        ttk.Button(nav_frame, text=" Back to Menu", command=self._back_to_menu).pack(side="left", padx=5)
        self.current_view = "reading_view"
    
    def _make_choice(self, choice_id: int):
        """Process a user's choice and generate next passage."""
        try:
            self.session_manager.process_choice(self.current_session.id, choice_id)
            self.current_session = self.session_manager.load_session(self.current_session.id)
            self.show_reading_view()
        except Exception as e:
            logger.error(f"Failed to process choice: {e}")
            messagebox.showerror("Error", f"Failed to continue story: {str(e)}")
    
    def _save_and_exit(self):
        """Save current session and return to main menu."""
        try:
            if self.current_session:
                self.session_manager.save_session(self.current_session)
            self.current_session = None
            self.show_main_menu()
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            messagebox.showerror("Error", f"Failed to save story: {str(e)}")
    
    def _back_to_menu(self):
        """Return to main menu without saving."""
        if messagebox.askyesno("Confirm", "Exit without saving?"):
            self.current_session = None
            self.show_main_menu()
    
    def _clear_current_view(self):
        """Clear all widgets from the frame."""
        for widget in self.winfo_children():
            widget.destroy()
