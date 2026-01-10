import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from typing import Dict, List, Optional

class PromptEditorDialog(tk.Toplevel):
    """
    A dialog for editing AI prompt templates.
    """
    def __init__(self, parent, study_manager):
        super().__init__(parent)
        self.study_manager = study_manager
        self.title("AI Prompt Editor")
        self.geometry("900x700")
        self.minsize(800, 600)
        
        # Track current selection
        self.current_category = None
        self.current_prompt_id = None
        self.current_template_type = 'template'
        
        self.setup_ui()
        self.load_categories()
        
        # Select first item by default if available
        self.after(100, self.select_first_prompt)

    def setup_ui(self):
        # Main layout: Left sidebar for selection, Right side for editing
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Sidebar
        sidebar = ttk.Frame(main_pane)
        main_pane.add(sidebar, weight=1)
        
        ttk.Label(sidebar, text="Choose Prompt", font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(0, 5))
        
        self.tree = ttk.Treeview(sidebar, show='tree', selectmode='browse')
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind('<<TreeviewSelect>>', self.on_tree_select)
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(sidebar, orient=tk.VERTICAL, command=self.tree.yview)
        tree_scroll.place(relx=1.0, rely=0, relheight=1.0, anchor='ne')
        self.tree.configure(yscrollcommand=tree_scroll.set)
        
        # Editor Area
        editor_frame = ttk.Frame(main_pane)
        main_pane.add(editor_frame, weight=3)
        
        # Header Info
        header = ttk.Frame(editor_frame)
        header.pack(fill=tk.X, padx=10, pady=5)
        
        self.lbl_prompt_title = ttk.Label(header, text="Select a prompt to edit", font=('Segoe UI', 12, 'bold'))
        self.lbl_prompt_title.pack(anchor=tk.W)
        
        self.lbl_placeholders = ttk.Label(header, text="", foreground="gray")
        self.lbl_placeholders.pack(anchor=tk.W, pady=2)
        
        # Text Editor
        ttk.Label(editor_frame, text="Template Body:").pack(anchor=tk.W, padx=10, pady=(10, 0))
        
        self.txt_editor = scrolledtext.ScrolledText(
            editor_frame, wrap=tk.WORD, font=('Consolas', 11),
            undo=True, background="#fdfdfd"
        )
        self.txt_editor.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Footer Action Buttons
        footer = ttk.Frame(editor_frame)
        footer.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(footer, text="Restore Default", command=self.restore_default).pack(side=tk.LEFT)
        ttk.Button(footer, text="Reset All to Defaults", command=self.confirm_reset_all).pack(side=tk.LEFT, padx=10)
        
        ttk.Button(footer, text="Save Changes", style='Accent.TButton', command=self.save_prompt).pack(side=tk.RIGHT)
        ttk.Button(footer, text="Close", command=self.destroy).pack(side=tk.RIGHT, padx=10)

    def load_categories(self):
        """Populate the treeview with categories and prompt IDs."""
        self.tree.delete(*self.tree.get_children())
        
        categories = {
            'word': 'Words (Definitions, Examples)',
            'sentence': 'Sentences (Grammar, Context)',
            'writing': 'Writing Lab',
            'chat': 'AI Chat Tutor'
        }
        
        for cat_id, cat_name in categories.items():
            parent = self.tree.insert('', tk.END, text=cat_name, open=True, values=(cat_id, ''))
            
            prompts_dict = self.study_manager.default_prompts.get(cat_id, {})
            for pid, pinfo in prompts_dict.items():
                p_label = pinfo.get('name', pid)
                
                # Check if it has multiple sub-templates (like Word prompts)
                if 'native_template' in pinfo and 'study_template' in pinfo:
                    p_node = self.tree.insert(parent, tk.END, text=p_label, open=False, values=(cat_id, pid, ''))
                    self.tree.insert(p_node, tk.END, text="Native Template", values=(cat_id, pid, 'native_template'))
                    self.tree.insert(p_node, tk.END, text="Study Template", values=(cat_id, pid, 'study_template'))
                else:
                    self.tree.insert(parent, tk.END, text=p_label, values=(cat_id, pid, 'template'))

    def select_first_prompt(self):
        """Auto-select the first leaf node."""
        children = self.tree.get_children()
        if not children:
            return
            
        # Drill down to find the first item with 3 values (leaf)
        node = children[0]
        while self.tree.get_children(node):
            node = self.tree.get_children(node)[0]
            
        self.tree.selection_set(node)
        self.tree.see(node)

    def on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return
            
        item = self.tree.item(selection[0])
        vals = item['values']
        
        # We only care about nodes that have a specific template type
        if len(vals) < 3 or not vals[2]:
            return
            
        self.current_category = vals[0]
        self.current_prompt_id = vals[1]
        self.current_template_type = vals[2]
        
        self.refresh_editor()

    def refresh_editor(self):
        if not self.current_category:
            return
            
        # Update labels
        pinfo = self.study_manager.default_prompts[self.current_category][self.current_prompt_id]
        p_name = pinfo.get('name', self.current_prompt_id)
        
        type_suffix = ""
        if self.current_template_type == 'native_template':
            type_suffix = " (Native Language)"
        elif self.current_template_type == 'study_template':
            type_suffix = " (Study Language)"
            
        self.lbl_prompt_title.config(text=f"{p_name}{type_suffix}")
        
        # Update placeholders label
        placeholders = self.get_available_placeholders()
        self.lbl_placeholders.config(text=f"Available Placeholders: {', '.join(placeholders)}")
        
        # Load content
        content = self.study_manager.get_custom_prompt(
            self.current_category, 
            self.current_prompt_id, 
            self.current_template_type
        )
        
        self.txt_editor.delete(1.0, tk.END)
        self.txt_editor.insert(tk.END, content)
        self.txt_editor.edit_reset()

    def get_available_placeholders(self) -> List[str]:
        """Determine which placeholders are relevant for the current prompt."""
        # This is a bit hardcoded based on StudyManager usage
        common = ['{study_language}', '{native_language}']
        
        if self.current_category == 'word':
            return common + ['{word}']
        elif self.current_category == 'sentence':
            return common + ['{sentence}', '{language}'] # {language} is the target explanation language
        elif self.current_category == 'writing':
            base = common
            if self.current_prompt_id == 'grade':
                base += ['{topic}', '{user_writing}']
            return base
        elif self.current_category == 'chat':
            return common + ['{topic}', '{persona}']
            
        return common

    def save_prompt(self):
        if not self.current_category:
            return
            
        content = self.txt_editor.get(1.0, tk.END).strip()
        if not content:
            messagebox.showwarning("Empty Prompt", "The prompt template cannot be empty.")
            return
            
        # Verify placeholders
        placeholders = self.get_available_placeholders()
        # Basic check to see if it uses some expected ones? 
        # For now just save it.
        
        try:
            self.study_manager.set_custom_prompt(
                self.current_category,
                self.current_prompt_id,
                self.current_template_type,
                content
            )
            messagebox.showinfo("Success", "Prompt template saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save prompt: {e}")

    def restore_default(self):
        if not self.current_category:
            return
            
        if messagebox.askyesno("Restore Default", f"Are you sure you want to restore the default template for this prompt?"):
            self.study_manager.reset_prompt(
                self.current_category,
                self.current_prompt_id,
                self.current_template_type
            )
            self.refresh_editor()

    def confirm_reset_all(self):
        if messagebox.askyesno("Reset All", "This will revert ALL AI prompts to their factory defaults. This action cannot be undone.\n\nProceed?"):
            self.study_manager.reset_all_prompts()
            self.refresh_editor()
            messagebox.showinfo("Reset Complete", "All prompts have been restored to defaults.")
