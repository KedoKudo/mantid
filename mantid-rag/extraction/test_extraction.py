#!/usr/bin/env python3
"""
Test extraction script that works without Mantid installation.

This script extracts algorithm metadata from C++ header files
for testing purposes, without requiring a built Mantid installation.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class TestAlgorithmMetadata:
    """Simplified algorithm metadata for testing."""
    name: str
    version: int
    summary: str
    category: str
    categories: List[str]
    see_also: List[str]
    file_path: str
    language: str = 'cpp'
    properties: List = None
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = []


class TestExtractor:
    """Extract algorithm metadata from source files for testing."""
    
    def __init__(self, mantid_root: Path):
        """Initialize with Mantid repository root."""
        self.mantid_root = Path(mantid_root)
        self.algorithms_dir = self.mantid_root / "Framework" / "Algorithms"
        self.headers_dir = self.algorithms_dir / "inc" / "MantidAlgorithms"
    
    def extract_from_headers(self, max_algorithms: int = 50) -> List[TestAlgorithmMetadata]:
        """
        Extract metadata from C++ header files.
        
        Args:
            max_algorithms: Maximum number to extract (for testing)
            
        Returns:
            List of algorithm metadata
        """
        algorithms = []
        header_files = list(self.headers_dir.glob("*.h"))
        
        logger.info(f"Found {len(header_files)} header files")
        logger.info(f"Extracting up to {max_algorithms} for testing...")
        
        for header_file in header_files[:max_algorithms]:
            try:
                metadata = self.parse_header_file(header_file)
                if metadata:
                    algorithms.append(metadata)
                    logger.debug(f"Extracted: {metadata.name}")
            except Exception as e:
                logger.debug(f"Skipped {header_file.name}: {e}")
                continue
        
        logger.info(f"Successfully extracted {len(algorithms)} algorithms")
        return algorithms
    
    def parse_header_file(self, header_path: Path) -> Optional[TestAlgorithmMetadata]:
        """
        Parse a single header file to extract metadata.
        
        Args:
            header_path: Path to header file
            
        Returns:
            AlgorithmMetadata or None if not an algorithm
        """
        with open(header_path, 'r') as f:
            content = f.read()
        
        # Check if it's an algorithm class
        if 'class' not in content or ': public' not in content:
            return None
        
        # Extract class name (usually matches filename)
        class_name = header_path.stem
        
        # Extract name() method
        name_match = re.search(r'const std::string name\(\) const.*?return "(\w+)"', content, re.DOTALL)
        if not name_match:
            return None
        algorithm_name = name_match.group(1)
        
        # Extract version
        version_match = re.search(r'int version\(\) const.*?return (\d+)', content, re.DOTALL)
        version = int(version_match.group(1)) if version_match else 1
        
        # Extract summary
        summary_match = re.search(r'const std::string summary\(\) const.*?return "(.*?)"', content, re.DOTALL)
        summary = summary_match.group(1) if summary_match else "No summary available"
        summary = summary.replace('\\n', ' ').replace('\n', ' ').strip()
        
        # Extract category
        category_match = re.search(r'const std::string category\(\) const.*?return "(.*?)"', content, re.DOTALL)
        category = category_match.group(1) if category_match else "Uncategorized"
        
        # Split category into list
        categories = [cat.strip() for cat in category.split('\\')]
        if len(categories) == 1:
            categories = [cat.strip() for cat in category.split(';')]
        
        # Extract seeAlso
        see_also = []
        see_also_match = re.search(r'const std::vector<std::string> seeAlso\(\) const.*?\{(.*?)\}', content, re.DOTALL)
        if see_also_match:
            see_also_content = see_also_match.group(1)
            see_also_strings = re.findall(r'"(\w+)"', see_also_content)
            see_also = see_also_strings
        
        return TestAlgorithmMetadata(
            name=algorithm_name,
            version=version,
            summary=summary,
            category=category,
            categories=categories,
            see_also=see_also,
            file_path=str(header_path.relative_to(self.mantid_root)),
            language='cpp'
        )
    
    def save_to_json(self, algorithms: List[TestAlgorithmMetadata], output_path: Path):
        """Save extracted data to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [asdict(alg) for alg in algorithms]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(algorithms)} algorithms to {output_path}")
        
        # Print size info
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"File size: {size_mb:.2f} MB")


if __name__ == '__main__':
    import sys
    
    # Get Mantid root (parent of mantid-rag directory)
    mantid_rag_dir = Path(__file__).parent.parent
    mantid_root = mantid_rag_dir.parent
    
    logger.info(f"Mantid root: {mantid_root}")
    
    # Test with small sample first
    extractor = TestExtractor(mantid_root)
    
    # Extract 50 algorithms for testing
    logger.info("=== Testing with 50 algorithms ===")
    algorithms = extractor.extract_from_headers(max_algorithms=50)
    
    output_dir = mantid_rag_dir / "test_data"
    extractor.save_to_json(algorithms, output_dir / "test_algorithms_50.json")
    
    # Show sample
    if algorithms:
        logger.info("\n=== Sample Algorithm ===")
        sample = algorithms[0]
        logger.info(f"Name: {sample.name} v{sample.version}")
        logger.info(f"Category: {sample.category}")
        logger.info(f"Summary: {sample.summary[:100]}...")
        logger.info(f"See also: {sample.see_also}")
    
    # Estimate full size
    if algorithms:
        avg_size_per_alg = output_dir.stat().st_size / len(algorithms) if len(algorithms) > 0 else 0
        estimated_full_size = (avg_size_per_alg * 1000) / (1024 * 1024)
        logger.info(f"\n=== Size Estimates ===")
        logger.info(f"Estimated size for ~1000 algorithms: {estimated_full_size:.2f} MB (JSON only)")
