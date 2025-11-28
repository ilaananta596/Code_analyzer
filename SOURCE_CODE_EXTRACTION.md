# Source Code Extraction from Cloned Repositories

## Overview

The system now automatically uses source code from cloned GitHub repositories (or local directories) to extract actual method source code instead of AST representations. This produces **better embeddings** for semantic search.

## How It Works

1. **When building CPG from GitHub:**
   - Repository is cloned to a directory
   - CPG is built from the cloned source
   - Source directory path is saved to `.source_info.json` alongside the CPG file

2. **When extracting methods:**
   - Script automatically detects source directory from `.source_info.json`
   - If source directory exists, methods are enhanced with actual source code
   - If not available, falls back to AST representation

## Usage

### Option 1: Build from GitHub with Source Code (Recommended)

```bash
# Build CPG and keep cloned repository
python scripts/build_cpg.py https://github.com/user/repo \
  --output data/cpg/repo.cpg.bin \
  --keep-clone

# Extract methods (automatically uses source code)
python scripts/extract_methods.py data/cpg/repo.cpg.bin \
  --output data/methods.json
```

### Option 2: Build from Local Directory

```bash
# Build CPG from local directory
python scripts/build_cpg.py /path/to/source \
  --output data/cpg/project.cpg.bin

# Extract methods (automatically uses source code)
python scripts/extract_methods.py data/cpg/project.cpg.bin \
  --output data/methods.json
```

### Option 3: Manual Source Directory

```bash
# Extract methods with explicit source directory
python scripts/extract_methods.py data/cpg/project.cpg.bin \
  --output data/methods.json \
  --source-dir /path/to/source
```

### Option 4: Skip Source Code Enhancement

```bash
# Extract methods without source code enhancement
python scripts/extract_methods.py data/cpg/project.cpg.bin \
  --output data/methods.json \
  --no-enhance
```

## File Structure

After building CPG, you'll have:
```
data/
├── cpg/
│   ├── repo.cpg.bin              # CPG file
│   └── repo.cpg.bin.source_info.json  # Source directory info
└── methods.json                   # Extracted methods (with source code)
```

The `.source_info.json` file contains:
```json
{
  "source_dir": "/tmp/graphrag_clone_xyz",
  "source_type": "github_clone",
  "cleanup": false
}
```

## Benefits

✅ **Better Embeddings**: Actual source code produces better semantic embeddings than AST  
✅ **Automatic**: No manual steps needed - just use `--keep-clone`  
✅ **Fallback**: If source unavailable, uses AST representation  
✅ **Readable**: LLMs can better understand actual source code  

## Important Notes

- **For GitHub repos**: Use `--keep-clone` to preserve the cloned repository for source code extraction
- **For local dirs**: Source directory is automatically saved and used
- **Cleanup**: If you don't use `--keep-clone`, the cloned repo is deleted after CPG building
- **File paths**: Source code extraction uses `filePath` and `lineNumber` from the CPG to locate methods

## Troubleshooting

**Source code not being extracted:**
- Check if `.source_info.json` exists next to your CPG file
- Verify the source directory path in the JSON file exists
- Ensure file paths in methods match actual source file locations
- Try using `--source-dir` explicitly

**Methods still showing AST code:**
- Source directory might not exist (if using GitHub without `--keep-clone`)
- File paths in CPG might not match source file locations
- Check that `--no-enhance` flag is not set

