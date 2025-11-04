#!/usr/bin/env python3
"""
Parse all RST documentation files for algorithms.

Extracts:
- Detailed descriptions
- Usage examples
- References
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class AlgorithmDocumentation:
    """Documentation for an algorithm."""
    algorithm_name: str
    version: int
    rst_file: str
    full_description: str
    usage_examples: List[str]
    references: List[str]


class DocumentationParser:
    """Parse Mantid algorithm RST documentation."""
    
    def __init__(self, mantid_root: Path):
        """Initialize parser."""
        self.mantid_root = Path(mantid_root)
        self.docs_dir = self.mantid_root / "docs" / "source" / "algorithms"
        self.errors = []
    
    def parse_all(self) -> List[AlgorithmDocumentation]:
        """Parse all RST files."""
        logger.info("="*60)
        logger.info("RST DOCUMENTATION PARSING")
        logger.info("="*60)
        
        if not self.docs_dir.exists():
            logger.error(f"Documentation directory not found: {self.docs_dir}")
            return []
        
        rst_files = list(self.docs_dir.glob("*-v*.rst"))
        logger.info(f"\nFound {len(rst_files)} RST files")
        logger.info("Parsing documentation...")
        
        docs = []
        for rst_file in rst_files:
            try:
                doc = self.parse_rst_file(rst_file)
                if doc:
                    docs.append(doc)
            except Exception as e:
                self.errors.append(f"{rst_file.name}: {str(e)}")
                logger.debug(f"  Error in {rst_file.name}: {e}")
        
        logger.info(f"\n{'='*60}")
        logger.info(f"Parsed {len(docs)} documentation files")
        if self.errors:
            logger.info(f"Errors: {len(self.errors)}")
        logger.info(f"{'='*60}")
        
        return docs
    
    def parse_rst_file(self, rst_path: Path) -> Optional[AlgorithmDocumentation]:
        """Parse a single RST file."""
        # Extract algorithm name and version from filename
        # Format: AlgorithmName-vX.rst
        filename = rst_path.stem
        match = re.match(r"(.+)-v(\d+)", filename)
        
        if not match:
            return None
        
        algorithm_name = match.group(1)
        version = int(match.group(2))
        
        # Read file
        with open(rst_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Extract description
        description = self.extract_description(content)
        
        # Extract usage examples
        examples = self.extract_usage_examples(content)
        
        # Extract references
        references = self.extract_references(content)
        
        # Get relative path
        try:
            rel_path = str(rst_path.relative_to(self.mantid_root))
        except ValueError:
            rel_path = str(rst_path)
        
        return AlgorithmDocumentation(
            algorithm_name=algorithm_name,
            version=version,
            rst_file=rel_path,
            full_description=description,
            usage_examples=examples,
            references=references
        )
    
    def extract_description(self, content: str) -> str:
        """Extract description from RST content."""
        # Find Description section
        desc_match = re.search(r'Description\s*\n[-=]+\s*\n(.*?)(?=\n\n[A-Z]|\nUsage|\Z)', content, re.DOTALL | re.IGNORECASE)
        
        if desc_match:
            description = desc_match.group(1).strip()
            # Limit to reasonable size
            if len(description) > 3000:
                description = description[:3000] + "..."
            return description
        
        # Fallback: get content after directives, before usage
        lines = content.split('\n')
        desc_lines = []
        in_description = False
        
        for line in lines:
            # Skip directive lines
            if line.strip().startswith('.. '):
                in_description = False
                continue
            
            # Skip property/metadata lines
            if line.strip().startswith(':'):
                continue
            
            # Start collecting non-empty lines
            if line.strip() and not line.strip().startswith('=') and not line.strip().startswith('-'):
                in_description = True
            
            if in_description:
                desc_lines.append(line)
                
                # Stop at Usage section
                if 'Usage' in line or 'usage' in line:
                    break
                
                # Limit length
                if len(desc_lines) > 50:
                    break
        
        return '\n'.join(desc_lines[:30]) if desc_lines else ""
    
    def extract_usage_examples(self, content: str) -> List[str]:
        """Extract Python usage examples."""
        examples = []
        
        # Find code blocks: .. code-block:: python, .. testcode::, etc.
        code_patterns = [
            r'\.\.\s+(?:code-block::\s+python|testcode::)\s*\n(.*?)(?=\n\.\.|(?=\n\n[^\s])|\Z)',
            r'\.\.\s+code::\s+python\s*\n(.*?)(?=\n\.\.|(?=\n\n[^\s])|\Z)'
        ]
        
        for pattern in code_patterns:
            matches = re.findall(pattern, content, re.DOTALL)
            for match in matches:
                # Clean up the code block
                lines = match.split('\n')
                # Remove common leading whitespace
                non_empty = [l for l in lines if l.strip()]
                if non_empty:
                    min_indent = min(len(l) - len(l.lstrip()) for l in non_empty if l.strip())
                    cleaned = [l[min_indent:] if len(l) > min_indent else l for l in lines]
                    code = '\n'.join(cleaned).strip()
                    if code and len(code) > 10:  # Ignore very short blocks
                        examples.append(code)
        
        # Also try to find usage examples in **Example** sections
        example_section = re.search(r'(?:Usage|Example)[s]?\s*\n[-=]+\s*\n(.*?)(?=\n\n[A-Z]|\Z)', content, re.DOTALL | re.IGNORECASE)
        if example_section:
            example_text = example_section.group(1)
            # Look for code in this section
            code_matches = re.findall(r'```python\n(.*?)```|`(.*?)`', example_text, re.DOTALL)
            for match in code_matches:
                code = match[0] if match[0] else match[1]
                if code and len(code.strip()) > 10:
                    examples.append(code.strip())
        
        # Deduplicate while preserving order
        seen = set()
        unique_examples = []
        for ex in examples:
            if ex not in seen:
                seen.add(ex)
                unique_examples.append(ex)
        
        return unique_examples[:5]  # Limit to first 5 examples
    
    def extract_references(self, content: str) -> List[str]:
        """Extract references and citations."""
        references = []
        
        # Find References section
        ref_match = re.search(r'(?:References?|Citations?)\s*\n[-=]+\s*\n(.*?)(?=\n\n[A-Z]|\Z)', content, re.DOTALL | re.IGNORECASE)
        
        if ref_match:
            ref_text = ref_match.group(1)
            # Extract lines that look like references
            lines = ref_text.split('\n')
            for line in lines:
                line = line.strip()
                # References often start with [, #, or contain DOI/arXiv
                if line and (line.startswith('[') or line.startswith('#') or 
                           'doi' in line.lower() or 'arxiv' in line.lower() or
                           'http' in line.lower()):
                    references.append(line)
        
        return references[:10]  # Limit to first 10 references
    
    def save_to_json(self, docs: List[AlgorithmDocumentation], output_path: Path):
        """Save documentation to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [asdict(doc) for doc in docs]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"\nSaved {len(docs)} documentation files to {output_path}")
        logger.info(f"File size: {size_mb:.2f} MB")
        
        # Statistics
        total_examples = sum(len(doc.usage_examples) for doc in docs)
        docs_with_examples = len([d for d in docs if d.usage_examples])
        total_refs = sum(len(doc.references) for doc in docs)
        
        logger.info(f"\nStatistics:")
        logger.info(f"  Documents with usage examples: {docs_with_examples}/{len(docs)}")
        logger.info(f"  Total usage examples: {total_examples}")
        logger.info(f"  Average examples per doc: {total_examples/len(docs):.1f}")
        logger.info(f"  Total references: {total_refs}")


if __name__ == '__main__':
    import sys
    
    # Get Mantid root
    mantid_rag_dir = Path(__file__).parent.parent
    mantid_root = mantid_rag_dir.parent
    
    logger.info(f"Mantid root: {mantid_root}\n")
    
    # Parse all
    parser = DocumentationParser(mantid_root)
    docs = parser.parse_all()
    
    # Save
    output_dir = mantid_rag_dir / "data"
    parser.save_to_json(docs, output_dir / "docs.json")
    
    # Show samples
    if docs:
        logger.info("\n" + "="*60)
        logger.info("SAMPLE DOCUMENTATION")
        logger.info("="*60)
        for i, doc in enumerate(docs[:3], 1):
            logger.info(f"\n{i}. {doc.algorithm_name} v{doc.version}")
            logger.info(f"   Description: {doc.full_description[:100]}...")
            logger.info(f"   Usage examples: {len(doc.usage_examples)}")
            logger.info(f"   References: {len(doc.references)}")
    
    sys.exit(0 if not parser.errors else 1)
