# RAG-Based Code Analysis Usage Guide

This guide explains how to use the RAG-based code analysis features in the app, which use `cpg_rag_complete` with Ollama for intelligent code analysis.

## Prerequisites

### 1. Install Ollama

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Start Ollama service (in a separate terminal)
ollama serve
```

### 2. Pull Required Models

```bash
# Pull LLM model for analysis
ollama pull llama3.2

# Pull embedding model
ollama pull nomic-embed-text
```

### 3. Install Python Dependencies

```bash
# Install cpg_rag_complete requirements
pip install -r cpg_rag_complete/requirements.txt

# Note: If you get import errors, the scripts handle multiple langchain versions automatically
```

## Workflow in the App

### Step 1: Build CPG

1. Go to the **📥 Setup** tab
2. Enter your repository URL or local path
3. Click **🔨 Build CPG**
4. The system will automatically:
   - Build the CPG
   - Extract CPG JSON to `cpg_rag_complete/data/`
   - Set up the RAG system (this may take a few minutes)

### Step 2: Run Analysis

Go to the **🔍 Analysis** tab and select your analysis type:

#### Fault Detection

**Purpose**: Detects security vulnerabilities, missing error handling, resource leaks, and code quality issues.

**Options**:
- **Security issues only**: Check this to focus only on security vulnerabilities
- **Export Format**: Choose console, json, md, or markdown

**Usage**:
1. Select "Fault Detection"
2. Choose your options
3. Click **🔍 Run Fault Detection**

**What it does**:
- Queries the RAG system with: "Find security vulnerabilities, resource leaks, missing error handling, and code quality issues"
- Uses Ollama LLM to analyze code and identify issues
- Returns grounded, cited responses based on actual code

#### Sensitive Data Tracking

**Purpose**: Tracks sensitive data flows (passwords, API keys, tokens, PII) through the codebase.

**Options**:
- **Track Specific Type**: Enter a specific type (e.g., "password", "api_key", "token") or leave empty for all
- **Export Format**: Choose console, json, md, or markdown

**Usage**:
1. Select "Sensitive Data Tracking"
2. Optionally enter a specific data type to track
3. Choose export format
4. Click **🔐 Run Sensitive Data Tracking**

**What it does**:
- Queries the RAG system to find hardcoded credentials, API keys, tokens, and sensitive data exposure
- Can focus on specific data types if specified
- Returns analysis with function locations and descriptions

#### Code Understanding

**Purpose**: Generates comprehensive overview of codebase structure, architecture, and entry points.

**Options**:
- **Understanding Mode**: 
  - **Overview**: General codebase overview
  - **Architecture**: Architecture description
  - **Entry Points**: Find entry points and main functions
- **Export Format**: Choose console or markdown

**Usage**:
1. Select "Code Understanding"
2. Choose your understanding mode
3. Choose export format
4. Click **📚 Generate Understanding**

**What it does**:
- Queries the RAG system with appropriate questions based on mode
- Uses semantic search to find relevant code
- Generates comprehensive descriptions using Ollama LLM

## Command Line Usage

You can also run analysis from the command line:

### Fault Detection

```bash
# All issues
python scripts/run_rag_analysis.py --analysis-type fault

# Security issues only
python scripts/run_rag_analysis.py --analysis-type fault --mode security

# With custom query
python scripts/run_rag_analysis.py --analysis-type fault --query "Find SQL injection vulnerabilities"

# Export to JSON
python scripts/run_rag_analysis.py --analysis-type fault --export json

# Export to Markdown
python scripts/run_rag_analysis.py --analysis-type fault --export md
```

### Sensitive Data Tracking

```bash
# All sensitive data
python scripts/run_rag_analysis.py --analysis-type sensitive

# Specific type
python scripts/run_rag_analysis.py --analysis-type sensitive --mode password

# Export to JSON
python scripts/run_rag_analysis.py --analysis-type sensitive --export json
```

### Code Understanding

```bash
# Overview
python scripts/run_rag_analysis.py --analysis-type understanding --mode overview

# Architecture
python scripts/run_rag_analysis.py --analysis-type understanding --mode architecture

# Entry Points
python scripts/run_rag_analysis.py --analysis-type understanding --mode entry-points

# Export to Markdown
python scripts/run_rag_analysis.py --analysis-type understanding --mode overview --export md
```

## Direct cpg_rag_complete Usage

You can also use `cpg_rag_complete` scripts directly:

### Interactive Mode

```bash
cd cpg_rag_complete
python step4_query_rag.py --interactive
```

Then type queries like:
- "Find SQL injection vulnerabilities"
- "What are the main components of this codebase?"
- "Find functions that handle user authentication"

### Single Query

```bash
python step4_query_rag.py --query "Find security vulnerabilities" --type fault
```

### Full Analysis

```bash
python step4_query_rag.py --all --export md
```

## Troubleshooting

### Ollama Not Running

**Error**: `Connection refused` or `Ollama connection refused`

**Solution**:
```bash
# Start Ollama in a separate terminal
ollama serve

# Verify it's running
curl http://localhost:11434/api/tags
```

### Models Not Found

**Error**: `model not found` or `model llama3.2 not found`

**Solution**:
```bash
# Pull required models
ollama pull llama3.2
ollama pull nomic-embed-text

# Verify models
ollama list
```

### RAG System Not Set Up

**Error**: `RAG system not set up` or `chroma_db not found`

**Solution**:
```bash
# Run setup manually
python cpg_rag_complete/step3_setup_rag.py --data-dir cpg_rag_complete/data
```

### No CPG JSON Found

**Error**: `CPG nodes JSON not found`

**Solution**:
```bash
# Extract CPG JSON first
python scripts/extract_cpg_json.py data/cpg/<project>.cpg.bin --output cpg_rag_complete/data
```

## What Makes This Different

The RAG-based analysis uses:
- **Semantic Search**: Finds code by meaning, not just keywords
- **LLM-Powered Analysis**: Uses Ollama (llama3.2) for intelligent analysis
- **Grounded Responses**: All answers are based on actual code snippets
- **Graph-Aware**: Understands code relationships and dependencies
- **Natural Language Queries**: Ask questions in plain English

## Analysis Capabilities

The system can detect:
- **Injection vulnerabilities**: SQL, command, XSS
- **Resource leaks**: Unclosed files, connections
- **Null pointer issues**: Missing null checks
- **Error handling**: Missing try/catch
- **Input validation**: Unvalidated user input
- **Unsafe operations**: eval(), exec(), pickle
- **Authentication issues**: Hardcoded credentials
- **Data flow**: Sensitive data exposure

## Notes

- **First-time setup**: The RAG setup (step3) may take several minutes for large codebases
- **Ollama must be running**: Always ensure `ollama serve` is running before analysis
- **Model loading**: First query may be slow as Ollama loads the model
- **Large codebases**: Analysis may take longer for very large projects

