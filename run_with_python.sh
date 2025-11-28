#!/bin/bash
# Wrapper script to run Python scripts with correct Python version
# Usage: ./run_with_python.sh <script> [args...]

CONDA_PYTHON="$(conda info --base)/envs/graphrag/bin/python"

if [ ! -f "$CONDA_PYTHON" ]; then
    echo "Error: Conda environment 'graphrag' not found"
    echo "Please run: conda activate graphrag"
    exit 1
fi

# Run the script with conda's Python
exec "$CONDA_PYTHON" "$@"

