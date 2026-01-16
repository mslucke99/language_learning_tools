import tkinter as tk
from tkinter import ttk

def setup_standard_header(parent, title, back_cmd=None, action_text=None, action_cmd=None):
    """Create a standard header with Back button, Title, and optional Action button."""
    header_frame = ttk.Frame(parent)
    header_frame.pack(fill="x", pady=(0, 10))
    
    # Left: Back Button
    if back_cmd:
        ttk.Button(header_frame, text="← Back", command=back_cmd).pack(side="left", padx=(0, 10))
        
    # Center: Title
    # Try to use a shared style if possible, or config locally
    # We assume style "Title.TLabel" is configured by the app
    lbl = ttk.Label(header_frame, text=title, font=("Arial", 14, "bold"))
    lbl.pack(side="left", fill="x", expand=True)
    
    # Right: Action Button (e.g., "+ Add Item")
    if action_text and action_cmd:
        ttk.Button(header_frame, text=action_text, command=action_cmd).pack(side="right")
        
    return header_frame

def bind_mousewheel(widget, recursive=False):
    """Bind mousewheel events to a widget."""
    # Windows uses <MouseWheel>, Linux uses <Button-4>/<Button-5> usually handled by scrolling widgets
    # Tkinter Scrollbar usually handles this if configured.
    # But for ScrolledText or Canvas on some OSs we might need this.
    
    def _on_mousewheel(event):
        if event.num == 5 or event.delta < 0:
            widget.yview_scroll(1, "units")
        elif event.num == 4 or event.delta > 0:
            widget.yview_scroll(-1, "units")
            
    # Bind to the widget itself
    # Use bind_all only when focused to avoid global scrolling issues
    widget.bind("<Enter>", lambda e: widget.bind_all("<Button-4>", _on_mousewheel))
    widget.bind("<Enter>", lambda e: widget.bind_all("<Button-5>", _on_mousewheel))
    widget.bind("<Enter>", lambda e: widget.bind_all("<MouseWheel>", _on_mousewheel))
    
    widget.bind("<Leave>", lambda e: widget.unbind_all("<Button-4>"))
    widget.bind("<Leave>", lambda e: widget.unbind_all("<Button-5>"))
    widget.bind("<Leave>", lambda e: widget.unbind_all("<MouseWheel>"))
