# GraphRAG Code Analysis System

A GraphRAG-style code analysis system that combines semantic retrieval, graph analysis, and LLM reasoning to answer questions about codebases. Includes fault detection, sensitive data tracking, and code understanding features.

A code analysis system that combines semantic search (ChromaDB), graph analysis (Joern), and open-source LLMs to answer questions about large codebases.

## Architecture

1. **Preprocessing Phase**: 
   - Build CPG from source code using Joern
   - Extract method representations from CPG (with actual source code)
   - Embed methods and store in ChromaDB for semantic search

2. **Query Phase**: 
   - Semantic retrieval: Find relevant methods using vector search
   - Graph expansion: Use Joern to get callers, callees, and types
   - LLM reasoning: Combine code + graph context to answer questions

## Prerequisites

- Python 3.11+
- Conda (for environment management)
- Joern installed and accessible in PATH
- Git (for GitHub repository cloning)
- Sufficient disk space for CPG files and model downloads
- GPU recommended (8GB+ VRAM) for LLM inference, but CPU works too

## Setup

1. **Create and activate conda environment:**
```bash
conda create -n graphrag python=3.11
conda activate graphrag
pip install -r requirements.txt
```

2. **Verify Joern installation:**
```bash
joern --version
joern-parse --version
```

## Usage

### Phase 1: Preprocessing

1. **Build CPG from source code or GitHub repository:**
```bash
# From local directory
python scripts/build_cpg.py <source_dir> --output data/cpg/project.cpg.bin

# From GitHub repository
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/project.cpg.bin

# From GitHub with specific branch
python scripts/build_cpg.py https://github.com/user/repo --branch main --output data/cpg/project.cpg.bin

# From GitHub and keep the cloned directory (RECOMMENDED for source code extraction)
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/project.cpg.bin --keep-clone

# From GitHub with custom clone directory (keeps clone in specified location)
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/project.cpg.bin --clone-dir /path/to/clone/location --keep-clone

# From GitHub with specific branch and keep clone
python scripts/build_cpg.py https://github.com/user/repo --branch main --output data/cpg/project.cpg.bin --keep-clone
```

**Build CPG arguments:**
- `source` (required): Path to source code directory or GitHub repository URL
- `--output, -o` (required): Output path for the CPG file
- `--branch, -b`: Git branch or tag to checkout (for GitHub repos only)
- `--keep-clone`: Keep the cloned repository directory after building CPG (useful for source code extraction)
- `--clone-dir`: Directory to clone GitHub repo (default: temporary directory, deleted unless --keep-clone is used)

2. **Extract methods from CPG:**
```bash
# Automatically uses source code from cloned repo (if built from GitHub with --keep-clone)
# The source directory is auto-detected from .source_info.json file created during CPG build
python scripts/extract_methods.py data/cpg/project.cpg.bin --output data/methods.json

# Or specify source directory manually (if --keep-clone was not used)
python scripts/extract_methods.py data/cpg/project.cpg.bin --output data/methods.json --source-dir /path/to/source

# Skip source code enhancement (faster, but less accurate embeddings)
python scripts/extract_methods.py data/cpg/project.cpg.bin --output data/methods.json --no-enhance
```

**Extract methods arguments:**
- `cpg_path` (required): Path to CPG file (.cpg.bin)
- `--output, -o`: Output JSON file path (default: methods.json)
- `--source-dir`: Source directory to extract actual code from (auto-detected from .source_info.json if available)
- `--no-enhance`: Skip enhancing with source code even if source directory is available

3. **Index methods in ChromaDB (for query feature):**
```bash
python scripts/index_methods.py data/methods.json --project-name project
```

**Note:** For analysis features (fault detection, sensitive data tracking, code understanding), CPG JSON is automatically extracted when you build CPG. The files are saved to `cpg_rag_system/data/cpg_nodes.json` and `cpg_rag_system/data/cpg_edges.json`.

### Phase 2: Query or Analysis

**Query (Original Feature):**
```bash
python scripts/query.py \
  --question "Where is the model training happening?" \
  --project-name project \
  --cpg-path data/cpg/project.cpg.bin
```

**Fault Detection:**
```bash
python scripts/run_fault_detection.py \
  --nodes-json cpg_rag_system/data/cpg_nodes.json \
  --all \
  --format console
```

**Sensitive Data Tracking:**
```bash
python scripts/run_sensitive_data_tracking.py \
  --nodes-json cpg_rag_system/data/cpg_nodes.json \
  --edges-json cpg_rag_system/data/cpg_edges.json \
  --all \
  --format console
```

**Code Understanding:**
```bash
python scripts/run_code_understanding.py \
  --nodes-json cpg_rag_system/data/cpg_nodes.json \
  --edges-json cpg_rag_system/data/cpg_edges.json \
  --overview \
  --format console
```

**Query arguments:**
- `--question, -q` (required): Your question about the codebase
- `--project-name, -p` (required): Project name (must match what you used in indexing)
- `--cpg-path`: Path to CPG file (required for graph expansion - callers, callees, types)
- `--device`: Device for LLM and embeddings (`cpu` or `cuda`, default: `cpu`)
- `--top-k`: Number of methods to retrieve (default: 5)
- `--llm-model`: LLM model for reasoning (default: `Qwen/Qwen2.5-Coder-7B-Instruct`)
- `--embedding-model`: Embedding model for semantic search (default: `microsoft/graphcodebert-base`)
- `--chromadb-dir`: ChromaDB directory (default: `./data/chromadb`)
- `--dump-prompt`: Save the final prompt to a file for inspection
- `--no-llm`: Skip LLM reasoning, only show retrieved code and graph data

**Example questions:**
- "Where is the model training happening?"
- "Who calls the validation logic?"
- "Explain the code flow"
- "What does this file do?"
- "Explain where the test cases are called"
- "Explain the logic of the code"

## Components

- `scripts/build_cpg.py`: Wrapper for joern-parse to build CPG (supports local directories and GitHub repositories)
- `scripts/extract_methods.py`: Extract method representations from CPG with actual source code
- `scripts/index_methods.py`: Embed methods and store in ChromaDB
- `scripts/query.py`: Main query orchestrator (retrieval + graph + LLM)
- `joern_scripts/`: Scala scripts for Joern graph queries
  - `extract_methods.sc`: Extract all methods from CPG
  - `get_graph_neighborhood.sc`: Get callers, callees, types for a method
- `models/config.yaml`: Configuration for embedding and LLM models

## Configuration

Edit `models/config.yaml` to customize:
- **Embedding model**: Default is `microsoft/graphcodebert-base`
- **LLM model**: Default is `Qwen/Qwen2.5-Coder-7B-Instruct` (code-specialized, 7B parameters)
- **Device**: CPU or CUDA
- **ChromaDB settings**: Persistence directory, collection names

## Features

✅ **Open-source only**: No proprietary APIs (OpenAI, Anthropic, etc.)  
✅ **GitHub support**: Build CPG directly from GitHub repositories  
✅ **Method-level indexing**: Efficient for large codebases  
✅ **On-demand graph expansion**: Only query graph for retrieved methods  
✅ **Actual source code**: Uses real source code (not just Joern's internal representation) for better embeddings  
✅ **Graph relationships**: Retrieves callers, callees, and types for context  
✅ **Self-contained answers**: Answers don't reference prompt structure  
✅ **Flexible LLM choice**: Use any Hugging Face model  
✅ **GPU support**: Automatic GPU detection and fallback to CPU  
✅ **Fault Detection**: Identifies security vulnerabilities, missing error handling, and code quality issues  
✅ **Sensitive Data Tracking**: Tracks flow of sensitive data (passwords, API keys, PII)  
✅ **Code Understanding**: Generates high-level codebase structure, architecture, and entry points  

## Model Recommendations

**LLM Models (for reasoning):**
- **Qwen/Qwen2.5-Coder-7B-Instruct** (default): Best balance of performance and resource usage, code-specialized
- **Qwen/Qwen2.5-Coder-32B-Instruct**: Best performance, requires ~64GB GPU memory
- **mistralai/Mistral-7B-Instruct-v0.2**: Good general-purpose model
- **microsoft/phi-2**: Smallest (2.7B), fastest, but less capable

**Embedding Models:**
- **microsoft/graphcodebert-base** (default): Code-specialized embeddings
- **sentence-transformers/all-MiniLM-L6-v2**: Smaller, faster alternative

## Web Interface (Streamlit)

The system includes a Streamlit web interface for easy interaction:

### Running the Web Interface

1. **On a remote machine (via SSH):**
   ```bash
   # Run the Streamlit app
   ./run_streamlit.sh
   
   # Or specify a custom port
   ./run_streamlit.sh 8502
   ```

2. **Access from your local machine:**
   ```bash
   # Set up SSH port forwarding
   ssh -L 8501:localhost:8501 user@remote-machine
   
   # Then open in your browser
   http://localhost:8501
   ```

3. **Or run directly:**
   ```bash
   streamlit run app.py --server.port=8501 --server.address=0.0.0.0
   ```

### Using the Web Interface

1. **Setup Tab:**
   - Enter a GitHub repository URL or local path
   - Click "Build CPG" to generate the Code Property Graph (automatically extracts CPG JSON for analysis features)
   - Click "Extract Methods" to extract methods from the CPG (for query feature)
   - Click "Index Methods" to index methods in ChromaDB (for query feature)

2. **Query Tab (Original Feature):**
   - Enter your question about the codebase
   - Click "Generate Answer" to get the analysis
   - View the answer and full output

3. **Code Analysis Tab (New Features):**
   - Select analysis type: Fault Detection, Sensitive Data Tracking, or Code Understanding
   - Configure options (security-only, track type, mode)
   - Click the respective button to run analysis
   - View results in console, JSON, Markdown, or HTML format

### Configuration

The sidebar allows you to configure:
- **Device**: GPU (cuda) or CPU
- **Top K Methods**: Number of methods to retrieve (3-20)
- **LLM Model**: HuggingFace model for reasoning
- **Embedding Model**: HuggingFace model for embeddings

## Limitations

- First-time model downloads can be large (7B models ~14GB)
- LLM inference on CPU can be slow (consider GPU or smaller models)
- CPG files can be large for big codebases
- Graph queries require CPG file to be available
- Callers extraction works but may return module-level callers for Python

## Troubleshooting

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues and solutions.

## Documentation

- [QUICKSTART.md](QUICKSTART.md): Quick start guide
- [MODEL_UPGRADE.md](MODEL_UPGRADE.md): Information about model upgrades
- [RETRIEVAL_IMPROVEMENTS.md](RETRIEVAL_IMPROVEMENTS.md): Details on retrieval improvements
- [SOURCE_CODE_EXTRACTION.md](SOURCE_CODE_EXTRACTION.md): How source code extraction works
