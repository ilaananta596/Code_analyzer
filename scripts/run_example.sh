#!/bin/bash
# Example script showing the complete GraphRAG workflow

set -e

PROJECT_NAME="example_project"
SOURCE_DIR="${1:-./example_source}"
CPG_PATH="data/cpg/${PROJECT_NAME}.cpg.bin"
METHODS_JSON="data/methods_${PROJECT_NAME}.json"

echo "=========================================="
echo "GraphRAG Code Analysis - Example Workflow"
echo "=========================================="
echo ""

# Step 1: Build CPG
echo "Step 1: Building CPG..."
python scripts/build_cpg.py "$SOURCE_DIR" --output "$CPG_PATH"
echo ""

# Step 2: Extract methods
echo "Step 2: Extracting methods..."
python scripts/extract_methods.py "$CPG_PATH" --output "$METHODS_JSON"
echo ""

# Step 3: Index methods
echo "Step 3: Indexing methods in ChromaDB..."
python scripts/index_methods.py "$METHODS_JSON" --project-name "$PROJECT_NAME"
echo ""

# Step 4: Example query
echo "Step 4: Running example query..."
python scripts/query.py \
  --question "What methods are called in the main entry point?" \
  --project-name "$PROJECT_NAME" \
  --cpg-path "$CPG_PATH"
echo ""

echo "=========================================="
echo "Workflow complete!"
echo "=========================================="

