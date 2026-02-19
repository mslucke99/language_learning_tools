import tkinter as tk
from tkinter import ttk, messagebox
import threading
from src.core.localization import tr
from src.services.text.vocab_calibration import VocabCalibrationService

class CalibrationDialog(tk.Toplevel):
    def __init__(self, parent, db, lang_code="ko", on_complete=None):
        super().__init__(parent)
        self.db = db
        self.lang_code = lang_code
        self.on_complete = on_complete
        self.service = VocabCalibrationService(db)
        
        # Get display name for language
        self.lang_name = VocabCalibrationService.DISPLAY_NAMES.get(lang_code, lang_code)
        
        self.title(f"{self.lang_name} - " + tr("title_vocab_calibration", "Vocabulary Calibration"))
        self.geometry("500x520")
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Header
        ttk.Label(main_frame, text=tr("lbl_calibration_intro", f"Let's calibrate your {self.lang_name} vocabulary!"), 
                 font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 10))
        
        ttk.Label(main_frame, text=tr("lbl_calibration_desc", 
                 f"To help us find the best {self.lang_name} sentences for you, we need to know roughly how many words you already know."),
                 wraplength=450).pack(anchor="w", pady=(0, 20))
                 
        # Level Selection
        ttk.Label(main_frame, text=tr("lbl_select_level", "Select your approximate level:")).pack(anchor="w")
        
        self.level_var = tk.StringVar(value="A1")
        levels = [
            ("Absolute Beginner (0 words)", "ABSOLUTE_BEGINNER"),
            ("Introductory (~100 words)", "INTRODUCTORY"),
            ("A1 - Beginner (~500 words)", "A1"),
            ("A2 - Elementary (~1,500 words)", "A2"),
            ("B1 - Intermediate (~3,000 words)", "B1"),
            ("B2 - Upper Intermediate (~5,000 words)", "B2"),
            ("C1 - Advanced (~8,000 words)", "C1"),
            ("C2 - Mastery (~12,000 words)", "C2")
        ]
        
        for text, val in levels:
            ttk.Radiobutton(main_frame, text=text, variable=self.level_var, value=val).pack(anchor="w", padx=20, pady=2)
            
        # Checkbox for existing cards
        self.scan_cards_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(main_frame, text=tr("chk_scan_flashcards", "Also include words from my flashcards"), 
                       variable=self.scan_cards_var).pack(anchor="w", pady=(20, 10))
                       
        # Progress
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_label = ttk.Label(self.progress_frame, text="")
        self.progress_label.pack(fill="x")
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate")
        self.progress_bar.pack(fill="x", pady=5)
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side="bottom", fill="x", pady=20)
        
        ttk.Button(btn_frame, text=tr("btn_start_calibration", "Start Calibration"), 
                  command=self.start_calibration).pack(side="right")
        ttk.Button(btn_frame, text=tr("btn_cancel", "Cancel"), command=self.destroy).pack(side="right", padx=10)

    def start_calibration(self):
        level = self.level_var.get()
        lang = self.lang_code
        scan_db = self.scan_cards_var.get()
        
        self.progress_frame.pack(fill="x", pady=10)
        
        def run():
            total_added = 0
            
            # 1. Frequency List
            try:
                def cb(curr, total, msg):
                    if total > 0:
                        self.update_progress(msg, (curr/total)*50) # First 50%
                    else:
                        self.update_progress(msg, 50)
                    
                added = self.service.calibrate_from_level(lang, level, cb)
                total_added += added
            except Exception as e:
                print(f"Error seeding frequency: {e}")
                
            # 2. Existing Cards
            if scan_db:
                self.update_progress("Scanning flashcards...", 60)
                try:
                    db_added = self.service.calibrate_from_db(lang)
                    total_added += db_added
                except Exception as e:
                    print(f"Error scanning DB: {e}")
            
            self.update_progress("Done!", 100)
            self.after(0, lambda: self.finish(total_added))
            
        threading.Thread(target=run, daemon=True).start()

    def update_progress(self, msg, val):
        self.after(0, lambda: self._update_ui(msg, val))
        
    def _update_ui(self, msg, val):
        self.progress_label.config(text=msg)
        self.progress_bar['value'] = val
        
    def finish(self, count):
        messagebox.showinfo("Calibration Complete", f"Successfully marked {count} words as known!")
        if self.on_complete:
            self.on_complete()
        self.destroy()
