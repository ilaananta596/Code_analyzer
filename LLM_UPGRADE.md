# LLM Model Upgrade

## Changes Made

### 1. Upgraded Model
- **Old**: `microsoft/phi-2` (2.7B parameters) - too small, poor instruction following
- **New**: `mistralai/Mistral-7B-Instruct-v0.2` (7B parameters) - better instruction following, code understanding

### 2. Improved Prompt Structure
- Clearer, more structured format
- Explicit instructions to explain in simple language
- Better organization of code and graph information
- Removed excessive separators that confused the model

### 3. Enhanced Generation Settings
- **Input context**: Increased from 1024 to 4096 tokens (can handle larger codebases)
- **Output length**: Set to 1024 tokens (focused, concise answers)
- **Temperature**: Reduced from 0.7 to 0.3 (more deterministic, focused responses)
- **Chat template support**: Properly uses instruction templates for better responses
- **Better decoding**: Improved extraction of generated text from model output

### 4. Key Improvements
- Uses chat templates when available (better for instruction models)
- Filters out operator calls from callees for cleaner output
- Better error handling and response extraction
- Lower temperature for more reliable, focused answers

## Usage

The default model is now `mistralai/Mistral-7B-Instruct-v0.2`. You can override it:

```bash
python scripts/query.py \
  --question "Who calls the validation logic?" \
  --project-name sam \
  --cpg-path data/cpg/sam.cpg.bin \
  --device cuda \
  --llm-model mistralai/Mistral-7B-Instruct-v0.2 \
  --top-k 5
```

## Alternative Models

If you want to try other models, here are good options:

1. **Code Llama** (code-specialized):
   ```bash
   --llm-model codellama/CodeLlama-7b-Instruct-hf
   ```

2. **Llama 2** (general purpose):
   ```bash
   --llm-model meta-llama/Llama-2-7b-chat-hf
   ```

3. **Qwen** (good instruction following):
   ```bash
   --llm-model Qwen/Qwen-7B-Chat
   ```

## Model Requirements

- **GPU**: Recommended for 7B models (8GB+ VRAM)
- **CPU**: Will work but much slower
- **Memory**: ~14GB RAM for 7B models

## Expected Improvements

- ✅ Clear, coherent answers in plain English
- ✅ Better understanding of code relationships
- ✅ Proper citation of methods, files, and line numbers
- ✅ No more garbage output with random separators
- ✅ Focused, relevant responses

