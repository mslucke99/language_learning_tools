import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from src.features.study_center.logic.study_manager import StudyManager
from src.core.localization import tr


class ScenarioEditorDialog(tk.Toplevel):
    def __init__(self, parent, study_manager: StudyManager, scenario_id: int = None, context_text: str = None):
        super().__init__(parent)
        self.study_manager = study_manager
        self.scenario_id = scenario_id
        self.context_text = context_text
        self.result = None
        
        self.title(tr("title_scenario_editor", "Role-Play Scenario Editor"))
        self.geometry("700x700")
        self.resizable(True, True)
        
        self.characters = []  # List of character dicts
        self.active_task_id = None
        
        self.setup_ui()
        if scenario_id:
            self.load_scenario(scenario_id)
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        self.wait_window()
    
    def setup_ui(self):
        # Title frame
        title_frame = ttk.Frame(self)
        title_frame.pack(fill="x", padx=10, pady=10)
        ttk.Label(title_frame, text=tr("header_scenario_editor", "Create or Edit Role-Play Scenario"), font=("Segoe UI", 14, "bold")).pack(anchor="w")
        
        # Main content in a scrolled frame
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        # --- Auto-generate Options ---
        gen_frame = ttk.LabelFrame(scrollable_frame, text=tr("btn_auto_generate", "✨ Auto-generate"), padding=10)
        gen_frame.pack(fill="x", pady=(10, 5))
        
        ttk.Label(gen_frame, text=tr("lbl_scenario_type", "Scenario Type:")).pack(side="left", padx=(0, 5))
        
        self.scenario_types = [
            (tr("opt_scenario_everyday", "Everyday Life"), "Everyday Life"),
            (tr("opt_scenario_work", "Work & Professional"), "Work & Professional"),
            (tr("opt_scenario_fantasy", "Fantasy World"), "Fantasy World"),
            (tr("opt_scenario_history", "Historical Situation"), "Historical Situation"),
            (tr("opt_scenario_travel", "Travel & Tourism"), "Travel & Tourism"),
            (tr("opt_scenario_mystery", "Mystery & Crime"), "Mystery & Crime")
        ]
        
        self.type_var = tk.StringVar(value=self.scenario_types[0][0])
        self.type_combo = ttk.Combobox(gen_frame, textvariable=self.type_var, values=[t[0] for t in self.scenario_types], state="readonly", width=30)
        self.type_combo.pack(side="left", padx=5)
        
        self.gen_btn = ttk.Button(gen_frame, text=tr("btn_generate", "Generate"), command=self._on_auto_generate)
        self.gen_btn.pack(side="left", padx=5)
        
        self.gen_status_label = ttk.Label(gen_frame, text="", font=("Segoe UI", 9, "italic"))
        self.gen_status_label.pack(side="left", padx=10)
        
        # --- Name ---
        ttk.Label(scrollable_frame, text=tr("lbl_scenario_name", "Scenario Name:"), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.name_entry = ttk.Entry(scrollable_frame, width=50)
        self.name_entry.pack(anchor="w", pady=(0, 10))
        
        # --- Description ---
        ttk.Label(scrollable_frame, text=tr("lbl_description", "Description:"), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.desc_text = scrolledtext.ScrolledText(scrollable_frame, height=3, wrap="word", font=("Segoe UI", 10))
        self.desc_text.pack(anchor="w", pady=(0, 10), fill="both", expand=False)
        
        # --- Situation ---
        ttk.Label(scrollable_frame, text=tr("lbl_situation", "Situation/Context:"), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.situation_text = scrolledtext.ScrolledText(scrollable_frame, height=4, wrap="word", font=("Segoe UI", 10))
        self.situation_text.pack(anchor="w", pady=(0, 10), fill="both", expand=False)
        
        # --- User Role ---
        ttk.Label(scrollable_frame, text=tr("lbl_user_role", "Your Role:"), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.user_role_entry = ttk.Entry(scrollable_frame, width=50)
        self.user_role_entry.pack(anchor="w", pady=(0, 10))
        
        # --- Characters ---
        ttk.Label(scrollable_frame, text=tr("lbl_ai_chars", "AI Characters:"), font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(15, 5))
        
        char_btn_frame = ttk.Frame(scrollable_frame)
        char_btn_frame.pack(anchor="w", pady=(0, 10))
        ttk.Button(char_btn_frame, text=tr("btn_add_char", "➕ Add Character"), command=self._add_character_dialog).pack(side="left", padx=2)
        ttk.Button(char_btn_frame, text=tr("btn_edit_selected", "🔄 Edit Selected"), command=self._edit_character_dialog).pack(side="left", padx=2)
        ttk.Button(char_btn_frame, text=tr("btn_remove_selected", "❌ Remove Selected"), command=self._remove_character).pack(side="left", padx=2)
        
        # Character list
        char_list_frame = ttk.Frame(scrollable_frame, relief="solid", borderwidth=1)
        char_list_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        char_scroll = ttk.Scrollbar(char_list_frame)
        self.char_listbox = tk.Listbox(char_list_frame, yscrollcommand=char_scroll.set, font=("Segoe UI", 10), height=6)
        char_scroll.config(command=self.char_listbox.yview)
        
        self.char_listbox.pack(side="left", fill="both", expand=True)
        char_scroll.pack(side="right", fill="y")
        
        # Buttons frame
        btn_frame = ttk.Frame(scrollable_frame)
        btn_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(btn_frame, text=tr("btn_save_scenario", "Save Scenario"), command=self._save_scenario).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("btn_cancel", "Cancel"), command=self.cancel).pack(side="left", padx=5)
        
        self._update_character_list()
    
    def _add_character_dialog(self):
        self._show_character_editor(None)
    
    def _edit_character_dialog(self):
        selection = self.char_listbox.curselection()
        if not selection:
            messagebox.showwarning(tr("header_search", "Select Character"), tr("msg_select_char", "Please select a character to edit."))
            return
        self._show_character_editor(selection[0])
    
    def _show_character_editor(self, char_index):
        """Open a dialog to add/edit a character."""
        dialog = tk.Toplevel(self)
        dialog.title(tr("title_char_details", "Character Details"))
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # Get existing character data if editing
        existing_char = self.characters[char_index] if char_index is not None else None
        
        # Name
        ttk.Label(dialog, text=tr("lbl_char_name", "Character Name:"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(anchor="w", padx=10, pady=(0, 10))
        if existing_char:
            name_entry.insert(0, existing_char['name'])
        
        # Role
        ttk.Label(dialog, text=tr("lbl_char_role", "Character Role:"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        role_entry = ttk.Entry(dialog, width=40)
        role_entry.pack(anchor="w", padx=10, pady=(0, 10))
        if existing_char:
            role_entry.insert(0, existing_char['role'])
        
        # Personality/Description
        ttk.Label(dialog, text=tr("lbl_char_personality", "Personality & Background:"), font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        personality_text = scrolledtext.ScrolledText(dialog, height=5, wrap="word", font=("Segoe UI", 10))
        personality_text.pack(anchor="w", padx=10, pady=(0, 10), fill="both", expand=True)
        if existing_char:
            personality_text.insert("1.0", existing_char.get('personality', ''))
        
        def save_char():
            name = name_entry.get().strip()
            role = role_entry.get().strip()
            personality = personality_text.get("1.0", "end-1c").strip()
            
            if not name or not role:
                messagebox.showerror(tr("error_title", "Required Fields"), tr("msg_fields_required", "Character Name and Role are required."))
                return
            
            char_data = {'name': name, 'role': role, 'personality': personality}
            
            if char_index is not None:
                self.characters[char_index] = char_data
            else:
                self.characters.append(char_data)
            
            self._update_character_list()
            dialog.destroy()
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text=tr("btn_save", "Save"), command=save_char).pack(side="left", padx=5)
        ttk.Button(btn_frame, text=tr("btn_cancel", "Cancel"), command=dialog.destroy).pack(side="left", padx=5)
    
    def _remove_character(self):
        selection = self.char_listbox.curselection()
        if not selection:
            messagebox.showwarning(tr("header_search", "Select Character"), tr("msg_select_char_remove", "Please select a character to remove."))
            return
        del self.characters[selection[0]]
        self._update_character_list()
    
    def _update_character_list(self):
        """Update the character listbox display."""
        self.char_listbox.delete(0, tk.END)
        for char in self.characters:
            label = f"{char['name']} - {char['role']}"
            self.char_listbox.insert(tk.END, label)
    
    def load_scenario(self, scenario_id):
        """Load an existing scenario."""
        scenario = self.study_manager.get_roleplay_scenario(scenario_id)
        if scenario:
            self.name_entry.insert(0, scenario['name'])
            self.desc_text.insert("1.0", scenario.get('description', ''))
            self.situation_text.insert("1.0", scenario['situation'])
            self.user_role_entry.insert(0, scenario['user_role'])
            self.characters = scenario.get('characters', [])
            self._update_character_list()
    
    def _save_scenario(self):
        """Validate and save the scenario."""
        name = self.name_entry.get().strip()
        description = self.desc_text.get("1.0", "end-1c").strip()
        situation = self.situation_text.get("1.0", "end-1c").strip()
        user_role = self.user_role_entry.get().strip()
        
        if not all([name, situation, user_role]):
            messagebox.showerror(tr("error_title", "Required Fields"), tr("msg_fields_required_scenario", "Name, Situation, and Your Role are required."))
            return
        
        if not self.characters:
            messagebox.showerror(tr("error_title", "No Characters"), tr("msg_no_chars", "Add at least one character to the scenario."))
            return
        
        if self.scenario_id:
            # Update existing
            success = self.study_manager.update_roleplay_scenario(
                self.scenario_id, name, description, user_role, situation, self.characters
            )
            if success:
                messagebox.showinfo(tr("msg_success", "Success"), tr("msg_scenario_updated", "Scenario updated successfully!"))
        else:
            # Create new
            scenario_id = self.study_manager.create_roleplay_scenario(
                name, description, user_role, situation, self.characters
            )
            messagebox.showinfo(tr("msg_success", "Success"), tr("msg_scenario_created", "Scenario created successfully!"))
            self.scenario_id = scenario_id
        
        self.result = {'id': self.scenario_id, 'name': name}
        self.destroy()
    
    def cancel(self):
        self.result = None
        self.destroy()

    def _on_auto_generate(self):
        """Trigger AI scenario generation."""
        if not self.study_manager.ai_available:
            messagebox.showwarning(tr("error_title", "AI Unavailable"), tr("msg_ai_unavailable", "AI service is not available. Check your settings."))
            return
            
        # Get the internal type name
        display_type = self.type_var.get()
        scenario_type = next((t[1] for t in self.scenario_types if t[0] == display_type), "Everyday Life")
        
        self.gen_btn.config(state="disabled")
        self.gen_status_label.config(text=tr("msg_generating_scenario", "Generating scenario... please wait."), foreground="blue")
        
        self.active_task_id = self.study_manager.queue_generation_task(
            'generate_roleplay_scenario',
            0,
            scenario_type=scenario_type,
            context_text=self.context_text
        )
        self._poll_generation()

    def _poll_generation(self):
        """Poll for generation task completion."""
        if not self.active_task_id:
            return
            
        status = self.study_manager.get_task_status(self.active_task_id)
        if status['status'] == 'completed':
            self._handle_generation_success(status['result'])
        elif status['status'] == 'failed':
            self._handle_generation_failure(status.get('error', 'Unknown error'))
        else:
            # Continue polling
            self.after(500, self._poll_generation)

    def _handle_generation_success(self, data):
        """Populate fields with generated data."""
        self.gen_btn.config(state="normal")
        self.gen_status_label.config(text=tr("msg_success", "Success"), foreground="green")
        
        # Clear existing
        self.name_entry.delete(0, tk.END)
        self.desc_text.delete("1.0", tk.END)
        self.situation_text.delete("1.0", tk.END)
        self.user_role_entry.delete(0, tk.END)
        self.characters = []
        
        # Insert new
        self.name_entry.insert(0, data.get('name', ''))
        self.desc_text.insert("1.0", data.get('description', ''))
        self.situation_text.insert("1.0", data.get('situation', ''))
        self.user_role_entry.insert(0, data.get('user_role', ''))
        
        # Add characters
        char_list = data.get('characters', [])
        for char in char_list:
            if isinstance(char, dict) and char.get('name') and char.get('role'):
                self.characters.append({
                    'name': char['name'],
                    'role': char['role'],
                    'personality': char.get('personality', '')
                })
        
        self._update_character_list()
        self.active_task_id = None
        
        messagebox.showinfo(tr("msg_success", "Success"), tr("msg_scenario_generated", "Scenario generated and populated!"))

    def _handle_generation_failure(self, error):
        """Handle generation error."""
        self.gen_btn.config(state="normal")
        self.gen_status_label.config(text=tr("error_title", "Error"), foreground="red")
        self.active_task_id = None
        messagebox.showerror(tr("error_title", "Generation Failed"), f"{tr('msg_error_topic', 'Error generating topic')}: {error}")


class ScenarioSelectorDialog(tk.Toplevel):
    """Dialog for selecting an existing scenario or creating a new one."""
    
    def __init__(self, parent, study_manager: StudyManager):
        super().__init__(parent)
        self.study_manager = study_manager
        self.result = None
        
        self.title(tr("title_select_scenario", "Select Role-Play Scenario"))
        self.geometry("600x400")
        self.resizable(True, True)
        
        self.setup_ui()
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        self.wait_window()
    
    def setup_ui(self):
        # Title
        ttk.Label(self, text=tr("lbl_available_scenarios", "Available Role-Play Scenarios"), font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text=tr("btn_create_new", "➕ Create New"), command=self._create_new).pack(side="left", padx=2)
        
        # Scenarios list
        canvas = tk.Canvas(self)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        scrollbar.pack(side="right", fill="y")
        
        scenarios = self.study_manager.get_roleplay_scenarios()
        
        if not scenarios:
            ttk.Label(scrollable_frame, text=tr("msg_no_scenarios", "No scenarios yet. Create one to get started!")).pack(pady=20)
        else:
            for scenario in scenarios:
                self._add_scenario_button(scrollable_frame, scenario)
    
    def _add_scenario_button(self, parent, scenario):
        """Add a selectable scenario button."""
        frame = ttk.Frame(parent, relief="solid", borderwidth=1)
        frame.pack(fill="x", pady=5, padx=5)
        
        # Scenario info
        info_text = f"{scenario['name']}\n{scenario['situation'][:60]}..."
        ttk.Label(frame, text=info_text, font=("Segoe UI", 10), justify="left").pack(side="left", fill="both", expand=True, padx=10, pady=10)
        
        # Action buttons
        ttk.Button(frame, text=tr("header_search", "Select"), command=lambda: self._select_scenario(scenario['id'])).pack(side="left", padx=2, pady=5)
        ttk.Button(frame, text=tr("btn_edit", "Edit"), command=lambda: self._edit_scenario(scenario['id'])).pack(side="left", padx=2, pady=5)
        ttk.Button(frame, text=tr("btn_delete", "Delete"), command=lambda: self._delete_scenario(scenario['id'], frame)).pack(side="left", padx=2, pady=5)
    
    def _select_scenario(self, scenario_id):
        """Select a scenario and close dialog."""
        self.result = scenario_id
        self.destroy()
    
    def _create_new(self):
        """Create a new scenario."""
        ScenarioEditorDialog(self, self.study_manager)
        # Refresh the list after creation
        self.destroy()
        self.__init__(self.master, self.study_manager)
    
    def _edit_scenario(self, scenario_id):
        """Edit an existing scenario."""
        ScenarioEditorDialog(self, self.study_manager, scenario_id)
        # Refresh the list after edit
        self.destroy()
        self.__init__(self.master, self.study_manager)
    
    def _delete_scenario(self, scenario_id, frame):
        """Delete a scenario."""
        if messagebox.askyesno(tr("btn_delete", "Confirm Delete"), tr("msg_confirm_delete", "Are you sure you want to delete this scenario?")):
            self.study_manager.delete_roleplay_scenario(scenario_id)
            frame.destroy()
