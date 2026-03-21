"""Review View for spaced repetition review sessions."""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from src.features.study_center.logic.study_manager import StudyManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header
from src.core.localization import tr


class ReviewView(ttk.Frame):
    """View for conducting review sessions with spaced repetition."""
    
    def __init__(self, parent, controller, study_manager: StudyManager, db: FlashcardDatabase, embedded=False):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        self.embedded = embedded
        
        # Review session state
        self.due_sentences = []
        self.current_index = 0
        self.session_results = []
        
        self.setup_ui()
        self.load_due_sentences()
    
    def setup_ui(self):
        if not self.embedded:
            setup_standard_header(
                self,
                tr("sentence_review", "Sentence Review"),
                back_cmd=self.go_back
            )
        else:
            header = ttk.Frame(self)
            header.pack(fill="x", padx=10, pady=5)
            ttk.Label(header, text=tr("sentence_review", "Sentence Review"), 
                     font=("Arial", 14, "bold")).pack(side="left")
        
        # Main content area
        self.content_frame = ttk.Frame(self, padding="20")
        self.content_frame.pack(fill="both", expand=True)
        
        # Progress indicator
        self.progress_frame = ttk.Frame(self.content_frame)
        self.progress_frame.pack(fill="x", pady=(0, 20))
        
        self.progress_label = ttk.Label(self.progress_frame, text="", font=("Arial", 12))
        self.progress_label.pack(side="left")
        
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode="determinate")
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=10)
        
        # Sentence display
        self.sentence_frame = ttk.LabelFrame(self.content_frame, text=tr("lbl_sentence", "Sentence"), padding="20")
        self.sentence_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        self.sentence_text = tk.Text(self.sentence_frame, font=("Arial", 14), wrap="word", 
                                     height=6, bg="#f5f5f5", relief="flat")
        self.sentence_text.pack(fill="both", expand=True)
        self.sentence_text.config(state="disabled")
        
        # Difficulty badge
        self.difficulty_label = ttk.Label(self.sentence_frame, text="", font=("Arial", 10))
        self.difficulty_label.pack(anchor="e", pady=(10, 0))
        
        # Action buttons
        self.button_frame = ttk.Frame(self.content_frame)
        self.button_frame.pack(fill="x")
        
        self.forgot_btn = ttk.Button(self.button_frame, text="✗ I Forgot", 
                                     command=lambda: self._record_review(False),
                                     style="Danger.TButton")
        self.forgot_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        self.remember_btn = ttk.Button(self.button_frame, text="✓ I Remember", 
                                       command=lambda: self._record_review(True),
                                       style="Success.TButton")
        self.remember_btn.pack(side="left", padx=5, fill="x", expand=True)
        
        # Feedback area
        self.feedback_frame = ttk.Frame(self.content_frame)
        self.feedback_frame.pack(fill="x", pady=(20, 0))
        
        self.feedback_label = ttk.Label(self.feedback_frame, text="", font=("Arial", 11), 
                                        foreground="blue", wraplength=400)
        self.feedback_label.pack()
        
        # Next review date
        self.next_review_label = ttk.Label(self.feedback_frame, text="", font=("Arial", 10))
        self.next_review_label.pack()
        
        # Empty state
        self.empty_frame = ttk.Frame(self.content_frame)
        self.empty_frame.pack(fill="both", expand=True)
        
        ttk.Label(self.empty_frame, text="🎉", font=("Arial", 48)).pack(pady=20)
        ttk.Label(self.empty_frame, text=tr("msg_no_sentences_due", "No sentences due for review!"),
                 font=("Arial", 14)).pack()
        ttk.Label(self.empty_frame, text=tr("msg_great_job", "Great job! Come back later."),
                 font=("Arial", 10)).pack()
        
        # Configure button styles
        style = ttk.Style()
        style.configure("Success.TButton", background="#4CAF50", foreground="white")
        style.configure("Danger.TButton", background="#f44336", foreground="white")
        
        self._show_empty_state()
    
    def load_due_sentences(self):
        """Load sentences due for review."""
        try:
            self.due_sentences = self.study_manager.get_due_sentences()
            self.current_index = 0
            self.session_results = []
            
            if self.due_sentences:
                self._show_review_state()
                self._load_current_sentence()
            else:
                self._show_empty_state()
        except Exception as e:
            messagebox.showerror(tr("msg_error", "Error"), f"Failed to load due sentences: {e}")
            self._show_empty_state()
    
    def _show_empty_state(self):
        """Show empty state when no sentences are due."""
        self.empty_frame.pack(fill="both", expand=True)
        self.progress_frame.pack(fill="x", pady=(0, 20))
        self.sentence_frame.pack_forget()
        self.button_frame.pack_forget()
        self.feedback_frame.pack_forget()
        
        self.progress_label.config(text="")
        self.progress_bar["value"] = 0
    
    def _show_review_state(self):
        """Show the review interface."""
        self.empty_frame.pack_forget()
        self.progress_frame.pack(fill="x", pady=(0, 20))
        self.sentence_frame.pack(fill="both", expand=True, pady=(0, 20))
        self.button_frame.pack(fill="x")
        self.feedback_frame.pack(fill="x", pady=(20, 0))
    
    def _load_current_sentence(self):
        """Load the current sentence for review."""
        if self.current_index >= len(self.due_sentences):
            self._show_session_complete()
            return
        
        sentence = self.due_sentences[self.current_index]
        
        # Update progress
        total = len(self.due_sentences)
        self.progress_label.config(text=f"{self.current_index + 1} / {total}")
        self.progress_bar["value"] = ((self.current_index + 1) / total) * 100
        
        # Display sentence
        self.sentence_text.config(state="normal")
        self.sentence_text.delete(1.0, tk.END)
        self.sentence_text.insert(tk.END, sentence['sentence'])
        self.sentence_text.config(state="disabled")
        
        # Display difficulty
        diff_score = sentence.get('difficulty_score')
        if diff_score is not None:
            diff_class = self._classify_difficulty(diff_score)
            diff_color = {"easy": "green", "medium": "orange", "hard": "red"}.get(diff_class, "black")
            self.difficulty_label.config(text=f"Difficulty: {diff_class.capitalize()} ({diff_score:.2f})", 
                                         foreground=diff_color)
        else:
            self.difficulty_label.config(text="Difficulty: Not analyzed", foreground="gray")
        
        # Clear feedback
        self.feedback_label.config(text="")
        self.next_review_label.config(text="")
        
        # Store current sentence ID
        self.current_sentence_id = sentence['id']
    
    def _classify_difficulty(self, score):
        """Classify difficulty score into easy/medium/hard."""
        if score <= 0.33:
            return "easy"
        elif score <= 0.66:
            return "medium"
        else:
            return "hard"
    
    def _record_review(self, correct: bool):
        """Record a review result."""
        if not hasattr(self, 'current_sentence_id'):
            return
        
        try:
            result = self.study_manager.record_sentence_review(
                self.current_sentence_id, correct
            )
            
            self.session_results.append({
                'sentence_id': self.current_sentence_id,
                'correct': correct,
                'result': result
            })
            
            # Show feedback
            if correct:
                self.feedback_label.config(text=f"✓ Correct! Next review in {result.get('interval_days', 1)} day(s)",
                                          foreground="green")
            else:
                self.feedback_label.config(text="✗ Incorrect. Review again tomorrow.",
                                          foreground="red")
            
            next_date = result.get('next_review_date', '')
            if next_date:
                self.next_review_label.config(text=f"Next review: {next_date}")
            
            # Move to next sentence after brief delay
            self.after(1500, self._advance_to_next)
            
        except Exception as e:
            messagebox.showerror(tr("msg_error", "Error"), f"Failed to record review: {e}")
    
    def _advance_to_next(self):
        """Move to the next sentence in the queue."""
        self.current_index += 1
        self._load_current_sentence()
    
    def _show_session_complete(self):
        """Show session completion summary."""
        total = len(self.session_results)
        correct = sum(1 for r in self.session_results if r['correct'])
        accuracy = (correct / total * 100) if total > 0 else 0
        
        self.empty_frame.pack(fill="both", expand=True)
        self.progress_frame.pack_forget()
        self.sentence_frame.pack_forget()
        self.button_frame.pack_forget()
        self.feedback_frame.pack_forget()
        
        # Clear and rebuild empty frame content
        for widget in self.empty_frame.winfo_children():
            widget.destroy()
        
        ttk.Label(self.empty_frame, text="📚", font=("Arial", 48)).pack(pady=20)
        ttk.Label(self.empty_frame, text=tr("msg_session_complete", "Session Complete!"),
                 font=("Arial", 14, "bold")).pack()
        
        summary_text = f"You reviewed {total} sentence(s).\nCorrect: {correct}/{total} ({accuracy:.0f}%)"
        ttk.Label(self.empty_frame, text=summary_text, font=("Arial", 11)).pack(pady=10)
        
        btn_frame = ttk.Frame(self.empty_frame)
        btn_frame.pack(pady=20)
        
        ttk.Button(btn_frame, text=tr("btn_review_more", "Review More"), 
                  command=self.load_due_sentences).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("btn_back_to_dashboard", "Back to Dashboard"), 
                  command=self.go_back).pack(side="left", padx=5)
    
    def go_back(self):
        """Navigate back to the dashboard."""
        if hasattr(self.controller, 'show_study_dashboard'):
            self.controller.show_study_dashboard()
    
    def on_show(self):
        """Refresh when view becomes visible."""
        self.load_due_sentences()