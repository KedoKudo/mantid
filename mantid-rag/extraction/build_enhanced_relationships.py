#!/usr/bin/env python3
"""
Enhanced relationship builder with workspace flow and child algorithms.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Set
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


class EnhancedRelationshipBuilder:
    """Build comprehensive relationship graph."""
    
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
        logger.info("BUILDING ENHANCED RELATIONSHIPS")
        logger.info("="*60)
        
        # 1. See Also relationships
        self._build_see_also_relationships()
        
        # 2. Workspace flow (producer → consumer)
        self._build_workspace_flow_relationships()
        
        # 3. Child algorithm relationships
        self._build_child_algorithm_relationships()
        
        # 4. Deprecation chains
        self._build_deprecation_relationships()
        
        # 5. Category relationships (limited)
        self._build_category_relationships()
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Built {len(self.relationships)} total relationships")
        logger.info(f"{'='*60}")
        
        return self.relationships
    
    def _build_see_also_relationships(self):
        logger.info("\n[1/5] Building seeAlso relationships...")
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
    
    def _build_workspace_flow_relationships(self):
        logger.info("\n[2/5] Building workspace flow relationships...")
        
        # Group by workspace type
        producers = defaultdict(list)  # workspace_type -> [(alg_id, property_name)]
        consumers = defaultdict(list)  # workspace_type -> [(alg_id, property_name)]
        
        for alg in self.algorithms:
            alg_id = f"{alg['name']}-v{alg['version']}"
            
            for prop in alg.get('properties', []):
                prop_type = prop.get('type', 'Unknown')
                direction = prop.get('direction', 'Input')
                
                # Only track workspace properties
                if 'Workspace' in prop_type or prop_type == 'Unknown':
                    if direction == 'Output':
                        producers[prop_type].append((alg_id, prop['name']))
                    elif direction == 'Input':
                        consumers[prop_type].append((alg_id, prop['name']))
        
        # Create flow relationships
        count = 0
        for ws_type in producers:
            if ws_type in consumers:
                # Limit connections to avoid explosion
                max_connections = 50
                producer_list = producers[ws_type][:max_connections]
                consumer_list = consumers[ws_type][:max_connections]
                
                for prod_alg, prod_prop in producer_list:
                    for cons_alg, cons_prop in consumer_list:
                        if prod_alg != cons_alg:
                            rel = Relationship(
                                from_algorithm=prod_alg,
                                to_algorithm=cons_alg,
                                relationship_type='workspace_flow',
                                weight=0.6,
                                metadata={
                                    'workspace_type': ws_type,
                                    'output_property': prod_prop,
                                    'input_property': cons_prop
                                }
                            )
                            self.relationships.append(rel)
                            count += 1
        
        logger.info(f"  Created {count} workspace_flow relationships")
        logger.info(f"  Workspace types tracked: {len(producers)}")
    
    def _build_child_algorithm_relationships(self):
        logger.info("\n[3/5] Building child algorithm relationships...")
        count = 0
        
        for alg in self.algorithms:
            parent_id = f"{alg['name']}-v{alg['version']}"
            child_names = alg.get('child_algorithms', [])
            
            for child_name in child_names:
                child_id = self._find_latest_version(child_name)
                
                if child_id and child_id in self.algorithm_lookup:
                    rel = Relationship(
                        from_algorithm=parent_id,
                        to_algorithm=child_id,
                        relationship_type='calls_child',
                        weight=0.9,
                        metadata={'parent': parent_id, 'child': child_id}
                    )
                    self.relationships.append(rel)
                    count += 1
        
        logger.info(f"  Created {count} calls_child relationships")
    
    def _build_deprecation_relationships(self):
        logger.info("\n[4/5] Building deprecation relationships...")
        count = 0
        
        for alg in self.algorithms:
            if alg.get('deprecated', False):
                deprecated_id = f"{alg['name']}-v{alg['version']}"
                replacement_name = alg.get('deprecated_by', '')
                
                if replacement_name:
                    replacement_id = self._find_latest_version(replacement_name)
                    
                    if replacement_id and replacement_id in self.algorithm_lookup:
                        rel = Relationship(
                            from_algorithm=deprecated_id,
                            to_algorithm=replacement_id,
                            relationship_type='replaced_by',
                            weight=1.0,
                            metadata={'deprecated': deprecated_id, 'replacement': replacement_id}
                        )
                        self.relationships.append(rel)
                        count += 1
        
        logger.info(f"  Created {count} replaced_by relationships")
    
    def _build_category_relationships(self):
        logger.info("\n[5/5] Building category relationships...")
        
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
    # Load enhanced algorithms
    with open('data/algorithms_enhanced.json', 'r') as f:
        algorithms = json.load(f)
    
    logger.info(f"Loaded {len(algorithms)} algorithms\n")
    
    # Build relationships
    builder = EnhancedRelationshipBuilder(algorithms)
    relationships = builder.build_all_relationships()
    builder.save_to_json(Path('data/relationships_enhanced.json'))
    
    # Print statistics
    stats = builder.get_statistics()
    logger.info("\n" + "="*60)
    logger.info("RELATIONSHIP STATISTICS")
    logger.info("="*60)
    for rel_type, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {rel_type:20s}: {count:>6,}")
    
    total = sum(stats.values())
    logger.info(f"  {'─'*28}")
    logger.info(f"  {'TOTAL':20s}: {total:>6,}")
