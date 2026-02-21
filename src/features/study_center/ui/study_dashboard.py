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
from src.features.mining.ui.mining_view import SentenceMiningView

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
        self.stats_tab = ttk.Frame(self.notebook, padding=20)
        self.notebook.add(self.stats_tab, text=tr("tab_overview", "📊 Overview"))
        self._setup_stats_tab(self.stats_tab)
        
        # Tab 2: Words
        self.words_tab = WordsViewFrame(self.notebook, self.controller, self.study_manager, self.db, embedded=True)
        self.notebook.add(self.words_tab, text=tr("tab_words", "📚 Words"))
        
        # Tab 3: Sentences
        self.sentences_tab = SentencesViewFrame(self.notebook, self.controller, self.study_manager, self.db, embedded=True)
        self.notebook.add(self.sentences_tab, text=tr("tab_sentences", "📖 Sentences"))
        
        # Tab 4: Grammar
        self.grammar_tab = GrammarBookViewFrame(self.notebook, self.controller, self.study_manager, self.db, embedded=True)
        self.notebook.add(self.grammar_tab, text=tr("tab_grammar", "📒 Grammar"))
        
        # Tab 5: Writing Lab
        self.writing_tab = WritingLabFrame(self.notebook, self.controller, self.study_manager, embedded=True)
        self.notebook.add(self.writing_tab, text=tr("tab_writing", "✍️ Writing Lab"))
        
        # Tab 6: AI Chat
        self.chat_tab = ChatDashboardFrame(self.notebook, self.controller, self.study_manager, embedded=True)
        self.notebook.add(self.chat_tab, text=tr("tab_chat", "💬 AI Chat"))
        
        # Tab 7: Quiz
        self.quiz_tab = QuizUIFrame(self.notebook, self.controller, self.study_manager, self.db, embedded=True)
        self.notebook.add(self.quiz_tab, text=tr("tab_quiz", "📝 Quiz"))

        # Tab 8: Sentence Mining
        self.mining_tab = SentenceMiningView(self.notebook, self.db, study_manager=self.study_manager)
        self.notebook.add(self.mining_tab, text=tr("tab_mining", "⛏️ Mining"))
        
        self.tabs = [self.stats_tab, self.words_tab, self.sentences_tab, self.grammar_tab, self.writing_tab, self.chat_tab, self.quiz_tab, self.mining_tab]
        
        # Bind Tab Shortcuts (Ctrl+1 to Ctrl+6)
        # Note: We bind to the parent because the frame itself might not have focus
        # But to avoid conflict, we should bind only when this frame is visible/active.
        # Ideally, bind to self.notebook or self.
        
        # Actually, global binding checking for visibility is safer for Tkinter
        # but let's try binding to the notebook which should receive events when active
        for i in range(1, 9):
            self.controller.root.bind(f"<Control-Key-{i}>", self._make_tab_switcher(i-1), add="+")
        
        # Bind tab change event to call on_show on the newly selected tab
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

    def _on_tab_changed(self, event=None):
        """Called when user switches between tabs within the notebook."""
        try:
            current_tab_index = self.notebook.index("current")
            if 0 <= current_tab_index < len(self.tabs):
                active_tab = self.tabs[current_tab_index]
                if hasattr(active_tab, 'on_show'):
                    active_tab.on_show()
        except Exception:
            pass

    def _make_tab_switcher(self, index):
        """Factory for tab switch callbacks to capture index."""
        def _switch(event):
            # Only switch if this dashboard is actually visible
            if self.winfo_viewable() and index < self.notebook.index("end"):
                 self.notebook.select(index)
        return _switch

    def _setup_stats_tab(self, parent):
        from src.features.statistics.ui.statistics_view import StatisticsViewFrame
        stats_view = StatisticsViewFrame(parent, self.controller, self.db)
        stats_view.pack(fill="both", expand=True)
        
        info_lbl = ttk.Label(parent, text="Use the tabs above to switch between different study tools.", font=("Arial", 10, "italic"))
        info_lbl.pack(pady=20)

    def on_show(self):
        """Refresh logic when dashboard becomes visible again."""
        # Refresh the active tab if it has an on_show method
        current_tab_index = self.notebook.index("current")
        if 0 <= current_tab_index < len(self.tabs):
            active_tab = self.tabs[current_tab_index]
            if hasattr(active_tab, 'on_show'):
                active_tab.on_show()

    def on_hide(self):
        """Logic when dashboard is hidden."""
        # Notify active tab
        current_tab_index = self.notebook.index("current")
        if 0 <= current_tab_index < len(self.tabs):
            active_tab = self.tabs[current_tab_index]
            if hasattr(active_tab, 'on_hide'):
                active_tab.on_hide()

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()
