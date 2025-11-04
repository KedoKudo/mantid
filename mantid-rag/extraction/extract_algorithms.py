"""
Algorithm metadata extraction from Mantid installation.

This module uses the Mantid API to extract comprehensive metadata from all
registered algorithms including properties, categories, and documentation.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import click

# Mantid imports (will be available when running in Mantid environment)
try:
    from mantid.api import AlgorithmFactory, AlgorithmManager, IAlgorithm
    from mantid.kernel import Direction
    MANTID_AVAILABLE = True
except ImportError:
    MANTID_AVAILABLE = False
    print("Warning: Mantid not available. Run this in a Mantid environment.")


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PropertyMetadata:
    """Metadata for an algorithm property."""
    name: str
    type: str
    direction: str  # 'Input', 'Output', 'InOut'
    optional: bool
    default_value: Optional[str]
    description: str
    validator_info: Optional[str]


@dataclass
class AlgorithmMetadata:
    """Complete metadata for a Mantid algorithm."""
    name: str
    version: int
    summary: str
    category: str
    categories: List[str]
    alias: str
    aliases_deprecated: str
    see_also: List[str]
    properties: List[PropertyMetadata]
    file_path: Optional[str]
    language: str  # 'cpp' or 'python'
    workspace_method_name: Optional[str]
    workspace_method_on: List[str]
    workspace_method_input_property: Optional[str]
    help_url: Optional[str]
    deprecated: bool


class AlgorithmExtractor:
    """Extract algorithm metadata from Mantid installation."""
    
    def __init__(self):
        """Initialize the extractor."""
        if not MANTID_AVAILABLE:
            raise RuntimeError("Mantid is not available. Cannot extract algorithms.")
        
        self.factory = AlgorithmFactory.Instance()
        self.algorithm_manager = AlgorithmManager.Instance()
    
    def extract_all_algorithms(self) -> List[AlgorithmMetadata]:
        """
        Extract metadata from all registered algorithms.
        
        Returns:
            List of AlgorithmMetadata objects
        """
        algorithms = []
        registered_names = self.factory.getRegisteredAlgorithms(True)
        
        logger.info(f"Found {len(registered_names)} unique algorithm names")
        
        for name in registered_names:
            versions = self.factory.getVersions(name)
            logger.info(f"Extracting {name} (versions: {versions})")
            
            for version in versions:
                try:
                    metadata = self.extract_algorithm_metadata(name, version)
                    algorithms.append(metadata)
                except Exception as e:
                    logger.error(f"Failed to extract {name} v{version}: {e}")
                    continue
        
        logger.info(f"Successfully extracted {len(algorithms)} algorithms")
        return algorithms
    
    def extract_algorithm_metadata(self, name: str, version: int) -> AlgorithmMetadata:
        """
        Extract metadata for a specific algorithm version.
        
        Args:
            name: Algorithm name
            version: Algorithm version
            
        Returns:
            AlgorithmMetadata object
        """
        # Create unmanaged algorithm instance
        alg = AlgorithmManager.createUnmanaged(name, version)
        alg.initialize()
        
        # Extract basic metadata
        metadata = AlgorithmMetadata(
            name=alg.name(),
            version=alg.version(),
            summary=alg.summary(),
            category=alg.category(),
            categories=alg.categories(),
            alias=alg.alias(),
            aliases_deprecated=alg.aliasDeprecated(),
            see_also=alg.seeAlso(),
            properties=self.extract_properties(alg),
            file_path=self._get_algorithm_file_path(alg),
            language=self._detect_language(alg),
            workspace_method_name=alg.workspaceMethodName() if alg.workspaceMethodName() else None,
            workspace_method_on=alg.workspaceMethodOn(),
            workspace_method_input_property=alg.workspaceMethodInputProperty() if alg.workspaceMethodInputProperty() else None,
            help_url=alg.helpURL() if alg.helpURL() else None,
            deprecated=bool(alg.aliasDeprecated())
        )
        
        return metadata
    
    def extract_properties(self, alg: IAlgorithm) -> List[PropertyMetadata]:
        """
        Extract property metadata from an algorithm.
        
        Args:
            alg: Initialized algorithm instance
            
        Returns:
            List of PropertyMetadata objects
        """
        properties = []
        
        for prop in alg.getProperties():
            # Determine direction
            if prop.direction == Direction.Input:
                direction = "Input"
            elif prop.direction == Direction.Output:
                direction = "Output"
            elif prop.direction == Direction.InOut:
                direction = "InOut"
            else:
                direction = "Unknown"
            
            # Get validator info if available
            validator_info = None
            if hasattr(prop, 'getValidator') and prop.getValidator():
                validator_info = str(prop.getValidator())
            
            property_meta = PropertyMetadata(
                name=prop.name,
                type=prop.type,
                direction=direction,
                optional=not prop.isValid().strip() == "",  # Check if property has default
                default_value=prop.valueAsStr if prop.valueAsStr else None,
                description=prop.documentation if hasattr(prop, 'documentation') else "",
                validator_info=validator_info
            )
            properties.append(property_meta)
        
        return properties
    
    def _get_algorithm_file_path(self, alg: IAlgorithm) -> Optional[str]:
        """
        Try to determine the source file path for an algorithm.
        
        Args:
            alg: Algorithm instance
            
        Returns:
            File path if determinable, None otherwise
        """
        # TODO: Implement file path detection
        # This might require inspecting __file__ attribute for Python algorithms
        # or using debug symbols for C++ algorithms
        return None
    
    def _detect_language(self, alg: IAlgorithm) -> str:
        """
        Detect whether algorithm is C++ or Python.
        
        Args:
            alg: Algorithm instance
            
        Returns:
            'cpp' or 'python'
        """
        # Check if it's a Python algorithm
        alg_type = type(alg).__name__
        if 'Python' in alg_type:
            return 'python'
        return 'cpp'
    
    def save_to_json(self, algorithms: List[AlgorithmMetadata], output_path: Path):
        """
        Save extracted algorithms to JSON file.
        
        Args:
            algorithms: List of algorithm metadata
            output_path: Path to output JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict for JSON serialization
        data = [asdict(alg) for alg in algorithms]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(algorithms)} algorithms to {output_path}")


@click.command()
@click.option('--output', '-o', type=click.Path(), default='data/algorithms.json',
              help='Output JSON file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def main(output: str, verbose: bool):
    """Extract algorithm metadata from Mantid installation."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not MANTID_AVAILABLE:
        logger.error("Mantid is not available. Please run in Mantid environment.")
        return 1
    
    extractor = AlgorithmExtractor()
    algorithms = extractor.extract_all_algorithms()
    extractor.save_to_json(algorithms, Path(output))
    
    logger.info(f"Extraction complete: {len(algorithms)} algorithms")
    return 0


if __name__ == '__main__':
    main()
