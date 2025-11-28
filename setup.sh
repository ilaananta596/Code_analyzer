#!/bin/bash
# Setup script for GraphRAG code analysis system

set -e

echo "=========================================="
echo "GraphRAG Setup Script"
echo "=========================================="
echo ""

# Check if conda is available
if ! command -v conda &> /dev/null; then
    echo "Error: conda is not installed or not in PATH"
    exit 1
fi

# Activate conda environment
echo "Activating conda environment 'graphrag'..."
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate graphrag

# Verify Python version
PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo "Python version: $PYTHON_VERSION"

if [[ ! "$PYTHON_VERSION" =~ ^3\.(1[0-9]|2[0-9]) ]]; then
    echo "Warning: Python 3.10+ is recommended. Current version: $PYTHON_VERSION"
fi

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo ""
echo "Installing requirements..."
pip install -r requirements.txt

echo ""
echo "=========================================="
echo "Setup complete!"
echo "=========================================="
echo ""
echo "To use the system, make sure to activate the environment:"
echo "  conda activate graphrag"
echo ""

