"""
Relationship builder for Mantid algorithms.

This module analyzes algorithm metadata to build relationship graphs including:
- seeAlso relationships
- Workspace type compatibility
- Common workflow patterns
- Deprecation chains
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import click

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Relationship:
    """Relationship between two algorithms."""
    from_algorithm: str  # AlgorithmName-vX
    to_algorithm: str    # AlgorithmName-vY
    relationship_type: str  # 'see_also', 'replaces', 'workspace_flow', etc.
    weight: float  # Strength of relationship (0.0 to 1.0)
    metadata: Dict[str, str]  # Additional information


class RelationshipBuilder:
    """Build relationship graph from algorithm metadata."""
    
    def __init__(self, algorithms_data: List[Dict]):
        """
        Initialize the relationship builder.
        
        Args:
            algorithms_data: List of algorithm metadata dictionaries
        """
        self.algorithms = algorithms_data
        self.algorithm_lookup = self._build_algorithm_lookup()
        self.relationships: List[Relationship] = []
    
    def _build_algorithm_lookup(self) -> Dict[str, Dict]:
        """
        Build lookup table for algorithms.
        
        Returns:
            Dictionary mapping algorithm_id to algorithm data
        """
        lookup = {}
        for alg in self.algorithms:
            alg_id = f"{alg['name']}-v{alg['version']}"
            lookup[alg_id] = alg
        return lookup
    
    def build_all_relationships(self) -> List[Relationship]:
        """
        Build all types of relationships.
        
        Returns:
            List of Relationship objects
        """
        logger.info("Building relationships...")
        
        # 1. Extract seeAlso relationships
        self._build_see_also_relationships()
        
        # 2. Build deprecation chains
        self._build_deprecation_relationships()
        
        # 3. Analyze workspace type compatibility
        self._build_workspace_type_relationships()
        
        # 4. Find common categories
        self._build_category_relationships()
        
        logger.info(f"Built {len(self.relationships)} relationships")
        return self.relationships
    
    def _build_see_also_relationships(self):
        """Build relationships from seeAlso metadata."""
        logger.info("Building seeAlso relationships...")
        
        for alg in self.algorithms:
            alg_id = f"{alg['name']}-v{alg['version']}"
            see_also = alg.get('see_also', [])
            
            for related_name in see_also:
                # Find the latest version of the related algorithm
                related_id = self._find_latest_version(related_name)
                
                if related_id and related_id in self.algorithm_lookup:
                    rel = Relationship(
                        from_algorithm=alg_id,
                        to_algorithm=related_id,
                        relationship_type='see_also',
                        weight=0.8,
                        metadata={'source': 'algorithm_metadata'}
                    )
                    self.relationships.append(rel)
    
    def _build_deprecation_relationships(self):
        """Build deprecation replacement chains."""
        logger.info("Building deprecation relationships...")
        
        # TODO: Implement deprecation chain detection
        # This would require parsing deprecation information
        # and finding replacement algorithms
        pass
    
    def _build_workspace_type_relationships(self):
        """Build relationships based on workspace type compatibility."""
        logger.info("Building workspace type relationships...")
        
        # Group algorithms by workspace types they produce and consume
        producers = defaultdict(list)  # workspace_type -> [algorithms]
        consumers = defaultdict(list)  # workspace_type -> [algorithms]
        
        for alg in self.algorithms:
            alg_id = f"{alg['name']}-v{alg['version']}"
            
            # Analyze properties to determine input/output workspace types
            for prop in alg.get('properties', []):
                if 'Workspace' in prop.get('type', ''):
                    ws_type = prop['type']
                    
                    if prop['direction'] == 'Input':
                        consumers[ws_type].append(alg_id)
                    elif prop['direction'] == 'Output':
                        producers[ws_type].append(alg_id)
        
        # Create relationships between producers and consumers
        for ws_type in producers:
            if ws_type in consumers:
                for producer_id in producers[ws_type]:
                    for consumer_id in consumers[ws_type]:
                        if producer_id != consumer_id:
                            rel = Relationship(
                                from_algorithm=producer_id,
                                to_algorithm=consumer_id,
                                relationship_type='workspace_flow',
                                weight=0.5,
                                metadata={'workspace_type': ws_type}
                            )
                            self.relationships.append(rel)
    
    def _build_category_relationships(self):
        """Build relationships based on shared categories."""
        logger.info("Building category relationships...")
        
        # Group algorithms by category
        category_groups = defaultdict(list)
        
        for alg in self.algorithms:
            alg_id = f"{alg['name']}-v{alg['version']}"
            categories = alg.get('categories', [])
            
            for category in categories:
                category_groups[category].append(alg_id)
        
        # Create relationships within categories (limit to avoid explosion)
        for category, alg_ids in category_groups.items():
            if len(alg_ids) > 1:
                # Only create relationships for small categories
                if len(alg_ids) <= 20:
                    for i, alg_id1 in enumerate(alg_ids):
                        for alg_id2 in alg_ids[i+1:]:
                            rel = Relationship(
                                from_algorithm=alg_id1,
                                to_algorithm=alg_id2,
                                relationship_type='same_category',
                                weight=0.3,
                                metadata={'category': category}
                            )
                            self.relationships.append(rel)
    
    def _find_latest_version(self, algorithm_name: str) -> str:
        """
        Find the latest version of an algorithm by name.
        
        Args:
            algorithm_name: Name of the algorithm
            
        Returns:
            Algorithm ID (name-vX) for latest version
        """
        versions = []
        for alg_id, alg in self.algorithm_lookup.items():
            if alg['name'] == algorithm_name:
                versions.append((alg['version'], alg_id))
        
        if versions:
            versions.sort(reverse=True)
            return versions[0][1]
        
        return None
    
    def save_to_json(self, output_path: Path):
        """
        Save relationships to JSON file.
        
        Args:
            output_path: Path to output JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [asdict(rel) for rel in self.relationships]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(self.relationships)} relationships to {output_path}")
    
    def get_statistics(self) -> Dict[str, int]:
        """
        Get relationship statistics.
        
        Returns:
            Dictionary of relationship type counts
        """
        stats = defaultdict(int)
        for rel in self.relationships:
            stats[rel.relationship_type] += 1
        return dict(stats)


@click.command()
@click.option('--input', '-i', type=click.Path(exists=True), required=True,
              help='Input algorithms JSON file')
@click.option('--output', '-o', type=click.Path(), default='data/relationships.json',
              help='Output relationships JSON file')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def main(input: str, output: str, verbose: bool):
    """Build relationship graph from algorithm metadata."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load algorithms
    with open(input, 'r') as f:
        algorithms = json.load(f)
    
    logger.info(f"Loaded {len(algorithms)} algorithms")
    
    # Build relationships
    builder = RelationshipBuilder(algorithms)
    relationships = builder.build_all_relationships()
    builder.save_to_json(Path(output))
    
    # Print statistics
    stats = builder.get_statistics()
    logger.info("Relationship statistics:")
    for rel_type, count in stats.items():
        logger.info(f"  {rel_type}: {count}")
    
    return 0


if __name__ == '__main__':
    main()
