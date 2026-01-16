import tkinter as tk
from tkinter import ttk, messagebox
import threading

from src.features.study_center.logic.study_manager import StudyManager
from src.core.ui_utils import setup_standard_header
from src.features.dashboard.prompt_editor_ui import PromptEditorDialog
from src.core.localization import tr, set_locale

# Config dir is now handled largely by the manager but kept for display if needed
from src.services.dropbox_sync import dropbox_manager, CONFIG_DIR

class SettingsUI(ttk.Frame):
    def __init__(self, parent, controller, study_manager):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        
        # Check Ollama
        self.ollama_available = study_manager.ollama_client is not None and study_manager.ollama_client.is_available()
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

        ttk.Label(gen_tab, text=tr("tip_languages", "Tip: Study language is what you are learning. Native language is used for definitions and UI."), 
                  font=("Arial", 9, "italic"), foreground="gray", wraplength=500).pack(anchor="w", pady=20)
        
        # --- TAB 2: AI MODEL (Ollama) ---
        ai_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(ai_tab, text=tr("tab_ai_model", "AI Model"))
        
        status_frame = ttk.Frame(ai_tab)
        status_frame.pack(fill="x", pady=(0, 20))
        
        status_lbl = "Connected ✅" if self.ollama_available else "Not Connected (Ollama not found) ❌"
        ttk.Label(status_frame, text=f"Ollama Status: {status_lbl}", font=("Arial", 11, "bold")).pack(side="left")
        
        ai_grid = ttk.Frame(ai_tab)
        ai_grid.pack(fill="x")
        
        ttk.Label(ai_grid, text="Default Model:").grid(row=0, column=0, sticky="w", pady=10)
        self.model_combo = ttk.Combobox(ai_grid, textvariable=self.model_var, state="readonly", width=32)
        self.model_combo.grid(row=0, column=1, sticky="w", padx=15)
        
        if self.ollama_available:
             try:
                 self.available_models = self.study_manager.ollama_client.get_available_models()
                 self.model_combo['values'] = self.available_models
             except:
                 self.model_combo['values'] = ["Error fetching models"]
        
        ttk.Label(ai_grid, text="Request Timeout (sec):").grid(row=1, column=0, sticky="w", pady=10)
        ttk.Spinbox(ai_grid, from_=5, to=300, increment=5, textvariable=self.timeout_var, width=10).grid(row=1, column=1, sticky="w", padx=15)
        
        ttk.Checkbutton(ai_tab, text="Pre-load model on application startup", variable=self.preload_var).pack(anchor="w", pady=15)
        
        # --- TAB 3: PROMPTS (Tuning) ---
        prompt_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(prompt_tab, text=tr("tab_prompts", "AI Prompts"))
        
        ttk.Label(prompt_tab, text="Customize AI Behavior", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        ttk.Label(prompt_tab, text="You can customize exactly how the AI defines words, explains grammar, grades your writing, and interacts in chat.", 
                  wraplength=500, justify="left").pack(anchor="w", pady=(0, 20))
        
        ttk.Button(prompt_tab, text="🎨 Open Advanced Prompt Editor", 
                   command=self.open_prompt_editor, style="Accent.TButton").pack(anchor="w", pady=10)
        
        ttk.Label(prompt_tab, text="Tip: Use the editor to add specific instructions for your target language or to change the tone of the AI tutor.", 
                  font=("Arial", 9, "italic"), foreground="gray", wraplength=500).pack(anchor="w", pady=20)
        
        # --- TAB 4: CLOUD SYNC ---
        sync_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(sync_tab, text="☁️ Cloud Sync (Dropbox)")
        
        ttk.Label(sync_tab, text="Dropbox Sync", font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(sync_tab, text="Sync your data via your private App Folder.", 
                  wraplength=500, justify="left").pack(anchor="w", pady=(0, 15))
        
        # Status indicator
        # self.sync_status_var = tk.StringVar(value="Not connected") # Moved to __init__
        status_frame = ttk.Frame(sync_tab)
        status_frame.pack(fill="x", pady=(0, 15))
        ttk.Label(status_frame, text="Status:").pack(side="left")
        ttk.Label(status_frame, textvariable=self.sync_status_var, font=("Arial", 10, "bold")).pack(side="left", padx=10)
        
        # Connect button
        connect_frame = ttk.Frame(sync_tab)
        connect_frame.pack(fill="x", pady=5)
        ttk.Button(connect_frame, text="🔗 Connect Dropbox", 
                   command=self._open_dropbox_auth).pack(side="left")
        ttk.Button(connect_frame, text="Unlink", 
                   command=self._disconnect_dropbox).pack(side="left", padx=10)
        
        # Sync actions
        ttk.Separator(sync_tab, orient="horizontal").pack(fill="x", pady=20)
        ttk.Label(sync_tab, text="Manual Sync Actions", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))
        
        action_frame = ttk.Frame(sync_tab)
        action_frame.pack(fill="x", pady=10)
        
        ttk.Button(action_frame, text="⬆️ Backup to Cloud", 
                   command=self._backup_to_cloud, width=20).pack(side="left", padx=5)
        ttk.Button(action_frame, text="⬇️ Restore from Cloud", 
                   command=self._restore_from_cloud, width=20).pack(side="left", padx=5)
        
        ttk.Label(sync_tab, text="⚠️ Backup will overwrite the cloud copy. Restore will merge changes.", 
                  font=("Arial", 9, "italic"), foreground="#CC5500", wraplength=500).pack(anchor="w", pady=15)
        
        # --- Safety & Checkpoints ---
        ttk.Separator(sync_tab, orient="horizontal").pack(fill="x", pady=20)
        ttk.Label(sync_tab, text="Safety & Checkpoints", font=("Arial", 11, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(sync_tab, text="Create a snapshot of your data before performing a manual sync to ensure you can revert if needed.", 
                  font=("Arial", 9), foreground="gray", wraplength=500).pack(anchor="w", pady=(0, 10))
        
        checkpoint_frame = ttk.Frame(sync_tab)
        checkpoint_frame.pack(fill="x", pady=5)
        
        ttk.Button(checkpoint_frame, text="💾 Local Checkpoint", 
                   command=lambda: self._create_checkpoint(cloud=False), width=20).pack(side="left", padx=5)
        ttk.Button(checkpoint_frame, text="☁️ Cloud Checkpoint", 
                   command=lambda: self._create_checkpoint(cloud=True), width=20).pack(side="left", padx=5)
        
        ttk.Button(sync_tab, text="📂 Open Backup Folder", 
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
        set_locale(lang_code)
        self.study_manager.set_ui_language(lang_code)
        # Refresh the current frame
        self.setup_ui()
        self.load_settings()
        # Also notify controller if it needs to refresh other parts (like title bars)
        if hasattr(self.controller, 'root'):
            self.controller.root.title(tr("app_title"))

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()

    def open_prompt_editor(self):
        editor = PromptEditorDialog(self.winfo_toplevel(), self.study_manager)
        editor.grab_set()

    def load_settings(self):
        # Load from StudyManager / Database
        self.study_lang_var.set(self.study_manager.study_language)
        self.native_lang_var.set(self.study_manager.native_language)
        
        current_model = self.study_manager.get_ollama_model()
        self.model_var.set(current_model if current_model else "")
        
        self.timeout_var.set(self.study_manager.get_request_timeout())
        self.preload_var.set(self.study_manager.get_preload_on_startup())

    def save_settings(self):
        try:
            # Update StudyManager & DB
            self.study_manager.set_native_language(self.native_lang_var.get().strip())
            self.study_manager.set_study_language(self.study_lang_var.get().strip())
            
            self.study_manager.set_ollama_model(self.model_var.get())
            self.study_manager.set_request_timeout(self.timeout_var.get())
            self.study_manager.set_preload_on_startup(self.preload_var.get())
            
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
            from src.services.conflict_dialog import ConflictResolverDialog
            from src.core.database import db # Singleton access
            
            # Setup Merger
            resolver_dialog_provider = lambda conflict_data: ConflictResolverDialog(self.winfo_toplevel(), conflict_data).show()
            merger = SyncMerger(db.db_path, temp_path, resolver_dialog_provider)
            
            stats = merger.perform_merge()
            
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
        

