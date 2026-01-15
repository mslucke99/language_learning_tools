"""
Conflict Resolver Dialog
------------------------
Tkinter dialog for user to resolve sync conflicts.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
from src.services.sync_merger import ConflictInfo, ConflictResolution

class ConflictResolverDialog(tk.Toplevel):
    """Dialog for resolving a single sync conflict."""
    
    def __init__(self, parent, conflict: ConflictInfo):
        super().__init__(parent)
        self.conflict = conflict
        self.result: Optional[ConflictResolution] = None
        
        self.title("Sync Conflict")
        self.geometry("500x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self.center_on_parent(parent)
    
    def center_on_parent(self, parent):
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")
    
    def _create_widgets(self):
        # Header
        header = ttk.Label(
            self, 
            text="⚠️ Conflict Detected",
            font=("Segoe UI", 14, "bold")
        )
        header.pack(pady=(15, 5))
        
        # Description
        desc = ttk.Label(
            self,
            text=f"{self.conflict.description}\nwas modified on both devices.",
            justify="center"
        )
        desc.pack(pady=5)
        
        # Comparison Frame
        compare_frame = ttk.Frame(self)
        compare_frame.pack(fill="x", padx=20, pady=10)
        
        # Local Info
        local_frame = ttk.LabelFrame(compare_frame, text="Local (This PC)")
        local_frame.pack(side="left", fill="both", expand=True, padx=5)
        ttk.Label(local_frame, text=f"Modified: {self.conflict.local_modified[:19]}").pack(anchor="w", padx=5, pady=2)
        
        # Remote Info
        remote_frame = ttk.LabelFrame(compare_frame, text="Remote (Cloud)")
        remote_frame.pack(side="right", fill="both", expand=True, padx=5)
        ttk.Label(remote_frame, text=f"Modified: {self.conflict.remote_modified[:19]}").pack(anchor="w", padx=5, pady=2)
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        ttk.Button(
            btn_frame, text="Keep Local",
            command=lambda: self._resolve(ConflictResolution.KEEP_LOCAL)
        ).pack(side="left", padx=5)
        
        ttk.Button(
            btn_frame, text="Keep Remote",
            command=lambda: self._resolve(ConflictResolution.KEEP_REMOTE)
        ).pack(side="left", padx=5)
        
        # "Always" buttons
        always_frame = ttk.Frame(self)
        always_frame.pack(fill="x", padx=20, pady=5)
        
        ttk.Button(
            always_frame, text="Always Keep Local",
            command=lambda: self._resolve(ConflictResolution.ALWAYS_LOCAL)
        ).pack(side="left", padx=5)
        
        ttk.Button(
            always_frame, text="Always Keep Remote",
            command=lambda: self._resolve(ConflictResolution.ALWAYS_REMOTE)
        ).pack(side="left", padx=5)
        
        # Cancel
        ttk.Button(
            self, text="Cancel Sync",
            command=lambda: self._resolve(ConflictResolution.CANCEL)
        ).pack(pady=10)
    
    def _resolve(self, resolution: ConflictResolution):
        self.result = resolution
        self.destroy()


def show_conflict_dialog(parent, conflict: ConflictInfo) -> ConflictResolution:
    """Show conflict dialog and return user's choice."""
    dialog = ConflictResolverDialog(parent, conflict)
    parent.wait_window(dialog)
    return dialog.result or ConflictResolution.CANCEL
