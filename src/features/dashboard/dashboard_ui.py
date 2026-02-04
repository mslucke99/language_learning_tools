import tkinter as tk
from tkinter import ttk, messagebox
from src.core.database import FlashcardDatabase
from src.services.llm_service import get_ai_client, is_ai_available
from src.features.study_center.logic.study_manager import StudyManager
from src.core.import_export import ImportExportManager
from src.core.localization import tr, set_locale

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
from src.features.dashboard.settings_ui import SettingsUI as SettingsFrame
from src.features.dashboard.task_queue_ui import TaskQueueDialog
from src.features.dashboard.dev_console_ui import DevConsoleDialog
# from src.services.dropbox_sync import dropbox_manager # Removing Dropbox ref
from src.services.auth_service import AuthService
from src.services.firestore_sync import FirestoreSyncManager

class DashboardApp:
    def __init__(self, root):
        self.root = root
        self.root.title(tr("app_title", "Language Learning Suite"))
        self.root.geometry("1300x850") # Slightly larger default
        
        # Initialize Core Services
        self.db = FlashcardDatabase()
        self.study_manager = StudyManager(self.db)
        self.ai_client = self.study_manager.ai_client
        self.ai_available = self.study_manager.ai_available
        
        self.io_manager = ImportExportManager(self.db, self.study_manager)

        # Auth & Sync
        self.auth_service = AuthService()
        self.sync_manager = FirestoreSyncManager(self.db.db_path)
        self.current_user_id = self.auth_service.get_current_user_id()
        if self.current_user_id:
            self.sync_manager.set_user_id(self.current_user_id)
        
        # Apply Persisted UI Locale
        set_locale(self.study_manager.ui_language)
        self.root.title(tr("app_title", "Language Learning Suite"))
        
        # Pre-load AI model if configured
        if self.ai_available and self.study_manager.get_preload_on_startup():
             self._preload_ai_model()

        # Styles
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6)
        style.configure("Large.TButton", font=("Arial", 11, "bold"), padding=15)
        
        # Main Container
        self.main_container = ttk.Frame(self.root)
        self.main_container.pack(fill="both", expand=True)
        
        # Status Bar
        self.setup_status_bar()
        
        # Navigation State
        self.current_frame = None
        
        # Start with Home (Dashboard)
        self.show_home()
        
        # Start periodic updates
        # Start periodic updates
        self._update_status_bar()
        
        # Bind Global Shortcuts
        self.bind_global_shortcuts()
        
    def bind_global_shortcuts(self):
        """Bind global navigation shortcuts."""
        self.root.bind("<Control-D>", lambda e: self.show_flashcards_dashboard())
        self.root.bind("<Control-S>", lambda e: self.show_study_center_dashboard())
        self.root.bind("<Control-C>", lambda e: self.show_chat_dashboard())
        self.root.bind("<Control-W>", lambda e: self.show_writing_lab_view())
        self.root.bind("<Control-Q>", lambda e: self.show_quiz_setup())
        # Use simple Ctrl+Letter for main navigation, Shift is often too complex for frequent use
        
    def _preload_ai_model(self):
        import threading
        def _load():
            try:
                self.ai_client.get_available_models()
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
    
    def is_ai_available(self):
        return self.ai_available
        
    def show_grammar_help(self):
        self.show_grammar_book_view()

    # --- Status Bar & Task Queue ---

    def setup_status_bar(self):
        self.status_bar = ttk.Frame(self.root, relief="sunken", padding=(10, 2))
        self.status_bar.pack(side="bottom", fill="x")
        
        self.ai_status_label = ttk.Label(self.status_bar, text="AI: Checking...")
        self.ai_status_label.pack(side="left", padx=5)
        
        ttk.Separator(self.status_bar, orient="vertical").pack(side="left", fill="y", padx=10)
        
        self.queue_status_label = ttk.Label(self.status_bar, text="AI Tasks: 0")
        self.queue_status_label.pack(side="left", padx=5)
        
        self.task_mgr_btn = ttk.Button(self.status_bar, text=tr("btn_tasks", "📋 Tasks"), command=self.show_task_manager, width=10)
        self.task_mgr_btn.pack(side="right", padx=5)

        self.dev_btn = ttk.Button(self.status_bar, text="🚀 Dev", command=self.show_dev_console, width=8)
        self.dev_btn.pack(side="right", padx=5)

        self.sync_btn = ttk.Button(self.status_bar, text="🔄 Sync", command=self.perform_global_sync, width=8)
        self.sync_btn.pack(side="right", padx=5)

        self.login_btn = ttk.Button(self.status_bar, text="Sign In", command=self.perform_sign_in, width=10)
        self.login_btn.pack(side="right", padx=5)
        
    def _update_status_bar(self):
        # Update AI Service Status
        provider_type = self.study_manager.llm_provider
        provider_name = provider_type.title()
        
        if self.study_manager.ai_available:
            # Check for potential mismatch in background
            active_model = self.study_manager.ai_client.model or "Default"
            
            # Smart logic: if Gemini is chosen but model is "qwen", show Offline until applied
            # This prevents the confusing 'Gemini: Online (qwen3:4b)' look
            is_mismatched = (provider_type == "gemini" and "gemini" not in active_model.lower()) or \
                            (provider_type == "openai" and "gpt" not in active_model.lower() and "o1" not in active_model.lower() and "o3" not in active_model.lower())
            
            if is_mismatched:
                self.ai_status_label.config(text=f"{provider_name}: {tr('status_updating', 'Syncing...')} ({active_model})", foreground="orange")
            else:
                self.ai_status_label.config(text=f"{provider_name}: {tr('status_online', 'Online')} ({active_model})", foreground="green")
        else:
            self.ai_status_label.config(text=f"{provider_name}: {tr('status_offline', 'Offline')}", foreground="red")
            
        # Update Queue Status
        q_status = self.study_manager.get_queue_status()
        total_active = q_status['queued'] + q_status['active']
        if total_active > 0:
            self.queue_status_label.config(text=f"AI Tasks: {total_active} pending", font=("Segoe UI", 9, "bold"))
            self.task_mgr_btn.config(text=f"📋 Tasks ({total_active})")
        else:
            self.queue_status_label.config(text="AI Tasks: 0", font=("Segoe UI", 9))
            self.task_mgr_btn.config(text="📋 Tasks")
        
        # Update Auth Status
        if self.current_user_id:
             self.login_btn.pack_forget() # Hide login if logged in
             self.sync_btn.pack(side="right", padx=5) # Ensure sync is visible
        else:
             self.sync_btn.pack_forget() # Hide sync if not logged in
             self.login_btn.pack(side="right", padx=5)

        # Schedule next update (every 3 seconds)
        self.root.after(3000, self._update_status_bar)

    def perform_sign_in(self):
        try:
            info = self.auth_service.sign_in()
            self.current_user_id = info.get('id')
            self.sync_manager.set_user_id(self.current_user_id)
            messagebox.showinfo("Signed In", f"Welcome, {info.get('name')}!")
            self._update_status_bar()
        except Exception as e:
            messagebox.showerror("Sign In Error", f"Failed to sign in:\n{e}")

    def show_task_manager(self):
        TaskQueueDialog(self.root, self.study_manager)

    def show_dev_console(self):
        DevConsoleDialog(self.root, self.study_manager)

    def perform_global_sync(self):
        """Perform a full cloud sync (download + merge) from the status bar."""
        if not self.current_user_id:
             messagebox.showwarning("Sync", "Please Sign In first.")
             return

        # Disable button during sync
        self.sync_btn.state(['disabled'])
        self.root.config(cursor="wait")
        self.root.update()

        try:
            stats = self.sync_manager.sync()
            
            if "error" in stats:
                 messagebox.showerror("Sync Error", stats["error"])
            else:
                self.reload_db()
                self.show_home() # Refresh view
                messagebox.showinfo("Sync Complete", 
                    f"Sync successful!\nDownloaded: {stats['downloaded']}\nUploaded: {stats['uploaded']}\nConflicts: {stats['conflicts']}")
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            messagebox.showerror("Sync Error", str(e))
        finally:
            self.sync_btn.state(['!disabled'])
            self.root.config(cursor="")

    def reload_db(self):
        """Re-initialize database connection and update dependent managers."""
        if hasattr(self, 'db'):
            try:
                self.db.close()
            except:
                pass
        
        from src.core.database import FlashcardDatabase
        self.db = FlashcardDatabase() # Uses default flashcards.db
        
        # Update dependencies
        self.study_manager.db = self.db
        self.io_manager.db = self.db
        
        print("[DB] Database connection re-initialized after sync.")

class HomeDashboard(ttk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        
        ttk.Label(self, text=tr("app_title"), font=("Arial", 32, "bold")).pack(pady=(60, 20))
        ttk.Label(self, text=tr("msg_welcome", "What would you like to do today?"), font=("Arial", 14, "italic")).pack(pady=(0, 40))
        
        # Grid frame for buttons
        grid_frame = ttk.Frame(self)
        grid_frame.pack(pady=20)
        
        # Row 1: Core Learning
        ttk.Button(grid_frame, text=tr("btn_flashcards", "🗂️ Flashcard Decks"), command=controller.show_flashcards_dashboard, style="Large.TButton").grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_study_tools", "📚 Study Tools"), command=controller.show_study_center_dashboard, style="Large.TButton").grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_quiz", "📝 Practice Quiz"), command=controller.show_quiz_setup, style="Large.TButton").grid(row=0, column=2, padx=15, pady=15, sticky="nsew")
        
        # Row 2: Advanced Practice
        ttk.Button(grid_frame, text=tr("btn_writing_lab", "✍️ Writing Lab"), command=controller.show_writing_lab_view, style="Large.TButton").grid(row=1, column=0, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_chat", "💬 AI Tutor Chat"), command=controller.show_chat_dashboard, style="Large.TButton").grid(row=1, column=1, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_settings", "⚙️ App Settings"), command=controller.show_settings, style="Large.TButton").grid(row=1, column=2, padx=15, pady=15, sticky="nsew")
        
        # Configure grid expansion
        for i in range(3):
            grid_frame.columnconfigure(i, weight=1, minsize=200)
        for i in range(2):
            grid_frame.rowconfigure(i, weight=1, minsize=100)
        
        # Footer
        footer = ttk.Frame(self)
        footer.pack(side="bottom", fill="x", pady=20)
        
        # Disclaimer at bottom
        disclaimer = ttk.Label(footer, text=tr("msg_disclaimer"), font=("Arial", 8), foreground="gray", wraplength=800, justify="center")
        disclaimer.pack(pady=(0, 10))

        ttk.Label(footer, text=f"{tr('lbl_language')} {controller.study_manager.study_language}", font=("Arial", 10)).pack(side="right", padx=30)
