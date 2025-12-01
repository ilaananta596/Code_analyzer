# CPG RAG Complete Pipeline

A complete, production-ready Code Property Graph (CPG) based Retrieval-Augmented Generation (RAG) system for intelligent security analysis of source code.

## 🎯 What This Does

Given any codebase, this system:
1. **Generates a CPG** using Joern (captures code structure and relationships)
2. **Extracts JSON** with proper deduplication and accurate line counts
3. **Creates vector stores** for semantic search (ChromaDB)
4. **Enables intelligent queries** using RAG with LLaMA

### Key Features
- ✅ **Proper Deduplication**: No duplicate methods for the same line number
- ✅ **Accurate Line Counts**: Correct total lines (not showing 6 lines for 15 modules)
- ✅ **Graph-Aware Analysis**: Understands call relationships and dependencies
- ✅ **Semantic Search**: Find code by meaning, not just keywords
- ✅ **LLM-Powered**: Intelligent security analysis using LLaMA
- ✅ **No Hallucination**: Grounded responses based only on actual code

## 📋 Prerequisites

### Required Software

1. **Python 3.10** (NOT 3.13 - has compatibility issues)
   ```bash
   # Using conda (recommended)
   conda create -n cpg-rag python=3.10
   conda activate cpg-rag
   ```

2. **Joern CLI** - For CPG generation
   ```bash
   # Download from https://joern.io/
   # Or use the install script:
   curl -L https://github.com/joernio/joern/releases/latest/download/joern-install.sh | bash
   unzip jeorn-cli.zip
   ```

3. **Ollama** - For LLM inference
   ```bash
   # Install Ollama
   curl -fsSL https://ollama.com/install.sh | sh
   
   # Start Ollama
   ollama serve
   
   # Pull required models
   ollama pull llama3.2
   ollama pull nomic-embed-text
   ```

### Python Dependencies

```bash
pip install -r requirements.txt
# If requirement.txt doesn't work please follow separate step to install joern.
```

## 🚀 Quick Start

### One-Command Pipeline

```bash
# Run the complete pipeline on your codebase
python run_pipeline.py /path/to/your/source/code --interactive
```
### If Joern error specify path 

```bash
python run_pipeline.py /path/to/your/source/code --joern-path ./joern-cli --interactive
```

This will:
1. Generate CPG from your source code
2. Extract methods with deduplication and accurate line counts
3. Create vector stores for semantic search
4. Launch interactive query mode

### Step-by-Step

```bash
# Step 1: Generate CPG
python step1_generate_cpg.py /path/to/source/code --output data/cpg.bin

# Step 2: Extract JSON (with deduplication)
python step2_extract_json.py data/cpg.bin --output data/ --source-dir /path/to/source/code

# Step 3: Setup RAG system
python step3_setup_rag.py --data-dir data/ --source-dir /path/to/source/code

# Step 4: Query!
python step4_query_rag.py --query "Find SQL injection vulnerabilities"
python step4_query_rag.py --interactive
python step4_query_rag.py --all --export md
```

## 📁 Project Structure

```
cpg_rag_complete/
├── config.py              # Central configuration
├── run_pipeline.py        # One-command complete pipeline
├── step1_generate_cpg.py  # Generate CPG from source code
├── step2_extract_json.py  # Extract JSON with deduplication
├── step3_setup_rag.py     # Setup vector stores
├── step4_query_rag.py     # Query interface
├── requirements.txt       # Python dependencies
├── .env.example           # Configuration template
├── data/                  # Generated data (created automatically)
│   ├── cpg.bin            # CPG binary
│   ├── cpg_nodes.json     # All CPG nodes
│   ├── cpg_edges.json     # All CPG edges
│   ├── methods.json       # Deduplicated methods
│   ├── calls.json         # Call relationships
│   └── codebase_stats.json # Statistics
├── chroma_db/             # Vector stores (created automatically)
└── output/                # Analysis reports (created automatically)
```

## 🔧 Configuration

Copy `.env.example` to `.env` and modify as needed:

```bash
cp .env.example .env
```

Key settings:
- `OLLAMA_MODEL`: LLM model for analysis (default: llama3.2)
- `OLLAMA_EMBEDDING_MODEL`: Embedding model (default: nomic-embed-text)
- `JOERN_CLI_PATH`: Path to Joern if not in PATH

## 📊 Usage Examples

### Security Vulnerability Detection

```bash
# Find all security issues
python step4_query_rag.py --all --export md

# Specific vulnerability queries
python step4_query_rag.py --query "Find SQL injection vulnerabilities"
python step4_query_rag.py --query "Find functions with potential buffer overflows"
python step4_query_rag.py --query "Find hardcoded credentials or API keys"
```

### Code Understanding

```bash
# Semantic search
python step4_query_rag.py --query "How does authentication work?" --type semantic

# Structure analysis
python step4_query_rag.py --query "Which functions have the most dependencies?" --type structural
```

### Interactive Mode

```bash
python step4_query_rag.py --interactive

# Then type queries:
# > Find functions that handle user input
# > What calls the database functions?
# > /type fault
# > Find resource leaks
```

### Export Reports

```bash
# JSON report
python step4_query_rag.py --all --export json

# Markdown report
python step4_query_rag.py --all --export md

# CSV for spreadsheets
python step4_query_rag.py --all --export csv
```

## 🔍 Understanding the Output

### Codebase Statistics (step2)

```
📊 CODEBASE STATISTICS (Accurate)
========================================
📁 Files: 234
🔧 Methods: 1,234 (deduplicated)
📝 Total Lines: 45,678

📈 By Language:
   Python: 189 files, 1,045 methods, 38,234 lines
   JavaScript: 45 files, 189 methods, 7,444 lines

🏆 Largest Methods:
   1. process_image_batch (main.py:456) - 234 lines
   2. train_model (ml.py:123) - 187 lines
   ...
```

### Query Results

```
❓ Question: Find SQL injection vulnerabilities

📊 Query type: fault
📚 Sources (5):
   - execute_query (database.py:45)
   - search_users (users.py:123)
   ...

📝 Answer:
- Function execute_query (database.py:45): Uses string formatting 
  to build SQL query with user input. No parameterized queries 
  detected. Called by: login_handler, api_endpoint, admin_panel.
  
- Function search_users (users.py:123): Concatenates user-provided 
  search term directly into SQL WHERE clause...
```

## ⚠️ Troubleshooting

### Issue: "joern-parse not found"

```bash
# Add Joern to PATH
export PATH=$PATH:/path/to/joern-cli

# Or specify path when running
python step1_generate_cpg.py source/ --joern-path /path/to/joern-cli
```

### Issue: "Ollama connection refused"

```bash
# Start Ollama service
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Issue: "No methods found" or wrong counts

Make sure to:
1. Run step2 with `--source-dir` for accurate line counting
2. The CPG file is not empty (check file size)
3. Your source files are in supported languages

```bash
# Verify CPG was created
ls -lh data/cpg.bin  # Should be > 1MB for real projects

# Check extracted stats
cat data/codebase_stats.json
```

### Issue: Python 3.13 compatibility

```bash
# Use Python 3.10 instead
conda create -n cpg-rag python=3.10
conda activate cpg-rag
pip install -r requirements.txt
```

### Issue: Duplicate methods in output

The pipeline automatically deduplicates methods. If you're seeing duplicates in raw Joern output, that's expected - step2 handles this.

Check the stats output:
```
🧹 Removed 1,266 duplicate methods
📊 2,500 → 1,234 methods
```

## 🏗️ Architecture

```
Source Code
    ↓
joern-parse → cpg.bin (Code Property Graph)
    ↓
step2_extract_json.py
    ├── Extract nodes/edges
    ├── Deduplicate methods
    ├── Calculate accurate line counts
    └── Generate statistics
    ↓
step3_setup_rag.py
    ├── Build graph index
    ├── Enrich methods (code, context, features)
    ├── Create embeddings (nomic-embed-text)
    └── Store in ChromaDB (3 collections)
    ↓
step4_query_rag.py
    ├── Semantic search (ChromaDB)
    ├── Context assembly
    ├── LLM analysis (LLaMA)
    └── Grounded, cited responses
```

## 📈 What Makes This Different

| Feature | Traditional Static Analysis | This RAG System |
|---------|----------------------------|-----------------|
| Analysis | Pattern matching | Semantic understanding |
| Context | Local only | Graph-aware (callers/callees) |
| Queries | Predefined rules | Natural language |
| Output | Rule violations | Explained vulnerabilities |
| Accuracy | Many false positives | Grounded, cited responses |

## 🔒 Security Analysis Capabilities

The system can detect:
- **Injection vulnerabilities**: SQL, command, XSS
- **Resource leaks**: Unclosed files, connections
- **Null pointer issues**: Missing null checks
- **Error handling**: Missing try/catch
- **Input validation**: Unvalidated user input
- **Unsafe operations**: eval(), exec(), pickle
- **Authentication issues**: Hardcoded credentials
- **Data flow**: Sensitive data exposure

## 📝 License

This system builds on:
- [Joern](https://joern.io) - CPG generation
- [LangChain](https://langchain.com) - RAG framework
- [Ollama](https://ollama.com) - LLM inference
- [ChromaDB](https://www.trychroma.com) - Vector database

## 🤝 Contributing

1. Test with different codebases
2. Report issues with specific error messages
3. Suggest new analysis capabilities
4. Improve documentation

---

**Remember**: This system works. The notebook proved it works. The pipeline follows the same proven approach. Don't overcomplicate it!
