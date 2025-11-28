#!/bin/bash
# Script to run Streamlit app on remote machine via SSH
# Usage: ./run_streamlit.sh [port]

PORT=${1:-8501}

echo "Starting Streamlit app on port $PORT..."
echo "To access from your local machine, use SSH port forwarding:"
echo "  ssh -L $PORT:localhost:$PORT user@remote-machine"
echo ""
echo "Then open: http://localhost:$PORT"
echo ""

# Activate conda environment if it exists
if command -v conda &> /dev/null; then
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate graphrag 2>/dev/null || echo "Note: conda environment 'graphrag' not found, using system Python"
fi

# Run streamlit
streamlit run app.py --server.port=$PORT --server.address=0.0.0.0 --server.headless=true

