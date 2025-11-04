# Mantid RAG Database - Full Extraction Report

**Date:** 2025-11-04  
**Mantid Source:** /home/user/mantid  
**Extraction Method:** Direct source code analysis (no Mantid runtime required)

---

## 📊 Extraction Summary

### Files Generated

| File | Size | Records | Description |
|------|------|---------|-------------|
| `algorithms.json` | 309 KB | 625 | Algorithm metadata from C++/Python source |
| `docs.json` | 767 KB | 1,070 | RST documentation with usage examples |
| `relationships.json` | 654 KB | 2,994 | Algorithm relationship graph |
| **TOTAL** | **1.73 MB** | **4,689** | **Complete extraction data** |

---

## 🔍 Algorithm Extraction Details

### By Language
- **C++ Algorithms:** 423 (67.7%)
- **Python Algorithms:** 202 (32.3%)
- **Total:** 625 algorithms

### Metadata Extracted Per Algorithm
✅ Name  
✅ Version  
✅ Summary  
✅ Category (hierarchical)  
✅ See Also relationships  
✅ File path (C++/Python source)  
✅ Alias (if any)  
✅ Deprecated status  
✅ Workspace method name  
✅ Help URL  

### Source Coverage
- **C++ Header Files Scanned:** 863
- **C++ Algorithms Found:** 423 (49% hit rate)
- **Python Files Scanned:** 216
- **Python Algorithms Found:** 202 (94% hit rate)

### Duplicates Detected
- **8 duplicate name/version pairs** - likely different file locations for same algorithm

### Top 10 Categories
1. **Uncategorized:** 38
2. **DataHandling\\Text:** 36
3. **DataHandling\\Nexus:** 30
4. **Utility\\Workspaces:** 29
5. **SANS:** 23
6. **Crystal\\Peaks:** 20
7. **DataHandling\\Instrument:** 20
8. **Diffraction\\DataHandling:** 19
9. **Diffraction\\Reduction:** 16
10. **Transforms\\Masking:** 15

**Total Unique Categories:** 138

---

## 📚 Documentation Extraction Details

### RST Files Processed
- **Total RST files:** 1,070
- **Successfully parsed:** 1,070 (100%)
- **Errors:** 0

### Content Extracted
- **Documents with usage examples:** 213 (19.9%)
- **Total usage examples extracted:** 305
- **Average examples per document:** 0.3
- **Total references extracted:** 114

### Documentation Quality
- 👍 **High coverage:** 1,070 docs for 625 algorithms (1.7 docs per algorithm on average)
- 📝 **Some algorithms have multiple version docs** (explaining >1 ratio)
- 💡 **Usage examples in 20%** of documents
- 📖 **References in 11%** of documents

### Extraction Methods
- ✅ Regex-based extraction from RST source
- ✅ Code block detection (.. code-block:: python, .. testcode::)
- ✅ Description section extraction
- ✅ Reference/citation detection

---

## 🕸️ Relationship Graph Details

### Relationship Types

| Type | Count | Description |
|------|-------|-------------|
| **see_also** | 675 | Explicit "see also" connections from algorithm metadata |
| **same_category** | 2,319 | Algorithms in same category (limited to categories with 2-20 members) |
| **TOTAL** | **2,994** | **Total relationship edges** |

### Graph Statistics
- **Nodes (Algorithms):** 625
- **Edges (Relationships):** 2,994
- **Average connections per algorithm:** 4.8
- **Graph density:** Sparse (small categories only to avoid explosion)

### Relationship Extraction Logic
1. **See Also:** Direct extraction from `seeAlso()` method in source code
2. **Same Category:** Algorithms sharing the same category tag
   - **Constraint:** Only categories with 2-20 members (prevents massive cliques)
   - **Weight:** 0.3 (lower than see_also weight of 0.8)

### Future Relationship Types (Not Yet Implemented)
- ⏳ **Workspace flow:** Producer/consumer based on workspace types
- ⏳ **Deprecation chains:** REPLACES edges for deprecated algorithms  
- ⏳ **Common workflows:** Frequently used together (requires usage analysis)
- ⏳ **Child algorithms:** Parent algorithm calls child algorithms

---

## ✅ Data Quality Assessment

### Strengths
✅ **Complete coverage** - All header and Python files scanned  
✅ **No extraction errors** - 100% success rate  
✅ **Rich metadata** - 10+ fields per algorithm  
✅ **Comprehensive documentation** - 1070 docs extracted  
✅ **Strong relationships** - 2994 connections  

### Limitations
⚠️ **No runtime properties** - Didn't extract property details (name, type, direction, validators)  
⚠️ **Limited usage examples** - Only 20% of docs have examples  
⚠️ **No workspace type flow** - Need property analysis for producer/consumer relationships  
⚠️ **No performance data** - Didn't capture complexity or runtime characteristics  

### Why No Property Extraction?
Property extraction requires **Mantid runtime** (AlgorithmFactory.createUnmanaged + initialize()).  
Current extraction is **pure static analysis** of source files without running Mantid.

**Options for property extraction:**
1. ✅ Build Mantid and run extraction with Mantid Python API (ideal)
2. ⏳ Parse `init()` methods in C++ source (complex, error-prone)
3. ⏳ Extract from RST directive output (docs already have property tables)

---

## 📈 Estimated Database Sizes

Based on extracted data:

| Component | Estimated Size |
|-----------|----------------|
| **FAISS index** (625 algs × 4 embeddings × 384 dims) | ~3.7 MB |
| **SQLite database** (with all metadata) | ~5.0 MB |
| **NetworkX graph** (625 nodes + 2994 edges) | ~4.5 MB |
| **Total database** | **~13.2 MB** |

**Revision from earlier estimate (~20 MB for 1000 algs):**  
We have 625 algorithms, not 1000, so database will be smaller than initially estimated.

---

## 🎯 Next Steps

### Immediate (Ready Now)
1. ✅ **Generate embeddings** - Use sentence-transformers on extracted summaries
2. ✅ **Build FAISS index** - Create vector index with 4 embeddings per algorithm
3. ✅ **Populate SQLite** - Insert all metadata into structured database
4. ✅ **Create NetworkX graph** - Build relationship graph from extracted data

### Enhancement (Future)
5. ⏳ **Extract properties** - Requires Mantid runtime or RST parsing
6. ⏳ **Enhance relationships** - Add workspace flow, deprecation chains
7. ⏳ **Extract performance data** - Parse complexity comments, benchmarks
8. ⏳ **Add more examples** - Mine GitHub/forums for real-world usage

### Quality Improvement
9. ⏳ **Resolve duplicates** - Investigate 8 duplicate algorithms
10. ⏳ **Categorize "Uncategorized"** - 38 algorithms need categories
11. ⏳ **Extract more examples** - Improve from 20% to >50% coverage

---

## 🔬 Technical Details

### Extraction Tools
- **Language:** Python 3
- **Dependencies:** json, re, pathlib (stdlib only)
- **Execution time:** ~2 minutes total
- **No Mantid runtime required** ✅

### Extraction Scripts
1. `extraction/extract_all_algorithms.py` - C++/Python algorithm extraction
2. `extraction/parse_all_docs.py` - RST documentation parsing
3. `extraction/build_all_relationships.py` - Relationship graph building

### Data Format
- **Storage:** JSON (human-readable, versionable)
- **Encoding:** UTF-8
- **Structure:** List of dictionaries with consistent schema
- **Validation:** Dataclass-based with type hints

---

## 📝 Sample Data

### Sample Algorithm
```json
{
  "name": "FFTDerivative",
  "version": 1,
  "summary": "Calculated derivatives of a spectra in the MatrixWorkspace using...",
  "category": "Arithmetic\\FFT",
  "categories": ["Arithmetic", "FFT"],
  "see_also": ["ExtractFFTSpectrum", "FFT", "MaxEnt"],
  "file_path": "Framework/Algorithms/inc/MantidAlgorithms/FFTDerivative.h",
  "language": "cpp",
  "alias": "",
  "deprecated": false,
  "workspace_method_name": "",
  "help_url": ""
}
```

### Sample Documentation
```json
{
  "algorithm_name": "MaskDetectors",
  "version": 1,
  "rst_file": "docs/source/algorithms/MaskDetectors-v1.rst",
  "full_description": "The algorithm zeroes the data in the spectra of the input workspace...",
  "usage_examples": [],
  "references": []
}
```

### Sample Relationship
```json
{
  "from_algorithm": "FFTDerivative-v1",
  "to_algorithm": "ExtractFFTSpectrum-v1",
  "relationship_type": "see_also",
  "weight": 0.8,
  "metadata": {"source": "algorithm_metadata"}
}
```

---

## 🎉 Conclusion

**Successfully extracted comprehensive data for 625 Mantid algorithms!**

✅ **Ready for database building**  
✅ **No git lfs needed** (total <2 MB)  
✅ **High quality metadata**  
✅ **Comprehensive documentation**  
✅ **Rich relationship graph**  

The extracted data provides a solid foundation for building a high-quality RAG database.
