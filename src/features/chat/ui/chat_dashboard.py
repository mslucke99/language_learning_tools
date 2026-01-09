import tkinter as tk
from tkinter import ttk, messagebox
from src.features.study_center.logic.study_manager import StudyManager
from src.core.ui_utils import setup_standard_header

class ChatDashboardFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.embedded = embedded
        self.setup_ui()
        
    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(self, "💬 Interactive Chat", back_cmd=self.go_back)
        
        # New Chat Controls
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill="x", pady=10, padx=20)
        
        ttk.Label(ctrl_frame, text="Start New Conversation:", font=("Segoe UI", 11)).pack(side="left")
        self.topic_entry = ttk.Entry(ctrl_frame, width=40)
        self.topic_entry.pack(side="left", padx=5)
        self.topic_entry.insert(0, "Ordering at a Cafe")
        
        ttk.Button(ctrl_frame, text="Start Chat", command=self._start_new_chat).pack(side="left")
        
        # Session List
        ttk.Label(self, text="Recent Conversations:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(20, 5), padx=20)
        
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=20)
        
        canvas = tk.Canvas(list_frame)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Determine width for canvas content
        def _on_canvas_configure(event):
             canvas.itemconfig(canvas.find_withtag("all")[0], width=event.width)
        canvas.bind("<Configure>", _on_canvas_configure)
        
        sessions = self.study_manager.get_chat_sessions()
        if not sessions:
            ttk.Label(scrollable_frame, text="No history yet. Start a new chat above!").pack(pady=20)
        
        for session in sessions:
            s_frame = ttk.Frame(scrollable_frame, relief="solid", borderwidth=1)
            s_frame.pack(fill="x", pady=5, padx=5)
            
            info = f"{session['cur_topic']} ({session['study_language']})"
            date = session['last_updated'].split('T')[0]
            
            ttk.Label(s_frame, text=info, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=10)
            ttk.Label(s_frame, text=date, font=("Segoe UI", 9)).pack(side="left", padx=10)
            
            ttk.Button(s_frame, text="Continue", command=lambda s=session: self._open_chat_session(s['id'])).pack(side="right", padx=5)

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()

    def _start_new_chat(self):
        topic = self.topic_entry.get().strip()
        if not topic: return
        session_id = self.study_manager.create_chat_session(topic)
        self._open_chat_session(session_id)

    def _open_chat_session(self, session_id):
        if hasattr(self.controller, 'show_active_chat'):
            self.controller.show_active_chat(session_id)
