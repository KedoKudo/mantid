# Mantid RAG Database

A Retrieval-Augmented Generation (RAG) database system for Mantid algorithms, designed to enable intelligent code generation and algorithm discovery through semantic search and relationship graphs.

## Overview

This system extracts metadata from ~1000+ Mantid algorithms and builds a hybrid database combining:
- **FAISS** for vector similarity search (semantic queries)
- **SQLite** for structured metadata storage
- **NetworkX** for relationship graphs (workflow discovery)

## Features

- ✅ **Semantic Search**: Find algorithms by natural language description
- ✅ **Relationship Graphs**: Discover algorithm workflows and dependencies
- ✅ **Version Management**: Support for multiple Mantid versions
- ✅ **LLM-Agnostic**: Works with Qwen, Llama, GPT, Claude, or any LLM
- ✅ **Open Source**: All components use open-source models and libraries
- ✅ **Incremental Updates**: Tools to update database for new releases

## Architecture

```
User Query → Retriever (FAISS + SQLite + Graph) → Context Builder → LLM → Response
                    ↓
            [Vector Search]
            [SQL Filtering]
            [Graph Traversal]
```

## Project Structure

```
mantid-rag/
├── extraction/          # Extract data from Mantid installation
│   ├── extract_algorithms.py    # Algorithm metadata extraction
│   ├── parse_docs.py             # RST documentation parser
│   ├── build_relationships.py    # Relationship graph builder
│   └── extract_performance.py    # Performance metadata extraction
│
├── ingestion/           # Build database from extracted data
│   ├── build_database.py         # Main database builder
│   ├── generate_embeddings.py    # Vector embedding generation
│   ├── create_faiss_index.py     # FAISS index creation
│   └── create_graph.py           # NetworkX graph creation
│
├── query/               # Query interface for the database
│   ├── retriever.py              # Main retrieval interface
│   ├── hybrid_search.py          # Hybrid vector+graph search
│   ├── context_builder.py        # Build LLM context from results
│   └── llm_adapters.py           # LLM adapter interface
│
├── update/              # Tools for updating database
│   ├── incremental_update.py     # Update for new releases
│   └── version_manager.py        # Manage multiple versions
│
├── database/            # Database storage (gitignored)
│   ├── mantid_v{version}.db      # SQLite database
│   ├── mantid_v{version}.faiss   # FAISS vector index
│   └── mantid_v{version}_graph.pkl  # NetworkX graph
│
├── config/              # Configuration files
│   ├── config.yaml               # Main configuration
│   └── schema.sql                # SQLite schema
│
├── scripts/             # Utility scripts
│   ├── build_full_database.sh    # End-to-end database build
│   ├── test_retrieval.py         # Test retrieval quality
│   └── export_statistics.py      # Generate database statistics
│
├── tests/               # Unit tests
│   ├── test_extraction.py
│   ├── test_ingestion.py
│   ├── test_query.py
│   └── test_integration.py
│
├── docs/                # Documentation
│   ├── ARCHITECTURE.md           # System architecture
│   ├── DATABASE_SCHEMA.md        # Database schema details
│   ├── USAGE.md                  # Usage guide
│   └── API.md                    # API documentation
│
├── requirements.txt     # Python dependencies
├── setup.py            # Package installation
└── .gitignore          # Git ignore patterns
```

## Quick Start

### Prerequisites

Install [pixi](https://pixi.sh) if not already installed:
```bash
curl -fsSL https://pixi.sh/install.sh | bash
```

### Installation

```bash
# Clone repository (or copy files)
cd mantid-rag

# Install all dependencies (pixi handles everything)
pixi install

# Or install with specific environment
pixi install --environment dev     # Development tools
pixi install --environment gpu     # GPU acceleration
pixi install --environment full    # All features

# Verify installation
pixi run python -c "from sentence_transformers import SentenceTransformer; print('OK')"
```

### Build Database

```bash
# Extract data from Mantid installation
pixi run extract --output data/algorithms.json
pixi run parse-docs --mantid-docs /path/to/mantid/docs --output data/docs.json
pixi run build-relationships --input data/algorithms.json --output data/relationships.json

# Build database
pixi run build-db --version 6.10 --data-dir data/

# Or run the full pipeline at once
pixi run build-full --version 6.10

# This creates:
# - database/mantid_v6.10.db
# - database/mantid_v6.10.faiss
# - database/mantid_v6.10_graph.pkl
```

### Query Database

```python
from query.retriever import MantidRAGRetriever

# Initialize retriever
retriever = MantidRAGRetriever(mantid_version="6.10")

# Search for algorithms
results = retriever.search("rebin my workspace", top_k=5)

for result in results:
    print(f"{result['name']}: {result['summary']}")
    print(f"Score: {result['score']:.3f}\n")

# Get workflow suggestions
workflow = retriever.get_workflow_suggestions("Rebin")
print(f"Before: {workflow['before']}")
print(f"After: {workflow['after']}")
```

### Use with LLM (Qwen Example)

```python
from query.retriever import MantidRAGRetriever
from query.llm_adapters import QwenAdapter
from query.context_builder import ContextBuilder

# Set up components
retriever = MantidRAGRetriever("6.10")
llm = QwenAdapter("Qwen/Qwen2.5-7B-Instruct")
context_builder = ContextBuilder()

# User query
query = "How do I rebin my workspace to uniform bin widths?"

# Retrieve relevant algorithms
algorithms = retriever.search(query, top_k=3)

# Build context
context = context_builder.build_context(algorithms)

# Generate prompt
prompt = f"""<|im_start|>system
You are a Mantid algorithm expert. Use the provided documentation to answer questions.
<|im_end|>
<|im_start|>user
Documentation:
{context}

Question: {query}
<|im_end|>
<|im_start|>assistant
"""

# Generate response
response = llm.generate(prompt)
print(response)
```

## Database Schema

### SQLite Tables

- **algorithms**: Algorithm metadata (name, version, summary, category, etc.)
- **properties**: Algorithm properties (name, type, direction, description)
- **categories**: Category hierarchy
- **documentation**: Full documentation and usage examples
- **relationships**: Algorithm relationships (see_also, replaces, workflow)
- **workspace_types**: Workspace type compatibility
- **embeddings**: Mapping between FAISS IDs and algorithm IDs

### FAISS Index

- **Dimension**: 384 (for all-MiniLM-L6-v2) or 768 (for all-mpnet-base-v2)
- **Index Type**: IndexFlatIP (cosine similarity via inner product)
- **Vectors per Algorithm**: 4 (summary, properties, usage, full)

### NetworkX Graph

- **Nodes**: Algorithms with full metadata
- **Edges**:
  - `see_also`: Related algorithms
  - `replaces`: Deprecation chain
  - `common_workflow`: Frequently used together
  - `produces/consumes`: Workspace type flow

## Requirements

- Python 3.9-3.12
- Mantid installation (for extraction)
- ~500MB disk space per Mantid version
- 4GB RAM (for embedding generation)
- [pixi](https://pixi.sh) package manager

## Pixi Environments

The project supports multiple environments for different use cases:

- **default**: Core dependencies only (vector search, graph, embeddings)
- **dev**: Includes testing, linting, formatting tools
- **gpu**: GPU-accelerated FAISS and PyTorch
- **full**: All features including visualization and API server

```bash
# Use specific environment
pixi shell -e dev      # Activate dev environment
pixi run -e gpu test   # Run tests in GPU environment
```

## Pixi Tasks

Common tasks are defined in `pixi.toml`:

```bash
# Database building
pixi run extract              # Extract algorithm metadata
pixi run parse-docs           # Parse RST documentation
pixi run build-relationships  # Build relationship graph
pixi run build-db             # Build complete database
pixi run build-full           # Run full pipeline

# Testing
pixi run test                 # Run tests
pixi run test-cov             # Run tests with coverage
pixi run test-integration     # Integration tests only

# Code quality
pixi run format               # Format code with black
pixi run lint                 # Lint with ruff
pixi run typecheck            # Type check with mypy
pixi run check                # Run all checks

# Server (when server feature enabled)
pixi run serve                # Start API server

# Documentation
pixi run docs-stats           # Generate database statistics
pixi run docs-test            # Test retrieval quality
```

## Dependencies

Core dependencies (managed by pixi via conda-forge):

- `sentence-transformers`: Embedding generation
- `faiss-cpu`: Vector similarity search
- `networkx`: Graph algorithms
- `numpy`, `scipy`: Numerical operations
- `pytorch`: Deep learning framework
- `transformers`: LLM integration

## Version Support

- Each Mantid major release gets a separate database
- Example: `mantid_v6.10.db`, `mantid_v6.11.db`, etc.
- Query interface can load specific versions

## Performance

- **Extraction**: ~2-5 minutes for all algorithms
- **Embedding Generation**: ~5-10 minutes for ~1000 algorithms
- **Database Build**: ~1-2 minutes
- **Query Latency**: <100ms for search, <200ms for hybrid search

## Contributing

See `docs/CONTRIBUTING.md` for guidelines.

## License

This project follows Mantid's licensing (GPL v3).

## Contact

For questions or issues, contact the Mantid development team.
