# Embedding Quality Recommendations

## Question 1: Joern AST vs Actual Source Code for Embeddings

### **Recommendation: Use Actual Source Code** ✅

**Why actual source code generates better embeddings:**

1. **Model Training Alignment**
   - GraphCodeBERT and similar models are trained on **actual source code**
   - They understand natural code patterns, variable names, and structure
   - AST representations contain artifacts (`tmp0`, `tmp1`) that confuse embeddings

2. **Semantic Richness**
   - Real code has meaningful variable names: `image_embedding`, `medsam_model`
   - AST has temporary names: `tmp4`, `tmp5`, `tmp6`
   - Comments and docstrings are preserved in source code
   - Better context for understanding method purpose

3. **Readability for LLMs**
   - When retrieved methods are shown to LLMs, source code is more interpretable
   - AST representation is verbose and hard to read
   - Better for final answer generation

4. **Example Comparison:**

   **AST (Current):**
   ```
   tmp4 = medsam_model.prompt_encoder(points = None, boxes = box_torch, masks = None)
   medsam_model.prompt_encoder(points = None, boxes = box_torch, masks = None)
   medsam_model.prompt_encoder
   sparse_embeddings = tmp4[0]
   tmp4[0]
   ```

   **Source Code (Better):**
   ```python
   sparse_embeddings, dense_embeddings = medsam_model.prompt_encoder(
       points=None, boxes=box_torch, masks=None
   )
   ```

### **Trade-offs:**

- **AST Pros:**
  - Always available (no need for source files)
  - Captures structural relationships
  
- **AST Cons:**
  - Less readable
  - Contains noise (temporary variables)
  - Poorer embedding quality

- **Source Code Pros:**
  - Better embeddings
  - More readable
  - Better for LLM reasoning
  
- **Source Code Cons:**
  - Requires source files to be accessible
  - May fail if files moved/deleted

## Question 2: Why Signatures Are Empty

### **Root Cause:**
Python doesn't have explicit method signatures like Java/C++. Joern's `m.signature` property is often empty for Python methods.

### **Solution:**
The updated script now **constructs signatures** from parameter names and types:

**Before:**
```json
"signature": ""
```

**After:**
```json
"signature": "show_mask(mask, ax, random_color)"
"signature": "medsam_inference(medsam_model, image_embedding, box_1024, H, W)"
```

## Implementation

### Option 1: Extract Source Code (Recommended)

1. **Extract methods with AST (as fallback):**
   ```bash
   python scripts/extract_methods.py data/cpg/sam.cpg.bin --output data/methods.json
   ```

2. **Enhance with actual source code:**
   ```bash
   python scripts/extract_source_code.py data/methods.json \
     --output data/methods_enhanced.json \
     --source-dir /path/to/source
   ```

3. **Index the enhanced version:**
   ```bash
   python scripts/index_methods.py data/methods_enhanced.json --project-name sam
   ```

### Option 2: Use AST (Current - Works but suboptimal)

Continue using current approach if source files aren't available:
- Embeddings will work but be less accurate
- Still useful for semantic search
- Good fallback option

## Updated Features

The updated `extract_methods.sc` now:
1. ✅ Constructs Python-style signatures from parameters
2. ✅ Extracts parameter names separately
3. ✅ Still provides AST code as fallback

The new `extract_source_code.py` script:
1. ✅ Reads actual source code from files
2. ✅ Uses filePath and lineNumber to locate methods
3. ✅ Handles Python indentation correctly
4. ✅ Falls back to AST if source not found

## Recommendation Summary

**For best embedding quality:**
1. Extract methods with updated script (now includes signatures)
2. Enhance with source code using `extract_source_code.py`
3. Index the enhanced version

**If source files unavailable:**
- Use AST version (current approach)
- Still functional but embeddings less optimal
- Signatures will now be populated

