import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
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
        
        paned = tk.PanedWindow(self, orient="vertical", sashrelief="raised", sashwidth=4)
        paned.pack(fill="both", expand=True, pady=10)
        
        # INPUT SECTION
        input_frame = ttk.Frame(paned)
        paned.add(input_frame, height=350)
        
        topic_header = ttk.Frame(input_frame)
        topic_header.pack(fill="x", pady=(0, 5))
        ttk.Label(topic_header, text="Topic & Background:", font=("Segoe UI", 12, "bold")).pack(side="left")
        
        topic_btn_frame = ttk.Frame(topic_header)
        topic_btn_frame.pack(side="right")
        ttk.Button(topic_btn_frame, text="🎲 AI Generate Topic", command=self._generate_writing_topic).pack(side="left", padx=5)
        
        self.topic_text = tk.Text(input_frame, height=4, font=("Segoe UI", 10), wrap="word")
        self.topic_text.pack(fill="x", pady=5)
        self.topic_text.insert("1.0", "Type your own topic here, or click 'AI Generate Topic'...")
        
        ttk.Label(input_frame, text="Your Composition:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 5))
        self.writing_text = tk.Text(input_frame, font=("Segoe UI", 11), wrap="word", undo=True)
        self.writing_text.pack(fill="both", expand=True, pady=5)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(fill="x", pady=10)
        self.grade_btn = ttk.Button(btn_frame, text="🏆 Grade & Get Feedback", command=self._grade_writing)
        self.grade_btn.pack(side="right", padx=5)
        
        # FEEDBACK SECTION
        self.feedback_frame = ttk.Frame(paned)
        paned.add(self.feedback_frame)
        
        ttk.Label(self.feedback_frame, text="Feedback & Suggestions:", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.feedback_display = scrolledtext.ScrolledText(self.feedback_frame, font=("Segoe UI", 10), wrap="word", state="disabled")
        self.feedback_display.pack(fill="both", expand=True, pady=5)
        
        self.sugg_bar = ttk.Frame(self.feedback_frame)
        self.sugg_bar.pack(fill="x", pady=5)
        self.sugg_label = ttk.Label(self.sugg_bar, text="AI Suggestions: None", font=("Segoe UI", 9, "italic"))
        self.sugg_label.pack(side="left")

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()

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
            ttk.Label(self.sugg_bar, text="Suggestions: None found.", font=("Segoe UI", 9, "italic")).pack(side="left")

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
