# Mantid RAG Database - Extraction Report

**Date:** 2025-11-04  
**Mantid Source:** /home/user/mantid  
**Method:** Static source code analysis (no Mantid runtime required)

---

## 📊 Final Results

### Algorithms Extracted: **632**
- **C++ Algorithms:** 430 (68%)
- **Python Algorithms:** 202 (32%)
- **With Properties:** 488 (77% coverage)
- **With Child Algorithms:** 99 (16%)
- **Deprecated:** 27 (4%)

### Documentation Parsed: **1,070 RST files**
- Usage examples: 305 (in 20% of docs)
- References: 114
- Success rate: 100%

### Relationships Built: **5,599**
- **workspace_flow:** 2,440 - Producer→Consumer based on workspace types
- **same_category:** 2,329 - Algorithms in same category
- **see_also:** 681 - Explicit metadata links
- **calls_child:** 149 - Parent→Child algorithm composition

---

## 📁 Generated Files

| File | Size | Content |
|------|------|---------|
| `algorithms.json` | 620 KB | 632 algorithms with properties |
| `docs.json` | 767 KB | 1,070 documentation files |
| `relationships.json` | 1.39 MB | 5,599 relationship edges |
| **Total** | **2.64 MB** | Complete extraction data |

---

## ✨ Key Features Extracted

### 1. Property Data (488 algorithms)
Extracted from `init()` / `PyInit()` methods:
- Property names
- Property types (where detectable)
- Directions (Input/Output/InOut)

### 2. Workspace Flow Relationships (2,440 edges)
Producer→Consumer relationships based on workspace I/O:
- Enables "what can I do with this output?" queries
- Tracks data flow through algorithm chains

### 3. Child Algorithm Calls (149 edges)
Parent→Child composition from `createChildAlgorithm()` calls:
- Reveals algorithm building blocks
- Shows workflow composition patterns

### 4. Category & Metadata Relationships (3,010 edges)
- See Also links from algorithm metadata
- Category-based groupings

---

## 🎯 Database Size Estimate

For 632 algorithms:
- **FAISS index:** ~3.8 MB
- **SQLite database:** ~6.0 MB
- **NetworkX graph:** ~7.0 MB
- **Total:** **~16.8 MB** (no git lfs needed!)

---

## 🚀 Usage

Run extraction:
```bash
pixi run extract-all
```

Output files (in data/, gitignored):
- `algorithms.json` - Algorithm metadata with properties
- `docs.json` - Documentation with usage examples  
- `relationships.json` - Relationship graph

All files are regeneratable from source code.
