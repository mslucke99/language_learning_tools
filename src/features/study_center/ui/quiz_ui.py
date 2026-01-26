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
        self.quiz_manager = QuizManager(db, study_manager.ai_client, timeout=timeout)
        
        self.setup_ui()
        
    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(self, "📝 Quiz Yourself", back_cmd=self.go_back)
        
        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)
        
        # Show Dashboard by default
        self._show_dashboard()

    def _show_dashboard(self):
        """Show the history dashboard entry point."""
        for widget in self.container.winfo_children():
            widget.destroy()
            
        header_fr = ttk.Frame(self.container, padding=20)
        header_fr.pack(fill="x")
        
        ttk.Label(header_fr, text="Quiz Dashboard", font=("Arial", 16, "bold")).pack(side="left")
        ttk.Button(header_fr, text="✨ Start New Quiz", style="Accent.TButton", 
                   command=self._show_quiz_setup).pack(side="right")
        
        # History Table
        history_fr = ttk.LabelFrame(self.container, text="Quiz History", padding=10)
        history_fr.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        columns = ("date", "type", "difficulty", "score")
        self.history_tree = ttk.Treeview(history_fr, columns=columns, show="headings", height=15)
        
        self.history_tree.heading("date", text="Date/Time")
        self.history_tree.heading("type", text="Type")
        self.history_tree.heading("difficulty", text="Difficulty")
        self.history_tree.heading("score", text="Score")
        
        self.history_tree.column("date", width=180)
        self.history_tree.column("type", width=120)
        self.history_tree.column("difficulty", width=100)
        self.history_tree.column("score", width=80, anchor="center")
        
        self.history_tree.pack(fill="both", expand=True, side="left")
        
        scrollbar = ttk.Scrollbar(history_fr, orient="vertical", command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(fill="y", side="right")
        
        self.history_tree.bind("<Double-1>", self._on_history_double_click)
        
        self._load_history()

    def _load_history(self):
        """Fetch history from manager and populate tree."""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)
            
        history = self.quiz_manager.get_quiz_history()
        for h in history:
            date_str = h['created_at'].replace('T', ' ')[:19]
            self.history_tree.insert("", "end", iid=str(h['id']), values=(
                date_str, 
                h['source_type'].capitalize(),
                h['difficulty'].capitalize(),
                f"{h['score']}%"
            ))

    def _on_history_double_click(self, event):
        item = self.history_tree.selection()
        if item:
            session_id = int(item[0])
            self._review_quiz(session_id)

    def _review_quiz(self, session_id):
        """Open the review window for a session."""
        QuizReviewWindow(self, self.quiz_manager, session_id, self.study_manager)

    def _show_quiz_setup(self):
        """Show the current setup UI."""
        for widget in self.container.winfo_children():
            widget.destroy()
            
        # Quiz Options
        options_frame = ttk.LabelFrame(self.container, text="New Quiz Settings", padding="20")
        options_frame.pack(fill="x", pady=20, padx=20)
        
        back_btn = ttk.Button(options_frame, text="◀ Back to History", command=self._show_dashboard)
        back_btn.pack(anchor="e")
        
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
        
        try:
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
                 
             win = QuizSessionWindow(self, self.quiz_manager, config)
             win.bind("<Destroy>", lambda e: self._show_dashboard()) # Refresh on close
             
        except Exception as e:
             messagebox.showerror("Error", f"Failed to start quiz: {e}")

class QuizReviewWindow(tk.Toplevel):
    def __init__(self, parent, quiz_manager, session_id, study_manager):
        super().__init__(parent)
        self.quiz_manager = quiz_manager
        self.session_id = session_id
        self.study_manager = study_manager
        
        self.title(f"Quiz Review: Session #{session_id}")
        self.geometry("800x700")
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        # Header
        header = ttk.Frame(self, padding=20)
        header.pack(fill="x")
        
        self.title_lbl = ttk.Label(header, text="Reviewing Session", font=("Arial", 16, "bold"))
        self.title_lbl.pack(side="left")
        
        self.score_lbl = ttk.Label(header, text="Score: --%", font=("Arial", 14, "bold"))
        self.score_lbl.pack(side="right")
        
        # Main Area (Two panels)
        paned = ttk.PanedWindow(self, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left: Question List
        list_fr = ttk.Frame(paned, padding=5)
        paned.add(list_fr, weight=2)
        
        ttk.Label(list_fr, text="Questions", font=("Arial", 10, "bold")).pack(anchor="w")
        self.questions_tree = ttk.Treeview(list_fr, columns=("status", "question"), show="headings")
        self.questions_tree.heading("status", text="Stat")
        self.questions_tree.heading("question", text="Question")
        self.questions_tree.column("status", width=50, anchor="center")
        self.questions_tree.column("question", width=300)
        self.questions_tree.pack(fill="both", expand=True)
        self.questions_tree.bind("<<TreeviewSelect>>", self._on_question_select)
        
        # Right: AI Insights & Suggestions
        insights_fr = ttk.Frame(paned, padding=5)
        paned.add(insights_fr, weight=3)
        
        # Notebook for details and AI
        self.tabs = ttk.Notebook(insights_fr)
        self.tabs.pack(fill="both", expand=True)
        
        # Tab 1: Question Details
        self.detail_tab = ttk.Frame(self.tabs, padding=15)
        self.tabs.add(self.detail_tab, text="🔍 Details")
        
        self.detail_text = tk.Text(self.detail_tab, wrap="word", font=("Arial", 11), height=10)
        self.detail_text.pack(fill="both", expand=True)
        self.detail_text.config(state="disabled")
        
        # Tab 2: AI Analysis
        self.ai_tab = ttk.Frame(self.tabs, padding=15)
        self.tabs.add(self.ai_tab, text="🤖 AI Analysis")
        
        self.analysis_btn = ttk.Button(self.ai_tab, text="✨ Analyze My Performance", 
                                      command=self._generate_analysis)
        self.analysis_btn.pack(pady=10)
        
        self.analysis_text = tk.Text(self.ai_tab, wrap="word", font=("Arial", 11), height=15)
        self.analysis_text.pack(fill="both", expand=True)
        
        # Suggestions bar (at bottom of AI tab)
        self.sugg_frame = ttk.Frame(self.ai_tab)
        self.sugg_frame.pack(fill="x", pady=10)

    def load_data(self):
        data = self.quiz_manager.get_session_details(self.session_id)
        if not data: return
        
        self.session_data = data
        self.title_lbl.config(text=f"Quiz Review: {data['source_type'].capitalize()} ({data['created_at'][:16]})")
        self.score_lbl.config(text=f"Score: {data['score']}%")
        
        for q in data['questions']:
            status = "✅" if q['is_correct'] else "❌"
            self.questions_tree.insert("", "end", iid=str(q['id']), values=(status, q['question_text']))

    def _on_question_select(self, event):
        item = self.questions_tree.selection()
        if not item: return
        q_id = int(item[0])
        q = next((x for x in self.session_data['questions'] if x['id'] == q_id), None)
        if not q: return
        
        self.detail_text.config(state="normal")
        self.detail_text.delete("1.0", "end")
        
        self.detail_text.insert("end", f"QUESTION:\n{q['question_text']}\n\n", "bold")
        self.detail_text.insert("end", f"YOUR ANSWER: {q['user_answer']}\n", "red" if not q['is_correct'] else "green")
        self.detail_text.insert("end", f"CORRECT ANSWER: {q['correct_answer']}\n\n", "green")
        
        if q.get('explanation'):
             self.detail_text.insert("end", f"EXPLANATION:\n{q['explanation']}")
             
        self.detail_text.config(state="disabled")

    def _generate_analysis(self):
        self.analysis_btn.config(state="disabled", text="⌛ Analyzing...")
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("end", "AI is analyzing your performance. This may take 10-20 seconds...\n")
        self.update()
        
        def run():
            try:
                study_lang = self.study_manager.study_language
                native_lang = self.study_manager.native_language
                
                response = self.quiz_manager.generate_performance_analysis(
                    self.session_id, study_lang, native_lang
                )
                
                if not response:
                    self._update_analysis_ui("Could not get AI feedback. Please check your connection.")
                    return
                
                # Parse structured response
                import re, json
                
                def extract(tag, text):
                    m = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL | re.IGNORECASE)
                    return m.group(1).strip() if m else ""
                
                analysis = extract("analysis", response)
                tips = extract("tips", response)
                suggestions_raw = extract("suggestions", response)
                
                full_report = f"### PERFORMANCE ANALYSIS\n{analysis}\n\n### ACTIONABLE TIPS\n{tips}"
                
                # Update text area
                self._update_analysis_ui(full_report)
                
                # Parse suggestions list
                if suggestions_raw:
                    try:
                        # Find potential json within block
                        json_match = re.search(r"(\[.*\])", suggestions_raw, re.DOTALL)
                        if json_match:
                            suggestions = json.loads(json_match.group(1))
                            self._display_suggestions(suggestions)
                    except Exception as e:
                        print(f"Error parsing suggestions: {e}")
                        
            except Exception as e:
                self._update_analysis_ui(f"An error occurred during analysis: {e}")
            finally:
                self.analysis_btn.config(state="normal", text="✨ Re-Analyze Performance")
        
        import threading
        threading.Thread(target=run, daemon=True).start()

    def _update_analysis_ui(self, text):
        self.analysis_text.delete("1.0", "end")
        self.analysis_text.insert("end", text)
        
    def _display_suggestions(self, suggestions):
        # Clear existing
        for w in self.sugg_frame.winfo_children(): w.destroy()
        
        if not suggestions: return
        
        ttk.Label(self.sugg_frame, text="Recommended for Study:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(0, 5))
        
        for item in suggestions:
            row = ttk.Frame(self.sugg_frame)
            row.pack(fill="x", pady=2)
            
            label = f"[{item.get('type', 'item')}] {item.get('item')}: {item.get('definition')}"
            ttk.Label(row, text=label, wraplength=500).pack(side="left", padx=5)
            
            # Action button
            if item.get('type') == 'vocab':
                ttk.Button(row, text="➕ Add Word", width=12, 
                           command=lambda i=item: self._add_vocab_sugg(i)).pack(side="right")
            else:
                ttk.Button(row, text="✨ Save Pattern", width=12, 
                           command=lambda i=item: self._add_grammar_sugg(i)).pack(side="right")

    def _add_vocab_sugg(self, item):
        word = item['item']
        definition = item['definition']
        
        from src.features.study_center.ui.dialogs import DeckPickerDialog
        dialog = DeckPickerDialog(self, self.db)
        self.wait_window(dialog)
        
        if dialog.selected_deck_id:
            deck_id = dialog.selected_deck_id
            self.db.add_flashcard(deck_id, word, definition)
            messagebox.showinfo("Success", f"Added '{word}' to deck!")

    def _add_grammar_sugg(self, item):
        title = item['item']
        content = item['definition']
        self.db.add_grammar_entry(title, content, tags="quiz-suggestion")
        messagebox.showinfo("Success", f"Saved '{title}' to Grammar Book!")

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
