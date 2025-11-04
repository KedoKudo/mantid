#!/usr/bin/env python3
"""
Full algorithm extraction from Mantid source code.

Extracts metadata from:
- C++ header files
- Python algorithm files
- RST documentation files
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class AlgorithmMetadata:
    """Complete algorithm metadata."""
    name: str
    version: int
    summary: str
    category: str
    categories: List[str]
    see_also: List[str]
    file_path: str
    language: str  # 'cpp' or 'python'
    alias: str = ""
    deprecated: bool = False
    workspace_method_name: str = ""
    help_url: str = ""


class FullExtractor:
    """Extract all algorithm metadata from Mantid source."""
    
    def __init__(self, mantid_root: Path):
        """Initialize with Mantid repository root."""
        self.mantid_root = Path(mantid_root)
        self.algorithms = []
        self.duplicates = defaultdict(list)
        self.errors = []
    
    def extract_all(self) -> List[AlgorithmMetadata]:
        """Extract from all sources."""
        logger.info("="*60)
        logger.info("FULL ALGORITHM EXTRACTION")
        logger.info("="*60)
        
        # 1. Extract from C++ headers
        logger.info("\n[1/2] Extracting from C++ headers...")
        cpp_algorithms = self.extract_cpp_algorithms()
        logger.info(f"  Found {len(cpp_algorithms)} C++ algorithms")
        
        # 2. Extract from Python files
        logger.info("\n[2/2] Extracting from Python algorithms...")
        python_algorithms = self.extract_python_algorithms()
        logger.info(f"  Found {len(python_algorithms)} Python algorithms")
        
        # Combine
        all_algorithms = cpp_algorithms + python_algorithms
        
        # Check for duplicates
        self.check_duplicates(all_algorithms)
        
        logger.info(f"\n{'='*60}")
        logger.info(f"TOTAL: {len(all_algorithms)} algorithms extracted")
        logger.info(f"  C++: {len(cpp_algorithms)}")
        logger.info(f"  Python: {len(python_algorithms)}")
        if self.duplicates:
            logger.info(f"  Duplicates: {len(self.duplicates)}")
        if self.errors:
            logger.info(f"  Errors: {len(self.errors)}")
        logger.info(f"{'='*60}")
        
        return all_algorithms
    
    def extract_cpp_algorithms(self) -> List[AlgorithmMetadata]:
        """Extract from C++ header files."""
        algorithms = []
        
        # Search in multiple framework directories
        search_paths = [
            "Framework/Algorithms/inc/MantidAlgorithms",
            "Framework/DataHandling/inc/MantidDataHandling",
            "Framework/MDAlgorithms/inc/MantidMDAlgorithms",
            "Framework/Crystal/inc/MantidCrystal",
            "Framework/CurveFitting/inc/MantidCurveFitting/Algorithms",
            "Framework/WorkflowAlgorithms/inc/MantidWorkflowAlgorithms",
            "Framework/ICat/inc/MantidICat",
            "Framework/LiveData/inc/MantidLiveData",
            "Framework/Reflectometry/inc/MantidReflectometry",
        ]
        
        header_files = []
        for search_path in search_paths:
            full_path = self.mantid_root / search_path
            if full_path.exists():
                headers = list(full_path.glob("*.h"))
                header_files.extend(headers)
                logger.debug(f"  {search_path}: {len(headers)} headers")
        
        logger.info(f"  Scanning {len(header_files)} header files...")
        
        for header_file in header_files:
            try:
                metadata = self.parse_cpp_header(header_file)
                if metadata:
                    algorithms.append(metadata)
            except Exception as e:
                self.errors.append(f"{header_file.name}: {str(e)}")
                logger.debug(f"  Error in {header_file.name}: {e}")
        
        return algorithms
    
    def parse_cpp_header(self, header_path: Path) -> Optional[AlgorithmMetadata]:
        """Parse a C++ header file."""
        with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Must be an algorithm class
        if not ': public' in content or 'Algorithm' not in content:
            return None
        
        # Extract name
        name_match = re.search(r'const std::string name\(\) const.*?return\s+"(\w+)"', content, re.DOTALL)
        if not name_match:
            return None
        algorithm_name = name_match.group(1)
        
        # Extract version
        version_match = re.search(r'int version\(\) const.*?return\s+(\d+)', content, re.DOTALL)
        version = int(version_match.group(1)) if version_match else 1
        
        # Extract summary
        summary_match = re.search(r'const std::string summary\(\) const.*?return\s+"(.*?)"', content, re.DOTALL)
        summary = summary_match.group(1) if summary_match else ""
        summary = summary.replace('\\n', ' ').replace('\n', ' ').strip()
        if not summary:
            summary = f"{algorithm_name} algorithm"
        
        # Extract category
        category_match = re.search(r'const std::string category\(\) const.*?return\s+"(.*?)"', content, re.DOTALL)
        category = category_match.group(1) if category_match else "Uncategorized"
        
        # Parse categories (can be delimited by \\ or ;)
        categories = [cat.strip() for cat in re.split(r'[\;]', category) if cat.strip()]
        if not categories:
            categories = [category]
        
        # Extract seeAlso
        see_also = []
        see_also_match = re.search(r'const std::vector<std::string>\s+seeAlso\(\)\s+const.*?\{(.*?)\}', content, re.DOTALL)
        if see_also_match:
            see_also_content = see_also_match.group(1)
            see_also = re.findall(r'"(\w+)"', see_also_content)
        
        # Extract alias
        alias = ""
        alias_match = re.search(r'const std::string alias\(\) const.*?return\s+"(.*?)"', content, re.DOTALL)
        if alias_match:
            alias = alias_match.group(1)
        
        # Check if deprecated
        deprecated = 'DeprecatedAlgorithm' in content or 'deprecated' in content.lower()
        
        # Extract workspace method name
        workspace_method = ""
        ws_method_match = re.search(r'const std::string workspaceMethodName\(\) const.*?return\s+"(.*?)"', content, re.DOTALL)
        if ws_method_match:
            workspace_method = ws_method_match.group(1)
        
        # Extract help URL
        help_url = ""
        help_match = re.search(r'const std::string helpURL\(\) const.*?return\s+"(.*?)"', content, re.DOTALL)
        if help_match:
            help_url = help_match.group(1)
        
        # Get relative path
        try:
            rel_path = str(header_path.relative_to(self.mantid_root))
        except ValueError:
            rel_path = str(header_path)
        
        return AlgorithmMetadata(
            name=algorithm_name,
            version=version,
            summary=summary,
            category=category,
            categories=categories,
            see_also=see_also,
            file_path=rel_path,
            language='cpp',
            alias=alias,
            deprecated=deprecated,
            workspace_method_name=workspace_method,
            help_url=help_url
        )
    
    def extract_python_algorithms(self) -> List[AlgorithmMetadata]:
        """Extract from Python algorithm files."""
        algorithms = []
        
        python_dir = self.mantid_root / "Framework/PythonInterface/plugins/algorithms"
        if not python_dir.exists():
            logger.warning(f"  Python algorithms directory not found: {python_dir}")
            return algorithms
        
        python_files = list(python_dir.glob("*.py"))
        logger.info(f"  Scanning {len(python_files)} Python files...")
        
        for py_file in python_files:
            try:
                metadata = self.parse_python_algorithm(py_file)
                if metadata:
                    algorithms.append(metadata)
            except Exception as e:
                self.errors.append(f"{py_file.name}: {str(e)}")
                logger.debug(f"  Error in {py_file.name}: {e}")
        
        return algorithms
    
    def parse_python_algorithm(self, py_path: Path) -> Optional[AlgorithmMetadata]:
        """Parse a Python algorithm file."""
        with open(py_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Must be a Python algorithm
        if 'PythonAlgorithm' not in content and 'DataProcessorAlgorithm' not in content:
            return None
        
        # Extract name from def name(self) or class name
        name_match = re.search(r'def\s+name\s*\(\s*self\s*\)\s*:.*?return\s+["\'](\w+)["\']', content, re.DOTALL)
        if not name_match:
            # Try class name
            class_match = re.search(r'class\s+(\w+)\s*\(', content)
            if not class_match:
                return None
            algorithm_name = class_match.group(1)
        else:
            algorithm_name = name_match.group(1)
        
        # Extract version
        version = 1
        version_match = re.search(r'def\s+version\s*\(\s*self\s*\)\s*:.*?return\s+(\d+)', content, re.DOTALL)
        if version_match:
            version = int(version_match.group(1))
        
        # Extract summary
        summary = ""
        summary_match = re.search(r'def\s+summary\s*\(\s*self\s*\)\s*:.*?return\s+["\'](.+?)["\']', content, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        if not summary:
            summary = f"{algorithm_name} algorithm"
        
        # Extract category
        category = "Uncategorized"
        category_match = re.search(r'def\s+category\s*\(\s*self\s*\)\s*:.*?return\s+["\'](.+?)["\']', content, re.DOTALL)
        if category_match:
            category = category_match.group(1)
        
        categories = [cat.strip() for cat in re.split(r'[\;]', category) if cat.strip()]
        if not categories:
            categories = [category]
        
        # Extract seeAlso
        see_also = []
        see_also_match = re.search(r'def\s+seeAlso\s*\(\s*self\s*\)\s*:.*?return\s+\[(.*?)\]', content, re.DOTALL)
        if see_also_match:
            see_also_content = see_also_match.group(1)
            see_also = re.findall(r'["\'](\w+)["\']', see_also_content)
        
        # Get relative path
        try:
            rel_path = str(py_path.relative_to(self.mantid_root))
        except ValueError:
            rel_path = str(py_path)
        
        return AlgorithmMetadata(
            name=algorithm_name,
            version=version,
            summary=summary,
            category=category,
            categories=categories,
            see_also=see_also,
            file_path=rel_path,
            language='python'
        )
    
    def check_duplicates(self, algorithms: List[AlgorithmMetadata]):
        """Check for duplicate algorithm names/versions."""
        seen = {}
        for alg in algorithms:
            key = f"{alg.name}-v{alg.version}"
            if key in seen:
                self.duplicates[key].append(alg)
                if key not in [d.name + f"-v{d.version}" for d in self.duplicates[key]]:
                    self.duplicates[key].insert(0, seen[key])
            else:
                seen[key] = alg
    
    def save_to_json(self, algorithms: List[AlgorithmMetadata], output_path: Path):
        """Save extracted data to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [asdict(alg) for alg in algorithms]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"\nSaved {len(algorithms)} algorithms to {output_path}")
        logger.info(f"File size: {size_mb:.2f} MB")
        
        # Save statistics
        stats_path = output_path.with_suffix('.stats.json')
        stats = {
            'total_algorithms': len(algorithms),
            'cpp_algorithms': len([a for a in algorithms if a.language == 'cpp']),
            'python_algorithms': len([a for a in algorithms if a.language == 'python']),
            'deprecated_count': len([a for a in algorithms if a.deprecated]),
            'duplicates': len(self.duplicates),
            'errors': len(self.errors),
            'categories': list(set(cat for alg in algorithms for cat in alg.categories)),
            'top_categories': self.get_top_categories(algorithms, top_n=10)
        }
        
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        logger.info(f"Saved statistics to {stats_path}")
    
    def get_top_categories(self, algorithms: List[AlgorithmMetadata], top_n: int = 10) -> Dict[str, int]:
        """Get most common categories."""
        category_counts = defaultdict(int)
        for alg in algorithms:
            for cat in alg.categories:
                category_counts[cat] += 1
        
        sorted_cats = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_cats[:top_n])


if __name__ == '__main__':
    import sys
    
    # Get Mantid root
    mantid_rag_dir = Path(__file__).parent.parent
    mantid_root = mantid_rag_dir.parent
    
    logger.info(f"Mantid root: {mantid_root}\n")
    
    # Extract all
    extractor = FullExtractor(mantid_root)
    algorithms = extractor.extract_all()
    
    # Save
    output_dir = mantid_rag_dir / "data"
    extractor.save_to_json(algorithms, output_dir / "algorithms.json")
    
    # Show samples
    if algorithms:
        logger.info("\n" + "="*60)
        logger.info("SAMPLE ALGORITHMS")
        logger.info("="*60)
        for i, alg in enumerate(algorithms[:5], 1):
            logger.info(f"\n{i}. {alg.name} v{alg.version} ({alg.language})")
            logger.info(f"   Category: {alg.category}")
            logger.info(f"   Summary: {alg.summary[:80]}...")
            if alg.see_also:
                logger.info(f"   See also: {', '.join(alg.see_also[:3])}")
    
    sys.exit(0 if not extractor.errors else 1)
