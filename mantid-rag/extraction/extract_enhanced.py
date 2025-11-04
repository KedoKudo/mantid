#!/usr/bin/env python3
"""
Enhanced extraction with properties and child algorithm detection.
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class PropertyInfo:
    """Property information."""
    name: str
    type: str
    direction: str  # 'Input', 'Output', 'InOut'
    optional: bool = True
    description: str = ""


@dataclass
class AlgorithmMetadata:
    """Complete algorithm metadata with properties."""
    name: str
    version: int
    summary: str
    category: str
    categories: List[str]
    see_also: List[str]
    file_path: str
    language: str
    alias: str = ""
    deprecated: bool = False
    deprecated_by: str = ""  # Replacement algorithm
    workspace_method_name: str = ""
    help_url: str = ""
    properties: List[PropertyInfo] = field(default_factory=list)
    child_algorithms: List[str] = field(default_factory=list)


class EnhancedExtractor:
    """Enhanced extractor with property and child algorithm detection."""
    
    def __init__(self, mantid_root: Path):
        self.mantid_root = Path(mantid_root)
        self.algorithms = []
        self.errors = []
    
    def extract_all(self) -> List[AlgorithmMetadata]:
        """Extract from all sources."""
        logger.info("="*60)
        logger.info("ENHANCED ALGORITHM EXTRACTION")
        logger.info("="*60)
        
        # Extract C++ algorithms
        logger.info("\n[1/2] Extracting from C++ headers and source...")
        cpp_algorithms = self.extract_cpp_algorithms()
        logger.info(f"  Found {len(cpp_algorithms)} C++ algorithms")
        
        # Extract Python algorithms
        logger.info("\n[2/2] Extracting from Python algorithms...")
        python_algorithms = self.extract_python_algorithms()
        logger.info(f"  Found {len(python_algorithms)} Python algorithms")
        
        all_algorithms = cpp_algorithms + python_algorithms
        
        logger.info(f"\n{'='*60}")
        logger.info(f"TOTAL: {len(all_algorithms)} algorithms extracted")
        logger.info(f"  With properties: {len([a for a in all_algorithms if a.properties])}")
        logger.info(f"  With child algorithms: {len([a for a in all_algorithms if a.child_algorithms])}")
        logger.info(f"  Deprecated: {len([a for a in all_algorithms if a.deprecated])}")
        logger.info(f"{'='*60}")
        
        return all_algorithms
    
    def extract_cpp_algorithms(self) -> List[AlgorithmMetadata]:
        """Extract from C++ files."""
        algorithms = []
        
        search_paths = [
            "Framework/Algorithms",
            "Framework/DataHandling",
            "Framework/MDAlgorithms",
            "Framework/Crystal",
            "Framework/CurveFitting",
            "Framework/WorkflowAlgorithms",
            "Framework/ICat",
            "Framework/LiveData",
            "Framework/Reflectometry",
        ]
        
        for search_path in search_paths:
            header_dir = self.mantid_root / search_path / "inc"
            src_dir = self.mantid_root / search_path / "src"
            
            if not header_dir.exists():
                continue
                
            header_files = list(header_dir.rglob("*.h"))
            
            for header_file in header_files:
                try:
                    # Find corresponding .cpp file
                    cpp_file = src_dir / (header_file.stem + ".cpp")
                    
                    metadata = self.parse_cpp_algorithm(header_file, cpp_file if cpp_file.exists() else None)
                    if metadata:
                        algorithms.append(metadata)
                except Exception as e:
                    self.errors.append(f"{header_file.name}: {str(e)}")
                    logger.debug(f"  Error in {header_file.name}: {e}")
        
        return algorithms
    
    def parse_cpp_algorithm(self, header_path: Path, cpp_path: Optional[Path]) -> Optional[AlgorithmMetadata]:
        """Parse C++ algorithm with properties."""
        with open(header_path, 'r', encoding='utf-8', errors='ignore') as f:
            header_content = f.read()
        
        if not ': public' in header_content or 'Algorithm' not in header_content:
            return None
        
        # Extract basic metadata
        name_match = re.search(r'const std::string name\(\) const.*?return\s+"(\w+)"', header_content, re.DOTALL)
        if not name_match:
            return None
        algorithm_name = name_match.group(1)
        
        version_match = re.search(r'int version\(\) const.*?return\s+(\d+)', header_content, re.DOTALL)
        version = int(version_match.group(1)) if version_match else 1
        
        summary_match = re.search(r'const std::string summary\(\) const.*?return\s+"(.*?)"', header_content, re.DOTALL)
        summary = summary_match.group(1).replace('\\n', ' ').replace('\n', ' ').strip() if summary_match else f"{algorithm_name} algorithm"
        
        category_match = re.search(r'const std::string category\(\) const.*?return\s+"(.*?)"', header_content, re.DOTALL)
        category = category_match.group(1) if category_match else "Uncategorized"
        categories = [cat.strip() for cat in re.split(r'[\;]', category) if cat.strip()] or [category]
        
        see_also = []
        see_also_match = re.search(r'const std::vector<std::string>\s+seeAlso\(\)\s+const.*?\{(.*?)\}', header_content, re.DOTALL)
        if see_also_match:
            see_also = re.findall(r'"(\w+)"', see_also_match.group(1))
        
        alias = ""
        alias_match = re.search(r'const std::string alias\(\) const.*?return\s+"(.*?)"', header_content, re.DOTALL)
        if alias_match:
            alias = alias_match.group(1)
        
        # Check for deprecation
        deprecated = False
        deprecated_by = ""
        if 'DeprecatedAlgorithm' in header_content or 'deprecated' in header_content.lower():
            deprecated = True
            # Try to find replacement
            dep_match = re.search(r'(?:Use|use|replaced by|See)\s+(\w+)', header_content)
            if dep_match:
                deprecated_by = dep_match.group(1)
        
        workspace_method = ""
        ws_method_match = re.search(r'const std::string workspaceMethodName\(\) const.*?return\s+"(.*?)"', header_content, re.DOTALL)
        if ws_method_match:
            workspace_method = ws_method_match.group(1)
        
        help_url = ""
        help_match = re.search(r'const std::string helpURL\(\) const.*?return\s+"(.*?)"', header_content, re.DOTALL)
        if help_match:
            help_url = help_match.group(1)
        
        # Extract properties from .cpp file
        properties = []
        child_algorithms = []
        
        if cpp_path and cpp_path.exists():
            with open(cpp_path, 'r', encoding='utf-8', errors='ignore') as f:
                cpp_content = f.read()
            
            properties = self.extract_cpp_properties(cpp_content)
            child_algorithms = self.extract_child_algorithms_cpp(cpp_content)
        
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
            deprecated_by=deprecated_by,
            workspace_method_name=workspace_method,
            help_url=help_url,
            properties=properties,
            child_algorithms=child_algorithms
        )
    
    def extract_cpp_properties(self, cpp_content: str) -> List[PropertyInfo]:
        """Extract properties from C++ init() method."""
        properties = []
        
        # Find init() method
        init_match = re.search(r'void\s+\w+::init\s*\(\s*\)\s*\{(.*?)^\}', cpp_content, re.DOTALL | re.MULTILINE)
        if not init_match:
            return properties
        
        init_body = init_match.group(1)
        
        # Find declareProperty calls
        # Pattern: declareProperty("Name", ..., Direction::Input/Output)
        property_patterns = [
            r'declareProperty\s*\(\s*"(\w+)".*?Direction::(\w+)',
            r'declareProperty\s*\(\s*std::make_unique<.*?>\s*\(\s*"(\w+)".*?Direction::(\w+)',
        ]
        
        for pattern in property_patterns:
            matches = re.findall(pattern, init_body, re.DOTALL)
            for name, direction in matches:
                # Try to extract type (this is heuristic)
                prop_type = "Unknown"
                
                # Look for workspace properties
                if 'WorkspaceProperty' in init_body:
                    ws_match = re.search(rf'WorkspaceProperty<([^>]+)>\s*\(\s*"{name}"', init_body)
                    if ws_match:
                        prop_type = ws_match.group(1).strip()
                
                properties.append(PropertyInfo(
                    name=name,
                    type=prop_type,
                    direction=direction,
                    optional=True,  # Would need validator analysis to determine
                    description=""
                ))
        
        return properties
    
    def extract_child_algorithms_cpp(self, cpp_content: str) -> List[str]:
        """Extract child algorithm calls from C++ exec() method."""
        child_algs = set()
        
        # Find exec() method
        exec_match = re.search(r'void\s+\w+::exec\s*\(\s*\)\s*\{(.*?)^\}', cpp_content, re.DOTALL | re.MULTILINE)
        if not exec_match:
            return list(child_algs)
        
        exec_body = exec_match.group(1)
        
        # Pattern: createChildAlgorithm("AlgorithmName")
        child_matches = re.findall(r'createChildAlgorithm\s*\(\s*"(\w+)"', exec_body)
        child_algs.update(child_matches)
        
        # Pattern: AlgorithmManager::create("AlgorithmName")
        create_matches = re.findall(r'AlgorithmManager.*?create\w*\s*\(\s*"(\w+)"', exec_body)
        child_algs.update(create_matches)
        
        return list(child_algs)
    
    def extract_python_algorithms(self) -> List[AlgorithmMetadata]:
        """Extract from Python files."""
        algorithms = []
        
        python_dir = self.mantid_root / "Framework/PythonInterface/plugins/algorithms"
        if not python_dir.exists():
            return algorithms
        
        python_files = list(python_dir.glob("*.py"))
        
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
        """Parse Python algorithm with properties."""
        with open(py_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if 'PythonAlgorithm' not in content and 'DataProcessorAlgorithm' not in content:
            return None
        
        # Extract name
        name_match = re.search(r'def\s+name\s*\(\s*self\s*\)\s*:.*?return\s+["\'](\w+)["\']', content, re.DOTALL)
        if not name_match:
            class_match = re.search(r'class\s+(\w+)\s*\(', content)
            if not class_match:
                return None
            algorithm_name = class_match.group(1)
        else:
            algorithm_name = name_match.group(1)
        
        version = 1
        version_match = re.search(r'def\s+version\s*\(\s*self\s*\)\s*:.*?return\s+(\d+)', content, re.DOTALL)
        if version_match:
            version = int(version_match.group(1))
        
        summary = ""
        summary_match = re.search(r'def\s+summary\s*\(\s*self\s*\)\s*:.*?return\s+["\'](.+?)["\']', content, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        if not summary:
            summary = f"{algorithm_name} algorithm"
        
        category = "Uncategorized"
        category_match = re.search(r'def\s+category\s*\(\s*self\s*\)\s*:.*?return\s+["\'](.+?)["\']', content, re.DOTALL)
        if category_match:
            category = category_match.group(1)
        categories = [cat.strip() for cat in re.split(r'[\;]', category) if cat.strip()] or [category]
        
        see_also = []
        see_also_match = re.search(r'def\s+seeAlso\s*\(\s*self\s*\)\s*:.*?return\s+\[(.*?)\]', content, re.DOTALL)
        if see_also_match:
            see_also = re.findall(r'["\'](\w+)["\']', see_also_match.group(1))
        
        # Check for deprecation
        deprecated = 'deprecat' in content.lower()
        deprecated_by = ""
        if deprecated:
            dep_match = re.search(r'(?:Use|use|replaced by|See)\s+(\w+)', content)
            if dep_match:
                deprecated_by = dep_match.group(1)
        
        # Extract properties from PyInit()
        properties = self.extract_python_properties(content)
        
        # Extract child algorithms from PyExec()
        child_algorithms = self.extract_child_algorithms_python(content)
        
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
            language='python',
            deprecated=deprecated,
            deprecated_by=deprecated_by,
            properties=properties,
            child_algorithms=child_algorithms
        )
    
    def extract_python_properties(self, content: str) -> List[PropertyInfo]:
        """Extract properties from PyInit() method."""
        properties = []
        
        # Find PyInit method
        init_match = re.search(r'def\s+PyInit\s*\(\s*self\s*\)\s*:(.*?)(?=\n    def\s|\nclass\s|\Z)', content, re.DOTALL)
        if not init_match:
            return properties
        
        init_body = init_match.group(1)
        
        # Pattern: self.declareProperty("Name", ...)
        # Try to detect direction from context
        prop_matches = re.findall(r'self\.declareProperty\s*\(\s*["\'](\w+)["\']', init_body)
        
        for prop_name in prop_matches:
            # Try to determine direction from variable naming
            direction = "Input"
            if 'output' in prop_name.lower() or prop_name.startswith('Out'):
                direction = "Output"
            
            # Try to find WorkspaceProperty for type
            prop_type = "Unknown"
            ws_match = re.search(rf'(Matrix|Event|Table|Peaks)WorkspaceProperty\s*\(\s*["\']{ prop_name}["\']', init_body)
            if ws_match:
                prop_type = ws_match.group(1) + "Workspace"
            
            properties.append(PropertyInfo(
                name=prop_name,
                type=prop_type,
                direction=direction,
                optional=True,
                description=""
            ))
        
        return properties
    
    def extract_child_algorithms_python(self, content: str) -> List[str]:
        """Extract child algorithm calls from PyExec() method."""
        child_algs = set()
        
        # Find PyExec method
        exec_match = re.search(r'def\s+PyExec\s*\(\s*self\s*\)\s*:(.*?)(?=\n    def\s|\nclass\s|\Z)', content, re.DOTALL)
        if not exec_match:
            return list(child_algs)
        
        exec_body = exec_match.group(1)
        
        # Pattern: self.createChildAlgorithm("AlgorithmName")
        child_matches = re.findall(r'createChildAlgorithm\s*\(\s*["\'](\w+)["\']', exec_body)
        child_algs.update(child_matches)
        
        # Pattern: simpleapi calls (direct algorithm usage)
        # This is harder to detect reliably, skip for now
        
        return list(child_algs)
    
    def save_to_json(self, algorithms: List[AlgorithmMetadata], output_path: Path):
        """Save with custom serialization for PropertyInfo."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict with proper serialization
        data = []
        for alg in algorithms:
            alg_dict = asdict(alg)
            data.append(alg_dict)
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"\nSaved {len(algorithms)} algorithms to {output_path}")
        logger.info(f"File size: {size_mb:.2f} MB")


if __name__ == '__main__':
    mantid_rag_dir = Path(__file__).parent.parent
    mantid_root = mantid_rag_dir.parent
    
    logger.info(f"Mantid root: {mantid_root}\n")
    
    extractor = EnhancedExtractor(mantid_root)
    algorithms = extractor.extract_all()
    
    output_dir = mantid_rag_dir / "data"
    extractor.save_to_json(algorithms, output_dir / "algorithms_enhanced.json")
    
    # Show sample with properties
    if algorithms:
        logger.info("\n" + "="*60)
        logger.info("SAMPLE WITH PROPERTIES")
        logger.info("="*60)
        for alg in algorithms:
            if alg.properties and alg.child_algorithms:
                logger.info(f"\n{alg.name} v{alg.version} ({alg.language})")
                logger.info(f"  Properties: {len(alg.properties)}")
                for prop in alg.properties[:3]:
                    logger.info(f"    - {prop.name} ({prop.type}, {prop.direction})")
                if alg.child_algorithms:
                    logger.info(f"  Child algorithms: {', '.join(alg.child_algorithms[:5])}")
                break
