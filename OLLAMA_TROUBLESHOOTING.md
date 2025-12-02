# Ollama Troubleshooting Guide

## Why Deprecation Warnings Appear

The deprecation warnings occur because LangChain has moved certain classes to separate packages:

1. **OllamaEmbeddings** and **ChatOllama** → moved to `langchain-ollama`
2. **Chroma** → moved to `langchain-chroma`

**Status**: ✅ **FIXED** - The code now uses the new packages with fallback to old imports for compatibility.

## Common Ollama Errors

### Error: "llama runner process has terminated: exit status 2"

**Cause**: The Ollama model process crashed. This can happen due to:
- Memory issues (GPU/CPU)
- Corrupted model files
- Model incompatibility

**Solutions**:

1. **Restart Ollama**:
   ```bash
   pkill ollama
   ollama serve
   ```

2. **Check if model is valid**:
   ```bash
   ollama show llama3.2
   ```

3. **Re-pull the model**:
   ```bash
   ollama rm llama3.2
   ollama pull llama3.2
   ```

4. **Use CPU mode** (if GPU issues):
   ```bash
   # Set environment variable
   export OLLAMA_NUM_GPU=0
   ollama serve
   ```

5. **Check system resources**:
   ```bash
   # Check memory
   free -h
   
   # Check GPU (if using)
   nvidia-smi
   ```

### Error: "CUDA error: out of memory"

**Cause**: GPU memory is insufficient for the model.

**Solutions**:

1. **Use CPU mode**:
   ```bash
   export OLLAMA_NUM_GPU=0
   ollama serve
   ```

2. **Use a smaller model**:
   ```bash
   ollama pull llama3.2:1b  # Smaller variant
   ```

3. **Free GPU memory**:
   - Close other GPU applications
   - Restart the system if needed

### Error: "Connection refused" or "Failed to connect"

**Cause**: Ollama service is not running.

**Solution**:
```bash
# Start Ollama
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Error: "model not found"

**Cause**: The required model hasn't been pulled.

**Solution**:
```bash
# Pull required models
ollama pull llama3.2
ollama pull nomic-embed-text

# Verify
ollama list
```

## Testing Ollama

### Test if Ollama is working:
```bash
# Test basic API
curl http://localhost:11434/api/tags

# Test model generation
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2",
  "prompt": "Say hello",
  "stream": false
}'
```

### Test from Python:
```python
from langchain_ollama import ChatOllama

llm = ChatOllama(model="llama3.2")
response = llm.invoke("Say hello")
print(response.content)
```

## Prevention Tips

1. **Always start Ollama before running analysis**:
   ```bash
   # In a separate terminal
   ollama serve
   ```

2. **Monitor Ollama logs** for errors:
   ```bash
   # Check Ollama process
   ps aux | grep ollama
   
   # Check logs (if available)
   journalctl -u ollama  # systemd service
   ```

3. **Use appropriate model size** for your system:
   - Small systems: `llama3.2:1b`
   - Medium systems: `llama3.2:3b` (default)
   - Large systems: `llama3.2:7b` or larger

4. **Set environment variables** for better control:
   ```bash
   export OLLAMA_NUM_GPU=0  # Force CPU
   export OLLAMA_HOST=0.0.0.0:11434  # Change host/port
   ```

## Quick Fixes

### If nothing works, try a complete reset:

```bash
# 1. Stop Ollama
pkill ollama

# 2. Remove models (optional - will need to re-download)
rm -rf ~/.ollama/models

# 3. Restart Ollama
ollama serve

# 4. Re-pull models
ollama pull llama3.2
ollama pull nomic-embed-text

# 5. Test
curl http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"test","stream":false}'
```

## Status Check Script

Create a simple test script to verify everything:

```bash
#!/bin/bash
echo "Checking Ollama..."

# Check if Ollama is running
if curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "✅ Ollama is running"
else
    echo "❌ Ollama is not running. Start with: ollama serve"
    exit 1
fi

# Check models
if ollama list | grep -q "llama3.2"; then
    echo "✅ llama3.2 model found"
else
    echo "❌ llama3.2 not found. Pull with: ollama pull llama3.2"
fi

if ollama list | grep -q "nomic-embed-text"; then
    echo "✅ nomic-embed-text model found"
else
    echo "❌ nomic-embed-text not found. Pull with: ollama pull nomic-embed-text"
fi

# Test generation
echo "Testing model..."
response=$(curl -s http://localhost:11434/api/generate -d '{"model":"llama3.2","prompt":"test","stream":false}')
if echo "$response" | grep -q "response"; then
    echo "✅ Model generation works"
else
    echo "❌ Model generation failed"
    echo "$response"
fi
```


