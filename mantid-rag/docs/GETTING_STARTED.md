# Getting Started with Mantid RAG Database

This guide will walk you through building and using the Mantid RAG database.

## Prerequisites

1. **Install pixi** (if not already installed):
   ```bash
   curl -fsSL https://pixi.sh/install.sh | bash
   ```

2. **Mantid installation** (for extraction phase)

## Step 1: Installation

```bash
cd mantid-rag

# Install all dependencies
pixi install

# Verify installation
pixi run python -c "import faiss, networkx, sentence_transformers; print('All dependencies OK')"
```

## Step 2: Extract Data from Mantid

You need to run the extraction scripts in a Mantid environment:

```bash
# Option A: If you have Mantid in your PATH
mantidpython -m extraction.extract_algorithms --output data/algorithms.json

# Option B: Use pixi with Mantid environment
pixi run extract --output data/algorithms.json
```

Extract documentation:
```bash
pixi run parse-docs --mantid-docs /path/to/mantid/docs --output data/docs.json
```

Build relationships:
```bash
pixi run build-relationships --input data/algorithms.json --output data/relationships.json
```

## Step 3: Build Database

Once you have the extracted data files:

```bash
pixi run build-db --version 6.10 --data-dir data/ --output-dir database/
```

This creates:
- `database/mantid_v6.10.db` - SQLite database
- `database/mantid_v6.10.faiss` - Vector index
- `database/mantid_v6.10_graph.pkl` - Relationship graph

Expected time: ~10-15 minutes for ~1000 algorithms

## Step 4: Query the Database

### Python API

```python
from query.retriever import MantidRAGRetriever

# Initialize
retriever = MantidRAGRetriever("6.10")

# Search for algorithms
results = retriever.search("rebin workspace", top_k=5)

for alg in results:
    print(f"{alg['name']}: {alg['summary']}")

retriever.close()
```

### With LLM (Qwen Example)

```python
from query.retriever import MantidRAGRetriever
from query.llm_adapters import QwenAdapter, create_mantid_rag_pipeline

# Set up
retriever = MantidRAGRetriever("6.10")
llm = QwenAdapter("Qwen/Qwen2.5-7B-Instruct")
query_fn = create_mantid_rag_pipeline(retriever, llm)

# Ask question
result = query_fn("How do I load and normalize a Nexus file?")
print(result['answer'])
print("Sources:", [alg['name'] for alg in result['sources']])
```

### With Ollama

```python
from query.llm_adapters import OllamaAdapter

# Make sure Ollama is running:
# ollama serve
# ollama pull qwen2.5:7b

llm = OllamaAdapter("qwen2.5:7b")
query_fn = create_mantid_rag_pipeline(retriever, llm)

result = query_fn("Show me how to rebin my data")
print(result['answer'])
```

## Step 5: Run Examples

```bash
pixi run python scripts/example_usage.py
```

## Common Tasks

### Update for New Mantid Release

```bash
# Extract data from new version
mantidpython -m extraction.extract_algorithms --output data/algorithms_v6.11.json

# Build new database
pixi run build-db --version 6.11 --data-dir data/

# Use new version
retriever = MantidRAGRetriever("6.11")
```

### Test Retrieval Quality

```bash
pixi run docs-test
```

### View Database Statistics

```bash
pixi run docs-stats
```

### Run Tests

```bash
pixi run test
```

### Code Formatting

```bash
pixi run format      # Format code
pixi run lint        # Check code quality
pixi run check       # Run all checks
```

## Troubleshooting

### "Mantid not available" Error

The extraction scripts require Mantid to be installed and accessible. Run them using `mantidpython` instead of regular Python.

### "Model not found" Error

Download the embedding model:
```python
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2')  # Downloads automatically
```

### FAISS Installation Issues

If you have a GPU:
```bash
pixi install --environment gpu
```

### Memory Issues During Build

Reduce batch size in `config/config.yaml`:
```yaml
embedding:
  batch_size: 16  # Reduce from 32
```

## Next Steps

1. **Read the architecture**: See `docs/ARCHITECTURE.md`
2. **Customize embedding model**: Edit `config/config.yaml`
3. **Add custom relationships**: Extend `extraction/build_relationships.py`
4. **Integrate with your application**: Use the query API
5. **Deploy as API server**: See `docs/DEPLOYMENT.md` (TODO)

## Getting Help

- Check the documentation in `docs/`
- Run `pixi run --help` to see available tasks
- Review example code in `scripts/example_usage.py`
- Report issues on GitHub

## Performance Tips

1. **Use hybrid search** for better results (combines vector + graph)
2. **Limit top_k** to 3-5 for focused answers
3. **Cache retriever instance** - don't recreate for every query
4. **Use GPU** if available for faster embedding generation
5. **Index frequently-used queries** in your application

## Advanced Usage

### Custom Embedding Model

```python
from ingestion.generate_embeddings import EmbeddingGenerator

generator = EmbeddingGenerator('all-mpnet-base-v2')  # Better quality
```

### Filter by Category

```python
# Query SQLite directly for category filtering
cursor = retriever.db.execute("""
    SELECT a.* FROM algorithms a
    JOIN algorithm_categories ac ON a.id = ac.algorithm_id
    JOIN categories c ON ac.category_id = c.id
    WHERE c.name LIKE '%Diffraction%'
""")
results = cursor.fetchall()
```

### Custom Prompt Templates

```python
from query.llm_adapters import QwenAdapter

llm = QwenAdapter("Qwen/Qwen2.5-7B-Instruct")

custom_prompt = llm.format_mantid_prompt(
    context=context,
    question=question,
    system_message="You are an expert in neutron scattering analysis..."
)

answer = llm.generate(custom_prompt)
```

Happy querying! 🚀
