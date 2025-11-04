# Database Size Estimates

## Summary

Based on testing with 34 sample algorithms, we estimate the following sizes for a complete Mantid RAG database with ~1000 algorithms:

## Estimated Sizes (for 1000 algorithms)

### Raw Extraction Data (JSON)
- `algorithms.json`: ~0.4 MB
- `docs.json`: ~0.7 MB (with usage examples)
- `relationships.json`: ~0.1 MB
- **Total JSON**: ~1.2 MB

### Processed Database Files
- `mantid_vX.faiss`: ~5.9 MB (vector index, 4 embeddings/algorithm, 384 dimensions)
- `mantid_vX.db`: ~7.8 MB (SQLite with full metadata)
- `mantid_vX_graph.pkl`: ~6.8 MB (NetworkX relationship graph)
- **Total Database**: ~20.5 MB

### Grand Total
**~21.7 MB per Mantid version**

## Git LFS Decision

✅ **Git LFS is NOT needed**

The database files are well under 100 MB, making them manageable in a standard git repository.

**However, we recommend:**
1. Keep database files in `.gitignore` (already configured)
2. Users build databases locally using: `pixi run build-full`
3. Or distribute pre-built databases separately for convenience

## Why Not Commit Database Files?

Even though they're small enough:
1. **Regeneratable**: Can be built from source code
2. **Version-specific**: Each Mantid release needs its own database
3. **Binary files**: Not suitable for git diff/merge
4. **Build flexibility**: Users might want different embedding models

## Distribution Options

### Option 1: Build from Source (Recommended)
```bash
cd mantid-rag
pixi install
pixi run build-full --version 6.10
```

### Option 2: Pre-built Databases
Host pre-built databases separately:
- GitHub Releases (attach as release assets)
- Institutional file server
- Cloud storage (S3, Google Drive, etc.)

### Option 3: Git LFS (Optional)
If you decide to version databases in git:
```bash
git lfs install
git lfs track 'database/*.faiss'
git lfs track 'database/*.db'  
git lfs track 'database/*.pkl'
git add .gitattributes
```

## Scaling Estimates

| Algorithms | JSON | FAISS | SQLite | Graph | Total |
|------------|------|-------|--------|-------|-------|
| 100        | 0.1  | 0.6   | 0.8    | 0.7   | 2.2   |
| 500        | 0.6  | 3.0   | 3.9    | 3.4   | 10.9  |
| 1000       | 1.2  | 5.9   | 7.8    | 6.8   | 21.7  |
| 2000       | 2.4  | 11.8  | 15.6   | 13.6  | 43.4  |
| 5000       | 6.0  | 29.5  | 39.0   | 34.0  | 108.5 |

All sizes in MB.

## Test Results

Tested with:
- 34 algorithms extracted from C++ headers
- Embedding model: all-MiniLM-L6-v2 (384 dimensions)
- 4 embeddings per algorithm (summary, properties, usage, full)

Actual sizes will vary based on:
- Complexity of algorithm properties
- Length of documentation
- Number of relationships
- Embedding model choice

## Recommendations

1. **Keep `.gitignore` patterns** - Already configured ✓
2. **Build locally** - Fast (<15 min for 1000 algorithms)
3. **Document build process** - README has instructions ✓
4. **Consider CI/CD** - Auto-build databases for releases
5. **Test with pixi** - Use `pixi run build-full` in production

## Notes on Pixi

This project is designed to use **pixi** for dependency management, aligning with Mantid's migration from traditional conda to pixi.

Users should:
```bash
# Install pixi first
curl -fsSL https://pixi.sh/install.sh | bash

# Then use pixi for all operations
pixi install              # Install dependencies
pixi run extract         # Extract data
pixi run build-db        # Build database
```

The test scripts in this repository use regular Python for testing purposes, but **production builds should use pixi** as documented in README.md.

## Last Updated

2025-11-04 - Initial size estimates based on 34 sample algorithms
