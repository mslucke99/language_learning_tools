import tkinter as tk
from tkinter import ttk, messagebox
from src.core.database import FlashcardDatabase
from src.services.llm_service import get_ai_client, is_ai_available
from src.features.study_center.logic.study_manager import StudyManager
from src.core.import_export import ImportExportManager
from src.core.localization import tr, set_locale, subscribe_locale
from src.core.config import config as app_config

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

from src.features.pronunciation_lab.ui.pronunciation_lab import PronunciationLabFrame
from src.features.audio_review.ui.audio_review import AudioReviewFrame

from src.features.chat.ui.chat_dashboard import ChatDashboardFrame
from src.features.chat.ui.active_chat import ActiveChatFrame
from src.features.dashboard.settings_ui import SettingsUI as SettingsFrame
from src.features.dashboard.task_queue_ui import TaskQueueDialog
from src.features.dashboard.dev_console_ui import DevConsoleDialog
# from src.services.dropbox_sync import dropbox_manager # Removing Dropbox ref
from src.services.auth_service import AuthService
from src.services.firestore_sync import FirestoreSyncManager
from src.core.pending_imports import PendingImportsProcessor

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
        
        # Navigation State
        self.current_frame = None
        self.current_frame_type = None
        self.current_frame_args = {}
        
        # Frame Caching for Performance
        self.frame_cache = {}  # (frame_class, frozenset(kwargs)) -> frame_instance
        # Frames that can be safely cached (no dynamic args, reusable)
        self.cacheable_frames = {
            HomeDashboard,
            StudyDashboardFrame,
            DeckSelectionFrame,
            ChatDashboardFrame,
            SettingsFrame,
        }
        
        # Subscribe to Locale Changes
        subscribe_locale(self._on_locale_changed)
        
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
        
        # Process any pending imports from browser extension (offline buffer)
        self._process_pending_imports()
        
    def bind_global_shortcuts(self):
        """Bind global navigation shortcuts."""
        self.root.bind("<Control-D>", lambda e: self.show_flashcards_dashboard())
        self.root.bind("<Control-S>", lambda e: self.show_study_center_dashboard())
        self.root.bind("<Control-C>", lambda e: self.show_chat_dashboard())
        self.root.bind("<Control-W>", lambda e: self.show_writing_lab_view())
        self.root.bind("<Control-Q>", lambda e: self.show_quiz_setup())
        self.root.bind("<Control-R>", lambda e: self.show_reading_mode())
        # Use simple Ctrl+Letter for main navigation, Shift is often too complex for frequent use
        
    def _preload_ai_model(self):
        import threading
        def _load():
            try:
                self.ai_client.get_available_models()
            except: pass
        threading.Thread(target=_load, daemon=True).start()

    def _hide_current_frame(self):
        """Hide the current frame without destroying it."""
        if self.current_frame:
            if hasattr(self.current_frame, 'on_hide'):
                self.current_frame.on_hide()
            self.current_frame.pack_forget()

    def _destroy_current_frame(self):
        """Destroy the current frame (for non-cached frames)."""
        if self.current_frame:
            self.current_frame.destroy()
        self.current_frame = None

    def clear_container(self):
        """Legacy method - now just hides."""
        self._hide_current_frame()

    def show_frame(self, frame_class, **kwargs):
        """Show a frame, using cache for eligible frames."""
        # Hide or destroy current frame
        if self.current_frame_type in self.cacheable_frames and self.current_frame_type in self.frame_cache:
            self._hide_current_frame()
        else:
            self._destroy_current_frame()
        
        # Determine if new frame is cacheable (class-only key for stable dependencies)
        new_cache_key = frame_class  # Simplified: just use the class as the key
        
        if frame_class in self.cacheable_frames:
            # Use cache for cacheable frames
            if new_cache_key in self.frame_cache:
                self.current_frame = self.frame_cache[new_cache_key]
                self.current_frame.pack(fill="both", expand=True)
                if hasattr(self.current_frame, 'on_show'):
                    self.current_frame.on_show()
            else:
                self.current_frame = frame_class(self.main_container, self, **kwargs)
                self.current_frame.pack(fill="both", expand=True)
                self.frame_cache[new_cache_key] = self.current_frame
        else:
            # Non-cacheable frame: always create fresh
            self.current_frame = frame_class(self.main_container, self, **kwargs)
            self.current_frame.pack(fill="both", expand=True)
        
        self.current_frame_type = frame_class
        self.current_frame_args = kwargs

    def _on_locale_changed(self):
        """Handle global locale change."""
        try:
            self.root.title(tr("app_title", "Language Learning Suite"))
            # Re-setup status bar labels/buttons
            if hasattr(self, 'status_bar'):
                self.status_bar.destroy()
                self.setup_status_bar()
            
            # Clear frame cache (frames have hardcoded translations)
            for key, frame in self.frame_cache.items():
                try:
                    frame.destroy()
                except: pass
            self.frame_cache.clear()
            
            # Refresh current frame if one exists
            if self.current_frame_type:
                self._destroy_current_frame()  # Force destroy for fresh translation
                self.show_frame(self.current_frame_type, **self.current_frame_args)
        except Exception as e:
            print(f"[Dashboard] Error during locale refresh: {e}")

    # --- Navigation Methods ---

    def show_home(self):
        self.show_frame(HomeDashboard)
        
    def show_flashcards_dashboard(self):
        self.show_deck_selection()
        
    def show_study_center_dashboard(self):
        self.show_study_dashboard()

    # --- Flashcards Feature ---
    
    def show_deck_selection(self):
        self.show_frame(DeckSelectionFrame, db=self.db)
        
    def show_deck_menu(self, deck_id):
        self.show_frame(DeckOverviewFrame, db=self.db, deck_id=deck_id)
        
    def view_all_cards(self, deck_id):
        self.show_frame(CardListFrame, db=self.db, deck_id=deck_id)
        
    def start_review(self, deck_id):
        self.show_frame(ReviewSessionFrame, db=self.db, deck_id=deck_id)
        
    # --- Study Center Feature ---
    
    def show_study_dashboard(self):
        self.show_frame(StudyDashboardFrame, study_manager=self.study_manager, db=self.db)
        
    def show_words_view(self):
        self.show_frame(WordsViewFrame, study_manager=self.study_manager, db=self.db)
        
    def show_sentences_view(self):
        self.show_frame(SentencesViewFrame, study_manager=self.study_manager, db=self.db)
        
    def show_grammar_book_view(self):
        self.show_frame(GrammarBookViewFrame, study_manager=self.study_manager, db=self.db)

    def show_quiz_setup(self):
        self.show_frame(QuizUIFrame, study_manager=self.study_manager, db=self.db)
        
    # --- Writing Lab Feature ---
    
    def show_writing_lab_view(self):
        self.show_frame(WritingLabFrame, study_manager=self.study_manager)
        
    def show_pronunciation_lab_view(self):
        self.show_frame(PronunciationLabFrame, study_manager=self.study_manager, db=self.db)
        
    # --- Audio Review Feature ---
    
    def show_audio_review_view(self):
        self.show_frame(AudioReviewFrame, study_manager=self.study_manager, db=self.db)
        
    # --- Chat Feature ---
    
    def show_chat_dashboard(self):
        self.show_frame(ChatDashboardFrame, study_manager=self.study_manager)
        
    def show_active_chat(self, session_id):
        self.show_frame(ActiveChatFrame, study_manager=self.study_manager, session_id=session_id)

    # --- Reading Mode Feature ---
    
    def show_reading_mode(self):
        from src.features.reader.ui.reading_mode_frame import ReadingModeFrame
        self.show_frame(ReadingModeFrame, study_manager=self.study_manager, db=self.db)

    # --- Settings ---
    
    def show_settings(self):
        self.show_frame(SettingsFrame, study_manager=self.study_manager)

    def show_knowledge_graph(self):
        """Generate and show the semantic knowledge graph in the browser."""
        import subprocess
        import os
        import webbrowser
        
        # Show a "Processing" message
        messagebox.showinfo("Knowledge Graph", "Generating your Semantic Vocabulary Galaxy...\nThis may take a few seconds.")
        
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts", "generate_vocab_map.py"))
        output_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "vocab_map.html"))
        
        def _run():
            try:
                # Run the script with language filtering
                lang = self.study_manager.study_language
                result = subprocess.run([sys.executable, script_path, "--output", output_path, "--language", lang], capture_output=True, text=True)
                if result.returncode == 0:
                    # Open the result in browser
                    webbrowser.open(f"file:///{output_path}")
                else:
                    messagebox.showerror("Graph Error", f"Failed to generate graph:\n{result.stderr}")
            except Exception as e:
                messagebox.showerror("Graph Error", f"An error occurred: {e}")
        
        import threading
        import sys
        threading.Thread(target=_run, daemon=True).start()

    # --- Utils ---
    
    def is_ai_available(self):
        return self.ai_available
        
    def show_grammar_help(self):
        self.show_grammar_book_view()

    def _process_pending_imports(self):
        """Check for and process any pending imports from the browser extension."""
        def _run_process():
            try:
                processor = PendingImportsProcessor(self.db)
                results = processor.process()
                if results['processed'] > 0:
                    msg = tr("msg_imported_items", "📥 Imported {count} items from browser extension", count=results['processed'])
                    # We can't easily show a transient message in the status bar from a thread without more logic
                    # For now, let's just log it or show a message box if it's significant
                    print(f"[Dashboard] {msg}")
                    self.root.after(1000, lambda: messagebox.showinfo(tr("title_import", "Imports Found"), msg))
            except Exception as e:
                print(f"[Dashboard] Error processing pending imports: {e}")

        import threading
        threading.Thread(target=_run_process, daemon=True).start()

    # --- Status Bar & Task Queue ---

    def setup_status_bar(self):
        self.status_bar = ttk.Frame(self.root, relief="sunken", padding=(10, 2))
        self.status_bar.pack(side="bottom", fill="x")
        
        self.ai_status_label = ttk.Label(self.status_bar, text=tr("status_checking", "AI: Checking..."))
        self.ai_status_label.pack(side="left", padx=5)
        
        ttk.Separator(self.status_bar, orient="vertical").pack(side="left", fill="y", padx=10)
        
        self.queue_status_label = ttk.Label(self.status_bar, text=tr("status_ai_pending", "AI Tasks: 0", count=0))
        self.queue_status_label.pack(side="left", padx=5)
        
        self.task_mgr_btn = ttk.Button(self.status_bar, text=tr("btn_tasks", "📋 Tasks"), command=self.show_task_manager, width=10)
        self.task_mgr_btn.pack(side="right", padx=5)

        self.dev_btn = ttk.Button(self.status_bar, text=tr("btn_dev", "🚀 Dev"), command=self.show_dev_console, width=8)
        self.dev_btn.pack(side="right", padx=5)

        self.sync_btn = ttk.Button(self.status_bar, text=tr("btn_sync", "🔄 Sync"), command=self.perform_global_sync, width=8)
        self.sync_btn.pack(side="right", padx=5)

        self.login_btn = ttk.Button(self.status_bar, text=tr("btn_sign_in", "Sign In"), command=self.perform_sign_in, width=10)
        self.login_btn.pack(side="right", padx=5)
        
    def _update_status_bar(self):
        # Update AI Service Status
        provider_type = self.study_manager.llm_provider
        provider_name = provider_type.title()
        
        # Optimization: Cache AI availability check for 30s
        import time
        now = time.time()
        if not hasattr(self, '_ai_avail_cache') or now - getattr(self, '_ai_avail_last_check', 0) > 30:
            self._ai_avail_cache = self.study_manager.ai_available and is_ai_available()
            self._ai_avail_last_check = now
        
        if self._ai_avail_cache:
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
            self.queue_status_label.config(text=tr("status_ai_pending", "AI Tasks: {count} pending", count=total_active), font=("Segoe UI", 9, "bold"))
            self.task_mgr_btn.config(text=f"📋 {tr('btn_tasks', 'Tasks')} ({total_active})")
        else:
            self.queue_status_label.config(text=tr("status_ai_pending", "AI Tasks: 0", count=0), font=("Segoe UI", 9))
            self.task_mgr_btn.config(text=f"📋 {tr('btn_tasks', 'Tasks')}")
        
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

    def export_deck_to_csv(self, deck_id):
        """Export a deck to CSV for Anki."""
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Deck to Anki CSV"
        )
        if filename:
            if self.io_manager.export_deck_to_csv(deck_id, filename):
                messagebox.showinfo("Export Success", f"Deck exported to {filename}")
            else:
                messagebox.showerror("Export Failed", "Could not export deck.")


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
        self.lang_label = None
        self.setup_ui()

    def setup_ui(self):
        # Clear existing content if any (though usually __init__ is fresh)
        for widget in self.winfo_children():
            widget.destroy()

        ttk.Label(self, text=tr("app_title"), font=("Arial", 32, "bold")).pack(pady=(60, 20))
        ttk.Label(self, text=tr("msg_welcome", "What would you like to do today?"), font=("Arial", 14, "italic")).pack(pady=(0, 40))
        
        # Grid frame for buttons
        grid_frame = ttk.Frame(self)
        grid_frame.pack(pady=20)
        
        # Row 1: Core Learning
        ttk.Button(grid_frame, text=tr("btn_flashcards", "🗂️ Flashcard Decks"), command=self.controller.show_flashcards_dashboard, style="Large.TButton").grid(row=0, column=0, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_study_tools", "📚 Study Tools"), command=self.controller.show_study_center_dashboard, style="Large.TButton").grid(row=0, column=1, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_quiz", "📝 Practice Quiz"), command=self.controller.show_quiz_setup, style="Large.TButton").grid(row=0, column=2, padx=15, pady=15, sticky="nsew")
        
        # Row 2: Advanced Practice
        ttk.Button(grid_frame, text=tr("btn_writing_lab", "✍️ Writing Lab"), command=self.controller.show_writing_lab_view, style="Large.TButton").grid(row=1, column=0, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_chat", "💬 AI Tutor Chat"), command=self.controller.show_chat_dashboard, style="Large.TButton").grid(row=1, column=1, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_reading_mode", "📖 Reading Mode"), command=self.controller.show_reading_mode, style="Large.TButton").grid(row=1, column=2, padx=15, pady=15, sticky="nsew")
        
        # Row 3: App Settings
        ttk.Button(grid_frame, text=tr("btn_vocab_map", "🕸️ Knowledge Graph"), command=self.controller.show_knowledge_graph, style="Large.TButton").grid(row=2, column=0, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_pronunciation_lab", "🎙️ Pronunciation Lab"), command=self.controller.show_pronunciation_lab_view, style="Large.TButton").grid(row=2, column=1, padx=15, pady=15, sticky="nsew")
        ttk.Button(grid_frame, text=tr("btn_settings", "⚙️ App Settings"), command=self.controller.show_settings, style="Large.TButton").grid(row=2, column=2, padx=15, pady=15, sticky="nsew")
        
        # Configure grid expansion
        for i in range(3):
            grid_frame.columnconfigure(i, weight=1, minsize=200)
        for i in range(3):
            grid_frame.rowconfigure(i, weight=1, minsize=100)
        
        # Footer
        footer = ttk.Frame(self)
        footer.pack(side="bottom", fill="x", pady=20)
        
        # Disclaimer at bottom
        disclaimer = ttk.Label(footer, text=tr("msg_disclaimer"), font=("Arial", 8), foreground="gray", wraplength=800, justify="center")
        disclaimer.pack(pady=(0, 10))

        self.lang_label = ttk.Label(footer, text=f"{tr('lbl_language')} {self.controller.study_manager.study_language}", font=("Arial", 10))
        self.lang_label.pack(side="right", padx=30)

    def on_show(self):
        """Refresh dynamic content like current language."""
        if self.lang_label:
            self.lang_label.config(text=f"{tr('lbl_language')} {self.controller.study_manager.study_language}")
