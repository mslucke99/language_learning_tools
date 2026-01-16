import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from src.features.study_center.logic.study_manager import StudyManager
from src.core.ui_utils import setup_standard_header
from src.features.dashboard.prompt_editor_ui import PromptEditorDialog
from src.core.localization import tr, set_locale

class SettingsFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        
        self.ollama_available = study_manager.ollama_client is not None and study_manager.ollama_client.is_available()
        self.available_models = []
        
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        setup_standard_header(self, tr("header_settings", "⚙️ Application Settings"), back_cmd=self.go_back)
        
        # Main Notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        
        # --- TAB 1: GENERAL (Languages) ---
        gen_tab = ttk.Frame(self.notebook, padding="20")
        self.notebook.add(gen_tab, text=tr("tab_general", "General"))
        
        ttk.Label(gen_tab, text=tr("lbl_language_config", "Language Configuration"), font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 20))
        
        lang_grid = ttk.Frame(gen_tab)
        lang_grid.pack(fill="x")
        
        # Study Language (Target)
        ttk.Label(lang_grid, text=tr("lbl_study_lang", "Study Language (target):")).grid(row=0, column=0, sticky="w", pady=10)
        self.study_lang_var = tk.StringVar()
        self.study_lang_combo = ttk.Combobox(lang_grid, textvariable=self.study_lang_var, 
                                            values=["Spanish", "French", "German", "Japanese", "Korean", "Mandarin", "Italian", "Portuguese", "Russian", "Arabic", "Biblical Greek"],
                                            width=32, state="readonly")
        self.study_lang_combo.grid(row=0, column=1, sticky="w", padx=15)
        
        # Native Language (for definitions)
        ttk.Label(lang_grid, text=tr("lbl_native_lang", "Native Language (ui/def):")).grid(row=1, column=0, sticky="w", pady=10)
        self.native_lang_var = tk.StringVar()
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
        self.model_var = tk.StringVar()
        self.model_combo = ttk.Combobox(ai_grid, textvariable=self.model_var, state="readonly", width=32)
        self.model_combo.grid(row=0, column=1, sticky="w", padx=15)
        
        if self.ollama_available:
             try:
                 self.available_models = self.study_manager.ollama_client.get_available_models()
                 self.model_combo['values'] = self.available_models
             except:
                 self.model_combo['values'] = ["Error fetching models"]
        
        ttk.Label(ai_grid, text="Request Timeout (sec):").grid(row=1, column=0, sticky="w", pady=10)
        self.timeout_var = tk.IntVar(value=30)
        ttk.Spinbox(ai_grid, from_=5, to=300, increment=5, textvariable=self.timeout_var, width=10).grid(row=1, column=1, sticky="w", padx=15)
        
        self.preload_var = tk.BooleanVar()
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
