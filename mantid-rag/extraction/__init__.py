"""
Extraction module for Mantid RAG database.

This module extracts algorithm metadata, documentation, and relationships
from a Mantid installation.
"""

from .extract_algorithms import AlgorithmExtractor
from .parse_docs import DocumentationParser
from .build_relationships import RelationshipBuilder

__all__ = [
    "AlgorithmExtractor",
    "DocumentationParser",
    "RelationshipBuilder",
]
