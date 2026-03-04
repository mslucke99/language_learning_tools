import tkinter as tk
from tkinter import ttk, messagebox
from src.features.study_center.logic.study_manager import StudyManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header
from src.core.localization import tr
from src.services.audio_service import AudioRecorder
from src.services.stt_providers import get_stt_provider
from src.services.tts_service import TTSService
from src.core.config import config as app_config
from src.features.study_center.ui.dialogs import DeckPickerDialog
import os
import threading

class AudioReviewFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, db: FlashcardDatabase):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        
        self.audio_recorder = AudioRecorder(sample_rate=app_config.audio_sample_rate)
        
        try:
            self.stt_provider = get_stt_provider(app_config.stt_provider)
            self.tts_service = TTSService(app_config.tts_provider)
        except Exception as e:
            print(f"[AudioReview] Failed to initialize audio services: {e}")
            self.stt_provider = None
            
        self.due_cards = []
        self.current_card_idx = -1
        self.is_recording = False
        self.session_active = False
        self.stats = {'correct': 0, 'incorrect': 0, 'total': 0}
        
        self.setup_ui()
        
    def setup_ui(self):
        setup_standard_header(self, tr("title_audio_review", "Audio Review"), 
                              tr("desc_audio_review", "Hands-free voice review of your due flashcards."))
        
        self.setup_panel = ttk.Frame(self, padding=20)
        self.setup_panel.pack(fill="both", expand=True)
        
        ttk.Label(self.setup_panel, text="Select a deck to begin hands-free review:", font=("Segoe UI", 12)).pack(pady=20)
        
        ttk.Button(self.setup_panel, text="Select Deck", command=self._select_deck, style="Large.TButton").pack(pady=10)
        
        ttk.Button(self.setup_panel, text=tr("btn_back", "Back to Dashboard"), command=self.controller.show_home).pack(pady=20)
        
        # Interactive Review Panel (hidden initially)
        self.review_panel = ttk.Frame(self, padding=20)
        
        self.status_lbl = ttk.Label(self.review_panel, text="", font=("Segoe UI", 16, "bold"), foreground="blue")
        self.status_lbl.pack(pady=20)
        
        self.question_lbl = ttk.Label(self.review_panel, text="", font=("Segoe UI", 24), wraplength=800, justify="center")
        self.question_lbl.pack(pady=40)
        
        self.instruction_lbl = ttk.Label(self.review_panel, text="Press SPACE to Record/Stop. Press ESC to End Session.", font=("Segoe UI", 12, "italic"))
        self.instruction_lbl.pack(pady=20)

    def _select_deck(self):
        picker = DeckPickerDialog(self, self.db, title="Review Deck")
        self.wait_window(picker.dialog)
        
        deck_id = picker.selected_deck_id
        if deck_id is None:
            return
            
        cards = self.db.get_due_flashcards(deck_id)
        if not cards:
            messagebox.showinfo("Done", "No cards due for review in this deck!")
            return
            
        self.due_cards = cards
        self.current_card_idx = -1
        self.stats = {'correct': 0, 'incorrect': 0, 'total': 0}
        
        self.setup_panel.pack_forget()
        self.review_panel.pack(fill="both", expand=True)
        
        # Bind keys
        self.winfo_toplevel().bind('<space>', self._handle_space)
        self.winfo_toplevel().bind('<Escape>', self._handle_escape)
        self.session_active = True
        
        self._next_card()

    def _handle_space(self, event):
        if not self.session_active: return
        # Prevent auto-repeat holding space
        if getattr(self, '_space_pressed', False): return
        self._space_pressed = True
        self.root.after(300, lambda: setattr(self, '_space_pressed', False))
        
        if self.status_lbl.cget("text") == "Waiting for Answer...":
            self._start_recording()
        elif self.status_lbl.cget("text") == "Recording...":
            self._stop_recording()

    def _handle_escape(self, event):
        self._end_session()

    def _end_session(self):
        self.session_active = False
        self.winfo_toplevel().unbind('<space>')
        self.winfo_toplevel().unbind('<Escape>')
        
        if self.is_recording:
            try: self.audio_recorder.stop_recording()
            except: pass
            
        self.review_panel.pack_forget()
        self.setup_panel.pack(fill="both", expand=True)
        
        total = self.stats['total']
        if total > 0:
            acc = (self.stats['correct'] / total) * 100
            messagebox.showinfo("Session Complete", f"Reviewed {total} cards.\nAccuracy: {acc:.1f}%\nCorrect: {self.stats['correct']}\nIncorrect: {self.stats['incorrect']}")

    def _next_card(self):
        if not self.session_active: return
        self.current_card_idx += 1
        if self.current_card_idx >= len(self.due_cards):
            self._end_session()
            return

        self.card = self.due_cards[self.current_card_idx]
        self.question_lbl.config(text=self.card.question)
        self.status_lbl.config(text="Reading Question...", foreground="blue")
        self.update_idletasks()
        
        def _read():
            try:
                # Read question out loud
                audio_path = self.tts_service.synthesize(self.card.question, language=self.study_manager.native_language)
                self.tts_service.play(audio_path)
                if self.session_active:
                    self.root.after(0, lambda: self.status_lbl.config(text="Waiting for Answer...", foreground="green"))
            except Exception as e:
                print(f"TTS Error: {e}")
                self.root.after(0, lambda: self.status_lbl.config(text="TTS Error. Press SPACE to record.", foreground="orange"))
                
        threading.Thread(target=_read, daemon=True).start()

    def _start_recording(self):
        try:
            self.audio_recorder.start_recording()
            self.is_recording = True
            self.status_lbl.config(text="Recording...", foreground="red")
        except Exception as e:
            messagebox.showerror("Audio Error", str(e))

    def _stop_recording(self):
        try:
            audio_path = self.audio_recorder.stop_recording()
            self.is_recording = False
            self.status_lbl.config(text="Processing Answer...", foreground="blue")
            
            threading.Thread(target=self._process_answer, args=(audio_path,), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Audio Error", str(e))

    def _process_answer(self, audio_path):
        if not self.session_active: return
        try:
            # Transcribe
            stt_res = self.stt_provider.transcribe(audio_path)
            user_transcript = stt_res.text
            
            # Grade Answer semantically
            prompt_template = self.study_manager._get_effective_prompt('speech', 'commuter_check')
            prompt = prompt_template.format(
                study_language=self.study_manager.study_language,
                question=self.card.question,
                answer=self.card.answer,
                transcription=user_transcript
            )
            
            llm_res = self.study_manager.ai_client.generate_response(prompt).strip()
            
            is_correct = llm_res.upper().startswith("CORRECT")
            quality = 4 if is_correct else 1
            
            self.stats['total'] += 1
            if is_correct:
                self.stats['correct'] += 1
                feedback_msg = "Correct."
            else:
                self.stats['incorrect'] += 1
                feedback_msg = "Incorrect. " + self.card.answer

            # Mark Reviewed
            self.card.mark_reviewed(quality)
            self.db.update_flashcard(self.card)
            self.db.log_review(self.card.id, quality, review_desc='audio_review')
            
            # Optionally handle pronunciation grading
            pronunciation_feedback = ""
            if getattr(self.card, 'pronunciation_flag', False):
                if app_config.stt_provider == "gemini":
                    # Multimodal feedback was already given via transcription if we passed audio
                    # But if we used commuter prompt, we would need 2 separate AI calls to get both meaning AND pronunciation
                    pronunciation_feedback = " Pronunciation logged via Gemini."
                else:
                    # Text diff grading
                    p_prompt = self.study_manager._get_effective_prompt('practice', 'pronunciation_feedback')
                    p_prompt = p_prompt.format(
                        study_language=self.study_manager.study_language,
                        native_language=self.study_manager.native_language,
                        target_text=self.card.answer,
                        transcribed_text=user_transcript
                    )
                    pronunciation_feedback = " " + self.study_manager.ai_client.generate_response(p_prompt)

            # Speak feedback
            final_spoken = f"{feedback_msg}. {pronunciation_feedback}"
            self.root.after(0, lambda: self.status_lbl.config(text="Reading Feedback..."))
            try:
                feedback_audio = self.tts_service.synthesize(final_spoken, language=self.study_manager.native_language)
                self.tts_service.play(feedback_audio)
            except:
                pass
            
            # Auto-advance
            self.root.after(1000, self._next_card)
            
        except Exception as e:
            print(f"Processing Error: {e}")
            self.root.after(0, lambda: self.status_lbl.config(text="Error. Press ESC to exit.", foreground="red"))
        finally:
            if os.path.exists(audio_path):
                try: os.remove(audio_path)
                except: pass

    # Utility proxy for thread safety on tk variables
    @property
    def root(self):
        return self.winfo_toplevel()
