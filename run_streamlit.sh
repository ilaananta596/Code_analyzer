#!/bin/bash
# Script to run Streamlit app on remote machine via SSH
# Usage: ./run_streamlit.sh [port]

PORT=${1:-8501}

echo "=========================================="
echo "Starting Streamlit app on port $PORT"
echo "=========================================="
echo ""
echo "To access from your local machine:"
echo "  1. Set up SSH port forwarding:"
echo "     ssh -L $PORT:localhost:$PORT user@remote-machine"
echo ""
echo "  2. Open in your browser:"
echo "     http://localhost:$PORT"
echo ""
echo "=========================================="
echo ""

# Activate conda environment if it exists
if command -v conda &> /dev/null; then
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate graphrag 2>/dev/null || echo "Note: conda environment 'graphrag' not found, using system Python"
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "Error: streamlit is not installed"
    echo "Please install it with: pip install streamlit"
    exit 1
fi

# Run streamlit
streamlit run app.py \
    --server.port=$PORT \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.enableCORS=false \
    --server.enableXsrfProtection=false

