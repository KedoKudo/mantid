"""
Context builder for LLM prompts.

Formats retrieved algorithm information into structured context for LLMs.
"""

import json
from typing import List, Dict


class ContextBuilder:
    """Build LLM context from retrieved algorithms."""
    
    def build_context(self, algorithms: List[Dict], max_length: int = 4000) -> str:
        """
        Build formatted context from algorithms.
        
        Args:
            algorithms: List of algorithm dictionaries
            max_length: Maximum context length in characters
            
        Returns:
            Formatted context string
        """
        context_parts = []
        current_length = 0
        
        for idx, alg in enumerate(algorithms, 1):
            alg_context = self._format_algorithm(alg, index=idx)
            alg_length = len(alg_context)
            
            if current_length + alg_length > max_length and idx > 1:
                # Stop adding if we exceed max length (but include at least one)
                break
            
            context_parts.append(alg_context)
            current_length += alg_length
        
        return "\n\n".join(context_parts)
    
    def _format_algorithm(self, alg: Dict, index: int) -> str:
        """
        Format a single algorithm for context.
        
        Args:
            alg: Algorithm dictionary
            index: Index in results
            
        Returns:
            Formatted algorithm string
        """
        parts = [f"## Algorithm {index}: {alg['name']} (v{alg['version']})"]
        
        # Summary
        if alg.get('summary'):
            parts.append(f"**Summary**: {alg['summary']}")
        
        # Category
        if alg.get('category'):
            parts.append(f"**Category**: {alg['category']}")
        
        # Properties
        if alg.get('properties'):
            parts.append("\n**Properties**:")
            for prop in alg['properties'][:10]:  # Limit to 10 properties
                prop_line = f"- `{prop['name']}` ({prop['type']}, {prop['direction']})"
                if prop.get('description'):
                    prop_line += f": {prop['description'][:100]}"
                if not prop.get('optional', True):
                    prop_line += " [Required]"
                parts.append(prop_line)
        
        # Usage example from documentation
        if alg.get('documentation'):
            doc = alg['documentation']
            if doc.get('usage_examples'):
                try:
                    examples = json.loads(doc['usage_examples'])
                    if examples and len(examples) > 0:
                        parts.append("\n**Usage Example**:")
                        parts.append(f"```python\n{examples[0][:300]}\n```")
                except (json.JSONDecodeError, TypeError):
                    pass
        
        # Relevance score
        if alg.get('score') is not None:
            parts.append(f"\n*Relevance score: {alg['score']:.3f}*")
        
        parts.append("---")
        
        return "\n".join(parts)
    
    def build_workflow_context(self, algorithm: Dict, workflow_info: Dict) -> str:
        """
        Build context including workflow information.
        
        Args:
            algorithm: Main algorithm
            workflow_info: Workflow suggestions from graph
            
        Returns:
            Formatted workflow context
        """
        parts = [f"# {algorithm['name']} Workflow Context\n"]
        
        # Main algorithm
        parts.append(self._format_algorithm(algorithm, index=1))
        
        # Algorithms that come before
        if workflow_info.get('before'):
            parts.append("\n## Commonly Used Before:")
            for alg_data in workflow_info['before'][:3]:
                parts.append(f"- {alg_data.get('name', 'Unknown')}: {alg_data.get('summary', '')}")
        
        # Algorithms that come after
        if workflow_info.get('after'):
            parts.append("\n## Commonly Used After:")
            for alg_data in workflow_info['after'][:3]:
                parts.append(f"- {alg_data.get('name', 'Unknown')}: {alg_data.get('summary', '')}")
        
        return "\n".join(parts)
