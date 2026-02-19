import tkinter as tk
from tkinter import ttk, messagebox
from src.features.study_center.logic.study_manager import StudyManager
from src.core.ui_utils import setup_standard_header
from src.features.chat.ui.scenario_editor import ScenarioEditorDialog, ScenarioSelectorDialog
from src.core.localization import tr

class ChatDashboardFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.embedded = embedded
        self.setup_ui()
        
    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(self, tr("header_interactive_chat", "💬 Interactive Chat"), back_cmd=self.go_back)
        
        # Chat Mode Selection
        mode_frame = ttk.LabelFrame(self, text=tr("lbl_chat_mode", "Chat Mode"), padding=10)
        mode_frame.pack(fill="x", pady=10, padx=20)
        
        self.mode_var = tk.StringVar(value="topical")
        
        ttk.Radiobutton(mode_frame, text=tr("opt_topical", "Topical - Free conversation on any topic"), 
                       variable=self.mode_var, value="topical", 
                       command=self._on_mode_change).pack(anchor="w", pady=5)
        ttk.Radiobutton(mode_frame, text=tr("opt_roleplay", "Role-Play - Interactive scenario with characters"), 
                       variable=self.mode_var, value="roleplay",
                       command=self._on_mode_change).pack(anchor="w", pady=5)
        
        # New Chat Controls - Topical Mode
        self.topical_frame = ttk.LabelFrame(self, text=tr("lbl_start_topical", "Start New Topical Conversation"), padding=10)
        self.topical_frame.pack(fill="x", pady=10, padx=20)
        
        ttk.Label(self.topical_frame, text=tr("lbl_topic", "Conversation Topic:"), font=("Segoe UI", 10)).pack(side="left")
        self.topic_entry = ttk.Entry(self.topical_frame, width=40)
        self.topic_entry.pack(side="left", padx=5)
        self.topic_entry.insert(0, tr("msg_default_topic", "Ordering at a Cafe"))
        
        ttk.Button(self.topical_frame, text=tr("btn_start_chat", "Start Chat"), command=self._start_topical_chat).pack(side="left")
        
        # New Chat Controls - Roleplay Mode
        self.roleplay_frame = ttk.LabelFrame(self, text=tr("lbl_start_roleplay", "Start New Role-Play Session"), padding=10)
        self.roleplay_frame.pack(fill="x", pady=10, padx=20)
        self.roleplay_frame.pack_forget()  # Hidden by default
        
        ttk.Button(self.roleplay_frame, text=tr("btn_create_scenario", "Create New Scenario"), 
                  command=self._create_roleplay_scenario).pack(side="left", padx=2)
        ttk.Button(self.roleplay_frame, text=tr("btn_select_scenario", "Select Existing Scenario"), 
                  command=self._select_roleplay_scenario).pack(side="left", padx=2)
        
        # Selected scenario display
        self.selected_scenario_label = ttk.Label(self.roleplay_frame, text=tr("lbl_no_scenario", "No scenario selected"), 
                                                 foreground="gray", font=("Segoe UI", 9, "italic"))
        self.selected_scenario_label.pack(side="left", padx=10)
        
        self.selected_scenario_id = None
        
        # Session List
        ttk.Label(self, text=tr("lbl_recent_chats", "Recent Conversations:"), font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(20, 5), padx=20)
        
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
            ttk.Label(scrollable_frame, text=tr("msg_no_chat_history", "No history yet. Start a new chat above!")).pack(pady=20)
        
        for session in sessions:
            self._add_session_button(scrollable_frame, session)
    
    def _add_session_button(self, parent, session):
        """Add a session display and button."""
        s_frame = ttk.Frame(parent, relief="solid", borderwidth=1)
        s_frame.pack(fill="x", pady=5, padx=5)
        
        mode = session.get('mode', 'topical')
        mode_badge = "🎭" if mode == 'roleplay' else "💬"
        
        info = f"{mode_badge} {session['cur_topic']} ({session['study_language']})"
        date = session['last_updated'].split('T')[0]
        
        ttk.Label(s_frame, text=info, font=("Segoe UI", 11, "bold")).pack(side="left", padx=10, pady=10)
        ttk.Label(s_frame, text=date, font=("Segoe UI", 9)).pack(side="left", padx=10)
        
        ttk.Button(s_frame, text=tr("btn_continue", "Continue"), command=lambda s=session: self._open_chat_session(s['id'])).pack(side="right", padx=5)
    
    def _on_mode_change(self):
        """Handle mode selection change."""
        if self.mode_var.get() == "topical":
            self.topical_frame.pack(fill="x", pady=10, padx=20)
            self.roleplay_frame.pack_forget()
            self.selected_scenario_id = None
        else:
            self.topical_frame.pack_forget()
            self.roleplay_frame.pack(fill="x", pady=10, padx=20)
    
    def _start_topical_chat(self):
        """Start a topical chat session."""
        topic = self.topic_entry.get().strip()
        if not topic:
            messagebox.showwarning(tr("header_topic_required", "Topic Required"), tr("msg_enter_topic", "Please enter a conversation topic."))
            return
        session_id = self.study_manager.create_chat_session(topic)
        self._open_chat_session(session_id)
    
    def _create_roleplay_scenario(self):
        """Create a new roleplay scenario."""
        dialog = ScenarioEditorDialog(self, self.study_manager)
        if dialog.result:
            self.selected_scenario_id = dialog.result['id']
            self.selected_scenario_label.config(text=f"✓ {dialog.result['name']}", foreground="green")
            self._start_roleplay_chat()
    
    def _select_roleplay_scenario(self):
        """Select an existing roleplay scenario."""
        dialog = ScenarioSelectorDialog(self, self.study_manager)
        if dialog.result:
            self.selected_scenario_id = dialog.result
            scenario = self.study_manager.get_roleplay_scenario(dialog.result)
            self.selected_scenario_label.config(text=f"✓ {scenario['name']}", foreground="green")
            self._start_roleplay_chat()
    
    def _start_roleplay_chat(self):
        """Start a roleplay chat session."""
        if not self.selected_scenario_id:
            messagebox.showwarning(tr("header_scenario_required", "Scenario Required"), tr("msg_select_scenario_first", "Please select or create a scenario first."))
            return
        
        try:
            session_id = self.study_manager.create_roleplay_chat_session(self.selected_scenario_id)
            self._open_chat_session(session_id)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start roleplay: {e}")

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()

    def _open_chat_session(self, session_id):
        if hasattr(self.controller, 'show_active_chat'):
            self.controller.show_active_chat(session_id)
