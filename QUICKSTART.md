# Quick Start Guide

## Setup

1. **Activate conda environment:**

   **If you have pyenv installed** (and `python --version` shows wrong version):
   ```bash
   source activate_graphrag.sh
   ```
   This script ensures conda's Python takes precedence over pyenv.

   **Otherwise:**
   ```bash
   conda activate graphrag
   ```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

   **Note:** If you see Python version errors, use:
   ```bash
   $(conda info --base)/envs/graphrag/bin/python -m pip install -r requirements.txt
   ```

## Workflow

### Step 1: Build CPG from Source Code

**From local directory:**
```bash
python scripts/build_cpg.py <source_directory> --output data/cpg/project.cpg.bin
```

Example:
```bash
python scripts/build_cpg.py /path/to/my/project --output data/cpg/myproject.cpg.bin
```

**From GitHub repository:**
```bash
python scripts/build_cpg.py <github_url> --output data/cpg/project.cpg.bin
```

Examples:
```bash
# Clone from GitHub and build CPG
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/repo.cpg.bin

# Clone specific branch
python scripts/build_cpg.py https://github.com/user/repo --branch main --output data/cpg/repo.cpg.bin

# Keep cloned repository (don't delete after building)
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/repo.cpg.bin --keep-clone

# Clone to specific directory
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/repo.cpg.bin --clone-dir ./cloned_repos/repo
```

Supported GitHub URL formats:
- `https://github.com/user/repo`
- `git@github.com:user/repo`
- `github.com/user/repo`

### Step 2: Extract Methods from CPG

```bash
python scripts/extract_methods.py data/cpg/project.cpg.bin --output data/methods.json
```

This will extract all methods from the CPG and save them to a JSON file.

**If building from GitHub and you want actual source code (recommended for better embeddings):**

```bash
# Build CPG with --keep-clone to preserve source files
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/repo.cpg.bin --keep-clone

# Extract methods (will automatically use source code from cloned repo)
python scripts/extract_methods.py data/cpg/repo.cpg.bin --output data/methods.json
```

The extraction script will automatically detect the source directory from the `.source_info.json` file created during CPG building and enhance methods with actual source code instead of AST representation.

### Step 3: Index Methods in ChromaDB

```bash
python scripts/index_methods.py data/methods.json --project-name myproject
```

This will:
- Load the methods from JSON
- Generate embeddings using the configured model (default: `microsoft/graphcodebert-base`)
- Store them in ChromaDB for semantic search

### Step 4: Query the Codebase

```bash
python scripts/query.py \
  --question "Who calls the validation logic?" \
  --project-name myproject \
  --cpg-path data/cpg/project.cpg.bin
```

## Example: Complete Workflow

**From local directory:**
```bash
# 1. Build CPG
python scripts/build_cpg.py ./my-source-code --output data/cpg/myproject.cpg.bin

# 2. Extract methods
python scripts/extract_methods.py data/cpg/myproject.cpg.bin --output data/methods.json

# 3. Index in ChromaDB
python scripts/index_methods.py data/methods.json --project-name myproject

# 4. Query
python scripts/query.py \
  --question "How does authentication work?" \
  --project-name myproject \
  --cpg-path data/cpg/myproject.cpg.bin
```

**From GitHub repository:**
```bash
# 1. Build CPG directly from GitHub
python scripts/build_cpg.py https://github.com/user/repo --output data/cpg/repo.cpg.bin

# 2. Extract methods
python scripts/extract_methods.py data/cpg/repo.cpg.bin --output data/methods.json

# 3. Index in ChromaDB
python scripts/index_methods.py data/methods.json --project-name repo

# 4. Query
python scripts/query.py \
  --question "How does authentication work?" \
  --project-name repo \
  --cpg-path data/cpg/repo.cpg.bin
```

## Configuration

Edit `models/config.yaml` to customize:
- Embedding model
- LLM model
- ChromaDB settings
- Device (CPU/CUDA)

## Notes

- The first time you run indexing, it will download the embedding model (can be large)
- LLM inference can be slow on CPU; consider using smaller models or GPU if available
- CPG files can be large; ensure you have sufficient disk space

## Troubleshooting

If `python --version` shows Python 3.7.9 instead of 3.11.14, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for solutions. The quickest fix is to use:
```bash
source activate_graphrag.sh
```

