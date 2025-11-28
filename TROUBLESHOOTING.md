# Troubleshooting Guide

## Python Version Issues

### Problem: Both `python` and `python3` show Python 3.7.9 instead of 3.11.14

**Cause:** pyenv shims are in your PATH and take precedence over conda's Python, even when conda environment is active. pyenv shims appear before conda's bin directory in PATH.

**Solutions (in order of preference):**

1. **Use the activation script** (Easiest - Recommended)
   ```bash
   source activate_graphrag.sh
   python --version  # Should show 3.11.14
   python scripts/build_cpg.py ...
   ```
   This script temporarily removes pyenv from PATH and activates conda.

2. **Use the wrapper script for running Python scripts**
   ```bash
   ./run_with_python.sh scripts/build_cpg.py <args>
   ./run_with_python.sh scripts/extract_methods.py <args>
   ```
   This directly uses conda's Python without PATH issues.

3. **Use the full path to conda's Python**
   ```bash
   conda activate graphrag
   $(conda info --base)/envs/graphrag/bin/python --version
   $(conda info --base)/envs/graphrag/bin/python scripts/build_cpg.py ...
   ```

4. **Manually fix PATH in your current shell**
   ```bash
   # Remove pyenv from PATH
   export PATH=$(echo $PATH | tr ':' '\n' | grep -v pyenv | tr '\n' ':' | sed 's/:$//')
   unset PYENV_ROOT
   unset PYENV_VERSION
   
   # Then activate conda
   conda activate graphrag
   python --version  # Should now show 3.11.14
   ```

5. **Fix your shell configuration permanently** (Advanced)
   Edit `~/.bashrc` or `~/.zshrc` to ensure conda's bin comes before pyenv shims:
   ```bash
   # Move conda initialization before pyenv, or
   # Remove pyenv shims from PATH when using conda
   ```

### Verify Correct Python

After using the activation script:
```bash
source activate_graphrag.sh
python --version  # Should be 3.11.14
which python      # Should point to conda's Python: /home/nidhi/miniconda3/envs/graphrag/bin/python
```

## Installation Issues

### ChromaDB or Transformers Version Errors

If you see version errors, make sure:
1. You're in the conda environment: `conda activate graphrag`
2. pip is upgraded: `pip install --upgrade pip`
3. Use `python` not `python3` for pip: `python -m pip install -r requirements.txt`

### Joern Not Found

Ensure Joern is installed and in PATH:
```bash
joern --version
joern-parse --version
```

If not found, add Joern to PATH:
```bash
export PATH=$PATH:/path/to/joern-cli
```

## Common Commands

**Option 1: Use the activation script (Recommended)**
```bash
source activate_graphrag.sh
python scripts/build_cpg.py ...
python scripts/extract_methods.py ...
python scripts/index_methods.py ...
python scripts/query.py ...
```

**Option 2: Use the wrapper script**
```bash
./run_with_python.sh scripts/build_cpg.py <args>
./run_with_python.sh scripts/extract_methods.py <args>
./run_with_python.sh scripts/index_methods.py <args>
./run_with_python.sh scripts/query.py <args>
```

**Option 3: Use full path to conda's Python**
```bash
CONDA_PYTHON="$(conda info --base)/envs/graphrag/bin/python"
$CONDA_PYTHON scripts/build_cpg.py ...
$CONDA_PYTHON scripts/extract_methods.py ...
$CONDA_PYTHON scripts/index_methods.py ...
$CONDA_PYTHON scripts/query.py ...
```

