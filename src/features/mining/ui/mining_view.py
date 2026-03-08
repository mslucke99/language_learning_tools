import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading

from src.core.localization import tr
from src.core.database import FlashcardDatabase
from src.services.dictionary.dictionary_manager import DictionaryManager, DictionaryEngine
from src.services.text.tokenizer_service import TokenizerService
from src.services.text.sentence_miner import SentenceMiner, MiningResult
from src.services.text.text_importer import TextImporter
from src.services.text.sentence_difficulty import (
    SentenceDifficultyScorer,
    UserProfile,
    make_tokenizer_adapter_from_tokenizer_service,
    make_recall_provider_from_db,
)
from src.services.text.difficulty_resources import load_resource_bundle
from src.services.text.difficulty_categories import CATEGORIES as DIFF_CATEGORIES
from src.services.text.vocab_calibration import VocabCalibrationService
from src.features.mining.ui.calibration_dialog import CalibrationDialog
from src.features.mining.ui.known_words_view import KnownWordsView
from src.features.chat.ui.scenario_editor import ScenarioEditorDialog


from src.features.study_center.logic.study_manager import StudyManager
from src.services.semantic_visualizer import SemanticVisualizer
from src.services.text.semantic_familiarity import SemanticFamiliarityScorer
from src.services.llm_service import get_ai_client

class SentenceMiningView(ttk.Frame):
    def __init__(self, parent, db: FlashcardDatabase, study_manager: StudyManager = None):
        super().__init__(parent)
        self.db = db
        self.study_manager = study_manager
        
        # Get language from StudyManager if available, otherwise default
        if self.study_manager:
            self.lang_code = self.study_manager.get_study_language_code()
        else:
            self.lang_code = "es" # Default fallback
            
        self.tokenizer = TokenizerService()
        self.dict_engine = DictionaryEngine()
        self.miner = SentenceMiner(db, self.tokenizer, difficulty_scorer=None)
        self._difficulty_scorer_cache = {}  # lang_code -> scorer (optional, for reuse)
        self.current_view_sentences = []
        self.selected_sentence = None
        self.mining_result = None
        self._embedding_cache = {}  # lemma -> list[float]

        self.setup_ui()
        
    def on_show(self):
        """Called when this tab is selected."""
        # Refresh language code in case user changed study language
        if self.study_manager:
            self.lang_code = self.study_manager.get_study_language_code()
        self.check_calibration()

    def check_calibration(self):
        service = VocabCalibrationService(self.db)
        if not service.is_calibrated(self.lang_code):
            lang_display = VocabCalibrationService.DISPLAY_NAMES.get(self.lang_code, self.lang_code)
            if messagebox.askyesno("Setup", f"You haven't calibrated your {lang_display} vocabulary yet. Do it now?"):
                CalibrationDialog(self, self.db, lang_code=self.lang_code, on_complete=self.refresh_unknown_panel)

    def setup_ui(self):
        # 1. Top Bar: Import Controls
        top_bar = ttk.Frame(self, padding=5)
        top_bar.pack(fill="x")
        
        self.var_filter = tk.StringVar(value="all")
        self.target_cat = tk.StringVar(value="Any")
        self.sort_mode = tk.StringVar(value="Order")
        
        ttk.Button(top_bar, text="Import File...", command=self.import_file).pack(side="left", padx=5)
        ttk.Button(top_bar, text="Paste Clipboard", command=self.import_clipboard).pack(side="left", padx=5)
        
        ttk.Button(top_bar, text="Manage Known Words", command=self.open_manager).pack(side="right", padx=5)
        
        # 2. Main Content
        # Use pack with expand=True to fill available space
        paned = tk.PanedWindow(self, orient="horizontal", sashrelief="raised")
        paned.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Left: Notebook for List vs Reading View
        self.notebook_left = ttk.Notebook(paned)
        paned.add(self.notebook_left, minsize=400)
        
        # Tab 1: Mining List
        self.tab_list = ttk.Frame(self.notebook_left)
        self.notebook_left.add(self.tab_list, text="Mining List")
        
        # Filter buttons (moved to tab_list)
        filter_frame = ttk.Frame(self.tab_list)
        filter_frame.pack(fill="x", pady=2)
        ttk.Radiobutton(filter_frame, text="All", variable=self.var_filter, value="all", command=self.filter_sentences).pack(side="left", padx=2)
        ttk.Radiobutton(filter_frame, text="i+0", variable=self.var_filter, value="i+0", command=self.filter_sentences).pack(side="left", padx=2)
        ttk.Radiobutton(filter_frame, text="i+1 (Target)", variable=self.var_filter, value="i+1", command=self.filter_sentences).pack(side="left", padx=2)

        ttk.Label(filter_frame, text="Category:").pack(side="left", padx=(10, 2))
        self.combo_category = ttk.Combobox(filter_frame, textvariable=self.target_cat, values=["Any", "Mastered", "Review", "Sweet Spot", "Stretch", "Too Hard"], width=12, state="readonly")
        self.combo_category.pack(side="left", padx=2)
        self.combo_category.bind("<<ComboboxSelected>>", lambda e: self.filter_sentences())

        ttk.Label(filter_frame, text="Sort:").pack(side="left", padx=(10, 2))
        self.combo_sort = ttk.Combobox(filter_frame, textvariable=self.sort_mode, values=["Order", "Difficulty (Low)", "Difficulty (High)", "Unknowns"], width=15, state="readonly")
        self.combo_sort.pack(side="left", padx=2)
        self.combo_sort.bind("<<ComboboxSelected>>", lambda e: self.filter_sentences())
        
        ttk.Separator(filter_frame, orient="vertical").pack(side="left", padx=10, fill="y")
        
        self.btn_reweight = ttk.Button(filter_frame, text="🧠 Reweight via Semantics", command=self.reweight_via_semantics)
        self.btn_reweight.pack(side="left", padx=5)
        
        self.tree_sentences = ttk.Treeview(
            self.tab_list, columns=("Text", "Level", "Difficulty", "Category"), show="headings"
        )
        self.tree_sentences.heading("Text", text="Text")
        self.tree_sentences.heading("Level", text="Unknowns")
        self.tree_sentences.heading("Difficulty", text="Difficulty")
        self.tree_sentences.heading("Category", text="Category")
        self.tree_sentences.column("Text", width=320)
        self.tree_sentences.column("Level", width=60, anchor="center")
        self.tree_sentences.column("Difficulty", width=56, anchor="center")
        self.tree_sentences.column("Category", width=90, anchor="center")
        self.tree_sentences.pack(fill="both", expand=True)
        
        # Configure tags for colors
        for cat_key, meta in DIFF_CATEGORIES.items():
            self.tree_sentences.tag_configure(cat_key, foreground=meta["color"])
        
        # Scrollbar for tree
        scrollbar = ttk.Scrollbar(self.tab_list, orient="vertical", command=self.tree_sentences.yview)
        self.tree_sentences.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree_sentences.pack(side="left", fill="both", expand=True)
        
        self.tree_sentences.bind("<<TreeviewSelect>>", self.on_sentence_select)
        
        # Tags for coloring
        self.tree_sentences.tag_configure("i+0", foreground="green")
        self.tree_sentences.tag_configure("i+1", foreground="#D4AF37") # Gold
        # self.tree_sentences.tag_configure("i+2", foreground="red") # Default black/red

        # Tab 2: Raw Reading View
        self.tab_reading = ttk.Frame(self.notebook_left)
        self.notebook_left.add(self.tab_reading, text="Reading View")
        
        self.txt_reading = tk.Text(self.tab_reading, wrap="word", font=("Arial", 11))
        scroll_reading = ttk.Scrollbar(self.tab_reading, orient="vertical", command=self.txt_reading.yview)
        self.txt_reading.configure(yscrollcommand=scroll_reading.set)
        scroll_reading.pack(side="right", fill="y")
        self.txt_reading.pack(side="left", fill="both", expand=True)

        # Right: Unknown Words & Details
        # Use a vertical paned window so details don't get cut off
        right_panel = tk.PanedWindow(paned, orient="vertical", sashrelief="raised")
        paned.add(right_panel, minsize=250)
        
        # Top Right: Unknown Words List (Quick Mark)
        self.unknown_frame = ttk.Labelframe(right_panel, text="Unknown Words in Text", height=200)
        right_panel.add(self.unknown_frame, minsize=150) # Add to paned window
        
        self.tree_unknown = ttk.Treeview(self.unknown_frame, columns=("Word",), show="headings")
        self.tree_unknown.heading("Word", text="Select Word to Action")
        self.tree_unknown.pack(fill="both", expand=True)
        
        # Action Buttons for Unknown Words
        btn_frame = ttk.Frame(self.unknown_frame)
        btn_frame.pack(fill="x", pady=2)
        
        self.btn_mark_known = ttk.Button(btn_frame, text="✓ Mark Known", state="disabled", command=self.mark_selected_known)
        self.btn_mark_known.pack(side="left", fill="x", expand=True, padx=2)
        
        self.btn_add_vocab = ttk.Button(btn_frame, text="📚 Add to Study", state="disabled", command=self.add_selected_to_study)
        self.btn_add_vocab.pack(side="left", fill="x", expand=True, padx=2)
        
        self.tree_unknown.bind("<<TreeviewSelect>>", self.on_unknown_select)
        
        # Bottom Right: Sentence Detail
        self.detail_frame = ttk.Labelframe(right_panel, text="Sentence Detail")
        right_panel.add(self.detail_frame, minsize=150) # Add to paned window
        
        self.lbl_detail = tk.Text(self.detail_frame, wrap="word", height=6, font=("Arial", 11))
        self.lbl_detail.pack(fill="x", padx=5, pady=5)
        self.lbl_detail.config(state="disabled")
        
        self.btn_add_sentence = ttk.Button(self.detail_frame, text="📖 Add to Study Center", state="disabled", command=self.add_sentence_to_study)
        self.btn_add_sentence.pack(pady=5, fill="x", padx=5)

        self.btn_use_for_chat = ttk.Button(self.detail_frame, text="💬 Use for Chat", state="disabled", command=self.use_sentence_for_chat)
        self.btn_use_for_chat.pack(pady=5, fill="x", padx=5)

    def open_manager(self):
        # If already open, just bring to front
        if hasattr(self, 'manager_win') and self.manager_win.winfo_exists():
            self.manager_win.lift()
            self.manager_win.focus_set()
            return
            
        self.manager_win = tk.Toplevel(self)
        self.manager_win.title("Known Words Manager")
        self.manager_win.geometry("600x500")
        
        self.manager_view = KnownWordsView(
            self.manager_win, 
            self.db, 
            self.lang_code, 
            on_change=self.on_known_words_changed
        )
        self.manager_view.pack(fill="both", expand=True)

    def on_known_words_changed(self):
        """Called when words are added/deleted in the manager."""
        if hasattr(self, 'mining_result'):
            self.update_mining_levels()
            self.refresh_unknown_panel()

    def import_file(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt *.srt *.html *.epub")])
        if path:
            try:
                text = TextImporter.import_file(path)
                self.process_text(text)
            except Exception as e:
                messagebox.showerror("Error", f"Import failed: {e}")

    def import_clipboard(self):
        try:
            text = self.clipboard_get()
            self.process_text(text)
        except:
            messagebox.showerror("Error", "Clipboard is empty")

    def _get_difficulty_scorer(self):
        """Build or reuse a SentenceDifficultyScorer for current language."""
        lang = self.lang_code or "en"
        if lang in self._difficulty_scorer_cache:
            return self._difficulty_scorer_cache[lang]
        try:
            db_path = getattr(self.db, "db_path", "")
            resources = load_resource_bundle(
                lang, db_path, load_frequency=True, load_graded=False, load_quantiles=False
            )
            profile = UserProfile(claimed_level="B1", language=lang)
            adapter = make_tokenizer_adapter_from_tokenizer_service(self.tokenizer)
            recall_provider = make_recall_provider_from_db(self.db)
            scorer = SentenceDifficultyScorer(
                tokenizer_adapter=adapter,
                resources=resources,
                user_profile=profile,
                recall_provider=recall_provider,
            )
            self._difficulty_scorer_cache[lang] = scorer
            return scorer
        except Exception:
            return None

    def process_text(self, text):
        if not text.strip(): return

        self.miner.difficulty_scorer = self._get_difficulty_scorer()

        def run():
            result = self.miner.analyze_text(text, self.lang_code)
            self.after(0, lambda: self.display_results(result))

        threading.Thread(target=run, daemon=True).start()

    def display_results(self, result: MiningResult):
        self.mining_result = result
        self.filter_sentences()
        self.refresh_unknown_panel()
        self.populate_reading_view()
        
    def populate_reading_view(self):
        """Show full text in reading view with sentence segmentation."""
        self.txt_reading.config(state="normal")
        self.txt_reading.delete("1.0", "end")
        
        if not self.mining_result:
            self.txt_reading.config(state="disabled")
            return
            
        for s in self.mining_result.sentences:
            # Insert text
            # We could tag unknown words here too, but for now just plain text
            self.txt_reading.insert("end", s.text + "\n")
            
        self.txt_reading.config(state="disabled")

    def filter_sentences(self):
        if not self.mining_result: return
        
        filter_mode = self.var_filter.get()
        target_cat = self.target_cat.get()
        sort_mode = self.sort_mode.get()

        # 1. Filter
        filtered = []
        for s in self.mining_result.sentences:
            # i+N Filter
            if filter_mode == "i+1" and s.level != 1: continue
            if filter_mode == "i+0" and s.level != 0: continue
            if filter_mode == "challenging" and s.level < 2: continue
            
            # Category Filter
            if target_cat != "Any":
                cat_display = DIFF_CATEGORIES.get(s.category, {}).get("display", "")
                if target_cat != cat_display:
                    continue
            
            filtered.append(s)

        # 2. Sort
        if sort_mode == "Difficulty (Low)":
            filtered.sort(key=lambda s: s.difficulty_score or 1.0)
        elif sort_mode == "Difficulty (High)":
            filtered.sort(key=lambda s: s.difficulty_score or 0.0, reverse=True)
        elif sort_mode == "Unknowns":
            filtered.sort(key=lambda s: s.level)
        
        # 3. Display
        self.tree_sentences.delete(*self.tree_sentences.get_children())
        self.current_view_sentences = filtered

        for s in filtered:
            diff_str = f"{s.difficulty_score:.2f}" if s.difficulty_score is not None else "-"
            cat_key = s.category
            cat_str = "-"
            if cat_key in DIFF_CATEGORIES:
                cat_str = DIFF_CATEGORIES[cat_key]["display"]
            
            self.tree_sentences.insert(
                "", "end",
                values=(s.text, f"{s.level} unknown", diff_str, cat_str),
                tags=(cat_key,) if cat_key in DIFF_CATEGORIES else (),
            )

    def update_mining_levels(self):
        """Recalculate unknown counts for all sentences after database change."""
        if not hasattr(self, 'mining_result'): return
        
        known_set = self.miner._load_known_vocabulary(self.lang_code)
        
        for s in self.mining_result.sentences:
            new_unknown = []
            for t in s.tokens:
                if self.miner._is_punctuation(t.lemma):
                    continue
                if t.lemma.lower() not in known_set:
                    new_unknown.append(t)
            
            s.unknown_words = new_unknown
            s.level = len(new_unknown)
            
        self.filter_sentences()

    def reweight_via_semantics(self):
        """Trigger on-demand semantic topic familiarity scoring."""
        if not self.mining_result:
            return

        # 1. Setup services
        visualizer = SemanticVisualizer(self.db)
        is_ok, msg = visualizer.check_dependencies()
        if not is_ok:
            messagebox.showwarning("Dependencies Missing", msg)
            return

        # 2. Get Cluster Profiles (including known_words and flashcards for this language)
        profiles = visualizer.get_cluster_profiles(language=self.lang_code)
        if not profiles:
            messagebox.showinfo("No Data", "You need to have some flashcards or known words with embeddings to use this feature. Visit the 'Vocabulary galaxy' in the Dashboard first or click 'Generate Map' there.")
            return

        # 3. Gather unique lemmas needing embeddings
        all_lemmas = set()
        for s in self.mining_result.sentences:
            for t in s.tokens:
                if not self.miner._is_punctuation(t.lemma):
                    lemma = t.lemma.lower()
                    if lemma not in self._embedding_cache:
                        all_lemmas.add(lemma)
        
        # 4. Fetch missing embeddings (in background? For now sync with wait cursor)
        self.config(cursor="watch")
        self.btn_reweight.config(state="disabled")
        self.update()
        
        try:
            if all_lemmas:
                ai_client = get_ai_client()
                lemmas_list = list(all_lemmas)
                # Batch process embeddings
                batch_size = 50
                for i in range(0, len(lemmas_list), batch_size):
                    batch = lemmas_list[i : i + batch_size]
                    embeddings = ai_client.generate_embeddings(batch)
                    if embeddings:
                        for lemma, emb in zip(batch, embeddings):
                            self._embedding_cache[lemma] = emb
            
            # 5. Score sentences
            fam_scorer = SemanticFamiliarityScorer(profiles)
            difficulty_scorer = self._get_difficulty_scorer()
            if not difficulty_scorer:
                return

            for s in self.mining_result.sentences:
                # Get embeddings for this sentence's tokens
                sent_embeddings = []
                for t in s.tokens:
                    lemma = t.lemma.lower()
                    if lemma in self._embedding_cache:
                        sent_embeddings.append(self._embedding_cache[lemma])
                
                if sent_embeddings:
                    familiarity = fam_scorer.score_words(sent_embeddings)
                    # We need the original SentenceScore to call reweight_with_semantics.
                    # Since we don't store it in SentenceResult, we'll re-calculate or 
                    # use the data we have. 
                    # Actually, SentenceMiningView doesn't store the SentenceScore object,
                    # just the float difficulty_score.
                    
                    # Refactor: We need a way to re-score. 
                    # Let's add a method to difficulty_scorer that just does the math if we have text.
                    # Or better, let's just use the features we HAVE if they were stored.
                    # Wait, SentenceResult doesn't have the features dict.
                    
                    # Okay, let's re-score the sentence fully once more with the new provider? 
                    # No, we want on-demand re-weighting without re-tokenizing.
                    
                    # Let's grab the score using the existing text (fast since tokens/recall are cached in scorer usually)
                    original_score = difficulty_scorer.score_sentence(s.text, self.lang_code)
                    new_score = difficulty_scorer.reweight_with_semantics(original_score, familiarity)
                    
                    s.difficulty_score = new_score.difficulty_score
                    s.category = new_score.difficulty_category

            # 6. Refresh
            self.filter_sentences()
            messagebox.showinfo("Complete", "Sentences have been reweighted based on your topic familiarity.\nSentences in familiar topics are now easier.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Semantic reweighting failed: {e}")
        finally:
            self.config(cursor="")
            self.btn_reweight.config(state="normal")

    def refresh_unknown_panel(self):
        if not hasattr(self, 'mining_result'): return
        self.tree_unknown.delete(*self.tree_unknown.get_children())
        
        # Get unknown words from current result
        # Re-calc based on current known_db is safer?
        # The result object has `all_unknown_words`. We should display them.
        # But if we just clicked one, it's now known. We need to re-check DB.
        
        # Quick hack: Iterate unique tokens from result, check DB.
        unique_tokens = list(self.mining_result.all_unknown_words.values())
        unique_tokens.sort(key=lambda x: x.lemma)
        
        for t in unique_tokens:
            if not self.db.is_word_known(t.lemma, self.lang_code):
                self.tree_unknown.insert("", "end", values=(t.lemma,), tags=(t.lemma,))

    def on_sentence_select(self, event):
        sel = self.tree_sentences.selection()
        if not sel: return
        
        idx = self.tree_sentences.index(sel[0])
        if idx < len(self.current_view_sentences):
            s = self.current_view_sentences[idx]
            self.selected_sentence = s
            
            self.lbl_detail.config(state="normal")
            self.lbl_detail.delete("1.0", "end")
            self.lbl_detail.insert("end", s.text + "\n\n")

            if s.difficulty_score is not None:
                cat_meta = DIFF_CATEGORIES.get(s.category, {})
                display_name = cat_meta.get("display", s.category or "-")
                self.lbl_detail.insert("end", f"Difficulty: {s.difficulty_score:.2f} ({display_name})\n")
                if "desc" in cat_meta:
                    self.lbl_detail.insert("end", f"Info: {cat_meta['desc']}\n")
                
                if s.difficulty_confidence is not None:
                    self.lbl_detail.insert("end", f"Confidence: {s.difficulty_confidence:.2f}\n")
                if s.bottleneck_word:
                    self.lbl_detail.insert("end", f"Bottleneck word: {s.bottleneck_word}\n")
                self.lbl_detail.insert("end", "\n")

            if s.unknown_words:
                self.lbl_detail.insert("end", "Unknown: " + ", ".join([t.lemma for t in s.unknown_words]) + "\n")

            if s.grammar_patterns:
                self.lbl_detail.insert("end", "Grammar: " + ", ".join(s.grammar_patterns) + "\n")

            self.lbl_detail.config(state="disabled")
            self.btn_add_sentence.config(state="normal" if s.level > 0 else "disabled")
            self.btn_use_for_chat.config(state="normal")

    def on_unknown_select(self, event):
        sel = self.tree_unknown.selection()
        has_sel = bool(sel)
        self.btn_mark_known.config(state="normal" if has_sel else "disabled")
        self.btn_add_vocab.config(state="normal" if has_sel else "disabled")

    def mark_selected_known(self):
        sel = self.tree_unknown.selection()
        if not sel: return
        
        item = sel[0]
        lemma = self.tree_unknown.item(item, "tags")[0] # Stored in tags
        
        # Mark known
        self.db.add_known_word(lemma, self.lang_code, source="mining_manual")
        
        # Remove from UI
        self.tree_unknown.delete(item)
        self.update_mining_levels()
        
        # Refresh manager if open
        if hasattr(self, 'manager_view') and self.manager_view.winfo_exists():
            self.manager_view.refresh_list()
            
    def add_selected_to_study(self):
        sel = self.tree_unknown.selection()
        if not sel: return
        
        item = sel[0]
        lemma = self.tree_unknown.item(item, "tags")[0]

        try:
            # Add to imported_content as 'word'
            self.db.add_imported_content(
                content_type="word",
                content=lemma,
                url="sentence_mining",
                title=f"Mining: {lemma}",
                language=self.lang_code,
                context=self.selected_sentence.text if self.selected_sentence else ""
            )
            messagebox.showinfo("Success", f"Added '{lemma}' to Study Center (Words tab)")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add word: {e}")

    def add_sentence_to_study(self):
        if not self.selected_sentence: return
        
        s = self.selected_sentence
        try:
            # Add to imported_content as 'sentence'
            self.db.add_imported_content(
                content_type="sentence",
                content=s.text,
                url="sentence_mining",
                title=f"Mining Sentence",
                language=self.lang_code,
                tags="mining"
            )
            messagebox.showinfo("Success", "Sentence added to Study Center (Sentences tab)")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add sentence: {e}")

    def use_sentence_for_chat(self):
        if not self.selected_sentence: return
        
        sentence_text = self.selected_sentence.text
        
        # Create a selection dialog
        dialog = tk.Toplevel(self)
        dialog.title("Use for Chat")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Use this sentence for:", padding=10).pack()
        
        def start_topical():
            dialog.destroy()
            topic = tk.simpledialog.askstring("Chat Topic", "Enter a topic for this conversation:", parent=self)
            if topic:
                full_topic = f"{topic} (Context: {sentence_text})"
                session_id = self.study_manager.create_chat_session(full_topic)
                messagebox.showinfo("Success", f"Chat created: '{topic}'\nGo to the Chat tab to start!")
        
        def start_roleplay():
            dialog.destroy()
            ScenarioEditorDialog(self, self.study_manager, context_text=sentence_text)
            
        ttk.Button(dialog, text="Topical Chat", command=start_topical).pack(fill="x", padx=20, pady=5)
        ttk.Button(dialog, text="Role-Play Scenario", command=start_roleplay).pack(fill="x", padx=20, pady=5)
        ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(fill="x", padx=20, pady=5)

