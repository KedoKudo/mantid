"""
FAISS index creation for vector similarity search.
"""

import logging
import sqlite3
from pathlib import Path
from typing import List, Tuple, Dict
import numpy as np
import faiss

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FAISSIndexBuilder:
    """Build FAISS index from embeddings."""
    
    def build_index(self, algorithm_embeddings: List[Tuple[Dict, List[Tuple[str, np.ndarray]]]], 
                   faiss_path: Path, db_path: Path):
        """
        Build FAISS index and save embedding metadata to SQLite.
        
        Args:
            algorithm_embeddings: List of (algorithm, embeddings) tuples
            faiss_path: Path to save FAISS index
            db_path: Path to SQLite database
        """
        # Collect all embeddings
        all_embeddings = []
        embedding_metadata = []
        
        conn = sqlite3.connect(db_path)
        
        for alg, embeddings in algorithm_embeddings:
            # Get algorithm ID from database
            cursor = conn.execute(
                "SELECT id FROM algorithms WHERE name = ? AND version = ?",
                (alg['name'], alg['version'])
            )
            row = cursor.fetchone()
            if not row:
                logger.warning(f"Algorithm not found in DB: {alg['name']}-v{alg['version']}")
                continue
            
            algorithm_id = row[0]
            
            for emb_type, emb_vector in embeddings:
                all_embeddings.append(emb_vector)
                embedding_metadata.append({
                    'algorithm_id': algorithm_id,
                    'embedding_type': emb_type
                })
        
        # Convert to numpy array
        embeddings_array = np.array(all_embeddings).astype('float32')
        dimension = embeddings_array.shape[1]
        
        logger.info(f"Building FAISS index with {len(embeddings_array)} vectors of dimension {dimension}")
        
        # Normalize for cosine similarity
        faiss.normalize_L2(embeddings_array)
        
        # Create FAISS index (Inner Product for normalized vectors = cosine similarity)
        index = faiss.IndexFlatIP(dimension)
        index.add(embeddings_array)
        
        # Save FAISS index
        faiss.write_index(index, str(faiss_path))
        
        # Save embedding metadata to SQLite
        for faiss_id, metadata in enumerate(embedding_metadata):
            conn.execute("""
                INSERT INTO embeddings (faiss_id, algorithm_id, embedding_type)
                VALUES (?, ?, ?)
            """, (faiss_id, metadata['algorithm_id'], metadata['embedding_type']))
        
        conn.commit()
        conn.close()
        
        logger.info(f"FAISS index created with {index.ntotal} vectors")
