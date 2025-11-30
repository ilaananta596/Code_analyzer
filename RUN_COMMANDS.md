# Commands to Run the GraphRAG Application

## Quick Start - Run Streamlit App

### Option 1: Using the provided script (Recommended)
```bash
cd /home/nidhi/Ila/ai
./run_streamlit.sh
```

Or specify a custom port:
```bash
./run_streamlit.sh 8502
```

### Option 2: Manual activation and run
```bash
cd /home/nidhi/Ila/ai
source activate_graphrag.sh
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

### Option 3: Direct Python command
```bash
cd /home/nidhi/Ila/ai
source activate_graphrag.sh
python -m streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

---

## Access the Application

### If running locally:
Open in browser: `http://localhost:8501`

### If running on remote machine via SSH:
1. Set up SSH port forwarding (on your local machine):
   ```bash
   ssh -L 8501:localhost:8501 user@remote-machine
   ```

2. Open in browser: `http://localhost:8501`

---

## Test Analysis Commands Directly

You can also test the analysis features directly from command line:

### 1. Extract CPG JSON (Required First Step)
```bash
cd /home/nidhi/Ila/ai
source activate_graphrag.sh

# Extract CPG nodes and edges from CPG binary
# This creates cpg_rag_system/data/cpg_nodes.json and cpg_rag_system/data/cpg_edges.json
python scripts/extract_cpg_json.py data/cpg/medsam.cpg.bin

# Or specify custom output directory
python scripts/extract_cpg_json.py data/cpg/medsam.cpg.bin --output cpg_rag_system/data
```

### 2. Fault Detection
```bash
cd /home/nidhi/Ila/ai
source activate_graphrag.sh

# Run fault detection on CPG nodes (uses cpg_rag_system/data/cpg_nodes.json by default)
python scripts/run_fault_detection.py --all

# Security issues only
python scripts/run_fault_detection.py --security

# Use custom nodes file
python scripts/run_fault_detection.py --nodes-json cpg_rag_system/data/cpg_nodes.json --all

# Export to JSON
python scripts/run_fault_detection.py --all --format json

# Export to HTML report
python scripts/run_fault_detection.py --all --format html --export report.html
```

### 3. Sensitive Data Tracking
```bash
cd /home/nidhi/Ila/ai
source activate_graphrag.sh

# Track all sensitive data (uses cpg_rag_system/data/cpg_nodes.json and cpg_edges.json by default)
python scripts/run_sensitive_data_tracking.py --all

# Track specific type (e.g., password)
python scripts/run_sensitive_data_tracking.py --track password

# Use custom files
python scripts/run_sensitive_data_tracking.py --nodes-json cpg_rag_system/data/cpg_nodes.json --edges-json cpg_rag_system/data/cpg_edges.json --all

# Export to JSON
python scripts/run_sensitive_data_tracking.py --all --format json

# Export to Markdown report
python scripts/run_sensitive_data_tracking.py --all --format markdown --export sensitive_data_report.md
```

### 4. Code Understanding
```bash
cd /home/nidhi/Ila/ai
source activate_graphrag.sh

# Generate overview (uses cpg_rag_system/data/cpg_nodes.json and cpg_edges.json by default)
python scripts/run_code_understanding.py --overview

# Generate architecture description
python scripts/run_code_understanding.py --architecture

# Find entry points
python scripts/run_code_understanding.py --entry-points

# Use custom files
python scripts/run_code_understanding.py --nodes-json cpg_rag_system/data/cpg_nodes.json --edges-json cpg_rag_system/data/cpg_edges.json --overview

# Export to markdown
python scripts/run_code_understanding.py --overview --format markdown --export overview.md
```

---

## Full Workflow Example

### Step 1: Start the Streamlit App
```bash
cd /home/nidhi/Ila/ai
./run_streamlit.sh
```

### Step 2: In the Browser (http://localhost:8501)

**Setup Tab:**
1. Enter repository URL or path (e.g., `https://github.com/user/repo`)
2. Click "🔨 Build CPG" (this automatically extracts CPG nodes/edges to `cpg_rag_system/data/`)
3. Click "📤 Extract Methods" (for the Query tab)
4. Click "🔍 Index Methods" (for the Query tab)

**Query Tab:**
- Enter your question and click "🚀 Generate Answer"

**Analysis Tab:**
- Select analysis type:
  - **Fault Detection**: Click "🔍 Run Fault Detection" (uses `cpg_rag_system/data/cpg_nodes.json`)
  - **Sensitive Data Tracking**: Click "🔐 Run Sensitive Data Tracking" (uses nodes and edges JSON)
  - **Code Understanding**: Click "📚 Generate Understanding" (uses nodes and edges JSON)

---

## Verify Installation

Check if all dependencies are available:
```bash
cd /home/nidhi/Ila/ai
source activate_graphrag.sh

# Check Python packages
python -c "import streamlit; print('✓ Streamlit installed')"
python -c "import rich; print('✓ Rich installed')"
python -c "import sys; sys.path.insert(0, 'cpg_rag_system'); from config import CONFIG; print('✓ CPG RAG system available')"

# Check scripts
python scripts/run_fault_detection.py --help
python scripts/run_sensitive_data_tracking.py --help
python scripts/run_code_understanding.py --help
```

---

## Troubleshooting

### If Streamlit doesn't start:
```bash
# Check if streamlit is installed
pip list | grep streamlit

# If not installed:
pip install streamlit
```

### If analysis scripts fail:
```bash
# Check if cpg_rag_system is accessible
ls -la cpg_rag_system/

# Check if methods JSON exists
ls -la data/methods_*.json
```

### If conda environment not found:
```bash
# Activate manually
source $(conda info --base)/etc/profile.d/conda.sh
conda activate graphrag
```

---

## Quick Test Commands

Test all analysis features quickly:
```bash
cd /home/nidhi/Ila/ai
source activate_graphrag.sh

# First, extract CPG JSON (if not already done)
python scripts/extract_cpg_json.py data/cpg/medsam.cpg.bin

# Test fault detection
echo "Testing Fault Detection..."
python scripts/run_fault_detection.py --all --format json | head -20

# Test sensitive data tracking
echo "Testing Sensitive Data Tracking..."
python scripts/run_sensitive_data_tracking.py --all --format json | head -20

# Test code understanding
echo "Testing Code Understanding..."
python scripts/run_code_understanding.py --overview | head -30
```

## Important Notes

- **CPG JSON files** are stored in `cpg_rag_system/data/` directory:
  - `cpg_rag_system/data/cpg_nodes.json` - All method nodes
  - `cpg_rag_system/data/cpg_edges.json` - All call edges
  
- **Automatic extraction**: When you build CPG in the Streamlit app, it automatically extracts the JSON files
  
- **Manual extraction**: If you have a CPG binary file, extract JSON manually:
  ```bash
  python scripts/extract_cpg_json.py <path-to-cpg.bin>
  ```

