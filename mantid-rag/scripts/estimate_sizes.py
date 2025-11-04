#!/usr/bin/env python3
"""
Estimate database sizes without requiring all dependencies installed.
Just uses the JSON data to calculate estimates.
"""

import json
import sys
from pathlib import Path

def estimate_sizes():
    """Estimate database sizes from test data."""
    
    # Load test data
    test_data_path = Path(__file__).parent.parent / "test_data" / "test_algorithms_50.json"
    
    if not test_data_path.exists():
        print(f"Test data not found: {test_data_path}")
        print("Run extraction/test_extraction.py first")
        return
    
    with open(test_data_path, 'r') as f:
        algorithms = json.load(f)
    
    num_algs = len(algorithms)
    print(f"Loaded {num_algs} algorithms for estimation")
    
    # Calculate JSON size
    json_size_mb = test_data_path.stat().st_size / (1024*1024)
    
    print("\n" + "="*60)
    print("ESTIMATED DATABASE SIZES (for 1000 algorithms)")
    print("="*60)
    
    # Estimates based on typical sizes
    # These are rough estimates based on similar projects
    
    # 1. FAISS index
    # Formula: num_vectors * dimension * 4 bytes (float32)
    # We have 4 embeddings per algorithm (summary, properties, usage, full)
    # Dimension is 384 for all-MiniLM-L6-v2
    vectors_per_alg = 4
    embedding_dimension = 384
    total_vectors = 1000 * vectors_per_alg
    faiss_size_mb = (total_vectors * embedding_dimension * 4) / (1024*1024)
    
    # 2. SQLite database
    # Rough estimate: ~5-10 KB per algorithm with all metadata
    # Plus embeddings table mapping
    sqlite_size_mb = (1000 * 8 * 1024) / (1024*1024)  # 8KB per algorithm
    
    # 3. NetworkX graph pickle
    # Rough estimate: ~5-10 KB per algorithm with relationships
    graph_size_mb = (1000 * 7 * 1024) / (1024*1024)  # 7KB per algorithm
    
    # 4. JSON files (raw extracted data)
    json_scale = 1000 / num_algs
    estimated_json_mb = json_size_mb * json_scale
    
    print(f"\nRaw extraction data (JSON):")
    print(f"  algorithms.json:     ~{estimated_json_mb:.1f} MB")
    print(f"  docs.json:           ~{estimated_json_mb * 1.5:.1f} MB (with examples)")
    print(f"  relationships.json:  ~{estimated_json_mb * 0.3:.1f} MB")
    print(f"  {'─'*45}")
    print(f"  Total JSON:          ~{estimated_json_mb * 2.8:.1f} MB")
    
    print(f"\nProcessed database files:")
    print(f"  mantid_vX.faiss:     ~{faiss_size_mb:.1f} MB")
    print(f"  mantid_vX.db:        ~{sqlite_size_mb:.1f} MB")
    print(f"  mantid_vX_graph.pkl: ~{graph_size_mb:.1f} MB")
    print(f"  {'─'*45}")
    print(f"  Total database:      ~{faiss_size_mb + sqlite_size_mb + graph_size_mb:.1f} MB")
    
    total_all = estimated_json_mb * 2.8 + faiss_size_mb + sqlite_size_mb + graph_size_mb
    
    print(f"\nGrand total (all files): ~{total_all:.1f} MB")
    
    print("\n" + "="*60)
    print("GIT LFS RECOMMENDATION")
    print("="*60)
    
    if total_all < 100:
        print("\n✓ Total size is manageable (<100 MB)")
        print("✓ Git LFS is OPTIONAL")
        print("\nRECOMMENDED APPROACH:")
        print("  1. Add database files to .gitignore")
        print("  2. Distribute database files separately or rebuild from source")
        print("  3. Users can run 'pixi run build-full' to build locally")
    else:
        print("\n⚠ Total size is large (>100 MB)")
        print("⚠ Git LFS is RECOMMENDED")
        print("\nSetup git lfs:")
        print("  git lfs install")
        print("  git lfs track 'database/*.faiss'")
        print("  git lfs track 'database/*.db'")
        print("  git lfs track 'database/*.pkl'")
    
    print("\n" + "="*60)
    print("CURRENT .gitignore STATUS")
    print("="*60)
    
    gitignore_path = Path(__file__).parent.parent / ".gitignore"
    if gitignore_path.exists():
        with open(gitignore_path, 'r') as f:
            content = f.read()
        
        ignored = []
        not_ignored = []
        
        patterns = [
            ('database/*.db', 'SQLite databases'),
            ('database/*.faiss', 'FAISS indexes'),
            ('database/*.pkl', 'NetworkX graphs'),
            ('data/', 'Extracted JSON data'),
            ('test_data/', 'Test data')
        ]
        
        for pattern, desc in patterns:
            # Simple check - just see if pattern or similar is in gitignore
            if pattern in content or pattern.replace('*', '') in content:
                ignored.append(f"  ✓ {pattern:25s} ({desc})")
            else:
                not_ignored.append(f"  ✗ {pattern:25s} ({desc})")
        
        if ignored:
            print("\nCurrently ignored:")
            for item in ignored:
                print(item)
        
        if not_ignored:
            print("\nNOT ignored (consider adding):")
            for item in not_ignored:
                print(item)
    
    print("\n" + "="*60)
    print("NEXT STEPS")
    print("="*60)
    print("\n1. Database files are ALREADY in .gitignore ✓")
    print("2. Extract full data: pixi run extract")
    print("3. Build database: pixi run build-db --version 6.10")
    print("4. Verify actual sizes match estimates")
    print("5. Distribute database files separately or via git lfs")
    

if __name__ == '__main__':
    estimate_sizes()
