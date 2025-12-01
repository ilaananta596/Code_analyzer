# CPG RAG Complete Pipeline 

A complete Code Property Graph (CPG) + Retrieval-Augmented Generation (RAG) system for structural, semantic, and security-aware analysis of source code.
This version corresponds to the implementation in the project root:

```
cpg_rag_complete_new2/
```

---

# Overview

This system takes any source code and performs the following:

1. Generates a Code Property Graph (CPG) using Joern
2. Extracts nodes, edges, methods, calls, and statistics
3. Deduplicates functions and calculates accurate line numbers
4. Builds hybrid vector stores (semantic, structural, fault, hybrid)
5. Runs an advanced RAG engine with graph expansion
6. Provides grounded LLM answers (no hallucination)
7. Supports interactive querying and fault/structural analysis

---

# Key Features

* AST + Joern merged extraction
* Duplicate-free method extraction
* Accurate file line counting
* Four vector-store retrieval approach
* Hybrid scoring + keyword boosts
* Call-graph-based expansion (callers + callees)
* Automatic telemetry disabling for Chroma
* Strict grounding rules for LLM responses
* Interactive CLI with multiple query types
* Detection of unsafe eval/exec/subprocess usage
* Static analysis of vulnerabilities and data flow

---

# Prerequisites

## Python

Use Python 3.10.

```
conda create -n cpg-rag python=3.10
conda activate cpg-rag
```

## Joern

Download from [https://joern.io](https://joern.io).

Place the Joern folder here:

```
cpg_rag_complete_new2/joern-cli/
```

Alternatively pass a custom path via `--joern-path`.

## Ollama

```
curl -fsSL https://ollama.com/install.sh | sh
ollama serve
```

Models required:

```
ollama pull llama3.2
ollama pull nomic-embed-text
```

## Python Dependencies

```
pip install -r requirements.txt
```

---

# Quick Start (Recommended)

From inside `cpg_rag_complete_new2/`:

```
python run_pipeline.py /path/to/source --joern-path ./joern-cli --interactive
```

This executes:

1. Step 1: Generate CPG
2. Step 2: Extract JSON
3. Step 3: Setup RAG
4. Step 4: Launch interactive query mode

---

# Step-by-Step Execution

## Step 1 — Generate CPG

```
python step1_generate_cpg.py /path/to/source --joern-path ./joern-cli
```

Output:

```
data/cpg.bin
```

---

## Step 2 — Extract JSON (AST + Joern)

```
python step2_extract_json.py data/cpg.bin --source-dir /path/to/source --output data/
```

Produces:

```
data/cpg_nodes.json
data/cpg_edges.json
data/methods.json
data/calls.json
data/codebase_stats.json
```

---

## Step 3 — Setup RAG System

```
python step3_setup_rag.py --source-dir /path/to/source
```

Produces:

```
data/enriched_methods.json
chroma_db/semantic
chroma_db/structural
chroma_db/fault
chroma_db/hybrid
```

---

## Step 4 — Query Engine

### Single Query

```
python step4_query_rag.py --query "Find vulnerabilities"
```

### Interactive Mode

```
python step4_query_rag.py --interactive
```

Interactive commands:

```
/stats
/type fault
/type structural
/type semantic
/type overview
/help
/quit
```

---

# Example Queries

Semantic:

```
What does process_data do?
```

Fault detection:

```
Find insecure use of eval, exec, or subprocess.
```

Call graph:

```
Show the call graph for handle_request.
```

Overview:

```
Summarize the entire codebase.
```

---

# Project Structure

```
cpg_rag_complete_new2/
│
├── config.py
├── run_pipeline.py
├── step1_generate_cpg.py
├── step2_extract_json.py
├── step3_setup_rag.py
├── step4_query_rag.py
│
├── data/
│   ├── cpg.bin
│   ├── cpg_nodes.json
│   ├── cpg_edges.json
│   ├── methods.json
│   ├── calls.json
│   ├── codebase_stats.json
│   ├── enriched_methods.json
│
├── chroma_db/
│   ├── semantic
│   ├── structural
│   ├── fault
│   ├── hybrid
│
└── output/
```

---

# Troubleshooting

## Joern not found

```
joern-parse not found
```

Fix:

```
export PATH=$PATH:$(pwd)/joern-cli
```

Or pass:

```
--joern-path ./joern-cli
```

## Ollama connection refused

```
ollama serve
```

Check:

```
curl http://localhost:11434/api/tags
```

## Chroma telemetry warnings

```
Failed to send telemetry event
```

Safe to ignore. Telemetry is disabled via:

```python
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
```

## Missing methods or wrong counts

Make sure step2 was run with `--source-dir`.

---

# Architecture

```
Source Code
    |
    v
Joern (CPG Generation)
    |
    v
step2_extract_json.py
    - AST extraction
    - Joern merging
    - Deduplication
    - Accurate line counting
    |
    v
step3_setup_rag.py
    - Enrich methods
    - Build graph index
    - Generate embeddings
    - Create vector stores
    |
    v
step4_query_rag.py
    - Multi-store retrieval
    - Graph expansion
    - Prompt assembly
    - LLM analysis
```
