import sys
import os
import tkinter as tk
from tkinter import messagebox

# Ensure src is in path if run from language_learning_tools root
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.features.dashboard.dashboard_ui import DashboardApp
except ImportError as e:
    # If run from src/
    try:
        from features.dashboard.dashboard_ui import DashboardApp
    except ImportError:
        print(f"Error importing app: {e}")
        print("Please run from the repository root, e.g., 'python3 src/main.py'")
        sys.exit(1)

def main():
    try:
        root = tk.Tk()
        app = DashboardApp(root)
        root.mainloop()
    except Exception as e:
        import traceback
        traceback.print_exc()
        messagebox.showerror("Critical Error", f"An unexpected error occurred:\n{str(e)}")

if __name__ == "__main__":
    main()
