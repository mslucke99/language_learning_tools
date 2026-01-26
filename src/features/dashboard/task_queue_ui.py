import tkinter as tk
from tkinter import ttk
import time

class TaskQueueDialog(tk.Toplevel):
    def __init__(self, parent, study_manager):
        super().__init__(parent)
        self.title("AI Task Queue Manager")
        self.geometry("700x500")
        self.study_manager = study_manager
        
        self.setup_ui()
        self.refresh_data()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Summary Header
        self.summary_label = ttk.Label(main_frame, text="Checking queue status...", font=("Segoe UI", 10, "bold"))
        self.summary_label.pack(fill="x", pady=(0, 10))
        
        # Task List
        columns = ("id", "type", "description", "status")
        self.tree = ttk.Treeview(main_frame, columns=columns, show="headings")
        self.tree.heading("id", text="Task ID")
        self.tree.heading("type", text="Type")
        self.tree.heading("description", text="Description")
        self.tree.heading("status", text="Status")
        
        self.tree.column("id", width=150)
        self.tree.column("type", width=100)
        self.tree.column("description", width=300)
        self.tree.column("status", width=100)
        
        self.tree.pack(fill="both", expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Actions
        btn_frame = ttk.Frame(main_frame, padding="10")
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="🔄 Refresh", command=self.refresh_data).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="🧹 Clear Completed", command=self.clear_completed).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close", command=self.destroy).pack(side="right", padx=5)

    def refresh_data(self):
        if not self.winfo_exists(): return
        
        status = self.study_manager.get_queue_status()
        self.summary_label.config(
            text=f"Queue: {status['queued']} pending | {status['active']} processing | {status['completed']} completed | {status['failed']} failed"
        )
        
        # Update Tree
        # For simplicity, we'll just re-populate. In a high-traffic app we'd diff.
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # 1. Active Tasks
        for t in status['active_info']:
            self.tree.insert("", "end", values=(t['id'], t['type'], t['description'], "PROCESSING"), tags=('processing',))
            
        # 2. Results (Queued/Completed/Failed) - Show last 30
        results = list(self.study_manager.processing_results.items())
        results.sort(key=lambda x: x[0], reverse=True) # Sort by ID (time-based)
        
        for task_id, res in results[:30]:
            if res['status'] == 'processing': continue # already shown in active
            status_str = res['status'].upper()
            self.tree.insert("", "end", values=(
                task_id, 
                res.get('type', 'N/A'), 
                res.get('description', 'AI Task'), 
                status_str
            ), tags=(res['status'],))

        self.tree.tag_configure('processing', foreground='blue')
        self.tree.tag_configure('completed', foreground='green')
        self.tree.tag_configure('failed', foreground='red')
        self.tree.tag_configure('queued', foreground='gray')
        
        # Auto-refresh every 2 seconds if active
        self.after(2000, self.refresh_data)

    def clear_completed(self):
        # We need a method in study_manager to clear results
        if hasattr(self.study_manager, 'clear_completed_tasks'):
            self.study_manager.clear_completed_tasks()
            self.refresh_data()
        else:
            # Inline fallback if method not yet added
            to_delete = [tid for tid, res in self.study_manager.processing_results.items() if res['status'] in ['completed', 'failed']]
            for tid in to_delete:
                del self.study_manager.processing_results[tid]
            self.refresh_data()
