import tkinter as tk
from tkinter import ttk, messagebox
from src.core.database import FlashcardDatabase
from src.services.llm_service import get_ollama_client, is_ollama_available
from src.features.study_center.logic.study_manager import StudyManager
from src.core.import_export import ImportExportManager

# Import Feature Views
from src.features.flashcards.ui.deck_selection import DeckSelectionFrame
from src.features.flashcards.ui.deck_overview import DeckOverviewFrame
from src.features.flashcards.ui.card_list import CardListFrame
from src.features.flashcards.ui.review_session import ReviewSessionFrame

from src.features.study_center.ui.study_dashboard import StudyDashboardFrame
from src.features.study_center.ui.words_view import WordsViewFrame
from src.features.study_center.ui.sentences_view import SentencesViewFrame
from src.features.study_center.ui.grammar_book_view import GrammarBookViewFrame
from src.features.study_center.ui.quiz_ui import QuizUIFrame

from src.features.writing_lab.ui.writing_lab import WritingLabFrame

from src.features.chat.ui.chat_dashboard import ChatDashboardFrame
from src.features.chat.ui.active_chat import ActiveChatFrame
from src.features.dashboard.settings_ui import SettingsFrame

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Language Learning Suite")
        self.root.geometry("1300x850") # Slightly larger default
        
        # Initialize Core Services
        self.db = FlashcardDatabase()
        self.ollama_client = get_ollama_client()
        self.ollama_available = is_ollama_available()
        
        self.study_manager = StudyManager(self.db, self.ollama_client)
        self.io_manager = ImportExportManager(self.db, self.study_manager)
        
        # Pre-load Ollama if configured
        if self.ollama_available and self.study_manager.get_preload_on_startup():
             self._preload_ollama()

        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6)
        style.configure("Large.TButton", font=("Arial", 11, "bold"), padding=15)
        
        # Main Container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True)
        
        # Navigation State
        self.current_frame = None
        
        # Start with Home (Dashboard)
        self.show_home()
        
    def _preload_ollama(self):
        import threading
        def _load():
            try:
                self.ollama_client.get_available_models()
            except: pass
        threading.Thread(target=_load, daemon=True).start()

    def clear_container(self):
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = None

    # --- Navigation Methods ---

    def show_home(self):
        self.clear_container()
        self.current_frame = HomeDashboard(self.main_container, self)
        self.current_frame.pack(fill="both", expand=True)
        
    def show_flashcards_dashboard(self):
        self.show_deck_selection()
        
    def show_study_center_dashboard(self):
        self.show_study_dashboard()

    # --- Flashcards Feature ---
    
    def show_deck_selection(self):
        self.clear_container()
        self.current_frame = DeckSelectionFrame(self.main_container, self, self.db)
        self.current_frame.pack(fill="both", expand=True)
        
    def show_deck_menu(self, deck_id):
        self.clear_container()
        self.current_frame = DeckOverviewFrame(self.main_container, self, self.db, deck_id)
        self.current_frame.pack(fill="both", expand=True)
        
    def view_all_cards(self, deck_id):
        self.clear_container()
        self.current_frame = CardListFrame(self.main_container, self, self.db, deck_id)
        self.current_frame.pack(fill="both", expand=True)
        
    def start_review(self, deck_id):
        self.clear_container()
        self.current_frame = ReviewSessionFrame(self.main_container, self, self.db, deck_id)
        self.current_frame.pack(fill="both", expand=True)
        
    # --- Study Center Feature ---
    
    def show_study_dashboard(self):
        self.clear_container()
        self.current_frame = StudyDashboardFrame(self.main_container, self, self.study_manager, self.db)
        self.current_frame.pack(fill="both", expand=True)
        
    def show_words_view(self):
        self.clear_container()
        self.current_frame = WordsViewFrame(self.main_container, self, self.study_manager, self.db)
        self.current_frame.pack(fill="both", expand=True)
        
    def show_sentences_view(self):
        self.clear_container()
        self.current_frame = SentencesViewFrame(self.main_container, self, self.study_manager, self.db)
        self.current_frame.pack(fill="both", expand=True)
        
    def show_grammar_book_view(self):
        self.clear_container()
        self.current_frame = GrammarBookViewFrame(self.main_container, self, self.study_manager, self.db)
        self.current_frame.pack(fill="both", expand=True)

    def show_quiz_setup(self):
        self.clear_container()
        self.current_frame = QuizUIFrame(self.main_container, self, self.study_manager, self.db)
        self.current_frame.pack(fill="both", expand=True)
        
    # --- Writing Lab Feature ---
    
    def show_writing_lab_view(self):
        self.clear_container()
        self.current_frame = WritingLabFrame(self.main_container, self, self.study_manager)
        self.current_frame.pack(fill="both", expand=True)
        
    # --- Chat Feature ---
    
    def show_chat_dashboard(self):
        self.clear_container()
        self.current_frame = ChatDashboardFrame(self.main_container, self, self.study_manager)
        self.current_frame.pack(fill="both", expand=True)
        
    def show_active_chat(self, session_id):
        self.clear_container()
        self.current_frame = ActiveChatFrame(self.main_container, self, self.study_manager, session_id)
        self.current_frame.pack(fill="both", expand=True)

    # --- Settings ---
    
    def show_settings(self):
        self.clear_container()
        self.current_frame = SettingsFrame(self.main_container, self, self.study_manager)
        self.current_frame.pack(fill="both", expand=True)

    # --- Utils ---
    
    def is_ollama_available(self):
        return self.ollama_available
        
    def show_grammar_help(self):
        self.show_grammar_book_view()

class HomeDashboard(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ttk.Label(self, text="Language Learning Suite", font=("Arial", 32, "bold")).pack(pady=(60, 20))
        ttk.Label(self, text="What would you like to do today?", font=("Arial", 14, "italic")).pack(pady=(0, 40))
        
        # Grid frame for buttons
        grid_frame = ttk.Frame(self)
        grid_frame.pack(pady=20)
        
        # Row 1: Core Learning
        ttk.Button(grid_frame, text="🗂️ Flashcard Decks", command=controller.show_flashcards_dashboard, style="Large.TButton").grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text="📚 Study Tools", command=controller.show_study_center_dashboard, style="Large.TButton").grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text="📝 Practice Quiz", command=controller.show_quiz_setup, style="Large.TButton").grid(row=0, column=2, padx=15, pady=15, sticky="nsew")
        
        # Row 2: Advanced Practice
        ttk.Button(grid_frame, text="✍️ Writing Lab", command=controller.show_writing_lab_view, style="Large.TButton").grid(row=1, column=0, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text="💬 AI Tutor Chat", command=controller.show_chat_dashboard, style="Large.TButton").grid(row=1, column=1, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text="⚙️ App Settings", command=controller.show_settings, style="Large.TButton").grid(row=1, column=2, padx=15, pady=15, sticky="nsew")
        
        # Configure grid expansion
        for i in range(3):
            grid_frame.columnconfigure(i, weight=1, minsize=200)
        for i in range(2):
            grid_frame.rowconfigure(i, weight=1, minsize=100)
        
        # Footer
        footer = ttk.Frame(self)
        footer.pack(side="bottom", fill="x", pady=20)
        ttk.Label(footer, text=f"Study Language: {controller.study_manager.study_language}", font=("Arial", 10)).pack(side="right", padx=30)
