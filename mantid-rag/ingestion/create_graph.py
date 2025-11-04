"""
NetworkX graph creation for algorithm relationships.
"""

import logging
import pickle
from pathlib import Path
from typing import Dict, List
import networkx as nx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GraphBuilder:
    """Build NetworkX relationship graph."""
    
    def build_graph(self, algorithms: List[Dict], relationships: List[Dict]) -> nx.DiGraph:
        """
        Build directed graph from algorithms and relationships.
        
        Args:
            algorithms: List of algorithm metadata
            relationships: List of relationship metadata
            
        Returns:
            NetworkX directed graph
        """
        G = nx.DiGraph()
        
        # Add algorithm nodes
        logger.info(f"Adding {len(algorithms)} algorithm nodes...")
        for alg in algorithms:
            node_id = f"{alg['name']}-v{alg['version']}"
            G.add_node(
                node_id,
                name=alg['name'],
                version=alg['version'],
                summary=alg['summary'],
                category=alg['category'],
                categories=alg.get('categories', []),
                deprecated=alg.get('deprecated', False),
                language=alg.get('language', 'unknown')
            )
        
        # Add relationship edges
        logger.info(f"Adding {len(relationships)} relationship edges...")
        for rel in relationships:
            from_node = rel['from_algorithm']
            to_node = rel['to_algorithm']
            
            if G.has_node(from_node) and G.has_node(to_node):
                G.add_edge(
                    from_node,
                    to_node,
                    relationship=rel['relationship_type'],
                    weight=rel.get('weight', 1.0),
                    metadata=rel.get('metadata', {})
                )
        
        logger.info(f"Graph built: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
        
        return G
    
    def save_graph(self, graph: nx.DiGraph, graph_path: Path):
        """
        Save graph to pickle file.
        
        Args:
            graph: NetworkX graph
            graph_path: Path to save graph
        """
        with open(graph_path, 'wb') as f:
            pickle.dump(graph, f, protocol=pickle.HIGHEST_PROTOCOL)
        
        logger.info(f"Graph saved to {graph_path}")
    
    @staticmethod
    def load_graph(graph_path: Path) -> nx.DiGraph:
        """
        Load graph from pickle file.
        
        Args:
            graph_path: Path to graph file
            
        Returns:
            NetworkX graph
        """
        with open(graph_path, 'rb') as f:
            graph = pickle.load(f)
        
        return graph
