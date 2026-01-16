import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from src.features.study_center.logic.study_manager import StudyManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header

class WritingLabFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.embedded = embedded
        
        self.setup_ui()
        
    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(self, "✍️ Writing Composition Lab", back_cmd=self.go_back)
        
        # MAIN TABBED CONTAINER
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)
        
        # TAB 1: COMPOSITION
        self.comp_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.comp_tab, text="✍️ Current Composition")
        
        self.setup_composition_tab()
        
        # TAB 2: HISTORY
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="📜 Writing History")
        
        self.setup_history_tab()

    def setup_composition_tab(self):
        # MAIN CONTAINER for Tab 1
        main_container = ttk.Frame(self.comp_tab)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # INPUT SECTION
        input_frame = ttk.LabelFrame(main_container, text="✏️ Composition Input", padding="10")
        input_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        # Topic
        topic_header = ttk.Frame(input_frame)
        topic_header.pack(fill="x", pady=(0, 5))
        ttk.Label(topic_header, text="Topic:", font=("Segoe UI", 10, "bold")).pack(side="left")
        ttk.Button(topic_header, text="🎲 Generate Topic", command=self._generate_writing_topic).pack(side="right")
        
        self.topic_text = tk.Text(input_frame, height=3, font=("Segoe UI", 10), wrap="word")
        self.topic_text.pack(fill="x", pady=(0, 10))
        self.topic_text.insert("1.0", "Type your own topic or click 'Generate Topic'...")
        
        # Writing Area
        ttk.Label(input_frame, text="Your Composition:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        self.writing_text = tk.Text(input_frame, font=("Segoe UI", 11), wrap="word", undo=True, height=10)
        self.writing_text.pack(fill="both", expand=True)
        
        # ACTION TOOLBAR (PROMINENT PLACEMENT)
        action_toolbar = ttk.Frame(main_container)
        action_toolbar.pack(fill="x", pady=10)
        
        # Center the grade button with larger size
        self.grade_btn = ttk.Button(
            action_toolbar, 
            text="🏆 Grade & Get Feedback", 
            command=self._grade_writing,
            width=30
        )
        self.grade_btn.pack(side="left", padx=5, ipady=8) 
        
        ttk.Button(
            action_toolbar, 
            text="💾 Save Draft", 
            command=self._save_draft
        ).pack(side="left", padx=5, ipady=8)

        ttk.Button(
            action_toolbar, 
            text="🆕 New / Clear", 
            command=self._new_composition
        ).pack(side="right", padx=5, ipady=5)
        
        # FEEDBACK SECTION
        feedback_frame = ttk.LabelFrame(main_container, text="📊 AI Feedback & Suggestions", padding="10")
        feedback_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        self.feedback_display = scrolledtext.ScrolledText(feedback_frame, font=("Segoe UI", 10), wrap="word", state="disabled", height=8)
        self.feedback_display.pack(fill="both", expand=True, pady=(0, 10))
        
        self.sugg_bar = ttk.Frame(feedback_frame)
        self.sugg_bar.pack(fill="x")
        self.sugg_label = ttk.Label(self.sugg_bar, text="AI Suggestions: None", font=("Segoe UI", 9, "italic"))
        self.sugg_label.pack(side="left")

    def setup_history_tab(self):
        main_container = ttk.Frame(self.history_tab)
        main_container.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Toolbar
        toolbar = ttk.Frame(main_container)
        toolbar.pack(fill="x", pady=(0, 10))
        
        ttk.Button(toolbar, text="🔄 Refresh", command=self._refresh_history).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📂 Load Selected", command=self._load_session).pack(side="left", padx=2)
        ttk.Button(toolbar, text="🗑️ Delete", command=self._delete_session).pack(side="left", padx=2)
        ttk.Button(toolbar, text="📤 Export Selected", command=self._export_session).pack(side="right", padx=2)
        
        # Treeview
        columns = ("date", "topic", "language", "grade")
        self.history_tree = ttk.Treeview(main_container, columns=columns, show="headings")
        
        self.history_tree.heading("date", text="Date/Time")
        self.history_tree.heading("topic", text="Topic")
        self.history_tree.heading("language", text="Language")
        self.history_tree.heading("grade", text="Grade")
        
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
            messagebox.showwarning("Empty", "Nothing to save!")
            return
            
        # Save as draft with N/A grade
        self.study_manager.db.add_writing_session(
            topic, writing, "", "Draft", self.study_manager.study_language
        )
        messagebox.showinfo("Success", "Draft saved to history!")
        self._refresh_history()

    def _new_composition(self):
        if messagebox.askyesno("Clear", "Start a new composition?"):
            self.topic_text.delete("1.0", "end")
            self.topic_text.insert("1.0", "Type your own topic or click 'Generate Topic'...")
            self.writing_text.delete("1.0", "end")
            self.feedback_display.configure(state="normal")
            self.feedback_display.delete("1.0", "end")
            self.feedback_display.configure(state="disabled")
            for widget in self.sugg_bar.winfo_children(): widget.destroy()
            self.sugg_label = ttk.Label(self.sugg_bar, text="AI Suggestions: None", font=("Segoe UI", 9, "italic"))
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
            messagebox.showwarning("Select", "Please select a session from history.")
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
            
        if messagebox.askyesno("Delete", "Delete this session from history?"):
            session_id = selected[0]
            self.study_manager.db.delete_writing_session(session_id)
            self._refresh_history()

    def _export_session(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("Select", "Please select a session to export.")
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
                
                messagebox.showinfo("Exported", f"Session exported to {path}")
            except Exception as e:
                messagebox.showerror("Export Error", str(e))

    def _generate_writing_topic(self):
        self.topic_text.delete("1.0", "end")
        self.topic_text.insert("1.0", "Generating topic... please wait.")
        task_id = self.study_manager.queue_generation_task('writing_topic', 0)
        self._check_writing_task(task_id, "topic")

    def _grade_writing(self):
        topic = self.topic_text.get("1.0", "end").strip()
        writing = self.writing_text.get("1.0", "end").strip()
        
        if not writing or len(writing) < 10:
             messagebox.showwarning("Incomplete", "Please write a bit more before grading!")
             return
             
        self.feedback_display.configure(state="normal")
        self.feedback_display.delete("1.0", "end")
        self.feedback_display.insert("1.0", "Analyzing your writing... this may take a moment.")
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
                self.topic_text.insert("1.0", f"Error generating topic: {error_msg}")
            else:
                 self.feedback_display.configure(state="normal")
                 self.feedback_display.delete("1.0", "end")
                 self.feedback_display.insert("1.0", f"Error grading writing: {error_msg}")
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
            msg = f"Suggestions: {fc_count} Words, {gram_count} Grammar Patterns"
            ttk.Label(self.sugg_bar, text=msg, font=("Segoe UI", 9, "bold")).pack(side="left", padx=5)
            
            if fc_count > 0:
                ttk.Button(self.sugg_bar, text="➕ Add Words", command=lambda: self._add_suggestions(suggestions, 'word')).pack(side="left", padx=2)
            if gram_count > 0:
                ttk.Button(self.sugg_bar, text="➕ Add Grammar", command=lambda: self._add_suggestions(suggestions, 'grammar')).pack(side="left", padx=2)
        else:
            self.sugg_label = ttk.Label(self.sugg_bar, text="Suggestions: None found.", font=("Segoe UI", 9, "italic"))
            self.sugg_label.pack(side="left")

    def _add_suggestions(self, suggestions, type_name):
        db = self.study_manager.db
        count = 0
        if type_name == 'word':
            for item in suggestions.get('flashcards', []):
                content_id = db.add_imported_content(
                    'word', item['word'], url="Writing Lab Suggestion",
                    title="AI Suggestion", language=self.study_manager.study_language
                )
                self.study_manager.add_word_definition(
                    content_id, item['definition'], definition_language=self.study_manager.native_language
                )
                count += 1
            messagebox.showinfo("Success", f"Added {count} words!")
        else:
            for item in suggestions.get('grammar', []):
                 db.add_grammar_entry(item['title'], item['explanation'], language=self.study_manager.study_language)
                 count += 1
            messagebox.showinfo("Success", f"Added {count} grammar patterns!")
