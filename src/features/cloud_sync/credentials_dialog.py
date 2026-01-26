import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import shutil
import os
from pathlib import Path
from typing import Optional, Callable

# Try to import CloudSyncManager constants
from src.services.cloud_sync import CONFIG_DIR, CREDENTIALS_FILE, CloudSyncManager

class CredentialsManagerDialog(tk.Toplevel):
    def __init__(self, parent, cloud_sync_manager: CloudSyncManager, on_update: Callable[[], None]):
        super().__init__(parent)
        self.cloud_sync = cloud_sync_manager
        self.on_update = on_update
        
        self.title("Google Drive Credentials")
        self.geometry("500x400")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        self._center_window(parent) # Assuming helper exists or just center manually
        
    def _center_window(self, parent):
        self.update_idletasks()
        try:
            x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
            y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{x}+{y}")
        except:
             # Fallback if parent not fully realized
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = (screen_width - 500) // 2
            y = (screen_height - 400) // 2
            self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Header
        ttk.Label(main_frame, text="Manage Credentials", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 10))
        
        # Explanation
        info_text = (
            "To sync with Google Drive, you need a 'credentials.json' file from the Google Cloud Console.\n\n"
            "This file contains your 'Client ID' and 'Client Secret'."
        )
        ttk.Label(main_frame, text=info_text, wraplength=450, justify="left").pack(anchor="w", pady=(0, 20))
        
        # Current Status
        self.status_frame = ttk.LabelFrame(main_frame, text="Current Status", padding="10")
        self.status_frame.pack(fill="x", pady=(0, 20))
        
        self.status_label = ttk.Label(self.status_frame, text="Checking...", font=("Segoe UI", 10))
        self.status_label.pack(anchor="w")
        self._update_status()

        # Actions Frame
        actions_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
        actions_frame.pack(fill="x", expand=True)
        
        ttk.Button(actions_frame, text="📂 Import credentials.json", 
                   command=self._import_file, width=25).pack(pady=5)
                   
        ttk.Button(actions_frame, text="✏️ Enter ID/Secret Manually", 
                   command=self._manual_entry, width=25).pack(pady=5)
                   
        ttk.Separator(actions_frame, orient="horizontal").pack(fill="x", pady=10)
        
        ttk.Button(actions_frame, text="🗑️ Clear Credentials", 
                   command=self._clear_credentials, style="Danger.TButton").pack(pady=5)
        
        # Footer
        ttk.Button(main_frame, text="Close", command=self.destroy).pack(side="bottom", pady=(10, 0))

    def _update_status(self):
        if hasattr(self.cloud_sync, 'has_credentials_file') and self.cloud_sync.has_credentials_file():
            self.status_label.config(text="✅ Credentials file found.", foreground="green")
        else:
            self.status_label.config(text="❌ No credentials file found.", foreground="red")

    def _import_file(self):
        filepath = filedialog.askopenfilename(
            title="Select credentials.json",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not filepath:
            return
            
        try:
            # Validate JSON structure
            with open(filepath, 'r') as f:
                data = json.load(f)
                if 'installed' not in data and 'web' not in data:
                    raise ValueError("Invalid credentials format. Missing 'installed' or 'web' key.")
            
            # Copy file
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            shutil.copy2(filepath, CREDENTIALS_FILE)
            
            messagebox.showinfo("Success", "Credentials imported successfully!")
            self._update_status()
            self.on_update()
            
        except json.JSONDecodeError:
            messagebox.showerror("Error", "Selected file is not valid JSON.")
        except ValueError as ve:
            messagebox.showerror("Error", str(ve))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import credentials: {e}")

    def _manual_entry(self):
        ManualEntryDialog(self, self._on_manual_params_provided)

    def _on_manual_params_provided(self, client_id, client_secret):
        try:
            data = {
                "installed": {
                    "client_id": client_id,
                    "project_id": "language-learning-suite", # Placeholder, usually not critical for auth flow
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "client_secret": client_secret,
                    "redirect_uris": ["http://localhost"]
                }
            }
            
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CREDENTIALS_FILE, 'w') as f:
                json.dump(data, f, indent=4)
                
            messagebox.showinfo("Success", "Credentials saved successfully!")
            self._update_status()
            self.on_update()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save credentials: {e}")

    def _clear_credentials(self):
        if not self.cloud_sync.has_credentials_file():
            return

        confirm = messagebox.askyesno("Confirm Clear", 
                                      "Are you sure you want to delete the credentials.json file?\n"
                                      "You will need to re-import it to sync again.")
        if confirm:
            try:
                if CREDENTIALS_FILE.exists():
                    os.remove(CREDENTIALS_FILE)
                
                # Also disconnect properly
                self.cloud_sync.disconnect()
                
                self._update_status()
                self.on_update()
                messagebox.showinfo("Cleared", "Credentials removed.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove credentials: {e}")


class ManualEntryDialog(tk.Toplevel):
    def __init__(self, parent, on_submit):
        super().__init__(parent)
        self.on_submit = on_submit
        self.title("Enter Client ID & Secret")
        self.geometry("450x250")
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        
        # Center
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        frame = ttk.Frame(self, padding=20)
        frame.pack(fill="both", expand=True)
        
        ttk.Label(frame, text="Client ID:").pack(anchor="w")
        self.id_entry = ttk.Entry(frame, width=50)
        self.id_entry.pack(fill="x", pady=(0, 10))
        
        ttk.Label(frame, text="Client Secret:").pack(anchor="w")
        self.secret_entry = ttk.Entry(frame, width=50, show="*") # Mask secret? Maybe not needed for API keys but good practice
        self.secret_entry.pack(fill="x", pady=(0, 20))
        
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="Save", command=self._submit).pack(side="right", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="right")

    def _submit(self):
        client_id = self.id_entry.get().strip()
        client_secret = self.secret_entry.get().strip()
        
        if not client_id or not client_secret:
            messagebox.showwarning("Missing Info", "Please enter both Client ID and Client Secret.")
            return
            
        self.on_submit(client_id, client_secret)
        self.destroy()
