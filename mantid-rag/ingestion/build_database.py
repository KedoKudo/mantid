"""
Main database builder for Mantid RAG system.

This module coordinates the creation of the complete database:
- SQLite database with metadata
- FAISS vector index
- NetworkX relationship graph
"""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional
import click

from .generate_embeddings import EmbeddingGenerator
from .create_faiss_index import FAISSIndexBuilder
from .create_graph import GraphBuilder

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseBuilder:
    """Main builder for Mantid RAG database."""
    
    def __init__(self, mantid_version: str, output_dir: Path):
        """
        Initialize the database builder.
        
        Args:
            mantid_version: Mantid version (e.g., '6.10')
            output_dir: Output directory for database files
        """
        self.mantid_version = mantid_version
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # File paths
        self.db_path = self.output_dir / f"mantid_v{mantid_version}.db"
        self.faiss_path = self.output_dir / f"mantid_v{mantid_version}.faiss"
        self.graph_path = self.output_dir / f"mantid_v{mantid_version}_graph.pkl"
        self.metadata_path = self.output_dir / f"mantid_v{mantid_version}_metadata.json"
        
        # Components
        self.embedding_generator = EmbeddingGenerator()
        self.faiss_builder = FAISSIndexBuilder()
        self.graph_builder = GraphBuilder()
    
    def build_complete_database(self, algorithms_file: Path, docs_file: Path, 
                                relationships_file: Path) -> Dict[str, str]:
        """
        Build the complete database from extracted data files.
        
        Args:
            algorithms_file: Path to algorithms JSON
            docs_file: Path to documentation JSON
            relationships_file: Path to relationships JSON
            
        Returns:
            Dictionary with paths to created files
        """
        logger.info(f"Building database for Mantid v{self.mantid_version}")
        
        # Load data
        logger.info("Loading extracted data...")
        with open(algorithms_file, 'r') as f:
            algorithms = json.load(f)
        
        with open(docs_file, 'r') as f:
            docs = json.load(f)
        
        with open(relationships_file, 'r') as f:
            relationships = json.load(f)
        
        logger.info(f"Loaded: {len(algorithms)} algorithms, {len(docs)} docs, {len(relationships)} relationships")
        
        # 1. Create SQLite database
        logger.info("Creating SQLite database...")
        self.create_sqlite_database(algorithms, docs, relationships)
        
        # 2. Generate embeddings and create FAISS index
        logger.info("Generating embeddings and building FAISS index...")
        self.create_faiss_index(algorithms, docs)
        
        # 3. Create NetworkX graph
        logger.info("Building relationship graph...")
        self.create_relationship_graph(algorithms, relationships)
        
        # 4. Save metadata
        metadata = {
            'mantid_version': self.mantid_version,
            'algorithm_count': len(algorithms),
            'relationship_count': len(relationships),
            'files': {
                'database': str(self.db_path),
                'faiss_index': str(self.faiss_path),
                'graph': str(self.graph_path)
            }
        }
        
        with open(self.metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Database build complete!")
        logger.info(f"  SQLite: {self.db_path}")
        logger.info(f"  FAISS: {self.faiss_path}")
        logger.info(f"  Graph: {self.graph_path}")
        
        return metadata['files']
    
    def create_sqlite_database(self, algorithms: List[Dict], docs: List[Dict], 
                               relationships: List[Dict]):
        """
        Create and populate SQLite database.
        
        Args:
            algorithms: Algorithm metadata list
            docs: Documentation list
            relationships: Relationships list
        """
        # Remove existing database
        if self.db_path.exists():
            self.db_path.unlink()
        
        # Create database with schema
        conn = sqlite3.connect(self.db_path)
        
        # Load schema
        schema_path = Path(__file__).parent.parent / "config" / "schema.sql"
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        conn.executescript(schema_sql)
        
        # Insert algorithms
        logger.info("Inserting algorithms...")
        for alg in algorithms:
            cursor = conn.execute("""
                INSERT INTO algorithms (name, version, summary, category, language, file_path,
                                       deprecated, alias, aliases_deprecated, workspace_method_name,
                                       workspace_method_input_property, help_url, mantid_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alg['name'], alg['version'], alg['summary'], alg['category'],
                alg['language'], alg.get('file_path'), alg.get('deprecated', False),
                alg.get('alias'), alg.get('aliases_deprecated'), alg.get('workspace_method_name'),
                alg.get('workspace_method_input_property'), alg.get('help_url'),
                self.mantid_version
            ))
            
            algorithm_id = cursor.lastrowid
            
            # Insert properties
            for prop in alg.get('properties', []):
                conn.execute("""
                    INSERT INTO properties (algorithm_id, name, type, direction, optional,
                                          default_value, description, validator_info)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    algorithm_id, prop['name'], prop['type'], prop['direction'],
                    prop.get('optional', False), prop.get('default_value'),
                    prop.get('description'), prop.get('validator_info')
                ))
            
            # Insert categories
            for category_name in alg.get('categories', []):
                # Get or create category
                cursor = conn.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
                row = cursor.fetchone()
                
                if row:
                    category_id = row[0]
                else:
                    cursor = conn.execute("INSERT INTO categories (name) VALUES (?)", (category_name,))
                    category_id = cursor.lastrowid
                
                # Link algorithm to category
                conn.execute("""
                    INSERT OR IGNORE INTO algorithm_categories (algorithm_id, category_id)
                    VALUES (?, ?)
                """, (algorithm_id, category_id))
        
        # Insert documentation
        logger.info("Inserting documentation...")
        doc_lookup = {f"{doc['algorithm_name']}-v{doc['version']}": doc for doc in docs}
        
        for alg in algorithms:
            alg_key = f"{alg['name']}-v{alg['version']}"
            if alg_key in doc_lookup:
                doc = doc_lookup[alg_key]
                
                # Get algorithm ID
                cursor = conn.execute(
                    "SELECT id FROM algorithms WHERE name = ? AND version = ?",
                    (alg['name'], alg['version'])
                )
                algorithm_id = cursor.fetchone()[0]
                
                conn.execute("""
                    INSERT INTO documentation (algorithm_id, rst_file, full_description,
                                              usage_examples, references)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    algorithm_id, doc.get('rst_file'),
                    doc.get('full_description'),
                    json.dumps(doc.get('usage_examples', [])),
                    json.dumps(doc.get('references', []))
                ))
        
        # Insert relationships
        logger.info("Inserting relationships...")
        for rel in relationships:
            # Get algorithm IDs
            from_parts = rel['from_algorithm'].rsplit('-v', 1)
            to_parts = rel['to_algorithm'].rsplit('-v', 1)
            
            cursor = conn.execute(
                "SELECT id FROM algorithms WHERE name = ? AND version = ?",
                (from_parts[0], int(from_parts[1]))
            )
            from_id_row = cursor.fetchone()
            
            cursor = conn.execute(
                "SELECT id FROM algorithms WHERE name = ? AND version = ?",
                (to_parts[0], int(to_parts[1]))
            )
            to_id_row = cursor.fetchone()
            
            if from_id_row and to_id_row:
                conn.execute("""
                    INSERT OR IGNORE INTO relationships (from_algorithm_id, to_algorithm_id,
                                                        relationship_type, weight, metadata)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    from_id_row[0], to_id_row[0], rel['relationship_type'],
                    rel.get('weight', 1.0), json.dumps(rel.get('metadata', {}))
                ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"SQLite database created: {self.db_path}")
    
    def create_faiss_index(self, algorithms: List[Dict], docs: List[Dict]):
        """
        Generate embeddings and create FAISS index.
        
        Args:
            algorithms: Algorithm metadata list
            docs: Documentation list
        """
        # Merge algorithms with docs
        doc_lookup = {f"{doc['algorithm_name']}-v{doc['version']}": doc for doc in docs}
        
        # Generate embeddings
        algorithm_embeddings = []
        for alg in algorithms:
            alg_key = f"{alg['name']}-v{alg['version']}"
            doc = doc_lookup.get(alg_key, {})
            
            embeddings = self.embedding_generator.generate_algorithm_embeddings(alg, doc)
            algorithm_embeddings.append((alg, embeddings))
        
        # Build FAISS index and save embedding metadata to SQLite
        self.faiss_builder.build_index(algorithm_embeddings, self.faiss_path, self.db_path)
        
        logger.info(f"FAISS index created: {self.faiss_path}")
    
    def create_relationship_graph(self, algorithms: List[Dict], relationships: List[Dict]):
        """
        Create NetworkX relationship graph.
        
        Args:
            algorithms: Algorithm metadata list
            relationships: Relationships list
        """
        graph = self.graph_builder.build_graph(algorithms, relationships)
        self.graph_builder.save_graph(graph, self.graph_path)
        
        logger.info(f"Relationship graph created: {self.graph_path}")


@click.command()
@click.option('--version', '-v', required=True, help='Mantid version (e.g., 6.10)')
@click.option('--data-dir', '-d', type=click.Path(exists=True), required=True,
              help='Directory containing extracted data files')
@click.option('--output-dir', '-o', type=click.Path(), default='database',
              help='Output directory for database files')
def main(version: str, data_dir: str, output_dir: str):
    """Build complete RAG database for Mantid algorithms."""
    data_dir = Path(data_dir)
    
    # Find data files
    algorithms_file = data_dir / "algorithms.json"
    docs_file = data_dir / "docs.json"
    relationships_file = data_dir / "relationships.json"
    
    # Verify files exist
    for file in [algorithms_file, docs_file, relationships_file]:
        if not file.exists():
            logger.error(f"Required file not found: {file}")
            return 1
    
    # Build database
    builder = DatabaseBuilder(version, Path(output_dir))
    builder.build_complete_database(algorithms_file, docs_file, relationships_file)
    
    return 0


if __name__ == '__main__':
    main()
