#!/bin/bash
# Fix Python path issue when pyenv interferes with conda

echo "Diagnosing Python path issue..."
echo ""

# Check current state
echo "Current Python versions:"
echo "  python: $(python --version 2>&1)"
echo "  python3: $(python3 --version 2>&1)"
echo ""

echo "Which commands:"
echo "  which python: $(which python)"
echo "  which python3: $(which python3)"
echo ""

# Activate conda and check
echo "Activating conda environment 'graphrag'..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate graphrag

echo ""
echo "After conda activation:"
echo "  python: $(python --version 2>&1)"
echo "  python3: $(python3 --version 2>&1)"
echo "  which python: $(which python)"
echo "  which python3: $(which python3)"
echo ""

# Check if conda's python is accessible
CONDA_PYTHON="$(conda info --base)/envs/graphrag/bin/python"
if [ -f "$CONDA_PYTHON" ]; then
    echo "Conda Python location: $CONDA_PYTHON"
    echo "Conda Python version: $($CONDA_PYTHON --version 2>&1)"
    echo ""
    echo "SOLUTION: Use 'python' instead of 'python3' when in conda environment"
    echo "Or use the full path: $CONDA_PYTHON"
fi

