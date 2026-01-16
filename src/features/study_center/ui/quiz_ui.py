import tkinter as tk
from tkinter import ttk, messagebox
from src.features.study_center.logic.study_manager import StudyManager
from src.features.study_center.logic.quiz_manager import QuizManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header

class QuizUIFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, db: FlashcardDatabase, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        self.embedded = embedded
        
        # Initialize QuizManager
        timeout = study_manager.request_timeout if study_manager else 30
        self.quiz_manager = QuizManager(db, study_manager.ollama_client, timeout=timeout)
        
        self.setup_ui()
        
    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(self, "📝 Quiz Yourself", back_cmd=self.go_back)
        
        # Quiz Options
        options_frame = ttk.LabelFrame(self, text="Quiz Settings", padding="20")
        options_frame.pack(fill="x", pady=20, padx=20)
        
        ttk.Label(options_frame, text="Quiz Type:", font=("Arial", 11)).pack(anchor="w", pady=(0, 5))
        self.quiz_type_var = tk.StringVar(value="vocab")
        
        radio_frame = ttk.Frame(options_frame)
        radio_frame.pack(fill="x", pady=5)
        ttk.Radiobutton(radio_frame, text="Vocabulary", variable=self.quiz_type_var, value="vocab", command=self._on_type_change).pack(side="left", padx=10)
        ttk.Radiobutton(radio_frame, text="Sentences", variable=self.quiz_type_var, value="sentence", command=self._on_type_change).pack(side="left", padx=10)
        ttk.Radiobutton(radio_frame, text="Grammar", variable=self.quiz_type_var, value="grammar", command=self._on_type_change).pack(side="left", padx=10)
        ttk.Radiobutton(radio_frame, text="🎓 Exam Practice", variable=self.quiz_type_var, value="exam", command=self._on_type_change).pack(side="left", padx=10)
        
        # --- Context Specific Options ---
        self.dynamic_settings = ttk.Frame(options_frame)
        self.dynamic_settings.pack(fill="x", pady=10)
        
        # Standard Quest Count
        self.standard_settings = ttk.Frame(self.dynamic_settings)
        self.standard_settings.pack(fill="x")
        
        ttk.Label(self.standard_settings, text="Question Count:", font=("Arial", 11)).pack(anchor="w", pady=(15, 5))
        self.count_var = tk.IntVar(value=10)
        count_spin = ttk.Spinbox(self.standard_settings, from_=5, to=50, increment=5, textvariable=self.count_var, width=10)
        count_spin.pack(anchor="w", pady=5)
        
        ttk.Label(self.standard_settings, text="Difficulty:", font=("Arial", 11)).pack(anchor="w", pady=(15, 5))
        self.diff_var = tk.StringVar(value="medium")
        diff_combo = ttk.Combobox(self.standard_settings, textvariable=self.diff_var, values=["easy", "medium", "hard"], state="readonly", width=15)
        diff_combo.pack(anchor="w", pady=5)

        # Exam Specific Settings
        self.exam_settings = ttk.Frame(self.dynamic_settings)
        # Hidden by default
        
        ttk.Label(self.exam_settings, text="Target Exam:", font=("Arial", 11)).pack(anchor="w", pady=(15, 5))
        self.exam_name_var = tk.StringVar(value="JLPT")
        self.exam_name_combo = ttk.Combobox(self.exam_settings, textvariable=self.exam_name_var, 
                                          values=["JLPT", "DELE", "HSK", "TOPIK", "TEF", "TCF", "IELTS", "TOEFL"], state="readonly", width=20)
        self.exam_name_combo.pack(anchor="w", pady=5)
        
        ttk.Label(self.exam_settings, text="Level:", font=("Arial", 11)).pack(anchor="w", pady=(10, 5))
        self.exam_level_var = tk.StringVar(value="N3/B1")
        self.exam_level_combo = ttk.Combobox(self.exam_settings, textvariable=self.exam_level_var, 
                                           values=["N5/A1", "N4/A2", "N3/B1", "N2/B2", "N1/C1", "C2"], state="readonly", width=15)
        self.exam_level_combo.pack(anchor="w", pady=5)

        ttk.Label(self.exam_settings, text="Section:", font=("Arial", 11)).pack(anchor="w", pady=(10, 5))
        self.exam_section_var = tk.StringVar(value="Grammar/Vocabulary")
        self.exam_section_combo = ttk.Combobox(self.exam_settings, textvariable=self.exam_section_var, 
                                             values=["Grammar/Vocabulary", "Reading Comprehension", "Listening (Transcript Mode)"], state="readonly", width=25)
        self.exam_section_combo.pack(anchor="w", pady=5)
        
        ttk.Label(self.exam_settings, text="Questions:", font=("Arial", 11)).pack(anchor="w", pady=(10, 5))
        self.exam_count_var = tk.IntVar(value=5)
        ttk.Spinbox(self.exam_settings, from_=1, to=20, increment=1, textvariable=self.exam_count_var, width=10).pack(anchor="w", pady=5)
        
        # Start Button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=30)
        ttk.Button(btn_frame, text="Start Quiz", command=self._start_quiz, style="Large.TButton").pack(ipadx=20, ipady=10)

    def _on_type_change(self):
        new_type = self.quiz_type_var.get()
        if new_type == "exam":
            self.standard_settings.pack_forget()
            self.exam_settings.pack(fill="x")
        else:
            self.exam_settings.pack_forget()
            self.standard_settings.pack(fill="x")

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()

    def _start_quiz(self):
        quiz_type = self.quiz_type_var.get()
        count = self.count_var.get()
        difficulty = self.diff_var.get()
        
        # In a real implementation we would fetch items based on type.
        # For now, let's assume quiz_manager handles generation.
        # We need to launch a Quiz Window.
        
        try:
             # Launch Quiz Session Window
             config = {
                 'type': quiz_type,
                 'count': count,
                 'difficulty': difficulty
             }
             
             if quiz_type == "exam":
                 config.update({
                     'exam_name': self.exam_name_var.get(),
                     'level': self.exam_level_var.get(),
                     'section': self.exam_section_var.get(),
                     'count': self.exam_count_var.get(),
                     'study_lang': self.study_manager.study_language if self.study_manager else "English",
                     'native_lang': self.study_manager.native_language if self.study_manager else "English"
                 })
                 
             QuizSessionWindow(self, self.quiz_manager, config)
             
        except Exception as e:
             messagebox.showerror("Error", f"Failed to start quiz: {e}")

class QuizSessionWindow(tk.Toplevel):
    def __init__(self, parent, quiz_manager, config):
        super().__init__(parent)
        self.quiz_manager = quiz_manager
        self.config = config
        self.quiz_type = config.get('type')
        
        self.title(f"Quiz Session: {self.quiz_type.capitalize()}")
        self.geometry("700x600")
        
        self.questions = []
        self.current_idx = 0
        self.score = 0
        self.attempt_id = -1
        
        loading_text = f"Generating {config.get('count')} questions..."
        if self.quiz_type == "exam":
            loading_text = f"Preparing {config.get('exam_name')} {config.get('level')} exam..."
            
        self.loading_lbl = ttk.Label(self, text=loading_text, font=("Arial", 14))
        self.loading_lbl.pack(pady=100)
        self.update()
        
        # We should use threading here eventually, but for now we follow the existing sync pattern
        self._initialize_session()

    def _initialize_session(self):
        try:
            if self.quiz_type == "exam":
                # Create exam attempt
                self.attempt_id = self.quiz_manager.create_exam_attempt(
                    self.config['exam_name'], self.config['level'], 
                    self.config['section'], self.config['count']
                )
                
                # Generate questions
                success = self.quiz_manager.generate_exam_questions(
                    self.attempt_id, self.config['exam_name'], self.config['level'],
                    self.config['section'], self.config['count'],
                    self.config['study_lang'], self.config['native_lang']
                )
                
                if success:
                    self.questions = self.quiz_manager.get_exam_questions(self.attempt_id)
            else:
                # Traditional quiz logic (mocked in previous version, now using manager correctly)
                # Note: Traditional quiz manager.generate_quiz returns session_id
                # but previous QuizSessionWindow seemed to expect a list of questions directly?
                # I'll update it to use the session-based approach compatible with current QuizManager.
                
                # For compatibility with source_id (currently hardcoded as 0 or Needs Collection ID)
                # In this app, we might need to pass a collection_id from the UI.
                # For now, I'll use a fallback or default collection if available.
                source_id = 1 # Placeholder or should come from UI
                session_id = self.quiz_manager.generate_quiz(
                    self.quiz_type, source_id, self.config['count'], self.config['difficulty']
                )
                
                if session_id != -1:
                    self.questions = self.quiz_manager.get_quiz_questions(session_id)
                    self.session_id = session_id

            if not self.questions:
                messagebox.showinfo("Info", "No questions were generated. Check Ollama status.")
                self.destroy()
                return
                
            self._show_question()
            
        except Exception as e:
            messagebox.showerror("Error", f"Session initialization failed: {e}")
            self.destroy()

    def _show_question(self):
        for widget in self.winfo_children(): widget.destroy()
        
        if self.current_idx >= len(self.questions):
             self._show_results()
             return
             
        q = self.questions[self.current_idx]
        
        header_frame = ttk.Frame(self, padding=10)
        header_frame.pack(fill="x")
        
        ttk.Label(header_frame, text=f"Question {self.current_idx + 1}/{len(self.questions)}", font=("Arial", 10)).pack(side="left")
        
        if self.quiz_type == "exam":
            ttk.Label(header_frame, text=f"{self.config['exam_name']} {self.config['level']} - {self.config['section']}", 
                      font=("Arial", 10, "italic")).pack(side="right")
        
        # Question Text
        question_container = ttk.Frame(self, padding=20)
        question_container.pack(fill="x")
        
        ttk.Label(question_container, text=q['question_text'], font=("Arial", 14, "bold"), wraplength=600).pack(pady=20)
        
        # Options
        options_frame = ttk.Frame(self, padding=40)
        options_frame.pack(fill="both", expand=True)
        
        choices = [
            ('A', q.get('choice_a', '')),
            ('B', q.get('choice_b', '')),
            ('C', q.get('choice_c', '')),
            ('D', q.get('choice_d', ''))
        ]
        
        for letter, text in choices:
            if text:
                btn_text = f"{letter}: {text}"
                ttk.Button(options_frame, text=btn_text, command=lambda l=letter: self._submit_answer(l)).pack(fill="x", pady=8)
             
    def _submit_answer(self, user_letter):
        q = self.questions[self.current_idx]
        
        if self.quiz_type == "exam":
            is_correct = self.quiz_manager.submit_exam_answer(q['id'], user_letter)
        else:
            is_correct = self.quiz_manager.submit_answer(q['id'], user_letter)
            
        if is_correct: 
            self.score += 1
            messagebox.showinfo("Correct!", "That's right!")
        else:
            correct_letter = q['correct_answer']
            correct_text = q.get(f"choice_{correct_letter.lower()}", "")
            msg = f"Incorrect. The correct answer was {correct_letter}: {correct_text}"
            if q.get('explanation'):
                msg += f"\n\nExplanation: {q['explanation']}"
            messagebox.showerror("Incorrect", msg)
             
        self.current_idx += 1
        self._show_question()
        
    def _show_results(self):
        for widget in self.winfo_children(): widget.destroy()
        
        if self.quiz_type == "exam":
            results = self.quiz_manager.finalize_exam_attempt(self.attempt_id)
        else:
            results = self.quiz_manager.calculate_score(self.session_id)
            
        score = results['score']
        
        ttk.Label(self, text="Practice Complete!", font=("Arial", 20, "bold")).pack(pady=40)
        
        res_frame = ttk.Frame(self)
        res_frame.pack(pady=20)
        
        ttk.Label(res_frame, text=f"Correct Answers: {results['correct']}/{results['total']}", font=("Arial", 14)).pack()
        ttk.Label(res_frame, text=f"Final Score: {score}%", font=("Arial", 18, "bold"), foreground="green" if score >= 70 else "orange").pack(pady=10)
        
        if self.quiz_type == "exam":
            msg = "Exam readiness: Excellent!" if score >= 80 else "Exam readiness: Needs more practice."
            ttk.Label(self, text=msg, font=("Arial", 12, "italic")).pack(pady=20)
        
        ttk.Button(self, text="Close", command=self.destroy).pack(pady=30)
