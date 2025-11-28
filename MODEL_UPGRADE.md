# Model Upgrade to Qwen2.5-Coder-7B-Instruct

## Problem Identified

The previous model (Mistral-7B-Instruct) was failing to recognize relevant methods even when they were present in the prompt. For example, when asked "Where is the model training happening?", it would see `main` from `train_multi_gpus.py` (Method 6) but still say "no clear evidence of model training exists."

## Root Causes

1. **Model Capability**: Mistral-7B-Instruct, while good for general tasks, is not specialized for code analysis
2. **Method Ranking**: The training method was ranked 6th by semantic similarity, making it less prominent
3. **Model Understanding**: The model wasn't making the connection between file paths (e.g., `train_multi_gpus.py`) and the question

## Solution

### 1. Upgraded to Qwen2.5-Coder-7B-Instruct

- **Specialized for code**: Qwen2.5-Coder is specifically trained for code understanding and analysis
- **Better reasoning**: Demonstrates high performance on code-related tasks
- **Same size**: 7B parameters (manageable for most GPUs)

### 2. Improved Prompt Instructions

Added explicit guidance to:
- Review ALL methods, not just the top ones
- Pay attention to file paths and method names as strong indicators
- Look for keywords in file paths (e.g., "train" in path when asked about training)

## Results

**Before (Mistral-7B-Instruct)**:
> "However, no clear evidence of model training exists in the provided code snippets..."

**After (Qwen2.5-Coder-7B-Instruct)**:
> "The model training is happening in the `train_multi_gpus.py` file. Specifically, it is initiated by the `main()` function located at line 260 of this file."

## Usage

The default model is now `Qwen/Qwen2.5-Coder-7B-Instruct`. You can override it:

```bash
python scripts/query.py \
  --question "Where is the model training happening?" \
  --project-name sam \
  --cpg-path data/cpg/sam.cpg.bin \
  --device cuda \
  --llm-model Qwen/Qwen2.5-Coder-7B-Instruct \
  --top-k 5
```

## Alternative Models

If you need even better performance and have the GPU memory:

- **Qwen2.5-Coder-32B-Instruct**: Much larger, better performance, requires ~64GB GPU memory
- **DeepSeek-Coder-33B**: Another excellent code model
- **CodeLlama-13B-Instruct**: Good alternative

For most use cases, Qwen2.5-Coder-7B-Instruct provides the best balance of performance and resource requirements.

