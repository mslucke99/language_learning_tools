import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from src.features.study_center.logic.study_manager import StudyManager
from src.core.ui_utils import setup_standard_header

class ActiveChatFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, session_id: int):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.active_session_id = session_id
        
        self.active_tasks = {}
        
        self.setup_ui()
        self._check_queue_status()
        
    def setup_ui(self):
        session_info = next((s for s in self.study_manager.get_chat_sessions() if s['id'] == self.active_session_id), None)
        title = f"💬 Chat: {session_info['cur_topic']}" if session_info else "Chat"
        setup_standard_header(self, title, back_cmd=self.go_back)
        
        paned = tk.PanedWindow(self, orient="horizontal", sashrelief="raised", sashwidth=4)
        paned.pack(fill="both", expand=True, pady=5)
        
        # --- LEFT: CHAT AREA ---
        chat_frame = ttk.Frame(paned, width=600)
        paned.add(chat_frame)
        
        self.chat_display = scrolledtext.ScrolledText(chat_frame, state="disabled", wrap="word", font=("Segoe UI", 11))
        self.chat_display.pack(fill="both", expand=True, pady=(0, 10))
        self.chat_display.tag_config("user", foreground="#007ACC", justify="right")
        self.chat_display.tag_config("assistant", foreground="#2E7D32")
        self.chat_display.tag_config("system", foreground="gray", font=("Segoe UI", 9, "italic"))
        
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill="x")
        
        self.chat_input = ttk.Entry(input_frame, font=("Segoe UI", 11))
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.chat_input.bind("<Return>", lambda e: self._send_message())
        
        self.send_btn = ttk.Button(input_frame, text="Send", command=self._send_message)
        self.send_btn.pack(side="right")
        
        # --- RIGHT: ANALYSIS TABS ---
        analysis_frame = ttk.Frame(paned, width=400)
        paned.add(analysis_frame)
        
        self.analysis_notebook = ttk.Notebook(analysis_frame)
        self.analysis_notebook.pack(fill="both", expand=True)
        
        self.feedback_tab = scrolledtext.ScrolledText(self.analysis_notebook, wrap="word", font=("Segoe UI", 10))
        self.vocab_tab = scrolledtext.ScrolledText(self.analysis_notebook, wrap="word", font=("Segoe UI", 10))
        self.grammar_tab = scrolledtext.ScrolledText(self.analysis_notebook, wrap="word", font=("Segoe UI", 10))
        
        self.analysis_notebook.add(self.feedback_tab, text="Feedback")
        self.analysis_notebook.add(self.vocab_tab, text="Vocabulary")
        self.analysis_notebook.add(self.grammar_tab, text="Grammar")
        
        self._refresh_chat_history()

    def go_back(self):
        if hasattr(self.controller, 'show_chat_dashboard'):
            self.controller.show_chat_dashboard()

    def _refresh_chat_history(self):
        messages = self.study_manager.get_chat_messages(self.active_session_id)
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == "user":
                self.chat_display.insert("end", f"You: {content}\n\n", "user")
            else:
                self.chat_display.insert("end", f"Tutor: {content}\n\n", "assistant")
                
            if msg.get('analysis'):
                try:
                    analysis = json.loads(msg['analysis'])
                    self._append_analysis(analysis)
                except:
                    pass
                    
        self.chat_display.see("end")
        self.chat_display.configure(state="disabled")

    def _append_analysis(self, analysis):
        if analysis.get('feedback'):
            self.feedback_tab.insert("end", f"--- New Feedback ---\n{analysis['feedback']}\n\n")
            self.feedback_tab.see("end")
        if analysis.get('vocab_section') or (analysis.get('suggestions') and analysis['suggestions'].get('flashcards')):
             self.vocab_tab.configure(state="normal")
             self.vocab_tab.delete("1.0", "end")
             
             # Add buttons for structured suggestions
             suggestions = analysis.get('suggestions', {})
             flashcards = suggestions.get('flashcards', [])
             
             if flashcards:
                 self.vocab_tab.insert("end", "--- Suggested Vocabulary ---\n")
                 for item in flashcards:
                     btn_text = f"➕ Add: {item['word']}"
                     # Create a clickable tag/button equivalent
                     # Tkinter Text widgets are tricky with buttons, so using tag_bind or window_create
                     # Simpler approach: Insert text description, then a button
                     self.vocab_tab.insert("end", f"• {item['word']}: {item['definition']}\n")
                     btn = ttk.Button(self.vocab_tab, text="Add", width=4, 
                                    command=lambda i=item: self._add_suggestion(i, 'word'))
                     self.vocab_tab.window_create("end", window=btn)
                     self.vocab_tab.insert("end", "\n\n")
             
             # Also show raw text if available, as fallback/context
             if analysis.get('vocab_section'):
                 self.vocab_tab.insert("end", "\n--- Full Analysis ---\n" + analysis['vocab_section'])
             
             self.vocab_tab.configure(state="disabled")
             
        if analysis.get('grammar_section') or (analysis.get('suggestions') and analysis['suggestions'].get('grammar')):
             self.grammar_tab.configure(state="normal")
             self.grammar_tab.delete("1.0", "end")
             
             suggestions = analysis.get('suggestions', {})
             grammar = suggestions.get('grammar', [])
             
             if grammar:
                 self.grammar_tab.insert("end", "--- Suggested Grammar ---\n")
                 for item in grammar:
                     self.grammar_tab.insert("end", f"• {item['title']}\n")
                     btn = ttk.Button(self.grammar_tab, text="Add", width=4, 
                                    command=lambda i=item: self._add_suggestion(i, 'grammar'))
                     self.grammar_tab.window_create("end", window=btn)
                     self.grammar_tab.insert("end", f"\n{item['explanation'][:100]}...\n\n")

             if analysis.get('grammar_section'):
                 self.grammar_tab.insert("end", "\n--- Full Analysis ---\n" + analysis['grammar_section'])
                 
             self.grammar_tab.configure(state="disabled")

    def _add_suggestion(self, item, type_name):
        try:
            if type_name == 'word':
                # Check duplicate
                existing = self.study_manager.db.find_flashcard_by_question(item['word'])
                if existing:
                    if not messagebox.askyesno("Duplicate", f"Word '{item['word']}' exists. Add anyway?"):
                        return

                content_id = self.study_manager.db.add_imported_content(
                    'word', item['word'], url="Chat Suggestion",
                    title="Interactive Chat", language=self.study_manager.study_language
                )
                self.study_manager.add_word_definition(
                    content_id, item['definition'], definition_language=self.study_manager.native_language
                )
                messagebox.showinfo("Saved", f"Added '{item['word']}'")
                
            elif type_name == 'grammar':
                self.study_manager.db.add_grammar_entry(
                    item['title'], item['explanation'], language=self.study_manager.study_language, tags="chat-generated"
                )
                messagebox.showinfo("Saved", f"Added '{item['title']}'")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add: {e}")

    def _send_message(self):
        msg = self.chat_input.get().strip()
        if not msg: return
        
        self.chat_input.delete(0, "end")
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"You: {msg}\n\n", "user")
        self.chat_display.insert("end", "Tutor is typing...\n\n", "system")
        self.chat_display.configure(state="disabled")
        self.chat_display.see("end")
        
        # We need item_id=0 or similar for generic chat, but logic uses context.
        # queue_generation_task arguments: task_type, item_id, **kwargs
        # For chat, item_id isn't directly used in study_manager.queue... for context retrieval unless specially handled.
        # Wait, get_chat_messages uses active_session_id.
        # study_manager.queue_generation_task calls generate_chat_response(session_id, user_message) if type is 'chat_message'.
        # We need to pass session_id somehow. study_manager.py logic needs to support it.
        # Looking at study_manager.py (not visible fully but assumed from `study_gui.py` usage):
        # `queue_generation_task('chat_message', 0, ...)` and args passed via kwargs to worker.
        
        task_id = self.study_manager.queue_generation_task(
            'chat_message',
            0, # Placeholder
            session_id=self.active_session_id,
            user_message=msg
        )
        
        self.active_tasks[task_id] = {'type': 'chat_message'}

    def _check_queue_status(self):
        completed = []
        for task_id in list(self.active_tasks.keys()):
             status = self.study_manager.get_task_status(task_id)
             if status['status'] in ['completed', 'failed']:
                  completed.append(task_id)
                  if status['status'] == 'completed':
                       self._handle_chat_response(status['result'])
                  elif status['status'] == 'failed':
                       self._handle_chat_error(status.get('error'))
                       
        for t in completed: del self.active_tasks[t]
        self.after(500, self._check_queue_status) # Check faster for chat

    def _handle_chat_response(self, result):
        # result is likely the response string or dict.
        # If StudyManager processes it and saves to DB, we just refresh.
        # But if result contains the text to display immediately:
        # Actually `generate_chat_response` usually returns the text answer.
        # And it saves to DB. So refreshing history is safest.
        self._refresh_chat_history()

    def _handle_chat_error(self, error):
        self.chat_display.configure(state="normal")
        self.chat_display.insert("end", f"Error: {error}\n\n", "system")
        self.chat_display.configure(state="disabled")
