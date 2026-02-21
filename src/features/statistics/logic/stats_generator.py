from datetime import datetime, timedelta
from collections import defaultdict
import sqlite3

class StatisticsManager:
    def __init__(self, db):
        self.db = db

    def get_study_heatmap_data(self, days=365):
        """
        Get review counts per day for the last N days.
        Returns a dictionary { 'YYYY-MM-DD': count }
        """
        cursor = self.db.conn.cursor()
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Query review_logs
        # Only count 'flashcard' reviews for now, or all? 'review_desc' column
        try:
            cursor.execute("""
                SELECT substr(review_date, 1, 10) as day, COUNT(*) 
                FROM review_logs 
                WHERE review_date >= ?
                GROUP BY day
            """, (start_date.isoformat(),))
            
            data = {}
            for row in cursor.fetchall():
                data[row[0]] = row[1]
            return data
        except sqlite3.OperationalError:
            # Table might not exist yet if migration failed or in test env
            return {}

    def get_retention_stats(self):
        """
        Get distribution of cards by Easiness factor.
        Returns { 'Hard': count, 'Medium': count, 'Easy': count }
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT easiness FROM flashcards")
        
        stats = {'Hard': 0, 'Medium': 0, 'Easy': 0}
        
        for row in cursor.fetchall():
            eff = row[0]
            if eff < 2.0:
                stats['Hard'] += 1
            elif eff < 2.8: # Default is 2.5
                stats['Medium'] += 1
            else:
                stats['Easy'] += 1
                
        return stats

    def get_weekly_progress(self):
        """
        Get reviews for the last 7 days.
        Returns list of (day_name, count)
        """
        data = self.get_study_heatmap_data(days=7)
        # Fill in missing days with 0
        result = []
        for i in range(6, -1, -1):
            date = datetime.now() - timedelta(days=i)
            key = date.strftime("%Y-%m-%d")
            day_name = date.strftime("%a")
            result.append((day_name, data.get(key, 0)))
        return result
