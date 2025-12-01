# GraphRAG Code Analysis System

A GraphRAG-style code analysis system that combines semantic retrieval, graph analysis, and LLM reasoning to answer questions about codebases. Includes fault detection, sensitive data tracking, and code understanding features.

## Prerequisites

- Python 3.11+
- Conda (for environment management)
- Joern installed and accessible in PATH
- Git (for GitHub repository cloning)
- Ollama (for RAG-based analysis features)
- Sufficient disk space for CPG files and model downloads
- GPU recommended (8GB+ VRAM) for LLM inference, but CPU works too

## Setup

1. **Create and activate conda environment:**
```bash
conda create -n graphrag python=3.11
conda activate graphrag
pip install -r requirements.txt
```

Or use the setup script:
```bash
./setup.sh
```

2. **Verify Joern installation:**
```bash
joern --version
joern-parse --version
```

3. **Start Ollama (for RAG analysis features):**
```bash
ollama serve
# Pull required models
ollama pull llama3.2
ollama pull nomic-embed-text
```

## Usage

### Original Query System (Semantic Search + Graph + LLM)

#### Step 1: Build CPG
```bash
# From GitHub repository (recommended)
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/project.cpg.bin --keep-clone

# From local directory
python scripts/build_cpg.py <source_dir> --output data/cpg/project.cpg.bin
```

#### Step 2: Extract Methods
```bash
python scripts/extract_methods.py data/cpg/project.cpg.bin --output data/methods.json
```

#### Step 3: Index Methods
```bash
python scripts/index_methods.py data/methods.json --project-name project
```

#### Step 4: Query
```bash
python scripts/query.py \
  --question "Where is the model training happening?" \
  --project-name project \
  --cpg-path data/cpg/project.cpg.bin
```

### New RAG-Based Analysis System

#### Step 1: Build CPG (same as above)
```bash
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/project.cpg.bin --keep-clone
```

#### Step 2: Extract CPG JSON
```bash
python scripts/extract_cpg_json.py data/cpg/project.cpg.bin --output cpg_rag_complete/data
```

#### Step 3: Setup RAG System
```bash
python cpg_rag_complete/step3_setup_rag.py --data-dir cpg_rag_complete/data --force
```

#### Step 4: Run Analysis
```bash
# Fault detection
python scripts/run_rag_analysis.py --analysis-type fault --query "Find security vulnerabilities"

# Sensitive data tracking
python scripts/run_rag_analysis.py --analysis-type sensitive --query "Track password handling"

# Code understanding
python scripts/run_rag_analysis.py --analysis-type understanding --query "Explain the architecture"
```

Or use the interactive query engine:
```bash
python cpg_rag_complete/step4_query_rag.py --interactive
```

## Web Interface (Streamlit)

### Running the Web Interface

1. **On a remote machine (via SSH):**
```bash
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
   - Click "Build CPG" to generate the Code Property Graph
   - For Query feature: Click "Extract Methods" then "Index Methods"
   - For RAG Analysis: CPG JSON is automatically extracted

2. **Query Tab (Original Feature):**
   - Enter your question about the codebase
   - Click "Generate Answer" to get the analysis

3. **Analysis Tab (RAG-Based Features):**
   - Select analysis type: Fault Detection, Sensitive Data Tracking, or Code Understanding
   - Enter your query
   - Click the respective button to run analysis

## Key Features

✅ **Open-source only**: No proprietary APIs  
✅ **GitHub support**: Build CPG directly from GitHub repositories  
✅ **Method-level indexing**: Efficient for large codebases  
✅ **Graph relationships**: Retrieves callers, callees, and types for context  
✅ **RAG-based analysis**: Fault detection, sensitive data tracking, code understanding  
✅ **Web interface**: Easy-to-use Streamlit frontend  

## Components

### Original Query System
- `scripts/build_cpg.py`: Build CPG from source or GitHub
- `scripts/extract_methods.py`: Extract methods from CPG
- `scripts/index_methods.py`: Index methods in ChromaDB
- `scripts/query.py`: Main query orchestrator

### RAG Analysis System
- `scripts/extract_cpg_json.py`: Extract CPG JSON
- `cpg_rag_complete/step3_setup_rag.py`: Setup RAG vector stores
- `cpg_rag_complete/step4_query_rag.py`: RAG query engine
- `scripts/run_rag_analysis.py`: Wrapper for RAG analysis

## Configuration

Edit `models/config.yaml` to customize:
- **Embedding model**: Default is `microsoft/graphcodebert-base`
- **LLM model**: Default is `Qwen/Qwen2.5-Coder-7B-Instruct`
- **Device**: CPU or CUDA
- **ChromaDB settings**: Persistence directory, collection names

For RAG system, edit `cpg_rag_complete/config.py`:
- **Ollama settings**: Model names, base URL
- **RAG settings**: Top K results, context depth

## Example Workflow

See `scripts/run_example.sh` for a complete example workflow.
