import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import json
from src.features.study_center.logic.study_manager import StudyManager


class ScenarioEditorDialog(tk.Toplevel):
    def __init__(self, parent, study_manager: StudyManager, scenario_id: int = None):
        super().__init__(parent)
        self.study_manager = study_manager
        self.scenario_id = scenario_id
        self.result = None
        
        self.title("Role-Play Scenario Editor")
        self.geometry("700x700")
        self.resizable(True, True)
        
        self.characters = []  # List of character dicts
        
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
        ttk.Label(title_frame, text="Create or Edit Role-Play Scenario", font=("Segoe UI", 14, "bold")).pack(anchor="w")
        
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
        
        # --- Name ---
        ttk.Label(scrollable_frame, text="Scenario Name:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.name_entry = ttk.Entry(scrollable_frame, width=50)
        self.name_entry.pack(anchor="w", pady=(0, 10))
        
        # --- Description ---
        ttk.Label(scrollable_frame, text="Description:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.desc_text = scrolledtext.ScrolledText(scrollable_frame, height=3, wrap="word", font=("Segoe UI", 10))
        self.desc_text.pack(anchor="ew", pady=(0, 10), fill="both", expand=False)
        
        # --- Situation ---
        ttk.Label(scrollable_frame, text="Situation/Context:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.situation_text = scrolledtext.ScrolledText(scrollable_frame, height=4, wrap="word", font=("Segoe UI", 10))
        self.situation_text.pack(anchor="ew", pady=(0, 10), fill="both", expand=False)
        
        # --- User Role ---
        ttk.Label(scrollable_frame, text="Your Role:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10, 2))
        self.user_role_entry = ttk.Entry(scrollable_frame, width=50)
        self.user_role_entry.pack(anchor="w", pady=(0, 10))
        
        # --- Characters ---
        ttk.Label(scrollable_frame, text="AI Characters:", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(15, 5))
        
        char_btn_frame = ttk.Frame(scrollable_frame)
        char_btn_frame.pack(anchor="w", pady=(0, 10))
        ttk.Button(char_btn_frame, text="➕ Add Character", command=self._add_character_dialog).pack(side="left", padx=2)
        ttk.Button(char_btn_frame, text="🔄 Edit Selected", command=self._edit_character_dialog).pack(side="left", padx=2)
        ttk.Button(char_btn_frame, text="❌ Remove Selected", command=self._remove_character).pack(side="left", padx=2)
        
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
        
        ttk.Button(btn_frame, text="Save Scenario", command=self._save_scenario).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel).pack(side="left", padx=5)
        
        self._update_character_list()
    
    def _add_character_dialog(self):
        self._show_character_editor(None)
    
    def _edit_character_dialog(self):
        selection = self.char_listbox.curselection()
        if not selection:
            messagebox.showwarning("Select Character", "Please select a character to edit.")
            return
        self._show_character_editor(selection[0])
    
    def _show_character_editor(self, char_index):
        """Open a dialog to add/edit a character."""
        dialog = tk.Toplevel(self)
        dialog.title("Character Details")
        dialog.geometry("500x300")
        dialog.transient(self)
        dialog.grab_set()
        
        # Get existing character data if editing
        existing_char = self.characters[char_index] if char_index is not None else None
        
        # Name
        ttk.Label(dialog, text="Character Name:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        name_entry = ttk.Entry(dialog, width=40)
        name_entry.pack(anchor="w", padx=10, pady=(0, 10))
        if existing_char:
            name_entry.insert(0, existing_char['name'])
        
        # Role
        ttk.Label(dialog, text="Character Role:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        role_entry = ttk.Entry(dialog, width=40)
        role_entry.pack(anchor="w", padx=10, pady=(0, 10))
        if existing_char:
            role_entry.insert(0, existing_char['role'])
        
        # Personality/Description
        ttk.Label(dialog, text="Personality & Background:", font=("Segoe UI", 11, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        personality_text = scrolledtext.ScrolledText(dialog, height=5, wrap="word", font=("Segoe UI", 10))
        personality_text.pack(anchor="ew", padx=10, pady=(0, 10), fill="both", expand=True)
        if existing_char:
            personality_text.insert("1.0", existing_char.get('personality', ''))
        
        def save_char():
            name = name_entry.get().strip()
            role = role_entry.get().strip()
            personality = personality_text.get("1.0", "end-1c").strip()
            
            if not name or not role:
                messagebox.showerror("Required Fields", "Character Name and Role are required.")
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
        ttk.Button(btn_frame, text="Save", command=save_char).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left", padx=5)
    
    def _remove_character(self):
        selection = self.char_listbox.curselection()
        if not selection:
            messagebox.showwarning("Select Character", "Please select a character to remove.")
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
            messagebox.showerror("Required Fields", "Name, Situation, and Your Role are required.")
            return
        
        if not self.characters:
            messagebox.showerror("No Characters", "Add at least one character to the scenario.")
            return
        
        if self.scenario_id:
            # Update existing
            success = self.study_manager.update_roleplay_scenario(
                self.scenario_id, name, description, user_role, situation, self.characters
            )
            if success:
                messagebox.showinfo("Success", "Scenario updated successfully!")
        else:
            # Create new
            scenario_id = self.study_manager.create_roleplay_scenario(
                name, description, user_role, situation, self.characters
            )
            messagebox.showinfo("Success", "Scenario created successfully!")
            self.scenario_id = scenario_id
        
        self.result = {'id': self.scenario_id, 'name': name}
        self.destroy()
    
    def cancel(self):
        self.result = None
        self.destroy()


class ScenarioSelectorDialog(tk.Toplevel):
    """Dialog for selecting an existing scenario or creating a new one."""
    
    def __init__(self, parent, study_manager: StudyManager):
        super().__init__(parent)
        self.study_manager = study_manager
        self.result = None
        
        self.title("Select Role-Play Scenario")
        self.geometry("600x400")
        self.resizable(True, True)
        
        self.setup_ui()
        
        # Make dialog modal
        self.transient(parent)
        self.grab_set()
        self.wait_window()
    
    def setup_ui(self):
        # Title
        ttk.Label(self, text="Available Role-Play Scenarios", font=("Segoe UI", 14, "bold")).pack(anchor="w", padx=10, pady=10)
        
        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="➕ Create New", command=self._create_new).pack(side="left", padx=2)
        
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
            ttk.Label(scrollable_frame, text="No scenarios yet. Create one to get started!").pack(pady=20)
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
        ttk.Button(frame, text="Select", command=lambda: self._select_scenario(scenario['id'])).pack(side="left", padx=2, pady=5)
        ttk.Button(frame, text="Edit", command=lambda: self._edit_scenario(scenario['id'])).pack(side="left", padx=2, pady=5)
        ttk.Button(frame, text="Delete", command=lambda: self._delete_scenario(scenario['id'], frame)).pack(side="left", padx=2, pady=5)
    
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
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this scenario?"):
            self.study_manager.delete_roleplay_scenario(scenario_id)
            frame.destroy()
