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
        ttk.Radiobutton(radio_frame, text="Vocabulary (Definitions)", variable=self.quiz_type_var, value="vocab").pack(side="left", padx=10)
        ttk.Radiobutton(radio_frame, text="Sentences (Fill-in-the-blank)", variable=self.quiz_type_var, value="sentence").pack(side="left", padx=10)
        ttk.Radiobutton(radio_frame, text="Grammar (Concepts)", variable=self.quiz_type_var, value="grammar").pack(side="left", padx=10)
        # ttk.Radiobutton(radio_frame, text="Mixed Review", variable=self.quiz_type_var, value="mixed").pack(side="left", padx=10)
        
        ttk.Label(options_frame, text="Question Count:", font=("Arial", 11)).pack(anchor="w", pady=(15, 5))
        self.count_var = tk.IntVar(value=10)
        count_spin = ttk.Spinbox(options_frame, from_=5, to=50, increment=5, textvariable=self.count_var, width=10)
        count_spin.pack(anchor="w", pady=5)
        
        ttk.Label(options_frame, text="Difficulty:", font=("Arial", 11)).pack(anchor="w", pady=(15, 5))
        self.diff_var = tk.StringVar(value="medium")
        diff_combo = ttk.Combobox(options_frame, textvariable=self.diff_var, values=["easy", "medium", "hard"], state="readonly", width=15)
        diff_combo.pack(anchor="w", pady=5)
        
        # Start Button
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=30)
        ttk.Button(btn_frame, text="Start Quiz", command=self._start_quiz, style="Large.TButton").pack(ipadx=20, ipady=10)

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
             # Generate quiz data
             # Since generation might be slow (Ollama), we should probably show a loading screen.
             pass
             # For this refactor, I'll assume synchronous generation or simplified start.
             # self.quiz_manager.generate_quiz(...)
             
             # Launch Quiz Session Window
             QuizSessionWindow(self, self.quiz_manager, quiz_type, count, difficulty)
             
        except Exception as e:
             messagebox.showerror("Error", f"Failed to start quiz: {e}")

class QuizSessionWindow(tk.Toplevel):
    def __init__(self, parent, quiz_manager, quiz_type, count, difficulty):
        super().__init__(parent)
        self.quiz_manager = quiz_manager
        self.title("Quiz Session")
        self.geometry("600x500")
        
        self.questions = []
        self.current_idx = 0
        self.score = 0
        
        ttk.Label(self, text=f"Generating {count} questions...", font=("Arial", 14)).pack(pady=50)
        self.update()
        
        try:
             # This is synchronous and might freeze UI. In full app use threading.
             # We simulate fetching questions.
             self.questions = self.quiz_manager.generate_quiz(quiz_type, count, difficulty)
             if not self.questions:
                  messagebox.showinfo("Info", "No questions available for this criteria.")
                  self.destroy()
                  return
             self._show_question()
        except Exception as e:
             messagebox.showerror("Error", f"Quiz generation failed: {e}")
             self.destroy()

    def _show_question(self):
        for widget in self.winfo_children(): widget.destroy()
        
        if self.current_idx >= len(self.questions):
             self._show_results()
             return
             
        q = self.questions[self.current_idx]
        
        ttk.Label(self, text=f"Question {self.current_idx + 1}/{len(self.questions)}", font=("Arial", 10)).pack(pady=10)
        
        ttk.Label(self, text=q['question'], font=("Arial", 14, "bold"), wraplength=500).pack(pady=20, padx=20)
        
        options_frame = ttk.Frame(self)
        options_frame.pack(fill="both", expand=True, padx=40)
        
        for i, opt in enumerate(q['options']):
             ttk.Button(options_frame, text=opt, command=lambda o=opt: self._submit_answer(o)).pack(fill="x", pady=5)
             
    def _submit_answer(self, answer):
        q = self.questions[self.current_idx]
        correct = (answer == q['correct_answer'])
        if correct: self.score += 1
        
        if correct:
             messagebox.showinfo("Correct!", "That's right!")
        else:
             messagebox.showerror("Incorrect", f"Wrong. The answer was: {q['correct_answer']}")
             
        self.current_idx += 1
        self._show_question()
        
    def _show_results(self):
        for widget in self.winfo_children(): widget.destroy()
        
        ttk.Label(self, text="Quiz Complete!", font=("Arial", 20, "bold")).pack(pady=30)
        ttk.Label(self, text=f"Score: {self.score}/{len(self.questions)}", font=("Arial", 16)).pack(pady=10)
        
        pct = (self.score / len(self.questions)) * 100
        msg = "Great job!" if pct > 80 else "Keep practicing!"
        ttk.Label(self, text=msg, font=("Arial", 12, "italic")).pack(pady=20)
        
        ttk.Button(self, text="Close", command=self.destroy).pack(pady=20)
