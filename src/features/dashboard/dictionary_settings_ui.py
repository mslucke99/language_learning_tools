import tkinter as tk
from tkinter import ttk, messagebox
import threading
from src.core.localization import tr
from src.services.dictionary.dictionary_manager import DictionaryManager

class DictionarySettingsFrame(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding="20")
        self.manager = DictionaryManager()
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        ttk.Label(self, text=tr("lbl_dict_management", "Offline Dictionaries"), font=("Arial", 12, "bold")).pack(anchor="w", pady=(0, 10))
        ttk.Label(self, text=tr("lbl_dict_desc", "Download dictionaries to enable offline definitions and faster sentence analysis."), 
                  wraplength=500, justify="left").pack(anchor="w", pady=(0, 20))

        # List of dictionaries
        cols = ("Language", "Status", "Action")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=8)
        self.tree.heading("Language", text="Language")
        self.tree.heading("Status", text="Status")
        self.tree.heading("Action", text="Action")
        
        self.tree.column("Language", width=150)
        self.tree.column("Status", width=120)
        self.tree.column("Action", width=100)
        
        self.tree.pack(fill="x", expand=True)
        self.tree.bind("<Double-1>", self._on_item_action)

        # Progress elements
        self.progress_frame = ttk.Frame(self)
        self.progress_frame.pack(fill="x", pady=10)
        
        self.lbl_progress = ttk.Label(self.progress_frame, text="")
        self.lbl_progress.pack(side="left")
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate")
        self.progress_bar.pack(side="right", fill="x", expand=True, padx=10)
        self.progress_frame.pack_forget() # Hide initially

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text=tr("btn_refresh_list", "Refresh List"), command=self.refresh_list).pack(side="left")

    def refresh_list(self):
        # Clear
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Hardcoded list of supported Kaikki dictionaries for now
        # In a real app, we might fetch this from a JSON file on GitHub
        languages = [
            ("English", "en"),
            ("Spanish", "es"),
            ("French", "fr"),
            ("German", "de"),
            ("Japanese", "ja"),
            ("Korean", "ko"),
            ("Chinese", "zh"),
            ("Italian", "it"),
            ("Portuguese", "pt"),
            ("Russian", "ru"),
        ]
        
        for name, code in languages:
            installed = self.manager.is_language_installed(code)
            status = "Installed ✅" if installed else "Not Installed"
            action = "Delete" if installed else "Download"
            self.tree.insert("", "end", values=(name, status, action), tags=(code,))
            
    def _on_item_action(self, event):
        item = self.tree.selection()[0]
        values = self.tree.item(item, "values")
        lang_name, status, action = values
        code = self.tree.item(item, "tags")[0]
        
        if action == "Download":
            self._start_download(lang_name, code)
        elif action == "Delete":
            if messagebox.askyesno("Confirm Delete", f"Delete {lang_name} dictionary?"):
                # TODO: Implement delete in Manager
                # For now just re-init DB or delete rows? 
                # Manager needs a delete method.
                pass

    def _start_download(self, lang_name, lang_code):
        self.progress_frame.pack(fill="x", pady=10)
        self.progress_bar['value'] = 0
        self.lbl_progress.config(text=f"Starting download for {lang_name}...")
        
        def run():
            try:
                def cb(curr, total, msg):
                    self.lbl_progress.config(text=msg)
                    if total > 0:
                        self.progress_bar['value'] = (curr / total) * 100
                    else:
                        self.progress_bar.config(mode="indeterminate")
                        self.progress_bar.start(10)

                self.manager.download_and_import(lang_name, lang_code, cb)
                self.after(0, lambda: self._download_complete(lang_name))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Error", f"Download failed: {e}"))
                self.after(0, lambda: self.progress_frame.pack_forget())

        threading.Thread(target=run, daemon=True).start()

    def _download_complete(self, lang_name):
        self.progress_frame.pack_forget()
        self.progress_bar.stop()
        messagebox.showinfo("Success", f"{lang_name} dictionary installed successfully!")
        self.refresh_list()
