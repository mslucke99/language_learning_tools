import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from src.core.database import FlashcardDatabase

class ManageCollectionsDialog:
    def __init__(self, parent, db: FlashcardDatabase, type_name: str, on_change=None):
        self.db = db
        self.type_name = type_name
        self.on_change = on_change
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(f"Manage {type_name.capitalize()} Folders")
        self.dialog.geometry("400x400")
        
        self.setup_ui()
        
    def setup_ui(self):
        ttk.Label(self.dialog, text="Create New Folder:", font=("Arial", 10, "bold")).pack(pady=5)
        self.name_var = tk.StringVar()
        ttk.Entry(self.dialog, textvariable=self.name_var, width=30).pack(pady=5)
        
        ttk.Label(self.dialog, text="Parent Folder (Optional):").pack(pady=5)
        colls = self.db.get_collections(self.type_name)
        options = ["None"] + [c['name'] for c in colls]
        self.coll_map = {c['name']: c['id'] for c in colls}
        
        self.parent_var = tk.StringVar(value="None")
        parent_combo = ttk.Combobox(self.dialog, textvariable=self.parent_var, values=options, state="readonly")
        parent_combo.pack(pady=5)
        
        ttk.Button(self.dialog, text="Create", command=self.add_coll).pack(pady=10)
        
        ttk.Separator(self.dialog, orient="horizontal").pack(fill="x", pady=10)
        
        ttk.Label(self.dialog, text="Existing Folders:", font=("Arial", 10, "bold")).pack(pady=5)
        list_frame = ttk.Frame(self.dialog)
        list_frame.pack(fill="both", expand=True, padx=20)
        
        self.lb = tk.Listbox(list_frame)
        self.lb.pack(side="left", fill="both", expand=True)
        for c in colls:
            self.lb.insert("end", f"{c['name']} (ID: {c['id']})")
            
        ttk.Button(self.dialog, text="Delete Selected", command=self.delete_coll).pack(pady=10)

    def add_coll(self):
        name = self.name_var.get().strip()
        if name:
            parent_name = self.parent_var.get()
            p_id = self.coll_map.get(parent_name) # None if "None"
            self.db.create_collection(name, self.type_name, p_id)
            if self.on_change: self.on_change()
            messagebox.showinfo("Success", "Folder created!")
            self.dialog.destroy()
            
    def delete_coll(self):
        sel = self.lb.curselection()
        if sel:
            item = self.lb.get(sel[0])
            cid = int(item.split("ID: ")[1].rstrip(")"))
            if messagebox.askyesno("Confirm", "Delete folder? Items inside will be uncategorized/deleted depending on policy."):
                self.db.delete_collection(cid)
                if self.on_change: self.on_change()
                self.dialog.destroy()

class MoveItemDialog:
    def __init__(self, parent, db: FlashcardDatabase, type_name: str, item_id: int, on_change=None):
        self.db = db
        self.type_name = type_name
        self.item_id = item_id
        self.on_change = on_change
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Move to Folder")
        self.dialog.geometry("300x150")
        
        self.setup_ui()
        
    def setup_ui(self):
        ttk.Label(self.dialog, text="Select Folder:").pack(pady=10)
        colls = self.db.get_collections(self.type_name)
        options = ["None (Uncategorized)"] + [c['name'] for c in colls]
        self.coll_map = {c['name']: c['id'] for c in colls}
        
        self.sel_var = tk.StringVar(value=options[0])
        combo = ttk.Combobox(self.dialog, textvariable=self.sel_var, values=options, state="readonly")
        combo.pack(pady=5)
        
        ttk.Button(self.dialog, text="Move", command=self.save_move).pack(pady=10)
        
    def save_move(self):
        coll_name = self.sel_var.get()
        coll_id = self.coll_map.get(coll_name)
        self.db.assign_to_collection(self.type_name, self.item_id, coll_id)
        if self.on_change: self.on_change()
        messagebox.showinfo("Success", "Item moved!")
        self.dialog.destroy()
