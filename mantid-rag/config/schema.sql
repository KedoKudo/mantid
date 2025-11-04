-- SQLite schema for Mantid RAG database

-- Algorithm metadata
CREATE TABLE IF NOT EXISTS algorithms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    version INTEGER NOT NULL,
    summary TEXT,
    category TEXT,
    language TEXT,  -- 'cpp' or 'python'
    file_path TEXT,
    deprecated BOOLEAN DEFAULT 0,
    deprecated_by TEXT,
    alias TEXT,
    aliases_deprecated TEXT,
    workspace_method_name TEXT,
    workspace_method_input_property TEXT,
    help_url TEXT,
    mantid_version TEXT,  -- e.g., '6.10.0'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(name, version)
);

-- Properties
CREATE TABLE IF NOT EXISTS properties (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    direction TEXT CHECK(direction IN ('Input', 'Output', 'InOut')),
    optional BOOLEAN DEFAULT 0,
    default_value TEXT,
    description TEXT,
    validator_info TEXT,
    FOREIGN KEY (algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE
);

-- Categories
CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    parent_id INTEGER,
    FOREIGN KEY (parent_id) REFERENCES categories(id) ON DELETE SET NULL
);

-- Algorithm-Category mapping (many-to-many)
CREATE TABLE IF NOT EXISTS algorithm_categories (
    algorithm_id INTEGER NOT NULL,
    category_id INTEGER NOT NULL,
    PRIMARY KEY (algorithm_id, category_id),
    FOREIGN KEY (algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE,
    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
);

-- Documentation
CREATE TABLE IF NOT EXISTS documentation (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_id INTEGER NOT NULL UNIQUE,
    rst_file TEXT,
    full_description TEXT,
    usage_examples TEXT,  -- JSON array
    references TEXT,  -- JSON array
    FOREIGN KEY (algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE
);

-- Relationships (for quick SQL queries)
CREATE TABLE IF NOT EXISTS relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_algorithm_id INTEGER NOT NULL,
    to_algorithm_id INTEGER NOT NULL,
    relationship_type TEXT NOT NULL,  -- 'see_also', 'replaces', 'workspace_flow', etc.
    weight REAL DEFAULT 1.0,
    metadata TEXT,  -- JSON for additional info
    UNIQUE(from_algorithm_id, to_algorithm_id, relationship_type),
    FOREIGN KEY (from_algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE,
    FOREIGN KEY (to_algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE
);

-- Workspace types
CREATE TABLE IF NOT EXISTS workspace_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL
);

-- Algorithm input/output workspace types
CREATE TABLE IF NOT EXISTS algorithm_workspace_types (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_id INTEGER NOT NULL,
    workspace_type_id INTEGER NOT NULL,
    io_type TEXT CHECK(io_type IN ('input', 'output', 'inout')),
    UNIQUE(algorithm_id, workspace_type_id, io_type),
    FOREIGN KEY (algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE,
    FOREIGN KEY (workspace_type_id) REFERENCES workspace_types(id) ON DELETE CASCADE
);

-- Performance hints (optional)
CREATE TABLE IF NOT EXISTS performance_info (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    algorithm_id INTEGER NOT NULL UNIQUE,
    complexity TEXT,  -- e.g., 'O(n)', 'O(n log n)'
    is_workflow BOOLEAN DEFAULT 0,
    child_algorithm_count INTEGER DEFAULT 0,
    typical_runtime TEXT,  -- e.g., 'fast', 'slow', 'very_slow'
    notes TEXT,
    FOREIGN KEY (algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE
);

-- Embeddings metadata (maps FAISS IDs to algorithm IDs)
CREATE TABLE IF NOT EXISTS embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faiss_id INTEGER NOT NULL UNIQUE,
    algorithm_id INTEGER NOT NULL,
    embedding_type TEXT NOT NULL,  -- 'summary', 'properties', 'usage', 'full'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (algorithm_id) REFERENCES algorithms(id) ON DELETE CASCADE
);

-- Indexes for fast queries
CREATE INDEX IF NOT EXISTS idx_algorithm_name ON algorithms(name);
CREATE INDEX IF NOT EXISTS idx_algorithm_version ON algorithms(version);
CREATE INDEX IF NOT EXISTS idx_algorithm_category ON algorithms(category);
CREATE INDEX IF NOT EXISTS idx_algorithm_deprecated ON algorithms(deprecated);
CREATE INDEX IF NOT EXISTS idx_property_algorithm ON properties(algorithm_id);
CREATE INDEX IF NOT EXISTS idx_property_name ON properties(name);
CREATE INDEX IF NOT EXISTS idx_relationship_from ON relationships(from_algorithm_id);
CREATE INDEX IF NOT EXISTS idx_relationship_to ON relationships(to_algorithm_id);
CREATE INDEX IF NOT EXISTS idx_relationship_type ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_embedding_algorithm ON embeddings(algorithm_id);
CREATE INDEX IF NOT EXISTS idx_embedding_faiss_id ON embeddings(faiss_id);
CREATE INDEX IF NOT EXISTS idx_embedding_type ON embeddings(embedding_type);
