import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from src.features.study_center.logic.study_manager import StudyManager
from src.core.database import FlashcardDatabase
from src.core.ui_utils import setup_standard_header
from src.core.localization import tr
from src.services.audio_service import AudioRecorder
from src.services.stt_providers import get_stt_provider
from src.services.tts_service import TTSService
from src.core.config import config as app_config
import os
import threading

class PronunciationLabFrame(ttk.Frame):
    def __init__(self, parent, controller, study_manager: StudyManager, db: FlashcardDatabase):
        super().__init__(parent)
        self.controller = controller
        self.study_manager = study_manager
        self.db = db
        
        self.audio_recorder = AudioRecorder(sample_rate=app_config.audio_sample_rate)
        
        # Audio services
        try:
            self.stt_provider = get_stt_provider(app_config.stt_provider)
            self.tts_service = TTSService(app_config.tts_provider)
        except Exception as e:
            print(f"[PronunciationLab] Failed to initialize audio services: {e}")
            self.stt_provider = None
        
        self.is_recording = False
        self.setup_ui()
        
    def setup_ui(self):
        setup_standard_header(self, tr("title_pronunciation_lab", "Pronunciation Lab"), 
                              tr("desc_pronunciation_lab", "Practice speaking and get AI feedback on your pronunciation."))
        
        # Main content area
        content_frame = ttk.Frame(self, padding=20)
        content_frame.pack(fill="both", expand=True)
        
        # Left Panel (Input / Target)
        left_panel = ttk.Frame(content_frame)
        left_panel.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        ttk.Label(left_panel, text=tr("lbl_target_sentence", "Target Sentence:"), font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.target_text = scrolledtext.ScrolledText(left_panel, height=8, width=40, font=("Segoe UI", 14), wrap=tk.WORD)
        self.target_text.pack(fill="both", expand=True, pady=(0, 10))
        
        controls_frame = ttk.Frame(left_panel)
        controls_frame.pack(fill="x", pady=10)
        
        self.play_btn = ttk.Button(controls_frame, text=tr("btn_play_native", "🔊 Play Native"), command=self._play_native)
        self.play_btn.pack(side="left", padx=5)
        
        self.record_btn = ttk.Button(controls_frame, text=tr("btn_record", "🎤 Record"), command=self._toggle_recording)
        self.record_btn.pack(side="left", padx=5)
        
        self.status_label = ttk.Label(controls_frame, text="", font=("Segoe UI", 10, "italic"))
        self.status_label.pack(side="left", padx=10)
        
        # Right Panel (Feedback)
        right_panel = ttk.Frame(content_frame)
        right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0))
        
        ttk.Label(right_panel, text=tr("lbl_feedback", "AI Feedback:"), font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5))
        
        self.feedback_text = scrolledtext.ScrolledText(right_panel, height=20, width=40, font=("Segoe UI", 12), wrap=tk.WORD, state=tk.DISABLED)
        self.feedback_text.pack(fill="both", expand=True, pady=(0, 10))
        
        # "Mark for Pronunciation" action for Audio Review
        self.mark_btn = ttk.Button(right_panel, text=tr("btn_mark_audio_review", "📌 Mark for Audio Review"), command=self._mark_card)
        self.mark_btn.pack(anchor="e")
        self.mark_btn.state(['disabled']) # Disabled by default until a flashcard is linked
        
        # Back Button
        footer = ttk.Frame(self)
        footer.pack(fill="x", side="bottom", pady=15, padx=20)
        ttk.Button(footer, text=tr("btn_back", "Back to Dashboard"), command=self.controller.show_home).pack(side="left")

    def _play_native(self):
        text = self.target_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Empty", "Please enter a target sentence to practice.")
            return
            
        self.play_btn.config(state=tk.DISABLED)
        self.status_label.config(text="Synthesizing audio...", foreground="blue")
        
        def _play():
            try:
                audio_path = self.tts_service.synthesize(text, language=self.study_manager.study_language)
                self.status_label.config(text="Playing audio...", foreground="blue")
                self.tts_service.play(audio_path)
                self.root.after(0, lambda: self.status_label.config(text=""))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Audio Error", str(e)))
                self.root.after(0, lambda: self.status_label.config(text="Error playing audio", foreground="red"))
            finally:
                self.root.after(0, lambda: self.play_btn.config(state=tk.NORMAL))
                
        threading.Thread(target=_play, daemon=True).start()

    def _toggle_recording(self):
        text = self.target_text.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Empty", "Please enter a target sentence first.")
            return

        if not self.is_recording:
            # Start Recording
            try:
                self.audio_recorder.start_recording()
                self.is_recording = True
                self.record_btn.config(text=tr("btn_stop_recording", "🛑 Stop Recording"))
                self.status_label.config(text="Recording...", foreground="red")
                self.play_btn.config(state=tk.DISABLED)
            except Exception as e:
                messagebox.showerror("Recording Error", f"Failed to access microphone: {e}")
        else:
            # Stop Recording & Process
            self.is_recording = False
            self.record_btn.config(text=tr("btn_record", "🎤 Record"))
            self.status_label.config(text="Processing audio...", foreground="blue")
            self.record_btn.config(state=tk.DISABLED)
            
            try:
                audio_path = self.audio_recorder.stop_recording()
                self._grade_pronunciation(audio_path, text)
            except Exception as e:
                messagebox.showerror("Recording Error", f"Failed to save recording: {e}")
                self._reset_ui()

    def _grade_pronunciation(self, audio_path: os.PathLike, target_text: str):
        def _process():
            try:
                # Use STT provider (which might be multimodal Gemini)
                if not self.stt_provider:
                    raise Exception("No STT Provider available/configured.")

                result = self.stt_provider.transcribe(audio_path)
                
                # Check if it was Gemini's multimodal STT (which returns full feedback in the text)
                raw_feedback = result.text
                
                # If Gemini just gave us a transcription (or we used Whisper), we'd need a second step to diff and grade.
                # Assuming Gemini STT provides rich text via prompt override (we need to configure GeminiSTTProvider to use the pronunciation prompt).
                # For now, let's just display what the STT provider returns. If it's whisper, it's just the transcribed text.
                
                # If it's just a raw text transcription (Whisper), call LLM to compare
                if app_config.stt_provider != "gemini":
                    self.root.after(0, lambda: self.status_label.config(text="Analyzing pronunciation differences..."))
                    
                    llm_client = self.study_manager.ai_client
                    prompt = self.study_manager._get_prompt('PRONUNCIATION_PROMPTS', 'text_diff_grade')
                    prompt = prompt.format(
                        study_language=self.study_manager.study_language,
                        native_language=self.study_manager.native_language,
                        target_text=target_text,
                        transcribed_text=raw_feedback
                    )
                    feedback_text = llm_client.generate_content(prompt)
                else:
                    feedback_text = raw_feedback

                self.root.after(0, lambda: self._display_feedback(feedback_text))
                
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Processing Error", str(e)))
                self.root.after(0, lambda: self.status_label.config(text="Error processing audio", foreground="red"))
            finally:
                # Cleanup temp audio file
                if os.path.exists(audio_path):
                    try: os.remove(audio_path)
                    except: pass
                self.root.after(0, self._reset_ui)

        threading.Thread(target=_process, daemon=True).start()

    def _display_feedback(self, feedback: str):
        self.feedback_text.config(state=tk.NORMAL)
        self.feedback_text.delete("1.0", tk.END)
        self.feedback_text.insert(tk.END, feedback)
        self.feedback_text.config(state=tk.DISABLED)
        self.status_label.config(text="Done.", foreground="green")

    def _reset_ui(self):
        self.record_btn.config(state=tk.NORMAL)
        self.play_btn.config(state=tk.NORMAL)

    def _mark_card(self):
        # To be implemented when we link this to specific flashcards
        pass
