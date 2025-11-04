# Mantid RAG Database Architecture

## Overview

The Mantid RAG (Retrieval-Augmented Generation) database system is designed to enable intelligent code generation and algorithm discovery through a combination of vector similarity search, structured metadata queries, and relationship graphs.

## System Components

### 1. Extraction Layer (`extraction/`)

Extracts raw data from Mantid installation:

- **`extract_algorithms.py`**: Uses Mantid's `AlgorithmFactory` to extract metadata
  - Algorithm properties, categories, versions
  - Workspace method information
  - Deprecation status and aliases
  
- **`parse_docs.py`**: Parses RST documentation files
  - Usage examples
  - Detailed descriptions
  - References and citations
  
- **`build_relationships.py`**: Analyzes metadata to build relationships
  - `seeAlso` connections
  - Workspace type compatibility
  - Category-based groupings
  - Deprecation chains

### 2. Ingestion Layer (`ingestion/`)

Transforms extracted data into queryable formats:

- **`generate_embeddings.py`**: Creates vector embeddings
  - Uses sentence-transformers (all-MiniLM-L6-v2 by default)
  - Multiple embeddings per algorithm (summary, properties, usage, full)
  - Normalized vectors for cosine similarity
  
- **`create_faiss_index.py`**: Builds FAISS index
  - IndexFlatIP for exact similarity search
  - Maps FAISS IDs to algorithm IDs in SQLite
  
- **`create_graph.py`**: Creates NetworkX graph
  - Directed graph with weighted edges
  - Nodes contain full algorithm metadata
  - Edges represent relationships with types and weights
  
- **`build_database.py`**: Orchestrates complete database build
  - Creates SQLite database from schema
  - Coordinates embedding generation and indexing
  - Saves all components with version tracking

### 3. Query Layer (`query/`)

Provides unified interface for retrieval and LLM integration:

- **`retriever.py`**: Main retrieval interface
  - Vector search using FAISS
  - SQL queries for structured data
  - Graph traversal for relationships
  - Hybrid search combining all three
  
- **`llm_adapters.py`**: LLM integration adapters
  - Abstract base class for any LLM
  - Qwen adapter (local model via transformers)
  - Ollama adapter (API-based)
  - vLLM adapter (high-performance serving)
  
- **`context_builder.py`**: Formats context for LLMs
  - Structures retrieved algorithms
  - Limits context to max tokens
  - Includes examples and metadata
  
- **`hybrid_search.py`**: Advanced search strategies
  - Combines vector similarity with graph features
  - Re-ranks based on centrality
  - Boosts related algorithms

### 4. Update Layer (`update/`)

Tools for maintaining database across versions:

- **`incremental_update.py`**: Updates for new Mantid releases
- **`version_manager.py`**: Manages multiple database versions

## Data Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. EXTRACTION                                               │
│    Mantid Installation                                       │
│         │                                                    │
│         ├─> AlgorithmFactory ──> algorithms.json            │
│         ├─> RST Docs ──────────> docs.json                  │
│         └─> Analysis ───────────> relationships.json        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. INGESTION                                                 │
│    JSON Files                                                │
│         │                                                    │
│         ├─> SQLite Builder ──> mantid_vX.db                 │
│         ├─> Embedding Gen ───> embeddings                   │
│         │         │                                          │
│         │         └──> FAISS Builder ──> mantid_vX.faiss    │
│         └─> Graph Builder ──> mantid_vX_graph.pkl           │
└─────────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. QUERY                                                     │
│    User Question                                             │
│         │                                                    │
│         ├─> Retriever                                        │
│         │     ├─> FAISS Search ──> Vector similarity        │
│         │     ├─> SQL Query ────> Structured filtering      │
│         │     └─> Graph Walk ───> Relationships             │
│         │                │                                   │
│         │                └──> Top-K Algorithms               │
│         │                                                    │
│         ├─> Context Builder ──> Formatted context           │
│         │                                                    │
│         └─> LLM Adapter ──> Generated answer                │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### SQLite Tables

1. **algorithms**: Core metadata (name, version, summary, category)
2. **properties**: Algorithm parameters (name, type, direction, description)
3. **categories**: Hierarchical categorization
4. **documentation**: Full docs, usage examples, references
5. **relationships**: Algorithm connections (see_also, workflow, etc.)
6. **embeddings**: Maps FAISS IDs to algorithms
7. **workspace_types**: Workspace type compatibility
8. **performance_info**: Optional performance metadata

### FAISS Index

- **Type**: IndexFlatIP (cosine similarity)
- **Vectors**: Multiple per algorithm (summary, properties, usage, full)
- **Dimension**: 384 (all-MiniLM-L6-v2) or 768 (all-mpnet-base-v2)
- **Normalization**: L2-normalized for cosine via inner product

### NetworkX Graph

- **Type**: DiGraph (directed graph)
- **Nodes**: Algorithm ID (name-vX) with full metadata
- **Edges**: Typed relationships with weights
  - `see_also`: Explicit relationships (weight: 0.8)
  - `workspace_flow`: Compatible workspace types (weight: 0.5)
  - `same_category`: Shared categories (weight: 0.3)

## Search Strategies

### Vector Search

1. Encode query using sentence-transformer
2. Normalize query vector
3. Search FAISS index (inner product = cosine similarity)
4. Map FAISS IDs to algorithms via SQLite
5. Return top-K by similarity score

### Graph Search

1. Find algorithm node by name/version
2. Get predecessors (used before) and successors (used after)
3. Follow relationship edges with type filtering
4. Return related algorithms with relationship types

### Hybrid Search

1. Perform vector search for initial candidates (2x top-K)
2. Re-rank using graph features:
   - Boost by degree centrality
   - Boost if connected to other high-scoring results
3. Sort by combined score
4. Return top-K

## LLM Integration

### Adapter Pattern

Abstract `LLMAdapter` base class with implementations for:
- **QwenAdapter**: Hugging Face transformers (local)
- **OllamaAdapter**: Ollama API (local server)
- **VLLMAdapter**: vLLM API (high-performance)

All adapters provide:
- `generate(prompt, **kwargs)` -> str
- `get_model_info()` -> Dict

### RAG Pipeline

```python
question → retrieve(top_k=3) → [algorithms]
                                    │
                                    ▼
                          build_context() → formatted_context
                                    │
                                    ▼
                          format_prompt() → prompt_with_context
                                    │
                                    ▼
                          llm.generate() → answer
```

## Versioning Strategy

Each Mantid major release gets separate database files:

```
database/
  ├── mantid_v6.9.db
  ├── mantid_v6.9.faiss
  ├── mantid_v6.9_graph.pkl
  ├── mantid_v6.10.db
  ├── mantid_v6.10.faiss
  └── mantid_v6.10_graph.pkl
```

Retriever can load specific version:
```python
retriever = MantidRAGRetriever("6.10")
```

## Performance Characteristics

### Extraction (Mantid v6.10, ~1000 algorithms)
- Algorithm metadata: ~2-3 minutes
- Documentation parsing: ~1-2 minutes
- Relationship building: ~30 seconds

### Ingestion
- Embedding generation: ~5-10 minutes (CPU)
- FAISS index build: ~1 second
- SQLite population: ~30 seconds
- Total: ~10-15 minutes

### Query (Latency)
- Vector search: <50ms
- Hybrid search: <100ms
- Graph traversal: <10ms

### Storage (per version)
- SQLite database: ~50-100 MB
- FAISS index: ~5-10 MB (depends on dimension)
- NetworkX graph: ~10-20 MB
- Total: ~100-150 MB

## Scalability

### Current Scale (~1000 algorithms)
- FAISS: Exact search (IndexFlatIP)
- SQLite: All data in memory possible
- NetworkX: In-memory graph

### Future Scale (10,000+ algorithms)
- FAISS: Switch to IndexIVFFlat or IndexHNSWFlat
- SQLite: Add more indexes, consider connection pooling
- NetworkX: Consider graph database (Neo4j) if needed

## Extension Points

### Adding New Embedding Types
```python
# In generate_embeddings.py
def generate_algorithm_embeddings(alg, doc):
    # ... existing embeddings ...
    
    # Add custom embedding
    custom_text = extract_custom_features(alg)
    custom_emb = self.model.encode(custom_text)
    embeddings.append(('custom', custom_emb))
```

### Adding New Relationship Types
```python
# In build_relationships.py
def _build_custom_relationships(self):
    # Analyze algorithms
    # Create Relationship objects
    # Append to self.relationships
```

### Adding New LLM Adapters
```python
# In llm_adapters.py
class CustomLLMAdapter(LLMAdapter):
    def generate(self, prompt, **kwargs):
        # Implement generation
        pass
    
    def get_model_info(self):
        return {'model_type': 'custom', ...}
```

## Best Practices

### For Retrieval
1. Start with vector search for broad queries
2. Use hybrid search for better ranking
3. Use graph search for workflow discovery
4. Filter by category for domain-specific queries

### For Context Building
1. Limit to 3-5 algorithms for focused answers
2. Include usage examples when available
3. Prioritize properties for code generation
4. Add workflow context for multi-step tasks

### For LLM Integration
1. Use appropriate system messages for Mantid
2. Format prompts with clear sections
3. Include examples in context
4. Post-process code for syntax checking

## Monitoring & Debugging

### Logs
- All modules use Python logging
- Configure via config.yaml
- Set level to DEBUG for detailed output

### Statistics
```python
# Get database statistics
retriever = MantidRAGRetriever("6.10")
print(f"Vectors: {retriever.faiss_index.ntotal}")
print(f"Algorithms: {retriever.graph.number_of_nodes()}")
print(f"Relationships: {retriever.graph.number_of_edges()}")
```

### Testing Retrieval Quality
```bash
pixi run docs-test  # Runs test queries and reports metrics
```
