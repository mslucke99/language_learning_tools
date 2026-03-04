import tkinter as tk
from tkinter import ttk, messagebox
import threading

from src.features.study_center.logic.study_manager import StudyManager
from src.core.ui_utils import setup_standard_header
from src.features.dashboard.prompt_editor_ui import PromptEditorDialog
from src.features.dashboard.dictionary_settings_ui import DictionarySettingsFrame
from src.core.localization import tr, set_locale

# Config dir is now handled largely by the manager but kept for display if needed
from src.services.dropbox_sync import dropbox_manager, CONFIG_DIR

class SettingsUI(ttk.Frame):
    def __init__(self, parent, controller, study_manager):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        
        # Check AI Service connection
        self.ai_available = study_manager.ai_client is not None and study_manager.ai_client.is_available()
        self.available_models = []
        
        # Initialize Dropbox Sync
        self.dropbox_sync = dropbox_manager
        
        # Variables
        self.study_lang_var = tk.StringVar()
        self.native_lang_var = tk.StringVar()
        self.model_var = tk.StringVar()
        self.timeout_var = tk.IntVar()
        self.preload_var = tk.BooleanVar()
        self.sync_status_var = tk.StringVar(value="Not connected")
        
        # LLM Provider Variables
        self.provider_var = tk.StringVar(value="ollama")
        self.api_key_var = tk.StringVar()
        self.base_url_var = tk.StringVar()
        
        # Audio & Voice Variables
        self.stt_provider_var = tk.StringVar(value=app_config.stt_provider)
        self.tts_provider_var = tk.StringVar(value=app_config.tts_provider)
        self.audio_rate_var = tk.IntVar(value=app_config.audio_sample_rate)
        
        from src.services.llm_providers.security import KeyringManager
        self.keyring = KeyringManager()
        
        if self.dropbox_sync.is_authenticated():
            self.sync_status_var.set("Connected to Dropbox ✅")
            
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        # Create Notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # --- TAB 1: GENERAL ---
        gen_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(gen_tab, text=tr("tab_general", "⚙️ General"))
        
        # Use a grid for alignment
        lang_grid = ttk.Frame(gen_tab)
        lang_grid.pack(fill="x")

        # Study Language (Target)
        ttk.Label(lang_grid, text=tr("lbl_study_lang", "Study Language (target):")).grid(row=0, column=0, sticky="w", pady=10)
        self.study_lang_combo = ttk.Combobox(lang_grid, textvariable=self.study_lang_var, 
                                            values=["Spanish", "French", "German", "Japanese", "Korean", "Mandarin", "Italian", "Portuguese", "Russian", "Arabic", "Biblical Greek"],
                                            width=32, state="readonly")
        self.study_lang_combo.grid(row=0, column=1, sticky="w", padx=15)
        
        # Native Language (for definitions)
        ttk.Label(lang_grid, text=tr("lbl_native_lang", "Native Language (ui/def):")).grid(row=1, column=0, sticky="w", pady=10)
        ttk.Entry(lang_grid, textvariable=self.native_lang_var, width=35).grid(row=1, column=1, sticky="w", padx=15)
        
        # UI Language (Test)
        ttk.Label(lang_grid, text=tr("lbl_ui_language", "UI Language (Test):")).grid(row=2, column=0, sticky="w", pady=10)
        ui_lang_frame = ttk.Frame(lang_grid)
        ui_lang_frame.grid(row=2, column=1, sticky="w", padx=15)
        ttk.Button(ui_lang_frame, text="EN", width=5, command=lambda: self._switch_ui('en')).pack(side="left", padx=2)
        ttk.Button(ui_lang_frame, text="KO", width=5, command=lambda: self._switch_ui('ko')).pack(side="left", padx=2)
        ttk.Button(ui_lang_frame, text="ES", width=5, command=lambda: self._switch_ui('es')).pack(side="left", padx=2)

        ttk.Label(gen_tab, text=tr("tip_languages", "Tip: Study language is what you are learning. Native language is used for definitions and UI."), 
                  font=("Arial", 9, "italic"), foreground="gray", wraplength=500).pack(anchor="w", pady=20)
        
        # --- TAB 2: AI MODEL ---
        ai_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(ai_tab, text=tr("tab_ai_model", "🤖 AI Model"))
        
        status_frame = ttk.Frame(ai_tab)
        status_frame.pack(fill="x", pady=(0, 20))
        
        self.ai_status_label = ttk.Label(status_frame, text="AI Status: Checking...", font=("Arial", 11, "bold"))
        self.ai_status_label.pack(side="left")
        
        self._update_ai_status()
        
        ai_grid = ttk.Frame(ai_tab)
        ai_grid.pack(fill="x")
        
        ttk.Label(ai_grid, text="Default Model:").grid(row=0, column=0, sticky="w", pady=10)
        model_frame = ttk.Frame(ai_grid)
        model_frame.grid(row=0, column=1, sticky="w", padx=15)
        
        self.model_combo = ttk.Combobox(model_frame, textvariable=self.model_var, state="readonly", width=32)
        self.model_combo.pack(side="left")
        
        ttk.Button(model_frame, text="🔄", width=3, command=self._refresh_model_list).pack(side="left", padx=5)
        
        self._refresh_model_list()
        
        
        ttk.Label(ai_grid, text=tr("lbl_timeout", "Request Timeout (sec):")).grid(row=1, column=0, sticky="w", pady=10)
        ttk.Spinbox(ai_grid, from_=5, to=300, increment=5, textvariable=self.timeout_var, width=10).grid(row=1, column=1, sticky="w", padx=15)
        
        ttk.Checkbutton(ai_tab, text=tr("lbl_preload", "Pre-load model on application startup"), variable=self.preload_var).pack(anchor="w", pady=15)
        
        # --- TAB 2.5: AI PROVIDERS ---
        prov_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(prov_tab, text=tr("tab_ai_providers", "🤖 AI Providers"))
        
        ttk.Label(prov_tab, text=tr("lbl_manage_backends", "Manage AI Backends"), font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        prov_grid = ttk.Frame(prov_tab)
        prov_grid.pack(fill="x")
        
        ttk.Label(prov_grid, text=tr("lbl_ai_backend", "AI Backend:")).grid(row=0, column=0, sticky="w", pady=10)
        self.prov_combo = ttk.Combobox(prov_grid, textvariable=self.provider_var, state="readonly", width=32,
                                     values=["ollama", "openai", "gemini", "lm_studio", "llama_cpp", "openai_compatible"])
        self.prov_combo.grid(row=0, column=1, sticky="w", padx=15)
        self.prov_combo.bind("<<ComboboxSelected>>", self._on_provider_changed)
        
        # API Key (Masked)
        self.lbl_key = ttk.Label(prov_grid, text=tr("lbl_api_key", "API Key:"))
        self.lbl_key.grid(row=1, column=0, sticky="w", pady=10)
        self.ent_key = ttk.Entry(prov_grid, textvariable=self.api_key_var, width=35, show="*")
        self.ent_key.grid(row=1, column=1, sticky="w", padx=15)
        
        # Base URL
        self.lbl_url = ttk.Label(prov_grid, text=tr("lbl_base_url", "Base URL:"))
        self.lbl_url.grid(row=2, column=0, sticky="w", pady=10)
        self.ent_url = ttk.Entry(prov_grid, textvariable=self.base_url_var, width=35)
        self.ent_url.grid(row=2, column=1, sticky="w", padx=15)
        
        actions_fr = ttk.Frame(prov_tab)
        actions_fr.pack(fill="x", pady=20)
        ttk.Button(actions_fr, text=tr("btn_test_conn", "Test Connection"), command=self._test_provider_connection).pack(side="left")
        ttk.Button(actions_fr, text=tr("btn_apply_backend", "Apply Backend"), command=self._apply_provider_config, style="Accent.TButton").pack(side="left", padx=10)
        
        ttk.Label(prov_tab, text=tr("msg_secure_storage", "Note: API keys are stored securely in your OS Credential Manager."), 
                  font=("Arial", 9, "italic"), foreground="gray", wraplength=500).pack(anchor="w", pady=10)
        
        # --- TAB 3: PROMPTS (Tuning) ---
        prompt_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(prompt_tab, text=tr("tab_prompts", "AI Prompts"))
        
        ttk.Label(prompt_tab, text=tr("lbl_customize_ai", "Customize AI Behavior"), font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        ttk.Label(prompt_tab, text=tr("lbl_customize_desc", "You can customize exactly how the AI defines words, explains grammar, grades your writing, and interacts in chat."), 
                  wraplength=500, justify="left").pack(anchor="w", pady=(0, 20))
        
        ttk.Button(prompt_tab, text=tr("btn_open_prompt_editor", "🎨 Open Advanced Prompt Editor"), 
                   command=self.open_prompt_editor, style="Accent.TButton").pack(anchor="w", pady=10)
        
        ttk.Button(prompt_tab, text=tr("btn_reset_prompts", "↺ Reset All Prompts to Default"), 
                   command=self.reset_all_prompts).pack(anchor="w", pady=(0, 10))
        
        ttk.Label(prompt_tab, text=tr("tip_prompt_editor", "Tip: Use the editor to add specific instructions for your target language."), 
                  font=("Arial", 9, "italic"), foreground="gray", wraplength=500).pack(anchor="w", pady=20)
        
        # --- TAB 3.5: DICTIONARIES ---
        dict_tab = DictionarySettingsFrame(self.notebook)
        self.notebook.add(dict_tab, text=tr("tab_dictionaries", "📚 Dictionaries"))

        # --- TAB 3.7: AUDIO & VOICE ---
        audio_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(audio_tab, text=tr("tab_audio_voice", "🎙️ Audio & Voice"))
        
        ttk.Label(audio_tab, text=tr("lbl_audio_settings", "Audio & Voice Services"), font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        audio_grid = ttk.Frame(audio_tab)
        audio_grid.pack(fill="x")
        
        # STT Provider
        ttk.Label(audio_grid, text=tr("lbl_stt_provider", "Speech-to-Text (STT):")).grid(row=0, column=0, sticky="w", pady=10)
        stt_combo = ttk.Combobox(audio_grid, textvariable=self.stt_provider_var, state="readonly", width=32,
                                values=["gemini", "whisper_cloud", "whisper_local"])
        stt_combo.grid(row=0, column=1, sticky="w", padx=15)
        
        # TTS Provider
        ttk.Label(audio_grid, text=tr("lbl_tts_provider", "Text-to-Speech (TTS):")).grid(row=1, column=0, sticky="w", pady=10)
        tts_combo = ttk.Combobox(audio_grid, textvariable=self.tts_provider_var, state="readonly", width=32,
                                values=["gtts", "pyttsx3"])
        tts_combo.grid(row=1, column=1, sticky="w", padx=15)
        
        # Sample Rate
        ttk.Label(audio_grid, text=tr("lbl_sample_rate", "Sample Rate (Hz):")).grid(row=2, column=0, sticky="w", pady=10)
        rate_combo = ttk.Combobox(audio_grid, textvariable=self.audio_rate_var, state="readonly", width=32,
                                 values=[16000, 22050, 44100, 48000])
        rate_combo.grid(row=2, column=1, sticky="w", padx=15)
        
        ttk.Label(audio_tab, text=tr("tip_audio_config", "Note: Gemini STT is recommended for best grading accuracy. pyttsx3 works offline."), 
                  font=("Arial", 9, "italic"), foreground="gray", wraplength=500).pack(anchor="w", pady=20)

        # --- TAB 4: CLOUD SYNC ---
        sync_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(sync_tab, text=tr("tab_cloud_sync", "☁️ Cloud Sync (Dropbox)"))
        
        ttk.Label(sync_tab, text=tr("lbl_dropbox_sync", "Dropbox Sync"), font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(sync_tab, text=tr("lbl_sync_description", "Sync your data via your private App Folder."), 
                  wraplength=500, justify="left").pack(anchor="w", pady=(0, 15))
        
        # Status indicator
        # self.sync_status_var = tk.StringVar(value="Not connected") # Moved to __init__
        status_frame = ttk.Frame(sync_tab)
        status_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(status_frame, text=tr("status_label", "Status:")).pack(side="left")
        ttk.Label(status_frame, textvariable=self.sync_status_var, font=("Arial", 10, "bold")).pack(side="left", padx=10)
        
        # Connect button
        connect_frame = ttk.Frame(sync_tab)
        connect_frame.pack(fill="x", pady=5)
        ttk.Button(connect_frame, text=tr("btn_connect_dropbox", "🔗 Connect Dropbox"), 
                   command=self._open_dropbox_auth).pack(side="left")
        ttk.Button(connect_frame, text=tr("btn_unlink", "Unlink"), 
                   command=self._disconnect_dropbox).pack(side="left", padx=10)
        
        # Sync actions
        ttk.Separator(sync_tab, orient="horizontal").pack(fill="x", pady=20)
        ttk.Label(sync_tab, text=tr("lbl_manual_sync", "Manual Sync Actions"), font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))
        
        action_frame = ttk.Frame(sync_tab)
        action_frame.pack(fill="x", pady=10)
        
        ttk.Button(action_frame, text=tr("btn_backup", "⬆️ Backup to Cloud"), 
                   command=self._backup_to_cloud, width=20).pack(side="left", padx=5)
        ttk.Button(action_frame, text=tr("btn_restore", "⬇️ Restore from Cloud"), 
                   command=self._restore_from_cloud, width=20).pack(side="left", padx=5)
        
        ttk.Label(sync_tab, text=tr("msg_sync_warning", "⚠️ Backup will overwrite the cloud copy. Restore will merge changes."), 
                  font=("Arial", 9, "italic"), foreground="#CC5500", wraplength=500).pack(anchor="w", pady=15)
        
        # --- Safety & Checkpoints ---
        ttk.Separator(sync_tab, orient="horizontal").pack(fill="x", pady=20)
        ttk.Label(sync_tab, text=tr("header_safety", "Safety & Checkpoints"), font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(sync_tab, text=tr("lbl_safety_description", "Create a snapshot of your data before performing a manual sync to ensure you can revert if needed."), 
                  font=("Arial", 9), foreground="gray", wraplength=500).pack(anchor="w", pady=(0, 10))
        
        checkpoint_frame = ttk.Frame(sync_tab)
        checkpoint_frame.pack(fill="x", pady=5)
        
        ttk.Button(checkpoint_frame, text=tr("btn_local_checkpoint", "Local Checkpoint"), 
                   command=lambda: self._create_checkpoint(cloud=False), width=20).pack(side="left", padx=5)
        ttk.Button(checkpoint_frame, text=tr("btn_cloud_checkpoint", "Cloud Checkpoint"), 
                   command=lambda: self._create_checkpoint(cloud=True), width=20).pack(side="left", padx=5)
        
        ttk.Button(sync_tab, text=tr("btn_open_backup", "📂 Open Backup Folder"), 
                   command=self._open_backup_folder, width=20).pack(anchor="w", padx=5, pady=10)

        ttk.Label(sync_tab, text=f"Config: {CONFIG_DIR}", 
                  font=("Arial", 8), foreground="gray").pack(anchor="w", pady=(20, 0))
        
        # --- FOOTER: SAVE BUTTON ---
        footer = ttk.Frame(self, padding=20)
        footer.pack(fill="x")
        
        save_btn = ttk.Button(footer, text=tr("btn_save_settings", "💾 Save All Settings"), command=self.save_settings, style="Large.TButton")
        save_btn.pack(side="right")
        
        ttk.Label(footer, text="Note: Some changes may require restarting the app.", font=("Arial", 9, "italic")).pack(side="left")

    def _switch_ui(self, lang_code):
        # This will trigger observers including DashboardApp
        set_locale(lang_code)
        self.study_manager.set_ui_language(lang_code)
        # Note: DashboardApp will refresh this settings frame anyway

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()

    def open_prompt_editor(self):
        editor = PromptEditorDialog(self.winfo_toplevel(), self.study_manager)
        editor.grab_set()

    def _update_ai_status(self):
        """Update the AI service status label."""
        p_name = self.study_manager.llm_provider.title()
        if self.study_manager.ai_client and self.study_manager.ai_client.is_available():
            self.ai_status_label.config(text=f"{p_name} Status: Connected ✅", foreground="green")
        else:
            self.ai_status_label.config(text=f"{p_name} Status: Disconnected ❌", foreground="red")

    def _refresh_model_list(self):
        """Fetch available models from the current provider."""
        if not self.study_manager.ai_client:
            self.model_combo['values'] = ["No provider active"]
            return
            
        def fetch():
            try:
                models = self.study_manager.ai_client.get_available_models()
                self.available_models = models
                self.model_combo['values'] = models
                # If current selection is invalid, pick first
                cur = self.model_var.get()
                if models and cur not in models:
                    self.model_var.set(models[0])
            except Exception as e:
                self.model_combo['values'] = ["Error fetching models"]
                print(f"Model fetch error: {e}")
                
        threading.Thread(target=fetch, daemon=True).start()

    def reset_all_prompts(self):
        if messagebox.askyesno("Confirm Reset", "This will revert ALL AI prompts to their factory defaults. This action cannot be undone.\n\nProceed?"):
            self.study_manager.reset_all_prompts()
            messagebox.showinfo("Reset Complete", "All prompts have been restored to defaults.")

    def load_settings(self):
        # Load from StudyManager / Database
        self.study_lang_var.set(self.study_manager.study_language)
        self.native_lang_var.set(self.study_manager.native_language)
        
        current_model = self.study_manager.get_ollama_model()
        self.model_var.set(current_model if current_model else "")
        
        self.timeout_var.set(self.study_manager.get_request_timeout())
        self.preload_var.set(self.study_manager.get_preload_on_startup())
        
        # Load Audio Settings
        from src.core.config import config as app_config
        self.stt_provider_var.set(app_config.stt_provider)
        self.tts_provider_var.set(app_config.tts_provider)
        self.audio_rate_var.set(app_config.audio_sample_rate)
        
        # Load Provider Config
        self.provider_var.set(self.study_manager.llm_provider)
        self.base_url_var.set(self.study_manager.llm_base_url or "")
        # Load API key from keyring if possible
        stored_key = self.keyring.get_api_key(self.study_manager.llm_provider)
        self.api_key_var.set(stored_key if stored_key else "")
        self._on_provider_changed(None, initial_load=True)

    def _on_provider_changed(self, event, initial_load=False):
        p = self.provider_var.get()
        # Hide/Show fields based on provider
        if p == "ollama":
            self.lbl_key.grid_remove()
            self.ent_key.grid_remove()
            self.lbl_url.grid()
            self.ent_url.grid()
        elif p in ["openai", "gemini"]:
            self.lbl_key.grid()
            self.ent_key.grid()
            self.lbl_url.grid_remove()
            self.ent_url.grid_remove()
        else: # compatible, studio, etc
            self.lbl_key.grid()
            self.ent_key.grid()
            self.lbl_url.grid()
            self.ent_url.grid()
        
        # Fresh API key for the new provider
        stored_key = self.keyring.get_api_key(p)
        self.api_key_var.set(stored_key if stored_key else "")
        
        # Load saved config (Base URL & Model) from DB for this provider
        saved_config = self.study_manager.get_provider_config(p)
        if saved_config['base_url']:
            self.base_url_var.set(saved_config['base_url'])
        else:
            # Default base URLs if not saved
            if p == "ollama": self.base_url_var.set("http://localhost:11434")
            elif p == "lm_studio": self.base_url_var.set("http://localhost:1234/v1")
            elif p == "llama_cpp": self.base_url_var.set("http://localhost:8080/v1")
            else: self.base_url_var.set("") # Cloud providers usually don't need it or use defaults
            
        # Update model var with saved model (or empty if none)
        # This prevents "Apply" from sending a leftover incompatible model string
        if not initial_load:
            self.model_var.set(saved_config['model'])
            self.available_models = []
            self.model_combo['values'] = [saved_config['model']] if saved_config['model'] else ["Switching..."]

    def _test_provider_connection(self):
        # Implementation of test logic
        backend = self.provider_var.get()
        url = self.base_url_var.get()
        key = self.api_key_var.get()
        
        self.config(cursor="wait")
        self.update()
        
        def run_test():
             from src.services.llm_service import LLMService
             # Store key temporarily in keyring for the test instance or pass it directly?
             # For now, let's just use a fresh service instance
             try:
                 # Update keyring first if key provided
                 if key: self.keyring.set_api_key(backend, key)
                 
                 test_service = LLMService(backend, {"base_url": url})
                 if test_service.is_available():
                     models = test_service.get_available_models()
                     msg = f"Connection Successful! ✅\n\nFound models: {', '.join(models[:5])}"
                     if len(models) > 5: msg += f" (+{len(models)-5} more)"
                     messagebox.showinfo("Success", msg)
                 else:
                     messagebox.showerror("Failed", "Could not connect to the AI backend. Check URL and API Key.")
             except Exception as e:
                 messagebox.showerror("Error", f"Test failed: {e}")
             finally:
                 self.config(cursor="")
        
        threading.Thread(target=run_test, daemon=True).start()

    def _apply_provider_config(self):
        backend = self.provider_var.get()
        url = self.base_url_var.get()
        key = self.api_key_var.get()
        
        if key:
            self.keyring.set_api_key(backend, key)
            
        self.study_manager.update_llm_config(backend, self.model_var.get(), url)
        messagebox.showinfo("Applied", f"AI backend switched to {backend}. Model set to {self.model_var.get()}")
        
        # Refresh model list based on new backend
        if self.study_manager.ai_client:
            self.available_models = self.study_manager.ai_client.get_available_models()
            self.model_combo['values'] = self.available_models

    def save_settings(self):
        try:
            # Update StudyManager & DB
            self.study_manager.set_native_language(self.native_lang_var.get().strip())
            self.study_manager.set_study_language(self.study_lang_var.get().strip())
            
            self.study_manager.set_llm_model(self.model_var.get())
            self.study_manager.set_request_timeout(self.timeout_var.get())
            self.study_manager.set_preload_on_startup(self.preload_var.get())
            
            # Save Audio Settings
            from src.core.config import config as app_config
            app_config.stt_provider = self.stt_provider_var.get()
            app_config.tts_provider = self.tts_provider_var.get()
            app_config.audio_sample_rate = int(self.audio_rate_var.get())
            app_config.save_to_file()
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            self.go_back()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {e}")
    
    # --- Cloud Sync Methods (Dropbox) ---
    def _open_dropbox_auth(self):
        from src.features.cloud_sync.dropbox_dialog import DropboxAuthDialog
        
        def on_success():
            self.sync_status_var.set("Connected to Dropbox ✅")
            messagebox.showinfo("Success", "Dropbox connected successfully!")

        DropboxAuthDialog(self.winfo_toplevel(), self.dropbox_sync, on_success)

    def _disconnect_dropbox(self):
        self.dropbox_sync.disconnect()
        self.sync_status_var.set("Not connected")
        messagebox.showinfo("Disconnected", "Dropbox account disconnected.")
    
    def _backup_to_cloud(self):
        if not self.dropbox_sync.is_authenticated():
            messagebox.showwarning("Not Connected", "Please connect your Dropbox account first.")
            return
        
        confirm = messagebox.askyesno("Confirm Backup", 
            "This will OVERWRITE your cloud backup '/Apps/LanguageLearningSuite/flashcards.db' with local data.\n\nProceed?")
        if not confirm:
            return
        
        # UI Feedback
        self.config(cursor="wait") 
        self.update()

        def status_callback(msg):
             print(f"[Sync] {msg}") # Just log for now

        success, message = self.dropbox_sync.upload_db(status_callback)
        
        self.config(cursor="")
        
        if success:
            messagebox.showinfo("Backup Complete", message)
        else:
            messagebox.showerror("Backup Failed", message)
    
    def _restore_from_cloud(self):
        if not self.dropbox_sync.is_authenticated():
            messagebox.showwarning("Not Connected", "Please connect your Dropbox account first.")
            return
        
        confirm = messagebox.askyesno("Confirm Restore", 
            "This will download 'flashcards.db' from Dropbox and MERGE it with your local data.\n\nProceed?")
        if not confirm:
            return

        # Use the CloudSyncManager wrapper mostly for the merge logic?
        # Actually we need to call dropbox_sync to get the temp file, then call SyncMerger manually
        # OR we can update CloudSyncManager to use Dropbox.
        # Ideally, lets just invoke the merge logic here for simplicity in this pivot.
        
        self.config(cursor="wait")
        self.update()
        
        success, temp_path, message = self.dropbox_sync.download_db_to_temp()
        
        if not success:
            self.config(cursor="")
            if "No backup found" in message:
                confirm = messagebox.askyesno("First-Time Sync", 
                    "No cloud backup found on Dropbox.\n\nWould you like to upload your local data as the initial cloud copy?")
                if confirm:
                    success_up, msg_up = self.dropbox_sync.upload_db()
                    if success_up:
                        messagebox.showinfo("Sync Initialized", "Initial upload complete!")
                    else:
                        messagebox.showerror("Upload Failed", msg_up)
            else:
                messagebox.showerror("Download Failed", message)
            return

        # Perform Merge
        try:
            from src.services.sync_merger import SyncMerger
            from src.services.conflict_dialog import show_conflict_dialog
            
            # Setup Merger
            resolver_dialog_provider = lambda conflict_data: show_conflict_dialog(self.winfo_toplevel(), conflict_data)
            merger = SyncMerger(self.study_manager.db.db_path, temp_path)
            merger.on_conflict = resolver_dialog_provider
            
            stats = merger.perform_merge()
            
            # 3. Reload and Cleanup
            merger.close()
            if hasattr(self.controller, 'reload_db'):
                self.controller.reload_db()
            
            # Cleanup temp
            import os
            try:
                os.remove(temp_path)
            except: 
                pass

            self.config(cursor="")
            
            summary = (
                f"Sync Complete!\n\n"
                f"Added: {stats['added']}\n"
                f"Updated: {stats['updated']}\n"
                f"Conflicts Resolved: {stats['conflicts_resolved']}\n"
                f"Soft Deleted: {stats['soft_deleted']}"
            )
            messagebox.showinfo("Restore Successful", summary)
            
        except Exception as e:
            self.config(cursor="")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Merge Failed", f"Error during merge: {e}")

    def _create_checkpoint(self, cloud: bool = False):
        """Create a data checkpoint snapshot."""
        self.config(cursor="wait")
        self.update()
        
        success, message = self.dropbox_sync.create_checkpoint(local=True, cloud=cloud)
        
        self.config(cursor="")
        if success:
            messagebox.showinfo("Checkpoint Created", message)
        else:
            messagebox.showerror("Checkpoint Failed", message)

    def _open_backup_folder(self):
        """Open the local backups folder in explorer."""
        import os
        backup_dir = CONFIG_DIR / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        os.startfile(str(backup_dir))
        

