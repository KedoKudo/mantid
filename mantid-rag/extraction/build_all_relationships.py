#!/usr/bin/env python3
"""Build relationships without click dependency."""

import json
import logging
from pathlib import Path
from typing import Dict, List
from dataclasses import dataclass, asdict
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Relationship:
    """Relationship between two algorithms."""
    from_algorithm: str
    to_algorithm: str
    relationship_type: str
    weight: float
    metadata: Dict[str, str]


class RelationshipBuilder:
    """Build relationship graph from algorithm metadata."""
    
    def __init__(self, algorithms_data: List[Dict]):
        self.algorithms = algorithms_data
        self.algorithm_lookup = self._build_algorithm_lookup()
        self.relationships: List[Relationship] = []
    
    def _build_algorithm_lookup(self) -> Dict[str, Dict]:
        lookup = {}
        for alg in self.algorithms:
            alg_id = f"{alg['name']}-v{alg['version']}"
            lookup[alg_id] = alg
        return lookup
    
    def build_all_relationships(self) -> List[Relationship]:
        logger.info("="*60)
        logger.info("BUILDING RELATIONSHIPS")
        logger.info("="*60)
        
        self._build_see_also_relationships()
        self._build_category_relationships()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Built {len(self.relationships)} relationships")
        logger.info(f"{'='*60}")
        
        return self.relationships
    
    def _build_see_also_relationships(self):
        logger.info("\nBuilding seeAlso relationships...")
        count = 0
        
        for alg in self.algorithms:
            alg_id = f"{alg['name']}-v{alg['version']}"
            see_also = alg.get('see_also', [])
            
            for related_name in see_also:
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
                    count += 1
        
        logger.info(f"  Created {count} see_also relationships")
    
    def _build_category_relationships(self):
        logger.info("\nBuilding category relationships...")
        
        category_groups = defaultdict(list)
        
        for alg in self.algorithms:
            alg_id = f"{alg['name']}-v{alg['version']}"
            categories = alg.get('categories', [])
            
            for category in categories:
                category_groups[category].append(alg_id)
        
        count = 0
        for category, alg_ids in category_groups.items():
            if 1 < len(alg_ids) <= 20:  # Only small categories
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
                        count += 1
        
        logger.info(f"  Created {count} same_category relationships")
    
    def _find_latest_version(self, algorithm_name: str) -> str:
        versions = []
        for alg_id, alg in self.algorithm_lookup.items():
            if alg['name'] == algorithm_name:
                versions.append((alg['version'], alg_id))
        
        if versions:
            versions.sort(reverse=True)
            return versions[0][1]
        
        return None
    
    def save_to_json(self, output_path: Path):
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [asdict(rel) for rel in self.relationships]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"\nSaved {len(self.relationships)} relationships to {output_path}")
        logger.info(f"File size: {size_mb:.2f} MB")
    
    def get_statistics(self) -> Dict[str, int]:
        stats = defaultdict(int)
        for rel in self.relationships:
            stats[rel.relationship_type] += 1
        return dict(stats)


if __name__ == '__main__':
    # Load algorithms
    with open('data/algorithms.json', 'r') as f:
        algorithms = json.load(f)
    
    logger.info(f"Loaded {len(algorithms)} algorithms\n")
    
    # Build relationships
    builder = RelationshipBuilder(algorithms)
    relationships = builder.build_all_relationships()
    builder.save_to_json(Path('data/relationships.json'))
    
    # Print statistics
    stats = builder.get_statistics()
    logger.info("\nRelationship statistics:")
    for rel_type, count in stats.items():
        logger.info(f"  {rel_type}: {count}")
