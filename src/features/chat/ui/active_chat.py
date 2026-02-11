import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from src.features.study_center.logic.study_manager import StudyManager
from src.core.ui_utils import setup_standard_header
from src.core.ui.related_items_panel import add_suggestion_to_storage
from src.core.localization import tr
from src.services.dictionary.dictionary_manager import DictionaryEngine

class ActiveChatFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, session_id: int):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.active_session_id = session_id
        
        self.active_session_id = session_id
        
        self.dict_engine = DictionaryEngine() # Initialize dictionary engine
        self.active_tasks = {}
        
        self.setup_ui()
        self._check_queue_status()
        
    def setup_ui(self):
        session_info = next((s for s in self.study_manager.get_chat_sessions() if s['id'] == self.active_session_id), None)
        mode = session_info.get('mode', 'topical') if session_info else 'topical'
        title_text = tr("header_chat_with_topic", "💬 Chat: {topic}", topic=session_info['cur_topic'] if session_info else "...")
        setup_standard_header(self, title_text, back_cmd=self.go_back)
        
        paned = tk.PanedWindow(self, orient="horizontal", sashrelief="raised", sashwidth=4)
        paned.pack(fill="both", expand=True, pady=5)
        
        # --- LEFT: CHAT AREA ---
        chat_frame = ttk.Frame(paned, width=600)
        paned.add(chat_frame)
        
        self.chat_display = scrolledtext.ScrolledText(chat_frame, state="disabled", wrap="word", font=("Segoe UI", 11))
        self.chat_display.pack(fill="both", expand=True, pady=(0, 10))
        self.chat_display.tag_config("user", foreground="#007ACC", justify="right")
        self.chat_display.tag_config("assistant", foreground="#2E7D32")
        self.chat_display.tag_config("character", foreground="#8B008B", font=("Segoe UI", 10, "bold"))  # For roleplay characters
        self.chat_display.tag_config("character", foreground="#8B008B", font=("Segoe UI", 10, "bold"))  # For roleplay characters
        self.chat_display.tag_config("system", foreground="gray", font=("Segoe UI", 9, "italic"))
        
        # Context Menu
        self.chat_display.bind("<Button-3>", self._on_right_click)
        
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill="x")
        
        self.chat_input = ttk.Entry(input_frame, font=("Segoe UI", 11))
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.chat_input.bind("<Return>", lambda e: self._send_message())
        
        self.send_btn = ttk.Button(input_frame, text=tr("btn_send", "Send"), command=self._send_message)
        self.send_btn.pack(side="right")
        
        # --- RIGHT: ANALYSIS TABS ---
        analysis_frame = ttk.Frame(paned, width=400)
        paned.add(analysis_frame)
        
        self.analysis_notebook = ttk.Notebook(analysis_frame)
        self.analysis_notebook.pack(fill="both", expand=True)
        
        self.feedback_tab = scrolledtext.ScrolledText(self.analysis_notebook, wrap="word", font=("Segoe UI", 10))
        self.vocab_tab = scrolledtext.ScrolledText(self.analysis_notebook, wrap="word", font=("Segoe UI", 10))
        self.grammar_tab = scrolledtext.ScrolledText(self.analysis_notebook, wrap="word", font=("Segoe UI", 10))
        
        self.analysis_notebook.add(self.feedback_tab, text=tr("tab_feedback", "Feedback"))
        self.analysis_notebook.add(self.vocab_tab, text=tr("tab_vocab", "Vocabulary"))
        self.analysis_notebook.add(self.grammar_tab, text=tr("tab_grammar", "Grammar"))
        
        self._refresh_chat_history()

    def go_back(self):
        if hasattr(self.controller, 'show_chat_dashboard'):
            self.controller.show_chat_dashboard()

    def _refresh_chat_history(self):
        messages = self.study_manager.get_chat_messages(self.active_session_id)
        session = next((s for s in self.study_manager.get_chat_sessions() if s['id'] == self.active_session_id), None)
        mode = session.get('mode', 'topical') if session else 'topical'
        
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        
        for msg in messages:
            role = msg['role']
            content = msg['content']
            
            if role == "user":
                self.chat_display.insert("end", f"{tr('lbl_you', 'You')}: {content}\n\n", "user")
            else:
                # For roleplay mode, display multi-character dialogue with formatting
                if mode == 'roleplay' and '**' in content:
                    # Content already formatted with character names
                    self.chat_display.insert("end", f"{content}\n\n", "character")
                else:
                    self.chat_display.insert("end", f"{tr('lbl_tutor', 'Tutor')}: {content}\n\n", "assistant")
                
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
                     btn = ttk.Button(self.grammar_tab, text=tr("btn_add", "Add"), width=4, 
                                    command=lambda i=item: self._add_suggestion(i, 'grammar'))
                     self.grammar_tab.window_create("end", window=btn)
                     self.grammar_tab.insert("end", f"\n{item['explanation'][:100]}...\n\n")

             if analysis.get('grammar_section'):
                 self.grammar_tab.insert("end", "\n--- Full Analysis ---\n" + analysis['grammar_section'])
                 
             self.grammar_tab.configure(state="disabled")

    def _add_suggestion(self, item, type_name):
        """Add a suggestion using the shared utility."""
        try:
            # Check for duplicates for word type
            if type_name == 'word':
                existing = self.study_manager.db.find_flashcard_by_question(item.get('word', ''))
                if existing:
                    if not messagebox.askyesno(tr("msg_duplicate", "Duplicate"), tr("msg_word_exists", "Word '{word}' exists. Add anyway?", word=item['word'])):
                        return
            
            success = add_suggestion_to_storage(
                self.study_manager.db,
                self.study_manager,
                item,
                type_name,
                source="Chat Suggestion"
            )
            
            if success:
                label = item.get('word', '') if type_name == 'word' else item.get('title', '')
                messagebox.showinfo(tr("msg_success", "Saved"), tr("msg_saved", "Added '{label}'", label=label))
            else:
                messagebox.showerror(tr("error_title", "Error"), tr("error_failed_to_add", "Failed to add item"))
                
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

    def _on_right_click(self, event):
        """Show context menu for definition/analysis."""
        try:
            # Check for selection first
            try:
                sel_start = self.chat_display.index("sel.first")
                sel_end = self.chat_display.index("sel.last")
                selected_text = self.chat_display.get(sel_start, sel_end).strip()
            except tk.TclError:
                selected_text = None

            # Get word under cursor
            index = self.chat_display.index(f"@{event.x},{event.y}")
            word = self.chat_display.get(f"{index} wordstart", f"{index} wordend").strip()
            
            menu = tk.Menu(self, tearoff=0)
            
            if selected_text:
                menu.add_command(label=tr("ctx_analyze_selection", "Analyze Selection"), 
                               command=lambda: self._analyze_text(selected_text))
                menu.add_separator()
            
            if word:
                menu.add_command(label=tr("ctx_define_word", "Define '{word}'", word=word), 
                               command=lambda: self._show_definition(word))
            
            if selected_text or word:
                menu.post(event.x_root, event.y_root)
                
        except Exception as e:
            print(f"Context menu error: {e}")

    def _show_definition(self, word):
        """Show a popup with dictionary definition."""
        # Detect language (simplified: assume target language for now, or check char range)
        #Ideally we pass the study language code.
        lang_code = "ko" # TODO: specific code or auto-detect. Using 'ko' as default for now implies testing.
        # Better: get from study_manager
        lang_map = {"Korean": "ko", "Spanish": "es", "Chinese": "zh", "Japanese": "ja", "English": "en"}
        target_lang = self.study_manager.study_language
        lang_code = lang_map.get(target_lang, "en") # Fallback
        
        results = self.dict_engine.lookup(word, lang_code)
        
        if not results:
            # Try English as fallback if no result? Or just show "No definition found."
            messagebox.showinfo(tr("title_def", "Definition"), tr("msg_no_def", "No definition found for '{word}' in {lang}.", word=word, lang=target_lang))
            return
            
        # Format definition
        text = ""
        for res in results[:3]: # Show top 3
            pos = res.get('pos', 'unk')
            defs = res.get('definitions', [])
            text += f"[{pos}]\n"
            for i, d in enumerate(defs, 1):
                text += f" {i}. {d}\n"
            text += "\n"
            
        messagebox.showinfo(tr("title_def", "Definition: {word}", word=word), text)

    def _analyze_text(self, text):
        """Show analysis for selected text."""
        # For now, just show tokens. In future, open proper Analysis View.
        from src.services.text.tokenizer_service import TokenizerService
        ts = TokenizerService()
         # Better: get from study_manager
        lang_map = {"Korean": "ko", "Spanish": "es", "Chinese": "zh", "Japanese": "ja", "English": "en"}
        target_lang = self.study_manager.study_language
        lang_code = lang_map.get(target_lang, "en") 
        
        tokens = ts.tokenize(text, lang_code)
        info = "\n".join([f"{t.text} [{t.pos}]" for t in tokens])
        messagebox.showinfo("Analysis", info)
