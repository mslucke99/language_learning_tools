import json
import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
from src.core.database import FlashcardDatabase
from src.services.llm_service import get_ai_client

import importlib.util

def _check_deps():
    deps = ['sklearn', 'umap', 'plotly']
    for d in deps:
        if importlib.util.find_spec(d) is None:
            return False
    return True

DEPENDENCIES_AVAILABLE = _check_deps()

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
                self.db.update_flashcard(card)
                processed_count += 1
                
        return processed_count

    def process_known_words(self, language: Optional[str] = None) -> int:
        """
        Generate embeddings for known_words that don't have them yet.
        Returns the number of processed words.
        """
        words = self.db.get_all_known_words(language)
        words_to_process = [w for w in words if not w.get('embedding_vector')]
        
        if not words_to_process:
            return 0
            
        # Process in batches
        batch_size = 50
        processed_count = 0
        
        for i in range(0, len(words_to_process), batch_size):
            batch = words_to_process[i:i + batch_size]
            texts = [w['lemma'] for w in batch]
            
            embeddings = self.ai_client.generate_embeddings(texts)
            if not embeddings:
                continue
                
            for word, embedding in zip(batch, embeddings):
                self.db.update_known_word_embedding(word['id'], json.dumps(embedding))
                processed_count += 1
                
        return processed_count

    def generate_map_data(self, deck_id: Optional[int] = None, language: Optional[str] = None) -> Optional[pd.DataFrame]:
        """
        Load embeddings from DB, run UMAP, and return a DataFrame with X, Y coordinates.
        Combines flashcards and known words.
        """
        is_ok, msg = self.check_dependencies()
        if not is_ok:
            print(f"[SemanticVisualizer] {msg}")
            return None

        # Fetch flashcards
        decks = self.db.get_all_decks()
        cards = []
        for deck in decks:
            if deck_id is None or deck['id'] == deck_id:
                cards.extend(self.db.get_all_flashcards(deck['id']))
        
        # Filter for only those with embeddings
        valid_cards = [c for c in cards if c.embedding_vector]
        
        # Fetch known_words
        # If deck_id is specified, we might not want all known_words, 
        # but usually deck_id=None means "process everything".
        target_lang = language
        if deck_id and not target_lang:
            for deck in decks:
                if deck['id'] == deck_id:
                    target_lang = deck.get('language')
                    break
        
        # Filter flashcards by language if target_lang is defined
        if target_lang:
            filtered_cards = []
            for c in valid_cards:
                # Find deck for this card to check language
                for deck in decks:
                    if deck['id'] == c.deck_id:
                        if deck.get('language') == target_lang:
                            filtered_cards.append(c)
                        break
            valid_cards = filtered_cards

        known_words = self.db.get_all_known_words(target_lang)
        valid_known = [w for w in known_words if w.get('embedding_vector')]
        
        if len(valid_cards) + len(valid_known) < 5: # UMAP needs some data
            return None

        # Combine data
        combined_data = []
        for c in valid_cards:
            combined_data.append({
                'id': f"fc_{c.id}",
                'word': c.question,
                'translation': c.answer,
                'accuracy': c.get_accuracy(),
                'embedding': json.loads(c.embedding_vector),
                'type': 'Flashcard'
            })
            
        for w in valid_known:
            combined_data.append({
                'id': f"kw_{w['id']}",
                'word': w['lemma'],
                'translation': f"Known ({w['source']})",
                'accuracy': 100.0, # Assumed known
                'embedding': json.loads(w['embedding_vector']),
                'type': 'Known Word'
            })

        embeddings = np.array([d['embedding'] for d in combined_data])
        
        # Reduce dimensions to 2D
        import umap
        reducer = umap.UMAP(n_neighbors=min(len(combined_data)-1, 15), min_dist=0.1, random_state=42)
        embedding_2d = reducer.fit_transform(embeddings)

        # Create DataFrame
        df = pd.DataFrame({
            'id': [d['id'] for d in combined_data],
            'word': [d['word'] for d in combined_data],
            'translation': [d['translation'] for d in combined_data],
            'x': embedding_2d[:, 0],
            'y': embedding_2d[:, 1],
            'accuracy': [d['accuracy'] for d in combined_data],
            'type': [d['type'] for d in combined_data]
        })

        # Perform clustering
        from sklearn.cluster import KMeans
        n_clusters = max(2, min(len(combined_data) // 5, 10))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        df['cluster'] = kmeans.fit_predict(embeddings)
        
        return df

    def get_semantic_analysis(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze clusters to find strong and weak areas."""
        if df is None or df.empty:
            return {"strong_areas": [], "weak_areas": []}

        # Calculate cluster stats
        cluster_stats = df.groupby('cluster').agg({
            'accuracy': 'mean',
            'word': 'count'
        }).rename(columns={'word': 'density'})

        strong = []
        weak = []

        for cluster_id, stats in cluster_stats.iterrows():
            words = df[df['cluster'] == cluster_id]['word'].tolist()[:5]
            area_info = {
                "cluster_center": cluster_id,
                "representative_words": words,
                "accuracy": stats['accuracy'],
                "density": stats['density']
            }
            if stats['accuracy'] >= 80:
                strong.append(area_info)
            elif stats['accuracy'] <= 40:
                weak.append(area_info)

        return {
            "strong_areas": strong,
            "weak_areas": weak
        }

    def get_cluster_profiles(self, deck_id: Optional[int] = None, language: Optional[str] = None) -> List[Any]:
        """Extract cluster centroids + strength for use by SemanticFamiliarityScorer."""
        from src.services.text.semantic_familiarity import ClusterProfile
        
        # Use our updated combined data
        df = self.generate_map_data(deck_id, language)
        if df is None or df.empty:
            return []

        # Re-fetch embeddings to avoid re-calculating UMAP here
        # (This is a bit duplicate but avoids large structural changes for now)
        decks = self.db.get_all_decks()
        
        # Filter flashcards
        cards = []
        for deck in decks:
            if deck_id is None or deck['id'] == deck_id:
                cards.extend(self.db.get_all_flashcards(deck['id']))
        valid_cards = [c for c in cards if c.embedding_vector]
        
        # Filter known words
        target_lang = language
        if deck_id and not target_lang:
            for deck in decks:
                if deck['id'] == deck_id:
                    target_lang = deck.get('language')
                    break
        known_words = self.db.get_all_known_words(target_lang)
        valid_known = [w for w in known_words if w.get('embedding_vector')]
        
        if not valid_cards and not valid_known:
            return []

        # Combine embeddings
        embeddings = []
        accuracies = []
        words = []
        
        for c in valid_cards:
            embeddings.append(json.loads(c.embedding_vector))
            accuracies.append(c.get_accuracy())
            words.append(c.question)
            
        for w in valid_known:
            embeddings.append(json.loads(w['embedding_vector']))
            accuracies.append(100.0)
            words.append(w['lemma'])
            
        embeddings_arr = np.array(embeddings)
        
        # KMeans
        from sklearn.cluster import KMeans
        n_clusters = max(2, min(len(embeddings) // 5, 10))
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings_arr)
        centroids = kmeans.cluster_centers_
        
        # Calculate stats per cluster
        df_temp = pd.DataFrame({
            'cluster': labels,
            'accuracy': accuracies,
            'word': words
        })
        
        cluster_stats = df_temp.groupby('cluster').agg({
            'accuracy': 'mean',
            'word': 'count'
        }).rename(columns={'word': 'density'})
        
        max_density = cluster_stats['density'].max() if not cluster_stats.empty else 1
        
        profiles = []
        for i, centroid in enumerate(centroids):
            accuracy = cluster_stats.loc[i, 'accuracy'] / 100.0 # 0-1
            density = min(1.0, cluster_stats.loc[i, 'density'] / (max_density or 1))
            
            # Strength = blend of density and performance
            strength = (accuracy * 0.7) + (density * 0.3)
            
            sample_words = df_temp[df_temp['cluster'] == i]['word'].tolist()[:5]
            
            profiles.append(ClusterProfile(
                centroid=centroid,
                strength=strength,
                sample_words=sample_words
            ))
            
        return profiles

    def export_interactive_map(self, df: pd.DataFrame, output_path: str = "vocab_map.html"):
        """Export the Plotly visualization to an HTML file."""
        if df.empty:
            return

        import plotly.express as px
        fig = px.scatter(
            df, x='x', y='y',
            text='word',
            color='type', # Use type for color instead of cluster ID for better intuition
            hover_data=['translation', 'accuracy', 'cluster'],
            title="Semantic Vocabulary Galaxy",
            template="plotly_dark",
            labels={'type': 'Vocabulary Type'}
        )
        
        fig.update_traces(textposition='top center')
        fig.update_layout(
            showlegend=True,
            xaxis_title=None,
            yaxis_title=None,
            xaxis_visible=False,
            yaxis_visible=False
        )
        
        fig.write_html(output_path)
        return output_path
