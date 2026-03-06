import math
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

@dataclass
class ClusterProfile:
    centroid: np.ndarray       # cluster center embedding
    strength: float            # 0-1 based on density + accuracy
    sample_words: List[str]    # for debugging/display

class SemanticFamiliarityScorer:
    """
    Computes topic familiarity for words based on how close they are
    to the user's known vocabulary clusters.
    """
    
    def __init__(self, cluster_profiles: List[ClusterProfile]):
        self.cluster_profiles = cluster_profiles
        
    def score_words(self, word_embeddings: List[List[float]]) -> float:
        """
        Returns 0-1 familiarity score (1 = very familiar topics).
        Higher score means words are on average closer to strong clusters.
        """
        if not self.cluster_profiles or not word_embeddings:
            return 0.5 # Neutral
            
        similarities = []
        for embedding in word_embeddings:
            vec = np.array(embedding)
            # Find closest cluster centroid
            max_sim = -1.0
            best_strength = 0.5
            
            for cluster in self.cluster_profiles:
                # Cosine similarity: (A dot B) / (||A|| * ||B||)
                # If embeddings are normalized, just dot product
                denom = (np.linalg.norm(vec) * np.linalg.norm(cluster.centroid))
                if denom == 0:
                    sim = 0.0
                else:
                    sim = np.dot(vec, cluster.centroid) / denom
                
                if sim > max_sim:
                    max_sim = sim
                    best_strength = cluster.strength
            
            # Map similarity to 0-1 and weight by cluster strength
            # Typical cosine sim for related words is 0.4-0.8.
            # We'll use a sigmoid-like mapping.
            # (max_sim - offset) * scale
            familiarity = 1.0 / (1.0 + math.exp(-10.0 * (max_sim - 0.6)))
            
            # Weight by how established the cluster is
            final_familiarity = familiarity * best_strength
            similarities.append(final_familiarity)
            
        if not similarities:
            return 0.5
            
        return sum(similarities) / len(similarities)
