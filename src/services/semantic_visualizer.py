import json
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from src.core.database import FlashcardDatabase
from src.services.llm_service import get_ai_client

try:
    from sklearn.cluster import KMeans, DBSCAN
    from sklearn.metrics import silhouette_score
    import umap
    import plotly.express as px
    import plotly.graph_objects as go
    DEPENDENCIES_AVAILABLE = True
except ImportError:
    DEPENDENCIES_AVAILABLE = False

class SemanticVisualizer:
    """
    Service for generating semantic embeddings, dimensionality reduction (UMAP),
    clustering, and semantic gap analysis.
    """
    
    def __init__(self, db: FlashcardDatabase):
        self.db = db
        self.ai_client = get_ai_client()
        
    def check_dependencies(self) -> Tuple[bool, str]:
        if not DEPENDENCIES_AVAILABLE:
            return False, "Missing dependencies: scikit-learn, umap-learn, or plotly. Please install them to use this feature."
        return True, ""

    def process_flashcards(self, deck_id: Optional[int] = None) -> int:
        """
        Generate embeddings for flashcards that don't have them yet.
        Returns the number of processed cards.
        """
        if deck_id:
            cards = self.db.get_all_flashcards(deck_id)
        else:
            # This is a bit inefficient if there are many decks, but get_all_flashcards is deck-based.
            # I'll need a way to get ALL flashcards across all decks.
            # Let's assume for now we use all decks if deck_id is None.
            decks = self.db.get_all_decks()
            cards = []
            for deck in decks:
                cards.extend(self.db.get_all_flashcards(deck['id']))

        cards_to_process = [c for c in cards if not c.embedding_vector]
        if not cards_to_process:
            return 0

        # Process in batches to avoid API limits/timeouts
        batch_size = 50
        processed_count = 0
        
        for i in range(0, len(cards_to_process), batch_size):
            batch = cards_to_process[i:i + batch_size]
            texts = [c.question for c in batch] # Usually the word/phrase
            
            embeddings = self.ai_client.generate_embeddings(texts)
            if not embeddings:
                continue
                
            for card, embedding in zip(batch, embeddings):
                card.embedding_vector = json.dumps(embedding)
                # Attempt to get a basic category if possible (Phase 1 Low-cost)
                # For now we'll leave category as None or use a placeholder
                self.db.update_flashcard(card)
                processed_count += 1
                
        return processed_count

    def generate_map_data(self, deck_id: Optional[int] = None) -> Optional[pd.DataFrame]:
        """
        Load embeddings from DB, run UMAP, and return a DataFrame with X, Y coordinates.
        """
        is_ok, msg = self.check_dependencies()
        if not is_ok:
            print(f"[SemanticVisualizer] {msg}")
            return None

        # Fetch all cards with embeddings
        decks = self.db.get_all_decks()
        cards = []
        for deck in decks:
            if deck_id is None or deck['id'] == deck_id:
                cards.extend(self.db.get_all_flashcards(deck['id']))
        
        valid_cards = [c for c in cards if c.embedding_vector]
        if len(valid_cards) < 5: # UMAP needs some data
            return None

        embeddings = np.array([json.loads(c.embedding_vector) for c in valid_cards])
        
        # Reduce dimensions to 2D
        reducer = umap.UMAP(n_neighbors=min(len(valid_cards)-1, 15), min_dist=0.1, random_state=42)
        embedding_2d = reducer.fit_transform(embeddings)

        # Create DataFrame
        df = pd.DataFrame({
            'id': [c.id for c in valid_cards],
            'word': [c.question for c in valid_cards],
            'translation': [c.answer for c in valid_cards],
            'x': embedding_2d[:, 0],
            'y': embedding_2d[:, 1],
            'accuracy': [c.get_accuracy() for c in valid_cards]
        })

        # Perform clustering
        n_clusters = max(2, min(len(valid_cards) // 5, 10))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(embeddings)
        
        return df

    def get_semantic_analysis(self, df: pd.DataFrame) -> Dict:
        """
        Identify weak, strong, and adjacent areas based on cluster density and accuracy.
        """
        if df.empty:
            return {}

        cluster_stats = df.groupby('cluster').agg({
            'accuracy': 'mean',
            'word': 'count'
        }).rename(columns={'word': 'density'})

        # Find strong areas (high density, high accuracy)
        strong_clusters = cluster_stats[
            (cluster_stats['density'] >= cluster_stats['density'].median()) & 
            (cluster_stats['accuracy'] >= 70)
        ].index.tolist()

        # Find weak areas (low density or low accuracy)
        weak_clusters = cluster_stats[
            (cluster_stats['density'] < cluster_stats['density'].median()) | 
            (cluster_stats['accuracy'] < 50)
        ].index.tolist()

        # Find adjacent areas (near strong clusters but not quite in them)
        # This is a bit complex without the full high-dim space, but we can 
        # look for clusters that are "small" but near "large" ones in 2D space.
        # For simplicity, we'll just return the cluster summaries.
        
        analysis = {
            'strong_areas': [],
            'weak_areas': [],
            'adjacent_areas': []
        }

        for cluster_id in strong_clusters:
            words = df[df['cluster'] == cluster_id]['word'].tolist()[:5]
            analysis['strong_areas'].append({
                'id': int(cluster_id),
                'sample_words': words,
                'accuracy': float(cluster_stats.loc[cluster_id, 'accuracy'])
            })

        for cluster_id in weak_clusters:
            words = df[df['cluster'] == cluster_id]['word'].tolist()[:5]
            analysis['weak_areas'].append({
                'id': int(cluster_id),
                'sample_words': words,
                'accuracy': float(cluster_stats.loc[cluster_id, 'accuracy'])
            })

        return analysis

    def export_interactive_map(self, df: pd.DataFrame, output_path: str = "vocab_map.html"):
        """Export the Plotly visualization to an HTML file."""
        if df.empty:
            return

        fig = px.scatter(
            df, x='x', y='y',
            text='word',
            color='cluster',
            hover_data=['translation', 'accuracy'],
            title="Semantic Vocabulary Galaxy",
            template="plotly_dark"
        )
        
        fig.update_traces(textposition='top center')
        fig.update_layout(
            showlegend=False,
            xaxis_title=None,
            yaxis_title=None,
            xaxis_visible=False,
            yaxis_visible=False
        )
        
        fig.write_html(output_path)
        return output_path
