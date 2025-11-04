"""
Embedding generation for Mantid algorithms.

Uses sentence-transformers to generate multiple embeddings per algorithm
for different query strategies.
"""

import logging
from typing import Dict, List, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generate embeddings for algorithm metadata."""
    
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Sentence-transformers model name
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")
    
    def generate_algorithm_embeddings(self, algorithm: Dict, documentation: Dict = None) -> List[Tuple[str, np.ndarray]]:
        """
        Generate multiple embeddings for an algorithm.
        
        Args:
            algorithm: Algorithm metadata dictionary
            documentation: Documentation dictionary (optional)
            
        Returns:
            List of (embedding_type, embedding_vector) tuples
        """
        embeddings = []
        
        # 1. Summary embedding (for "what does it do" queries)
        summary_text = f"{algorithm['name']}: {algorithm['summary']}"
        summary_emb = self.model.encode(summary_text, convert_to_numpy=True)
        embeddings.append(('summary', summary_emb))
        
        # 2. Properties embedding (for parameter-based queries)
        props_texts = []
        for prop in algorithm.get('properties', []):
            prop_text = f"{prop['name']} ({prop['type']}, {prop['direction']}): {prop.get('description', '')}"
            props_texts.append(prop_text)
        
        if props_texts:
            props_text = " ".join(props_texts)
            props_emb = self.model.encode(props_text, convert_to_numpy=True)
            embeddings.append(('properties', props_emb))
        
        # 3. Usage embedding (from documentation examples)
        if documentation and documentation.get('usage_examples'):
            usage_text = " ".join(documentation['usage_examples'][:3])  # Limit to first 3 examples
            if usage_text.strip():
                usage_emb = self.model.encode(usage_text, convert_to_numpy=True)
                embeddings.append(('usage', usage_emb))
        
        # 4. Full context embedding (combination for general queries)
        full_parts = [summary_text]
        if props_texts:
            full_parts.append(" ".join(props_texts[:5]))  # First 5 properties
        if documentation:
            full_parts.append(documentation.get('full_description', '')[:500])  # First 500 chars
        
        full_text = " ".join(full_parts)
        full_emb = self.model.encode(full_text, convert_to_numpy=True)
        embeddings.append(('full', full_emb))
        
        return embeddings
