#!/usr/bin/env python3
"""
Test script to measure database file sizes with different numbers of algorithms.

This helps us decide if we need git lfs.
"""

import sys
import json
import logging
import sqlite3
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_database_sizes():
    """Test database sizes with sample data."""
    
    # Import after path is set
    try:
        from sentence_transformers import SentenceTransformer
        import faiss
        import networkx as nx
    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Install with: pip install sentence-transformers faiss-cpu networkx")
        return
    
    # Load test data
    test_data_path = Path(__file__).parent.parent / "test_data" / "test_algorithms_50.json"
    
    if not test_data_path.exists():
        logger.error(f"Test data not found: {test_data_path}")
        logger.error("Run extraction/test_extraction.py first")
        return
    
    with open(test_data_path, 'r') as f:
        algorithms = json.load(f)
    
    logger.info(f"Loaded {len(algorithms)} algorithms for testing")
    
    # Test directory
    test_db_dir = Path(__file__).parent.parent / "test_data" / "test_db"
    test_db_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Test embedding generation
    logger.info("\n=== Testing Embedding Generation ===")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    dimension = model.get_sentence_embedding_dimension()
    logger.info(f"Embedding dimension: {dimension}")
    
    all_embeddings = []
    for alg in algorithms:
        # Generate 4 embeddings per algorithm (summary, properties, usage, full)
        summary_text = f"{alg['name']}: {alg['summary']}"
        summary_emb = model.encode(summary_text)
        
        # We'll create 4 embeddings per algorithm
        for _ in range(4):
            all_embeddings.append(summary_emb)
    
    embeddings_array = np.array(all_embeddings).astype('float32')
    logger.info(f"Generated {len(embeddings_array)} embeddings")
    logger.info(f"Embedding array size: {embeddings_array.nbytes / (1024*1024):.2f} MB in memory")
    
    # 2. Test FAISS index
    logger.info("\n=== Testing FAISS Index ===")
    faiss.normalize_L2(embeddings_array)
    index = faiss.IndexFlatIP(dimension)
    index.add(embeddings_array)
    
    faiss_path = test_db_dir / "test.faiss"
    faiss.write_index(index, str(faiss_path))
    faiss_size = faiss_path.stat().st_size / (1024*1024)
    logger.info(f"FAISS index saved: {faiss_size:.2f} MB")
    
    # 3. Test SQLite database
    logger.info("\n=== Testing SQLite Database ===")
    db_path = test_db_dir / "test.db"
    if db_path.exists():
        db_path.unlink()
    
    conn = sqlite3.connect(str(db_path))
    
    # Create simple schema
    conn.execute("""
        CREATE TABLE algorithms (
            id INTEGER PRIMARY KEY,
            name TEXT,
            version INTEGER,
            summary TEXT,
            category TEXT,
            file_path TEXT
        )
    """)
    
    conn.execute("""
        CREATE TABLE embeddings (
            id INTEGER PRIMARY KEY,
            faiss_id INTEGER,
            algorithm_id INTEGER,
            embedding_type TEXT
        )
    """)
    
    # Insert data
    for i, alg in enumerate(algorithms):
        conn.execute("""
            INSERT INTO algorithms (name, version, summary, category, file_path)
            VALUES (?, ?, ?, ?, ?)
        """, (alg['name'], alg['version'], alg['summary'], alg['category'], alg['file_path']))
        
        # 4 embeddings per algorithm
        for j in range(4):
            conn.execute("""
                INSERT INTO embeddings (faiss_id, algorithm_id, embedding_type)
                VALUES (?, ?, ?)
            """, (i*4 + j, i+1, ['summary', 'properties', 'usage', 'full'][j]))
    
    conn.commit()
    conn.close()
    
    db_size = db_path.stat().st_size / (1024*1024)
    logger.info(f"SQLite database saved: {db_size:.2f} MB")
    
    # 4. Test NetworkX graph
    logger.info("\n=== Testing NetworkX Graph ===")
    G = nx.DiGraph()
    
    for alg in algorithms:
        node_id = f"{alg['name']}-v{alg['version']}"
        G.add_node(node_id, **alg)
        
        # Add some relationships
        for related in alg.get('see_also', []):
            related_id = f"{related}-v1"  # Assume v1
            if G.has_node(related_id):
                G.add_edge(node_id, related_id, relationship='see_also', weight=0.8)
    
    import pickle
    graph_path = test_db_dir / "test_graph.pkl"
    with open(graph_path, 'wb') as f:
        pickle.dump(G, f, protocol=pickle.HIGHEST_PROTOCOL)
    
    graph_size = graph_path.stat().st_size / (1024*1024)
    logger.info(f"NetworkX graph saved: {graph_size:.2f} MB")
    logger.info(f"Graph has {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
    
    # 5. Calculate totals and estimates
    logger.info("\n" + "="*60)
    logger.info("=== SIZE SUMMARY ===")
    logger.info("="*60)
    
    total_size = faiss_size + db_size + graph_size
    
    logger.info(f"\nFor {len(algorithms)} algorithms:")
    logger.info(f"  FAISS index:  {faiss_size:>8.2f} MB")
    logger.info(f"  SQLite DB:    {db_size:>8.2f} MB")
    logger.info(f"  Graph:        {graph_size:>8.2f} MB")
    logger.info(f"  {'─'*30}")
    logger.info(f"  TOTAL:        {total_size:>8.2f} MB")
    
    # Estimate for 1000 algorithms
    scaling_factor = 1000 / len(algorithms)
    estimated_faiss = faiss_size * scaling_factor
    estimated_db = db_size * scaling_factor
    estimated_graph = graph_size * scaling_factor
    estimated_total = total_size * scaling_factor
    
    logger.info(f"\nEstimated for 1000 algorithms:")
    logger.info(f"  FAISS index:  {estimated_faiss:>8.2f} MB")
    logger.info(f"  SQLite DB:    {estimated_db:>8.2f} MB")
    logger.info(f"  Graph:        {estimated_graph:>8.2f} MB")
    logger.info(f"  {'─'*30}")
    logger.info(f"  TOTAL:        {estimated_total:>8.2f} MB")
    
    # Git LFS recommendation
    logger.info("\n" + "="*60)
    logger.info("=== GIT LFS RECOMMENDATION ===")
    logger.info("="*60)
    
    if estimated_total < 100:
        logger.info("✓ Database files are relatively small (<100 MB)")
        logger.info("✓ Git LFS is OPTIONAL but recommended for binary files")
        logger.info("✓ Consider adding *.db, *.faiss, *.pkl to .gitignore instead")
        logger.info("  and distribute database files separately")
    else:
        logger.info("⚠ Database files are large (>100 MB)")
        logger.info("⚠ Git LFS is RECOMMENDED for files over 50 MB")
        logger.info("⚠ Set up git lfs before committing database files")
    
    logger.info("\nSuggested .gitignore patterns:")
    logger.info("  database/*.db")
    logger.info("  database/*.faiss")
    logger.info("  database/*.pkl")
    logger.info("  test_data/")
    
    logger.info("\nIf using git lfs:")
    logger.info("  git lfs track 'database/*.faiss'")
    logger.info("  git lfs track 'database/*.db'")
    logger.info("  git lfs track 'database/*.pkl'")
    

if __name__ == '__main__':
    test_database_sizes()
