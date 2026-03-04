import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, simpledialog
import json
from src.features.study_center.logic.study_manager import StudyManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header
from src.features.study_center.ui.dialogs import DeckPickerDialog
from src.core.localization import tr
from src.services.audio_service import AudioRecorder
from src.core.config import config as app_config
import os
import threading

class WritingTopicDialog(tk.Toplevel):
    """Dialog for customizing writing topic generation options."""
    
    def __init__(self, parent):
        super().__init__(parent)
        self.title(tr("dlg_topic_options", "Writing Topic Options"))
        self.geometry("400x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        self.result = None  # {difficulty, scenario_type, topic_category}
        
        self.setup_ui()
        
        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() // 2) - (400 // 2)
        y = parent.winfo_y() + (parent.winfo_height() // 2) - (350 // 2)
        self.geometry(f"+{x}+{y}")
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill="both", expand=True)
        
        # Difficulty Level
        ttk.Label(main_frame, text=tr("lbl_difficulty", "Difficulty Level:"), font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        
        self.difficulty_var = tk.StringVar(value="medium")
        difficulty_frame = ttk.Frame(main_frame)
        difficulty_frame.pack(anchor="w", padx=20, pady=(0, 15))
        
        for difficulty in ["beginner", "intermediate", "advanced"]:
            ttk.Radiobutton(
                difficulty_frame,
                text=difficulty.capitalize(),
                variable=self.difficulty_var,
                value=difficulty
            ).pack(anchor="w", pady=3)
        
        # Scenario Type
        ttk.Label(main_frame, text=tr("lbl_scenario_type", "Writing Type:"), font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        
        self.scenario_var = tk.StringVar()
        scenario_options = [
            "Blog post",
            "Essay",
            "Email",
            "Short story",
            "Review",
            "Dialogue",
            "News article",
            "Any type"
        ]
        self.scenario_var.set(scenario_options[7])  # Default to "Any type"
        
        scenario_frame = ttk.Frame(main_frame)
        scenario_frame.pack(anchor="w", fill="x", pady=(0, 15))
        
        ttk.Combobox(
            scenario_frame,
            textvariable=self.scenario_var,
            values=scenario_options,
            state="readonly",
            width=30
        ).pack(fill="x")
        
        # Topic Category
        ttk.Label(main_frame, text=tr("lbl_topic_category", "Topic Category:"), font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 8))
        
        self.category_var = tk.StringVar()
        category_options = [
            "Travel and culture",
            "Food and cooking",
            "Technology",
            "Health and wellness",
            "Entertainment",
            "Sports",
            "Education",
            "Environment",
            "Current events",
            "Personal experiences",
            "Any topic"
        ]
        self.category_var.set(category_options[-1])  # Default to "Any topic"
        
        category_frame = ttk.Frame(main_frame)
        category_frame.pack(anchor="w", fill="x", pady=(0, 20))
        
        ttk.Combobox(
            category_frame,
            textvariable=self.category_var,
            values=category_options,
            state="readonly",
            width=30
        ).pack(fill="x")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", side="bottom")
        
        ttk.Button(
            button_frame,
            text=tr("btn_generate", "Generate"),
            command=self._on_generate
        ).pack(side="left", padx=5)
        
        ttk.Button(
            button_frame,
            text=tr("btn_cancel", "Cancel"),
            command=self._on_cancel
        ).pack(side="right", padx=5)
    
    def _on_generate(self):
        """Return selected options and close dialog."""
        self.result = {
            'difficulty': self.difficulty_var.get(),
            'scenario_type': self.scenario_var.get(),
            'topic_category': self.category_var.get()
        }
        self.destroy()
    
    def _on_cancel(self):
        """Close dialog without generating."""
        self.result = None
        self.destroy()
    
    def show(self):
        """Show dialog and return result."""
        self.wait_window()
        return self.result

class WritingLabFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.embedded = embedded
        
        self.audio_recorder = AudioRecorder(sample_rate=app_config.audio_sample_rate)
        self.is_recording = False
        self.speech_mode = tk.BooleanVar(value=False)
        
        self.setup_ui()
        
    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(self, tr("header_writing_lab", "✍️ Writing Composition Lab"), back_cmd=self.go_back)
        
        # MAIN TABBED CONTAINER
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # TAB 1: COMPOSITION
        self.comp_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.comp_tab, text=tr("tab_current_comp", "✍️ Current Composition"))
        self.setup_composition_tab()
        
        # TAB 2: FEEDBACK
        self.feedback_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.feedback_tab, text=tr("tab_feedback", "📊 Feedback"))
        self.setup_feedback_tab()
        
        # TAB 3: HISTORY
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text=tr("tab_writing_history", "📜 Writing History"))
        self.setup_history_tab()

    def setup_composition_tab(self):
        # TOOLBAR (ALWAYS VISIBLE)
        toolbar = ttk.Frame(self.comp_tab)
        toolbar.pack(fill="x", padx=10, pady=(10, 5))
        
        # Action buttons
        self.grade_btn = ttk.Button(
            toolbar, 
            text=tr("btn_grade", "🏆 Grade & Get Feedback"), 
            command=self._grade_writing,
            width=30
        )
        self.grade_btn.pack(side="left", padx=2, ipady=8) 
        
        ttk.Button(
            toolbar, 
            text=tr("btn_save_draft", "💾 Save Draft"), 
            command=self._save_draft
        ).pack(side="left", padx=2, ipady=8)

        ttk.Button(
            toolbar, 
            text=tr("btn_new_clear", "🆕 New / Clear"), 
            command=self._new_composition
        ).pack(side="left", padx=2, ipady=5)
        
        ttk.Button(
            toolbar, 
            text=tr("btn_generate_topic", "🎲 Generate Topic"), 
            command=self._generate_writing_topic
        ).pack(side="right", padx=2, ipady=5)

        # Speech Mode Toggle
        self.speech_check = ttk.Checkbutton(
            toolbar,
            text=tr("lbl_speech_mode", "🎙️ Speech Mode"),
            variable=self.speech_mode,
            command=self._on_toggle_speech_mode
        )
        self.speech_check.pack(side="right", padx=10)
        
        # SIDE-BY-SIDE LAYOUT: Topic (Left) + Writing (Right)
        main_container = ttk.Frame(self.comp_tab)
        main_container.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # LEFT SIDE: TOPIC AREA (Fixed width)
        topic_frame = ttk.LabelFrame(main_container, text=tr("lbl_topic", "Topic:"), padding="10")
        topic_frame.pack(side="left", fill="both", padx=(0, 5), ipadx=5)
        
        # Set a reasonable width for topic frame
        topic_frame.configure(width=300)
        
        self.topic_text = tk.Text(topic_frame, height=20, font=("Segoe UI", 10), wrap="word")
        self.topic_text.pack(fill="both", expand=True)
        self.topic_text.insert("1.0", tr("msg_placeholder_topic", "Type your own topic or click 'Generate Topic'..."))
        
        # RIGHT SIDE: WRITING AREA (Expands to fill)
        writing_frame = ttk.LabelFrame(main_container, text=tr("lbl_your_comp", "Your Composition:"), padding="10")
        writing_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        self.writing_text = tk.Text(writing_frame, font=("Segoe UI", 11), wrap="word", undo=True)
        self.writing_text.pack(fill="both", expand=True)

        # RECORDING UI (Overlay or swap)
        self.record_frame = ttk.Frame(writing_frame)
        self.record_btn = ttk.Button(
            self.record_frame,
            text=tr("btn_start_recording", "🎤 Start Oral Presentation"),
            command=self._toggle_speech_recording,
            style="Large.TButton"
        )
        self.record_btn.pack(pady=50)
        self.speech_status = ttk.Label(self.record_frame, text="", font=("Segoe UI", 12, "italic"))
        self.speech_status.pack()

    def _on_toggle_speech_mode(self):
        if self.speech_mode.get():
            self.writing_text.pack_forget()
            self.record_frame.pack(fill="both", expand=True)
            self.grade_btn.config(state=tk.DISABLED)
        else:
            self.record_frame.pack_forget()
            self.writing_text.pack(fill="both", expand=True)
            self.grade_btn.config(state=tk.NORMAL)

    def _toggle_speech_recording(self):
        topic = self.topic_text.get("1.0", tk.END).strip()
        if not topic or topic.startswith("Type your own"):
            if not messagebox.askyesno("No Topic", "You haven't set a topic. Record anyway?"):
                return
            topic = "Free Speech"

        if not self.is_recording:
            try:
                self.audio_recorder.start_recording()
                self.is_recording = True
                self.record_btn.config(text=tr("btn_stop_recording", "🛑 Stop Recording"))
                self.speech_status.config(text="Recording Presentation...", foreground="red")
            except Exception as e:
                messagebox.showerror("Audio Error", str(e))
        else:
            self.is_recording = False
            self.record_btn.config(text=tr("btn_start_recording", "🎤 Start Oral Presentation"), state=tk.DISABLED)
            self.speech_status.config(text="Processing Speech Analysis...", foreground="blue")
            
            try:
                audio_path = self.audio_recorder.stop_recording()
                self._grade_speech(audio_path, topic)
            except Exception as e:
                messagebox.showerror("Audio Error", str(e))
                self.record_btn.config(state=tk.NORMAL)
                self.speech_status.config(text="")

    def _grade_speech(self, audio_path, topic):
        self.feedback_display.configure(state="normal")
        self.feedback_display.delete("1.0", tk.END)
        self.feedback_display.insert("1.0", tr("msg_analyzing", "Analyzing your presentation..."))
        self.feedback_display.configure(state="disabled")
        
        def _task():
            task_id = self.study_manager.queue_generation_task('grade_speech', 0, audio_path=audio_path, topic=topic)
            self.after(0, lambda: self._check_writing_task(task_id, "grade"))
            self.after(0, lambda: self.record_btn.config(state=tk.NORMAL))
            self.after(0, lambda: self.speech_status.config(text=""))
            
        threading.Thread(target=_task, daemon=True).start()

    def setup_feedback_tab(self):
        """Feedback tab - displays AI feedback after grading"""
        main_container = ttk.Frame(self.feedback_tab)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Feedback display
        feedback_frame = ttk.LabelFrame(main_container, text=tr("lbl_ai_feedback", "📊 AI Feedback & Suggestions"), padding="10")
        feedback_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        self.feedback_display = scrolledtext.ScrolledText(feedback_frame, font=("Segoe UI", 10), wrap="word", state="disabled")
        self.feedback_display.pack(fill="both", expand=True, pady=(0, 10))
        
        # Suggestions bar
        self.sugg_bar = ttk.Frame(feedback_frame)
        self.sugg_bar.pack(fill="x")
        self.sugg_label = ttk.Label(self.sugg_bar, text=tr("lbl_ai_sugg_none", "AI Suggestions: None"), font=("Segoe UI", 9, "italic"))
        self.sugg_label.pack(side="left")

    def setup_history_tab(self):
        main_container = ttk.Frame(self.history_tab)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Toolbar
        toolbar = ttk.Frame(main_container)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Button(toolbar, text=tr("btn_refresh", "🔄 Refresh"), command=self._refresh_history).pack(side="left", padx=2)
        ttk.Button(toolbar, text=tr("btn_load_selected", "📂 Load Selected"), command=self._load_session).pack(side="left", padx=2)
        ttk.Button(toolbar, text=tr("btn_delete", "🗑️ Delete"), command=self._delete_session).pack(side="left", padx=2)
        ttk.Button(toolbar, text=tr("btn_export_selected", "📤 Export Selected"), command=self._export_session).pack(side="right", padx=2)
        
        # Treeview
        columns = ("date", "topic", "language", "grade")
        self.history_tree = ttk.Treeview(main_container, columns=columns, show="headings")
        
        self.history_tree.heading("date", text=tr("tree_date", "Date/Time"))
        self.history_tree.heading("topic", text=tr("tree_topic", "Topic"))
        self.history_tree.heading("language", text=tr("lbl_language", "Language"))
        self.history_tree.heading("grade", text=tr("tree_grade", "Grade"))
        
        self.history_tree.column("date", width=150)
        self.history_tree.column("topic", width=300)
        self.history_tree.column("language", width=80)
        self.history_tree.column("grade", width=80)
        
        self.history_tree.pack(fill="both", expand=True)
        
        # Bind double-click to load
        self.history_tree.bind("<Double-1>", lambda e: self._load_session())
        
        # Initial load
        self._refresh_history()

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()

    def _save_draft(self):
        topic = self.topic_text.get("1.0", "end").strip()
        writing = self.writing_text.get("1.0", "end").strip()
        
        if not writing or writing.startswith("Type your own"):
            messagebox.showwarning(tr("msg_empty", "Empty"), tr("msg_nothing_to_save", "Nothing to save!"))
            return
            
        # Save as draft with N/A grade
        self.study_manager.db.add_writing_session(
            topic, writing, "", "Draft", self.study_manager.study_language
        )
        messagebox.showinfo(tr("msg_success", "Success"), tr("msg_draft_saved", "Draft saved to history!"))
        self._refresh_history()

    def _new_composition(self):
        if messagebox.askyesno(tr("btn_new_clear", "Clear"), tr("msg_confirm_new", "Start a new composition?")):
            self.topic_text.delete("1.0", "end")
            self.topic_text.insert("1.0", tr("msg_placeholder_topic", "Type your own topic or click 'Generate Topic'..."))
            self.writing_text.delete("1.0", "end")
            self.feedback_display.configure(state="normal")
            self.feedback_display.delete("1.0", "end")
            self.feedback_display.configure(state="disabled")
            for widget in self.sugg_bar.winfo_children(): widget.destroy()
            self.sugg_label = ttk.Label(self.sugg_bar, text=tr("lbl_ai_sugg_none", "AI Suggestions: None"), font=("Segoe UI", 9, "italic"))
            self.sugg_label.pack(side="left")

    def _refresh_history(self):
        # Clear existing
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        # Load from DB
        sessions = self.study_manager.get_writing_history()
        for s in sessions:
            # Format date for display
            date_str = s['created_at'].replace('T', ' ')[:16]
            self.history_tree.insert("", "end", iid=s['id'], values=(
                date_str, s['topic'], s['study_language'], s['grade']
            ))

    def _load_session(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning(tr("header_search", "Select"), tr("msg_select_session", "Please select a session from history."))
            return
            
        session_id = selected[0]
        sessions = self.study_manager.get_writing_history()
        session = next((s for s in sessions if str(s['id']) == str(session_id)), None)
        
        if session:
            # Populate text areas
            self.topic_text.delete("1.0", "end")
            self.topic_text.insert("1.0", session['topic'])
            self.writing_text.delete("1.0", "end")
            self.writing_text.insert("1.0", session['user_writing'])
            
            # Populate feedback
            self.feedback_display.configure(state="normal")
            self.feedback_display.delete("1.0", "end")
            self.feedback_display.insert("1.0", session['feedback'] or "")
            self.feedback_display.configure(state="disabled")
            
            # Handle suggestions if analysis exists
            if session.get('analysis'):
                try:
                    suggestions = json.loads(session['analysis'])
                    self._display_writing_feedback(session['feedback'], suggestions)
                except:
                    pass
            
            # Switch tab
            self.notebook.select(self.comp_tab)

    def _delete_session(self):
        selected = self.history_tree.selection()
        if not selected:
            return
            
        if messagebox.askyesno(tr("btn_delete", "Delete"), tr("msg_confirm_delete_session", "Delete this session from history?")):
            session_id = selected[0]
            self.study_manager.db.delete_writing_session(session_id)
            self._refresh_history()

    def _export_session(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning(tr("header_search", "Select"), tr("msg_select_session", "Please select a session to export."))
            return
            
        session_id = selected[0]
        sessions = self.study_manager.get_writing_history()
        session = next((s for s in sessions if str(s['id']) == str(session_id)), None)
        
        if not session: return

        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md"), ("Text", "*.txt")],
            initialfile=f"Writing_{session['created_at'][:10]}.md"
        )
        
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"# Writing Session: {session['topic']}\n")
                    f.write(f"**Date:** {session['created_at'].replace('T', ' ')[:16]}\n")
                    f.write(f"**Language:** {session['study_language']}\n")
                    f.write(f"**Grade:** {session['grade']}\n\n")
                    f.write("## Your Writing\n")
                    f.write(f"{session['user_writing']}\n\n")
                    f.write("## AI Feedback\n")
                    f.write(f"{session['feedback']}\n")
                    
                    if session.get('analysis'):
                        try:
                            sugg = json.loads(session['analysis'])
                            if sugg.get('flashcards') or sugg.get('grammar'):
                                f.write("\n## Related Items\n")
                                for fc in sugg.get('flashcards', []):
                                    f.write(f"- Word: {fc['word']} | {fc['definition']}\n")
                                for gm in sugg.get('grammar', []):
                                    f.write(f"- Grammar: {gm['title']}\n")
                        except Exception as e:
                            print(f"Export suggestions error: {e}")
                
                messagebox.showinfo(tr("msg_success", "Exported"), tr("msg_exported_to", "Session exported to {path}", path=path))
            except Exception as e:
                messagebox.showerror(tr("msg_export_error", "Export Error"), str(e))

    def _generate_writing_topic(self):
        # Open topic options dialog
        dialog = WritingTopicDialog(self.winfo_toplevel())
        options = dialog.show()
        
        if options is None:
            # User cancelled
            return
        
        self.topic_text.delete("1.0", "end")
        self.topic_text.insert("1.0", tr("msg_analyzing", "Generating topic... please wait."))
        
        # Queue task with topic options as kwargs
        task_id = self.study_manager.queue_generation_task(
            'writing_topic', 
            0,
            difficulty=options['difficulty'],
            scenario_type=options['scenario_type'],
            topic_category=options['topic_category']
        )
        self._check_writing_task(task_id, "topic")

    def _grade_writing(self):
        topic = self.topic_text.get("1.0", "end").strip()
        writing = self.writing_text.get("1.0", "end").strip()
        
        if not writing or len(writing) < 10:
             messagebox.showwarning(tr("msg_success", "Incomplete"), tr("msg_incomplete_grading", "Please write a bit more before grading!"))
             return
             
        self.feedback_display.configure(state="normal")
        self.feedback_display.delete("1.0", "end")
        self.feedback_display.insert("1.0", tr("msg_analyzing", "Analyzing your writing... this may take a moment."))
        self.feedback_display.configure(state="disabled")
        self.grade_btn.configure(state="disabled")
        
        task_id = self.study_manager.queue_generation_task('grade_writing', 0, user_writing=writing, topic=topic)
        self._check_writing_task(task_id, "grade")

    def _check_writing_task(self, task_id, task_type):
        status = self.study_manager.get_task_status(task_id)
        if status['status'] == 'completed':
            if task_type == "topic":
                self.topic_text.delete("1.0", "end")
                self.topic_text.insert("1.0", status['result'])
            else:
                self._display_writing_feedback(status['result'], status.get('suggestions', {}))
                self.grade_btn.configure(state="normal")
        elif status['status'] == 'failed':
            error_msg = status.get('error', 'Unknown error')
            if task_type == "topic":
                self.topic_text.delete("1.0", "end")
                self.topic_text.insert("1.0", tr("msg_error_topic", "Error generating topic: {error}", error=error_msg))
            else:
                 self.feedback_display.configure(state="normal")
                 self.feedback_display.delete("1.0", "end")
                 self.feedback_display.insert("1.0", tr("msg_error_grading", "Error grading writing: {error}", error=error_msg))
                 self.feedback_display.configure(state="disabled")
                 self.grade_btn.configure(state="normal")
        else:
             self.after(1000, lambda: self._check_writing_task(task_id, task_type))

    def _display_writing_feedback(self, feedback, suggestions):
        self.feedback_display.configure(state="normal")
        self.feedback_display.delete("1.0", "end")
        self.feedback_display.insert("1.0", feedback)
        self.feedback_display.configure(state="disabled")
        
        for widget in self.sugg_bar.winfo_children(): widget.destroy()
        
        fc_count = len(suggestions.get('flashcards', []))
        gram_count = len(suggestions.get('grammar', []))
        
        if fc_count > 0 or gram_count > 0:
            msg = tr("msg_sugg_count", "Suggestions: {words} Words, {grammar} Grammar Patterns", words=fc_count, grammar=gram_count)
            ttk.Label(self.sugg_bar, text=msg, font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            
            if fc_count > 0:
                ttk.Button(self.sugg_bar, text=tr("msg_added_cards", "➕ Add Words"), command=lambda: self._add_suggestions(suggestions, 'word')).pack(side="left", padx=2)
            if gram_count > 0:
                ttk.Button(self.sugg_bar, text=tr("msg_added_grammar", "➕ Add Grammar"), command=lambda: self._add_suggestions(suggestions, 'grammar')).pack(side="left", padx=2)
        else:
            self.sugg_label = ttk.Label(self.sugg_bar, text=tr("msg_sugg_none", "Suggestions: None found."), font=("Segoe UI", 9, "italic"))
            self.sugg_label.pack(side="left")
        
        # Switch to Feedback tab to show results
        self.notebook.select(self.feedback_tab)

    def _add_suggestions(self, suggestions, type_name):
        db = self.study_manager.db
        count = 0
        if type_name == 'word':
            items = suggestions.get('flashcards', [])
            if not items: return
            
            # Ask Destination
            choice = messagebox.askyesnocancel(tr("msg_added_words", "Add Words"), tr("msg_save_to", "Save {count} words to?\n\nYes: Flashcard Deck\nNo: Vocabulary List (Study Center)", count=len(items)))
            if choice is None: return

            if choice: # Yes -> Deck
                # writing_lab doesn't hold 'db' directly in self, but study_manager does
                deck_id = DeckPickerDialog(self.winfo_toplevel(), db).show()
                if not deck_id: return
                
                added_count = 0
                for item in items:
                    # Skip duplicates silently in batch to avoid spam
                    if not db.find_flashcard_in_deck(deck_id, item['word']):
                        db.add_flashcard(deck_id, item['word'], item['definition'])
                        added_count += 1
                
                if added_count < len(items):
                    messagebox.showinfo(tr("msg_success", "Success"), tr("msg_added_cards_partial", "Added {count} cards to deck! ({total}-{count} were duplicates)", count=added_count, total=len(items)))
                else:
                    messagebox.showinfo(tr("msg_success", "Success"), tr("msg_added_cards", "Added all {count} cards to deck!", count=added_count))
                    
            else: # No -> Vocab List
                for item in items:
                    content_id = db.add_imported_content(
                        'word', item['word'], url="Writing Lab Suggestion",
                        title="AI Suggestion", language=self.study_manager.study_language
                    )
                    self.study_manager.add_word_definition(
                        content_id, item['definition'], definition_language=self.study_manager.native_language
                    )
                    count += 1
                messagebox.showinfo(tr("msg_success", "Success"), tr("msg_added_words", "Added {count} words to vocabulary list!", count=count))
        else:
            for item in suggestions.get('grammar', []):
                 db.add_grammar_entry(item['title'], item['explanation'], language=self.study_manager.study_language)
                 count += 1
            messagebox.showinfo(tr("msg_success", "Success"), tr("msg_added_grammar", "Added {count} grammar patterns!", count=count))
