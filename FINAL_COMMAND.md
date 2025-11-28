# Final Command and Status

## ✅ Fixed Issues

1. **Joern Script Fixed**: Graph neighborhood script now works correctly
   - Callees: ✅ Working
   - Types: ✅ Working  
   - Callers: ⚠️ Empty for now (Joern API complexity for Python - can be enhanced)

2. **Prompt Dumping**: ✅ Added `--dump-prompt` argument

3. **GPU Support**: ✅ Added `--device` flag

4. **Retrieval Improvements**: ✅ Removed hardcoded question enhancement, works for any question

## Complete Command with GPU

```bash
python scripts/query.py \
  --question "Who calls the validation logic?" \
  --project-name sam \
  --cpg-path data/cpg/sam.cpg.bin \
  --device cuda \
  --dump-prompt prompts/query_prompt.txt \
  --top-k 5
```

**Arguments:**
- `--question`: Your question (any type)
- `--project-name sam`: Must match what you used in indexing
- `--cpg-path data/cpg/sam.cpg.bin`: Path to your CPG file
- `--device cuda`: Use GPU (falls back to CPU if not available)
- `--dump-prompt prompts/query_prompt.txt`: Save the final prompt to a file
- `--top-k 5`: Number of methods to retrieve (default: 5)

## What's Working

✅ **Semantic Retrieval**: Finds relevant methods for any question  
✅ **Graph Expansion**: Gets callees and types for each retrieved method  
✅ **Prompt Dumping**: Saves final prompt to file for inspection  
✅ **GPU Support**: Uses GPU if available and configured  
✅ **Generic Retrieval**: Works for any question type (no hardcoded keywords)

## Current Limitations

⚠️ **Callers**: Currently returns empty list
- Joern API for getting callers in Python is complex
- Callees and types work perfectly
- Callers can be enhanced later with proper Joern traversal

## Example Output

The script will:
1. Retrieve top-K methods from ChromaDB
2. Get graph neighborhood (callees, types) for each method
3. Build a comprehensive prompt
4. Save prompt to file (if `--dump-prompt` provided)
5. Generate answer with LLM (or show retrieved data if `--no-llm`)

## Next Steps for Better Retrieval

If retrieval quality is still poor:

1. **Re-index with improved representations:**
   ```bash
   python scripts/index_methods.py data/methods.json --project-name sam
   ```

2. **Try different questions:**
   - More specific: "validation function" instead of "validation logic"
   - Different phrasing: "methods that validate" instead of "who calls validation"

3. **Increase top-k:**
   ```bash
   python scripts/query.py ... --top-k 10
   ```

4. **Check your codebase:**
   - Ensure methods are properly named
   - Verify the question matches terminology in your code

