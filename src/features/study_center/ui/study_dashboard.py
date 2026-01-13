import tkinter as tk
from tkinter import ttk
from src.features.study_center.logic.study_manager import StudyManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header
from src.core.localization import tr

# Import views to embed
from src.features.study_center.ui.words_view import WordsViewFrame
from src.features.study_center.ui.sentences_view import SentencesViewFrame
from src.features.study_center.ui.grammar_book_view import GrammarBookViewFrame
from src.features.study_center.ui.quiz_ui import QuizUIFrame
from src.features.writing_lab.ui.writing_lab import WritingLabFrame
from src.features.chat.ui.chat_dashboard import ChatDashboardFrame

class StudyDashboardFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, db: FlashcardDatabase):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        self.setup_ui()
        
    def setup_ui(self):
        # Header
        setup_standard_header(self, tr("study_center", "Study Tools & Practice"), back_cmd=self.go_back)
        
        # Main Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Tab 1: Overview & Stats
        stats_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(stats_tab, text=tr("tab_overview", "📊 Overview"))
        self._setup_stats_tab(stats_tab)
        
        # Tab 2: Words
        words_tab = WordsViewFrame(self.notebook, self.controller, self.study_manager, self.db, embedded=True)
        self.notebook.add(words_tab, text=tr("tab_words", "📚 Words"))
        
        # Tab 3: Sentences
        sentences_tab = SentencesViewFrame(self.notebook, self.controller, self.study_manager, self.db, embedded=True)
        self.notebook.add(sentences_tab, text=tr("tab_sentences", "📖 Sentences"))
        
        # Tab 4: Grammar
        grammar_tab = GrammarBookViewFrame(self.notebook, self.controller, self.study_manager, self.db, embedded=True)
        self.notebook.add(grammar_tab, text=tr("tab_grammar", "📒 Grammar"))
        
        # Tab 5: Writing Lab
        writing_tab = WritingLabFrame(self.notebook, self.controller, self.study_manager, embedded=True)
        self.notebook.add(writing_tab, text=tr("tab_writing", "✍️ Writing Lab"))
        
        # Tab 6: AI Chat
        chat_tab = ChatDashboardFrame(self.notebook, self.controller, self.study_manager, embedded=True)
        self.notebook.add(chat_tab, text=tr("tab_chat", "💬 AI Chat"))
        
        # Tab 7: Quiz
        quiz_tab = QuizUIFrame(self.notebook, self.controller, self.study_manager, self.db, embedded=True)
        self.notebook.add(quiz_tab, text=tr("tab_quiz", "📝 Quiz"))

    def _setup_stats_tab(self, parent):
        stats = self.study_manager.get_study_statistics()
        
        title_lbl = ttk.Label(parent, text=tr("title_progress", "Learning Progress"), font=("Arial", 16, "bold"))
        title_lbl.pack(pady=(0, 20))
        
        stats_frame = ttk.LabelFrame(parent, text=tr("lbl_stats", "Detailed Statistics"), padding="15")
        stats_frame.pack(fill="x", pady=5)
        
        stats_content = f"""
Words in Library: {stats['total_words']}
Words Processed: {stats['words_with_definitions']} ({stats['words_percentage']:.1f}%)

Sentences in Library: {stats['total_sentences']}
Sentences Explained: {stats['sentences_with_explanations']} ({stats['sentences_percentage']:.1f}%)

Configuration:
  Study Language: {self.study_manager.study_language}
  Native Language: {self.study_manager.native_language}
        """
        
        stats_label = ttk.Label(stats_frame, text=stats_content, justify="left", font=("Courier", 10))
        stats_label.pack()
        
        info_lbl = ttk.Label(parent, text="Use the tabs above to switch between different study tools.", font=("Arial", 10, "italic"))
        info_lbl.pack(pady=20)

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()
