# GraphRAG Code Analysis System

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

3. **Index methods in ChromaDB:**
```bash
python scripts/index_methods.py data/methods.json --project-name project

# With custom embedding model
python scripts/index_methods.py data/methods.json --project-name project --embedding-model microsoft/graphcodebert-base
```

### Phase 2: Query

**Basic query:**
```bash
python scripts/query.py \
  --question "Where is the model training happening?" \
  --project-name project \
  --cpg-path data/cpg/project.cpg.bin
```

**Full-featured query with all options:**
```bash
python scripts/query.py \
  --question "Who calls the validation logic?" \
  --project-name project \
  --cpg-path data/cpg/project.cpg.bin \
  --device cuda \
  --top-k 5 \
  --llm-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --dump-prompt prompts/query_prompt.txt
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

## Model Recommendations

**LLM Models (for reasoning):**
- **Qwen/Qwen2.5-Coder-7B-Instruct** (default): Best balance of performance and resource usage, code-specialized
- **Qwen/Qwen2.5-Coder-32B-Instruct**: Best performance, requires ~64GB GPU memory
- **mistralai/Mistral-7B-Instruct-v0.2**: Good general-purpose model
- **microsoft/phi-2**: Smallest (2.7B), fastest, but less capable

**Embedding Models:**
- **microsoft/graphcodebert-base** (default): Code-specialized embeddings
- **sentence-transformers/all-MiniLM-L6-v2**: Smaller, faster alternative

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
