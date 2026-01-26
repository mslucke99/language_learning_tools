import tkinter as tk
from tkinter import ttk, messagebox
import webbrowser
from src.services.dropbox_sync import DropboxSyncManager

class DropboxAuthDialog(tk.Toplevel):
    """
    Dialog to handle the Dropbox PKCE "Paste Code" flow.
    """
    def __init__(self, parent, dropbox_manager: DropboxSyncManager, on_success):
        super().__init__(parent)
        self.dropbox_manager = dropbox_manager
        self.on_success = on_success
        
        self.title("Connect to Dropbox")
        self.geometry("500x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._center_window(parent)
        
    def _center_window(self, parent):
        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{x}+{y}")
        except:
            pass

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Step 1: Open Browser
        step1_frame = ttk.LabelFrame(main_frame, text="Step 1: Application Approval", padding=10)
        step1_frame.pack(fill="x", pady=10)
        
        ttk.Label(step1_frame, text="Click to open Dropbox in your browser.\nLog in and click 'Allow' to get your access code.", 
                  wraplength=400, justify="left").pack(anchor="w", pady=5)
        
        ttk.Button(step1_frame, text="🌐 Open Dropbox Auth Page", 
                   command=self._open_browser).pack(anchor="w", pady=5)
        
        # Step 2: Paste Code
        step2_frame = ttk.LabelFrame(main_frame, text="Step 2: Enter Access Code", padding=10)
        step2_frame.pack(fill="x", pady=10)
        
        ttk.Label(step2_frame, text="Paste the code shown in your browser:").pack(anchor="w")
        
        self.code_entry = ttk.Entry(step2_frame, width=50)
        self.code_entry.pack(fill="x", pady=5)
        self.code_entry.bind("<Return>", lambda e: self._submit_code())
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(btn_frame, text="Connect", command=self._submit_code, style="Accent.TButton").pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")
        
    def _open_browser(self):
        url = self.dropbox_manager.get_auth_url()
        webbrowser.open(url)
        self.code_entry.focus_set()

    def _submit_code(self):
        code = self.code_entry.get().strip()
        if not code:
            messagebox.showwarning("Input Required", "Please enter the access code.")
            return
            
        # UI Feedback
        self.config(cursor="wait")
        self.update()
        
        success, message = self.dropbox_manager.finish_auth(code)
        
        self.config(cursor="")
        
        if success:
            messagebox.showinfo("Success", message)
            self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Connection Failed", message)
