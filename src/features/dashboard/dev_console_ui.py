import tkinter as tk
from tkinter import ttk, scrolledtext
import json

class DevConsoleDialog(tk.Toplevel):
    def __init__(self, parent, study_manager):
        super().__init__(parent)
        self.title("🚀 Developer Console - LLM Activity")
        self.geometry("1000x700")
        self.study_manager = study_manager
        
        self.setup_ui()
        self.refresh_logs()
        
    def setup_ui(self):
        # MAIN PANED WINDOW (List on top, Details on bottom)
        self.paned = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self.paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # TOP FRAME: Log List
        list_frame = ttk.Frame(self.paned)
        self.paned.add(list_frame, weight=1)
        
        cols = ("time", "type", "desc", "dur", "status")
        self.tree = ttk.Treeview(list_frame, columns=cols, show="headings", height=8)
        self.tree.heading("time", text="Time")
        self.tree.heading("type", text="Type")
        self.tree.heading("desc", text="Description")
        self.tree.heading("dur", text="Duration")
        self.tree.heading("status", text="Status")
        
        self.tree.column("time", width=80)
        self.tree.column("type", width=120)
        self.tree.column("desc", width=250)
        self.tree.column("dur", width=80)
        self.tree.column("status", width=80)
        
        self.tree.pack(fill="both", expand=True, side="left")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scroll.set)
        
        # BOTTOM FRAME: Details
        self.details_tab = ttk.Notebook(self.paned)
        self.paned.add(self.details_tab, weight=2)
        
        # Tab 1: Rendered Prompt
        self.prompt_text = scrolledtext.ScrolledText(self.details_tab, font=("Consolas", 10), wrap="word", bg="#1e1e1e", fg="#d4d4d4")
        self.details_tab.add(self.prompt_text, text="📝 Rendered Prompt")
        
        # Tab 2: Raw Response
        self.response_text = scrolledtext.ScrolledText(self.details_tab, font=("Consolas", 10), wrap="word", bg="#1e1e1e", fg="#d4d4d4")
        self.details_tab.add(self.response_text, text="🤖 Raw Response")
        
        # Tab 3: Stats/Metadata
        self.stats_text = scrolledtext.ScrolledText(self.details_tab, font=("Segoe UI", 10), wrap="word")
        self.details_tab.add(self.stats_text, text="📊 Activity Stats")
        
        # Bottom Actions
        btn_frame = ttk.Frame(self, padding=5)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="🔄 Refresh Logs", command=self.refresh_logs).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="📋 Copy Prompt", command=self._copy_prompt).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🤖 Copy Raw", command=self._copy_raw).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right", padx=5)

    def refresh_logs(self):
        if not self.winfo_exists(): return
        
        logs = self.study_manager.get_debug_logs()
        
        # Clear existing
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Reverse to show newest at top
        for i, log in enumerate(reversed(logs)):
            status = "ERROR" if log.get('error') else "OK"
            self.tree.insert("", "end", iid=str(len(logs)-1-i), values=(
                log['timestamp'], log['type'], log.get('description', ''), log['duration'], status
            ))

    def _on_select(self, event):
        selected = self.tree.selection()
        if not selected: return
        
        idx = int(selected[0])
        logs = self.study_manager.get_debug_logs()
        if idx >= len(logs): return
        
        log = logs[idx]
        
        # Update Prompt
        self.prompt_text.delete("1.0", tk.END)
        self.prompt_text.insert("1.0", log['prompt'])
        
        # Update Response
        self.response_text.delete("1.0", tk.END)
        self.response_text.insert("1.0", log['raw_response'])
        
        # Update Stats
        self.stats_text.delete("1.0", tk.END)
        stats = f"Task: {log['type']}\n"
        stats += f"Description: {log.get('description', 'N/A')}\n"
        stats += f"Timestamp: {log['timestamp']}\n"
        stats += f"Duration: {log['duration']}\n"
        if log.get('error'):
            stats += f"Error: {log['error']}\n"
        self.stats_text.insert("1.0", stats)

    def _copy_prompt(self):
        self.clipboard_clear()
        self.clipboard_append(self.prompt_text.get("1.0", tk.END))
        
    def _copy_raw(self):
        self.clipboard_clear()
        self.clipboard_append(self.response_text.get("1.0", tk.END))
