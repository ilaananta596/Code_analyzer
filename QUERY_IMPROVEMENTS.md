# Query Script Improvements

## New Features

### 1. Prompt Dumping
You can now save the final prompt to a text file for inspection:

```bash
python scripts/query.py \
  --question "your question" \
  --project-name project \
  --cpg-path data/cpg/sam.cpg.bin \
  --dump-prompt prompts/query_prompt.txt
```

### 2. Improved Retrieval Quality

**Problems Fixed:**
- ❌ `<module>` entries were being retrieved (not useful)
- ❌ Question enhancement wasn't happening
- ❌ Method names weren't prominent in embeddings

**Improvements Made:**
- ✅ Filter out `<module>` entries by default (retrieve 3x more, filter, then take top-K)
- ✅ Enhanced question with context (e.g., "validation" → adds "validation function method check verify")
- ✅ Better text representation: Method name first, then signature, code, callees
- ✅ Include parameter names in embeddings
- ✅ Filter out operator calls from callees list

### 3. Better Text Representation for Indexing

The indexing now includes:
1. **Method name** (most prominent)
2. **Signature** (with parameter names)
3. **File path** (context)
4. **Code** (increased from 1000 to 1500 chars)
5. **Callees** (filtered to meaningful calls only)
6. **Parameter names** (new!)

## Complete Command with GPU

```bash
python scripts/query.py \
  --question "Who calls the validation logic?" \
  --project-name sam \
  --cpg-path data/cpg/sam.cpg.bin \
  --device cuda \
  --dump-prompt prompts/validation_query.txt \
  --top-k 5
```

**Breakdown:**
- `--question`: Your question
- `--project-name sam`: Project name (must match what you used in indexing)
- `--cpg-path data/cpg/sam.cpg.bin`: Path to your CPG file
- `--device cuda`: Use GPU (falls back to CPU if not available)
- `--dump-prompt`: Save prompt to file
- `--top-k 5`: Number of methods to retrieve (default: 5)

## If Retrieval Still Poor

### Option 1: Re-index with Better Representations

The improvements to `index_methods.py` require re-indexing:

```bash
# Re-index your methods
python scripts/index_methods.py data/methods.json --project-name sam
```

### Option 2: Increase top-k

Try retrieving more methods:

```bash
python scripts/query.py \
  --question "Who calls the validation logic?" \
  --project-name sam \
  --cpg-path data/cpg/sam.cpg.bin \
  --device cuda \
  --top-k 10
```

### Option 3: Use More Specific Questions

Instead of "Who calls the validation logic?", try:
- "validation function"
- "validate method"
- "check validation"
- "verify function"

### Option 4: Check Your Codebase

The question "Who calls the validation logic?" might not match your codebase if:
- Methods aren't named with "validation" or "validate"
- Validation is done inline rather than in separate functions
- The codebase uses different terminology

**To check what's in your index:**
```bash
# Search for validation-related methods
python -c "
import json
with open('data/methods.json') as f:
    data = json.load(f)
methods = [m for m in data['methods'] if 'valid' in m.get('methodName', '').lower() or 'valid' in m.get('code', '').lower()[:200]]
print(f'Found {len(methods)} methods with validation')
for m in methods[:5]:
    print(f\"  - {m.get('methodName')} ({m.get('filePath')})\")
"
```

## Expected Output

With the improvements, you should see:
1. Better method retrieval (fewer `<module>` entries)
2. More relevant methods for your question
3. Prompt saved to file (if `--dump-prompt` used)
4. Graph neighborhood data for each method
5. LLM answer with citations

## Troubleshooting

**Still getting `<module>` entries:**
- Make sure you re-indexed after the improvements
- Check that your methods.json has proper method names
- Try increasing `--top-k` to 10 or 15

**GPU not working:**
- Check: `python -c "import torch; print(torch.cuda.is_available())"`
- Verify: `nvidia-smi`
- The script will automatically fall back to CPU

**Graph neighborhood empty:**
- Ensure CPG file exists and is valid
- Check that method names in ChromaDB match CPG method names
- Look for warnings in the output

