"""
Documentation parser for Mantid algorithm RST files.

This module parses the RST documentation files in the Mantid docs directory
to extract usage examples, detailed descriptions, and references.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
import click
from docutils.core import publish_doctree
from docutils.parsers.rst import Parser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AlgorithmDocumentation:
    """Documentation for a Mantid algorithm."""
    algorithm_name: str
    version: int
    rst_file: str
    full_description: str
    usage_examples: List[str]
    references: List[str]


class DocumentationParser:
    """Parse Mantid algorithm documentation from RST files."""
    
    def __init__(self, docs_dir: Path):
        """
        Initialize the documentation parser.
        
        Args:
            docs_dir: Path to Mantid docs directory
        """
        self.docs_dir = Path(docs_dir)
        self.algorithms_dir = self.docs_dir / "source" / "algorithms"
        
        if not self.algorithms_dir.exists():
            raise FileNotFoundError(f"Algorithms directory not found: {self.algorithms_dir}")
    
    def parse_all_documentation(self) -> List[AlgorithmDocumentation]:
        """
        Parse all algorithm RST files.
        
        Returns:
            List of AlgorithmDocumentation objects
        """
        docs = []
        rst_files = list(self.algorithms_dir.glob("*-v*.rst"))
        
        logger.info(f"Found {len(rst_files)} RST files")
        
        for rst_file in rst_files:
            try:
                doc = self.parse_documentation_file(rst_file)
                docs.append(doc)
            except Exception as e:
                logger.error(f"Failed to parse {rst_file.name}: {e}")
                continue
        
        logger.info(f"Successfully parsed {len(docs)} documentation files")
        return docs
    
    def parse_documentation_file(self, rst_file: Path) -> AlgorithmDocumentation:
        """
        Parse a single RST documentation file.
        
        Args:
            rst_file: Path to RST file
            
        Returns:
            AlgorithmDocumentation object
        """
        # Extract algorithm name and version from filename
        # Format: AlgorithmName-vX.rst
        filename = rst_file.stem
        match = re.match(r"(.+)-v(\d+)", filename)
        
        if not match:
            raise ValueError(f"Invalid RST filename format: {filename}")
        
        algorithm_name = match.group(1)
        version = int(match.group(2))
        
        # Read RST content
        with open(rst_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse RST to extract structured content
        full_description = self._extract_description(content)
        usage_examples = self._extract_usage_examples(content)
        references = self._extract_references(content)
        
        return AlgorithmDocumentation(
            algorithm_name=algorithm_name,
            version=version,
            rst_file=str(rst_file),
            full_description=full_description,
            usage_examples=usage_examples,
            references=references
        )
    
    def _extract_description(self, content: str) -> str:
        """
        Extract the main description from RST content.
        
        Args:
            content: RST file content
            
        Returns:
            Description text
        """
        # TODO: Implement RST parsing to extract description
        # For now, just return first paragraph after directives
        lines = content.split('\n')
        description_lines = []
        
        in_description = False
        for line in lines:
            # Skip directive lines
            if line.strip().startswith('.. '):
                in_description = False
                continue
            
            # Start collecting after we pass directives
            if not line.strip().startswith(':') and line.strip():
                in_description = True
            
            if in_description:
                description_lines.append(line)
                # Stop at next section or directive
                if line.strip().startswith('---') or line.strip().startswith('==='):
                    break
        
        return '\n'.join(description_lines[:20])  # Limit to first 20 lines
    
    def _extract_usage_examples(self, content: str) -> List[str]:
        """
        Extract Python usage examples from RST content.
        
        Args:
            content: RST file content
            
        Returns:
            List of code examples
        """
        examples = []
        
        # Find code blocks (.. code-block:: python or .. testcode::)
        code_block_pattern = r'\.\. (?:code-block:: python|testcode::)(.*?)(?=\n\.\. |\n\n[^\s]|\Z)'
        matches = re.findall(code_block_pattern, content, re.DOTALL)
        
        for match in matches:
            # Clean up indentation
            lines = match.split('\n')
            cleaned_lines = [line.strip() for line in lines if line.strip()]
            if cleaned_lines:
                examples.append('\n'.join(cleaned_lines))
        
        return examples
    
    def _extract_references(self, content: str) -> List[str]:
        """
        Extract references/citations from RST content.
        
        Args:
            content: RST file content
            
        Returns:
            List of references
        """
        references = []
        
        # Find references section
        # TODO: Implement more sophisticated reference extraction
        if 'References' in content or 'references' in content:
            # Simple extraction of lines after "References" header
            lines = content.split('\n')
            in_references = False
            for line in lines:
                if 'References' in line or 'references' in line:
                    in_references = True
                    continue
                if in_references:
                    if line.strip().startswith('.. [') or line.strip().startswith('['):
                        references.append(line.strip())
                    elif line.strip().startswith('===') or line.strip().startswith('---'):
                        break
        
        return references
    
    def save_to_json(self, docs: List[AlgorithmDocumentation], output_path: Path):
        """
        Save parsed documentation to JSON file.
        
        Args:
            docs: List of documentation objects
            output_path: Path to output JSON file
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = [asdict(doc) for doc in docs]
        
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved {len(docs)} documentation files to {output_path}")


@click.command()
@click.option('--mantid-docs', '-d', type=click.Path(exists=True), required=True,
              help='Path to Mantid docs directory')
@click.option('--output', '-o', type=click.Path(), default='data/docs.json',
              help='Output JSON file path')
@click.option('--verbose', '-v', is_flag=True, help='Verbose logging')
def main(mantid_docs: str, output: str, verbose: bool):
    """Parse Mantid algorithm documentation from RST files."""
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    parser = DocumentationParser(Path(mantid_docs))
    docs = parser.parse_all_documentation()
    parser.save_to_json(docs, Path(output))
    
    logger.info(f"Documentation parsing complete: {len(docs)} files")
    return 0


if __name__ == '__main__':
    main()
