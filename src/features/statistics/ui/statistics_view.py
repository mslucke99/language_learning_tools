import tkinter as tk
from tkinter import ttk
from src.features.statistics.logic.stats_generator import StatisticsManager
from src.core.localization import tr

class StatisticsViewFrame(ttk.Frame):
    def __init__(self, parent, controller, db):
        super().__init__(parent)
        self.controller = controller
        self.stats_manager = StatisticsManager(db)
        
        # Styles
        style = ttk.Style()
        style.configure("Stat.TLabel", font=("Arial", 10))
        style.configure("StatTitle.TLabel", font=("Arial", 14, "bold"))
        
        self.setup_ui()
        self.refresh_stats()

    def setup_ui(self):
        # Title
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=20)
        ttk.Button(header, text=f"← {tr('btn_back', 'Back')}", command=self.go_back).pack(side="left")
        ttk.Label(header, text=tr("header_statistics", "Study Statistics"), style="StatTitle.TLabel").pack(side="left", padx=20)
        
        # Main content (scrollable if needed, but keeping simple for now)
        self.content = ttk.Frame(self)
        self.content.pack(fill="both", expand=True, padx=20)
        
        # Grid layout for charts
        self.heatmap_frame = ttk.LabelFrame(self.content, text=tr("lbl_activity_heatmap", "Study Activity (Last 30 Days)"))
        self.heatmap_frame.pack(fill="x", pady=10)
        
        self.heatmap_canvas = tk.Canvas(self.heatmap_frame, height=150, bg="white")
        self.heatmap_canvas.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Retention Stats
        self.retention_frame = ttk.LabelFrame(self.content, text=tr("lbl_retention_chart", "Flashcard Retention"))
        self.retention_frame.pack(fill="x", pady=10)
        
        self.retention_canvas = tk.Canvas(self.retention_frame, height=200, bg="white")
        self.retention_canvas.pack(fill="both", expand=True, padx=10, pady=10)

    def refresh_stats(self):
        # Clear canvases
        self.heatmap_canvas.delete("all")
        self.retention_canvas.delete("all")
        
        # Draw Heatmap
        # Mock data/logic for drawing squares
        data = self.stats_manager.get_study_heatmap_data(days=30)
        self.draw_heatmap(self.heatmap_canvas, data)
        
        # Draw Retention (Pie/Bar)
        retention = self.stats_manager.get_retention_stats()
        self.draw_retention_chart(self.retention_canvas, retention)

    def draw_heatmap(self, canvas, data):
        # Simple grid of 30 days
        # Each box 20x20
        start_x, start_y = 10, 10
        box_size = 20
        gap = 5
        
        import datetime
        today = datetime.date.today()
        
        for i in range(29, -1, -1):
            day = today - datetime.timedelta(days=i)
            key = day.isoformat()
            count = data.get(key, 0)
            
            # Color based on count
            if count == 0: color = "#ebedf0"
            elif count < 5: color = "#9be9a8"
            elif count < 10: color = "#40c463"
            else: color = "#216e39"
            
            x = start_x + ((29 - i) * (box_size + gap))
            y = start_y
            
            canvas.create_rectangle(x, y, x + box_size, y + box_size, fill=color, outline="#ccc")
            # Label
            if i % 5 == 0:
                canvas.create_text(x + 10, y + 30, text=day.strftime("%d"), font=("Arial", 8))

    def draw_retention_chart(self, canvas, stats):
        # Simple Bar Chart
        if not stats: return
        
        total = sum(stats.values())
        if total == 0: return

        bar_width = 80
        gap = 40
        max_height = 150
        start_x = 50
        base_y = 180
        
        # Find max value for scaling
        max_val = max(stats.values())
        
        colors = {'Hard': '#ff6b6b', 'Medium': '#feca57', 'Easy': '#1dd1a1'}
        
        for i, (label, count) in enumerate(stats.items()):
            x = start_x + (i * (bar_width + gap))
            height = (count / max_val) * max_height if max_val > 0 else 0
            
            # Draw bar
            canvas.create_rectangle(x, base_y - height, x + bar_width, base_y, fill=colors.get(label, 'gray'))
            
            # Draw text
            canvas.create_text(x + bar_width/2, base_y + 15, text=label)
            canvas.create_text(x + bar_width/2, base_y - height - 10, text=str(count))

    def go_back(self):
        if hasattr(self.controller, 'show_home'):
            self.controller.show_home()
