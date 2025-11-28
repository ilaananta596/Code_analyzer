# GPU Usage and Graph Neighborhood in Query Script

## Answers to Your Questions

### 1. Is the model running on GPU?

**Current Status:**
- **Default**: Both embedding and LLM models run on **CPU** by default
- **GPU Support**: Available but must be configured

**How to Enable GPU:**

**Option 1: Edit `models/config.yaml`**
```yaml
embedding:
  device: "cuda"  # Change from "cpu" to "cuda"

llm:
  device: "cuda"  # Change from "cpu" to "cuda"
```

**Option 2: Use command-line flag (NEW)**
```bash
python scripts/query.py \
  --question "your question" \
  --project-name project \
  --cpg-path data/cpg/project.cpg.bin \
  --device cuda
```

**What Changed:**
- ✅ Embedding model now respects device setting
- ✅ Added `--device` command-line flag to override config
- ✅ Automatic CUDA availability check with fallback to CPU
- ✅ Better device information in output

### 2. Is graph neighborhood being fetched?

**Yes!** Graph neighborhood is fetched in **Step 2** of the query process.

**How it works:**
1. **Step 1**: Semantic retrieval from ChromaDB (finds relevant methods)
2. **Step 2**: Graph expansion via Joern (fetches callers, callees, types for each retrieved method)
3. **Step 3**: LLM reasoning (combines code + graph context)

**Requirements:**
- Must provide `--cpg-path` argument
- CPG file must exist and be valid

**What's fetched:**
- **Callers**: Methods that call the retrieved method
- **Callees**: Methods called by the retrieved method  
- **Types**: Types used in the method

**Example:**
```bash
python scripts/query.py \
  --question "Who calls the validation logic?" \
  --project-name project \
  --cpg-path data/cpg/project.cpg.bin  # Required for graph expansion
```

**If CPG path not provided:**
- Graph expansion is skipped
- Only semantic retrieval results are used
- LLM still works but with less context

## Complete Query Flow

```
User Question
    ↓
Step 1: Semantic Retrieval (ChromaDB)
    ↓
    Retrieve top-K methods
    ↓
Step 2: Graph Expansion (Joern) ← YES, THIS HAPPENS!
    ↓
    For each retrieved method:
    - Query callers
    - Query callees  
    - Query types
    ↓
Step 3: LLM Reasoning
    ↓
    Build prompt with:
    - Retrieved code
    - Graph neighborhood (callers/callees/types)
    - Question
    ↓
    Generate answer
```

## Performance Notes

**GPU Usage:**
- **Embedding model**: Faster on GPU for large batches
- **LLM model**: Significantly faster on GPU (especially for larger models)
- **Memory**: GPU models require more VRAM

**Graph Expansion:**
- Runs sequentially for each retrieved method
- Each Joern query takes ~1-2 seconds
- For top-5 methods: ~5-10 seconds total
- Can be parallelized in future improvements

## Troubleshooting

**GPU not working:**
1. Check CUDA availability: `python -c "import torch; print(torch.cuda.is_available())"`
2. Verify GPU: `nvidia-smi`
3. Check config: `models/config.yaml` has `device: "cuda"`
4. Use `--device cuda` flag to override

**Graph neighborhood empty:**
1. Ensure `--cpg-path` is provided
2. Verify CPG file exists and is valid
3. Check that method names in ChromaDB match CPG method names
4. Look for warnings in output about method not found

