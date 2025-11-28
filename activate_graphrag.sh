#!/bin/bash
# Proper activation script for graphrag conda environment
# This ensures conda's Python takes precedence over pyenv

# Deactivate pyenv for this session
if [ -n "$PYENV_ROOT" ]; then
    export PATH=$(echo $PATH | tr ':' '\n' | grep -v pyenv | tr '\n' ':' | sed 's/:$//')
    unset PYENV_ROOT
    unset PYENV_VERSION
    unset PYENV_VIRTUAL_ENV
fi

# Activate conda
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate graphrag

# Verify
echo "✓ Conda environment 'graphrag' activated"
echo "  Python version: $(python --version 2>&1)"
echo "  Python path: $(which python)"
echo ""
echo "You can now use 'python' or 'python3' - both will use Python 3.11.14"

