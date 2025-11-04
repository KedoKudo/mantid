"""
Main retriever interface for Mantid RAG database.

Provides unified access to vector search, SQL queries, and graph traversal.
"""

import logging
import sqlite3
import pickle
from pathlib import Path
from typing import Dict, List, Optional
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
import networkx as nx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MantidRAGRetriever:
    """Main retrieval interface for Mantid RAG database."""
    
    def __init__(self, mantid_version: str, database_dir: Path = Path("database")):
        """
        Initialize the retriever.
        
        Args:
            mantid_version: Mantid version (e.g., '6.10')
            database_dir: Directory containing database files
        """
        self.mantid_version = mantid_version
        self.database_dir = Path(database_dir)
        
        # File paths
        self.db_path = self.database_dir / f"mantid_v{mantid_version}.db"
        self.faiss_path = self.database_dir / f"mantid_v{mantid_version}.faiss"
        self.graph_path = self.database_dir / f"mantid_v{mantid_version}_graph.pkl"
        
        # Verify files exist
        for path in [self.db_path, self.faiss_path, self.graph_path]:
            if not path.exists():
                raise FileNotFoundError(f"Database file not found: {path}")
        
        # Load components
        logger.info(f"Loading Mantid RAG database v{mantid_version}...")
        self.db = sqlite3.connect(str(self.db_path))
        self.db.row_factory = sqlite3.Row  # Access columns by name
        
        self.faiss_index = faiss.read_index(str(self.faiss_path))
        
        with open(self.graph_path, 'rb') as f:
            self.graph = pickle.load(f)
        
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        logger.info(f"Database loaded: {self.faiss_index.ntotal} vectors, "
                   f"{self.graph.number_of_nodes()} algorithms, "
                   f"{self.graph.number_of_edges()} relationships")
    
    def search(self, query: str, top_k: int = 5, search_type: str = 'hybrid') -> List[Dict]:
        """
        Search for relevant algorithms.
        
        Args:
            query: Natural language query
            top_k: Number of results to return
            search_type: 'vector', 'graph', or 'hybrid'
            
        Returns:
            List of algorithm dictionaries with scores
        """
        if search_type == 'vector':
            return self.vector_search(query, top_k)
        elif search_type == 'graph':
            return self.graph_search(query)
        else:  # hybrid
            return self.hybrid_search(query, top_k)
    
    def vector_search(self, query: str, top_k: int = 5, 
                     embedding_type: Optional[str] = None) -> List[Dict]:
        """
        Perform vector similarity search.
        
        Args:
            query: Search query
            top_k: Number of results
            embedding_type: Filter by embedding type ('summary', 'properties', 'usage', 'full')
            
        Returns:
            List of results with scores
        """
        # Encode query
        query_emb = self.embedding_model.encode([query])[0].astype('float32')
        query_emb = query_emb.reshape(1, -1)
        faiss.normalize_L2(query_emb)
        
        # Search FAISS (get more than needed for filtering)
        k_search = top_k * 4 if embedding_type else top_k * 2
        distances, indices = self.faiss_index.search(query_emb, k_search)
        
        # Get algorithm IDs and filter by embedding type if specified
        results = []
        seen_algorithms = set()
        
        for faiss_id, distance in zip(indices[0], distances[0]):
            if faiss_id == -1:  # FAISS returns -1 for empty slots
                continue
            
            # Get algorithm info from embeddings table
            cursor = self.db.execute("""
                SELECT algorithm_id, embedding_type 
                FROM embeddings 
                WHERE faiss_id = ?
            """, (int(faiss_id),))
            
            row = cursor.fetchone()
            if not row:
                continue
            
            algorithm_id, emb_type = row
            
            # Filter by embedding type if specified
            if embedding_type and emb_type != embedding_type:
                continue
            
            # Avoid duplicates (same algorithm with different embeddings)
            if algorithm_id in seen_algorithms:
                continue
            
            seen_algorithms.add(algorithm_id)
            
            # Get full algorithm data
            alg_data = self.get_algorithm_by_id(algorithm_id)
            if alg_data:
                alg_data['score'] = float(distance)
                alg_data['match_type'] = emb_type
                results.append(alg_data)
            
            if len(results) >= top_k:
                break
        
        return results
    
    def hybrid_search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Perform hybrid search combining vector and graph features.
        
        Args:
            query: Search query
            top_k: Number of results
            
        Returns:
            Re-ranked results
        """
        # 1. Get initial candidates from vector search
        candidates = self.vector_search(query, top_k=top_k * 2)
        
        # 2. Re-rank using graph features
        for result in candidates:
            node_id = f"{result['name']}-v{result['version']}"
            
            if not self.graph.has_node(node_id):
                continue
            
            # Boost based on graph centrality
            if self.graph.number_of_nodes() > 0:
                try:
                    # Use degree centrality (fast to compute)
                    centrality = self.graph.degree(node_id) / (self.graph.number_of_nodes() - 1)
                    result['score'] += centrality * 0.1
                except:
                    pass
            
            # Boost if connected to other high-scoring results
            for other in candidates:
                other_id = f"{other['name']}-v{other['version']}"
                if node_id != other_id and self.graph.has_edge(node_id, other_id):
                    result['score'] += 0.05
        
        # 3. Sort by updated scores
        candidates.sort(key=lambda x: x['score'], reverse=True)
        
        return candidates[:top_k]
    
    def graph_search(self, algorithm_name: str) -> Dict:
        """
        Get algorithm relationships from graph.
        
        Args:
            algorithm_name: Algorithm name (with or without version)
            
        Returns:
            Dictionary with related algorithms
        """
        # Find node ID
        if '-v' not in algorithm_name:
            # Find latest version
            versions = [n for n in self.graph.nodes() if n.startswith(f"{algorithm_name}-v")]
            if not versions:
                return {}
            node_id = max(versions)  # Get latest version
        else:
            node_id = algorithm_name
        
        if not self.graph.has_node(node_id):
            return {}
        
        # Get related nodes
        predecessors = list(self.graph.predecessors(node_id))
        successors = list(self.graph.successors(node_id))
        
        return {
            'algorithm': node_id,
            'before': [self.graph.nodes[n] for n in predecessors[:5]],
            'after': [self.graph.nodes[n] for n in successors[:5]],
            'relationships': self.graph.edges(node_id, data=True)
        }
    
    def get_algorithm_by_id(self, algorithm_id: int) -> Optional[Dict]:
        """
        Get full algorithm data by database ID.
        
        Args:
            algorithm_id: Algorithm database ID
            
        Returns:
            Algorithm dictionary with all metadata
        """
        cursor = self.db.execute("""
            SELECT * FROM algorithms WHERE id = ?
        """, (algorithm_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
        
        alg = dict(row)
        
        # Get properties
        cursor = self.db.execute("""
            SELECT * FROM properties WHERE algorithm_id = ?
        """, (algorithm_id,))
        alg['properties'] = [dict(r) for r in cursor.fetchall()]
        
        # Get documentation
        cursor = self.db.execute("""
            SELECT * FROM documentation WHERE algorithm_id = ?
        """, (algorithm_id,))
        doc_row = cursor.fetchone()
        if doc_row:
            alg['documentation'] = dict(doc_row)
        
        return alg
    
    def get_workflow_suggestions(self, algorithm_name: str) -> Dict:
        """
        Find algorithms commonly used before/after this one.
        
        Args:
            algorithm_name: Algorithm name
            
        Returns:
            Dictionary with workflow suggestions
        """
        return self.graph_search(algorithm_name)
    
    def close(self):
        """Close database connections."""
        self.db.close()
