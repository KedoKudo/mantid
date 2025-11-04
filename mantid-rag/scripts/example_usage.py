#!/usr/bin/env python3
"""
Example usage of Mantid RAG database.

Demonstrates how to query the database and integrate with LLMs.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from query.retriever import MantidRAGRetriever
from query.llm_adapters import QwenAdapter, OllamaAdapter, create_mantid_rag_pipeline
from query.context_builder import ContextBuilder


def example_vector_search():
    """Example: Simple vector search."""
    print("=" * 60)
    print("Example 1: Vector Search")
    print("=" * 60)
    
    # Initialize retriever
    retriever = MantidRAGRetriever("6.10")
    
    # Search for algorithms
    query = "rebin my workspace to uniform bin widths"
    results = retriever.vector_search(query, top_k=3)
    
    print(f"\nQuery: {query}\n")
    for i, alg in enumerate(results, 1):
        print(f"{i}. {alg['name']} (v{alg['version']})")
        print(f"   Summary: {alg['summary']}")
        print(f"   Score: {alg['score']:.3f}\n")
    
    retriever.close()


def example_hybrid_search():
    """Example: Hybrid search with graph reranking."""
    print("=" * 60)
    print("Example 2: Hybrid Search")
    print("=" * 60)
    
    retriever = MantidRAGRetriever("6.10")
    
    query = "normalize my data"
    results = retriever.hybrid_search(query, top_k=5)
    
    print(f"\nQuery: {query}\n")
    for i, alg in enumerate(results, 1):
        print(f"{i}. {alg['name']} (v{alg['version']}) - Score: {alg['score']:.3f}")
        print(f"   Category: {alg['category']}")
        print(f"   {alg['summary'][:100]}...\n")
    
    retriever.close()


def example_workflow_discovery():
    """Example: Find workflow around an algorithm."""
    print("=" * 60)
    print("Example 3: Workflow Discovery")
    print("=" * 60)
    
    retriever = MantidRAGRetriever("6.10")
    
    # Get workflow suggestions
    workflow = retriever.get_workflow_suggestions("Rebin")
    
    print(f"\nWorkflow around: {workflow.get('algorithm', 'N/A')}\n")
    
    print("Commonly used BEFORE:")
    for alg in workflow.get('before', [])[:3]:
        print(f"  - {alg.get('name', 'N/A')}")
    
    print("\nCommonly used AFTER:")
    for alg in workflow.get('after', [])[:3]:
        print(f"  - {alg.get('name', 'N/A')}")
    
    retriever.close()


def example_with_qwen():
    """Example: Full RAG with Qwen (requires model)."""
    print("=" * 60)
    print("Example 4: RAG with Qwen")
    print("=" * 60)
    
    try:
        # Initialize components
        retriever = MantidRAGRetriever("6.10")
        llm = QwenAdapter("Qwen/Qwen2.5-7B-Instruct")
        
        # Create RAG pipeline
        query_fn = create_mantid_rag_pipeline(retriever, llm)
        
        # Ask question
        question = "How do I rebin my workspace to have uniform bin widths of 100?"
        print(f"\nQuestion: {question}\n")
        
        result = query_fn(question, top_k=2)
        
        print("Answer:")
        print(result['answer'])
        print("\n\nSources:")
        for alg in result['sources']:
            print(f"  - {alg['name']} (v{alg['version']})")
        
        retriever.close()
        
    except ImportError as e:
        print(f"Qwen model not available: {e}")
        print("Install with: pixi add transformers pytorch")
    except FileNotFoundError as e:
        print(f"Model not found: {e}")
        print("Download model or use Ollama adapter instead")


def example_with_ollama():
    """Example: RAG with Ollama (requires Ollama server)."""
    print("=" * 60)
    print("Example 5: RAG with Ollama")
    print("=" * 60)
    
    try:
        # Initialize components
        retriever = MantidRAGRetriever("6.10")
        llm = OllamaAdapter("qwen2.5:7b")
        
        # Create RAG pipeline
        query_fn = create_mantid_rag_pipeline(retriever, llm)
        
        # Ask question
        question = "Show me how to load a Nexus file and normalize it"
        print(f"\nQuestion: {question}\n")
        
        result = query_fn(question, top_k=3)
        
        print("Answer:")
        print(result['answer'])
        print("\n\nSources:")
        for alg in result['sources']:
            print(f"  - {alg['name']} (v{alg['version']})")
        
        retriever.close()
        
    except Exception as e:
        print(f"Ollama not available: {e}")
        print("Start Ollama server: ollama serve")
        print("Pull model: ollama pull qwen2.5:7b")


if __name__ == "__main__":
    # Run examples
    example_vector_search()
    print("\n\n")
    
    example_hybrid_search()
    print("\n\n")
    
    example_workflow_discovery()
    print("\n\n")
    
    # Uncomment to try LLM integration (requires models)
    # example_with_qwen()
    # example_with_ollama()
