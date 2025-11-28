# Streamlit Web Interface Guide

## Overview

The Streamlit web interface provides an easy-to-use GUI for the GraphRAG code analysis system. It allows you to analyze code repositories through a simple web interface.

## Running on a Remote Machine (SSH)

### Step 1: Start the Streamlit App

On your remote machine, run:

```bash
cd /path/to/Code_analyzer
./run_streamlit.sh
```

Or specify a custom port:

```bash
./run_streamlit.sh 8502
```

### Step 2: Set Up SSH Port Forwarding

On your **local machine**, set up SSH port forwarding:

```bash
ssh -L 8501:localhost:8501 user@remote-machine
```

Replace:
- `8501` with the port you're using (default is 8501)
- `user@remote-machine` with your SSH connection details

### Step 3: Access the Web Interface

Open your browser and go to:

```
http://localhost:8501
```

## Using the Interface

### Setup Tab

1. **Enter Repository**: 
   - GitHub URL: `https://github.com/user/repo`
   - Local path: `/path/to/local/repo`

2. **Build CPG**: 
   - Click "Build CPG" to generate the Code Property Graph
   - This may take several minutes for large repositories

3. **Extract Methods**: 
   - Click "Extract Methods" to extract method representations from the CPG
   - This processes the CPG and extracts method details

4. **Index Methods**: 
   - Click "Index Methods" to embed and index methods in ChromaDB
   - This enables semantic search

### Query Tab

1. **Enter Question**: Type your question about the codebase
2. **Generate Answer**: Click the button to get the analysis
3. **View Results**: See the answer and full output

### Configuration (Sidebar)

- **Device**: Choose GPU (cuda) or CPU
- **Top K Methods**: Number of methods to retrieve (3-20)
- **LLM Model**: HuggingFace model for reasoning
- **Embedding Model**: HuggingFace model for embeddings

## Troubleshooting

### Port Already in Use

If port 8501 is already in use:

```bash
./run_streamlit.sh 8502
```

Then use port 8502 in your SSH forwarding.

### Can't Access from Browser

1. Check SSH port forwarding is active
2. Verify the port matches in both commands
3. Try accessing `http://127.0.0.1:8501` instead

### Conda Environment Not Found

The script automatically detects conda environments. If it doesn't work:

```bash
# Manually activate conda
conda activate graphrag

# Then run streamlit directly
streamlit run app.py --server.port=8501 --server.address=0.0.0.0
```

### Streamlit Not Installed

```bash
pip install streamlit
# or
conda install -c conda-forge streamlit
```

## Tips

- The first time you build a CPG for a repository, it may take 5-10 minutes
- Large repositories will take longer to process
- GPU is recommended for faster LLM inference
- You can reset the session to start with a new repository

