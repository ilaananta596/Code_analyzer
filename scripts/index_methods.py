#!/usr/bin/env python3
"""
Embed method representations and index them in ChromaDB.
"""

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import List, Dict, Any

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import yaml


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "models" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def embed_and_index(
    methods_json: str,
    project_name: str,
    embedding_model_name: str = "microsoft/graphcodebert-base",
    chromadb_dir: str = "./data/chromadb"
) -> bool:
    """
    Embed methods and index in ChromaDB.
    
    Args:
        methods_json: Path to JSON file with extracted methods
        project_name: Name of the project (for collection naming)
        embedding_model_name: Name of embedding model
        chromadb_dir: Directory for ChromaDB persistence
    
    Returns:
        True if successful
    """
    # Load methods
    methods_path = Path(methods_json)
    if not methods_path.exists():
        print(f"Error: Methods JSON file '{methods_json}' does not exist")
        return False
    
    with open(methods_path, 'r') as f:
        data = json.load(f)
    
    methods = data.get("methods", [])
    if not methods:
        print("Error: No methods found in JSON file")
        return False
    
    print(f"Loading embedding model '{embedding_model_name}'...")
    print("Note: Warnings about model weights initialization are expected and can be ignored.")
    try:
        # Suppress warnings about model weights initialization when using non-sentence-transformers models
        # These warnings are expected when using HuggingFace models with sentence-transformers
        import os
        import logging
        
        # Suppress transformers warnings
        os.environ["TRANSFORMERS_VERBOSITY"] = "error"
        logging.getLogger("transformers").setLevel(logging.ERROR)
        logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
        
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=UserWarning)
            warnings.filterwarnings("ignore", message=".*Some weights of.*were not initialized.*")
            warnings.filterwarnings("ignore", message=".*Creating a new one with mean pooling.*")
            warnings.filterwarnings("ignore", message=".*No sentence-transformers model found.*")
            model = SentenceTransformer(embedding_model_name)
        print("✓ Model loaded successfully")
    except Exception as e:
        print(f"Error loading embedding model: {e}")
        return False
    
    # Build text representations
    print("Building method text representations...")
    method_texts = []
    method_metadata = []
    
    for i, method in enumerate(methods):
        # Build text representation optimized for semantic retrieval
        # Structure: Most important info first, then context
        # This helps embeddings capture the essence of the method
        text_parts = []
        
        # File path FIRST if it contains important keywords (train, eval, test, etc.)
        # This helps with queries like "where is training" or "where is evaluation"
        file_path = method.get("filePath", "")
        method_name = method.get("methodName", "")
        
        # Check if file path contains important keywords
        important_keywords = ["train", "eval", "test", "validation", "infer", "predict"]
        file_path_lower = file_path.lower()
        has_important_keyword = any(keyword in file_path_lower for keyword in important_keywords)
        
        if file_path and has_important_keyword:
            # Put file path first for training/eval files (ALWAYS, even for <module>)
            path_parts = file_path.replace("\\", "/").split("/")
            if len(path_parts) > 1:
                text_parts.append(f"File: {'/'.join(path_parts[-2:])}")
            else:
                text_parts.append(f"File: {file_path}")
            # Also include just the filename for emphasis
            filename = path_parts[-1] if path_parts else file_path
            text_parts.append(filename)
            # For training files, add explicit keywords
            if "train" in file_path_lower:
                text_parts.append("training")
                text_parts.append("train")
        
        # Method name (most important for semantic matching)
        # Repeat it for emphasis in the embedding
        if method_name and method_name != "<module>":
            text_parts.append(f"Method: {method_name}")
            # Also include just the name for better matching
            text_parts.append(method_name)
            # For "main" methods, add context that it's an entry point
            if method_name == "main" and has_important_keyword:
                text_parts.append("entry point main function")
        elif method_name == "<module>" and has_important_keyword:
            # For <module> entries in important files, add context
            if "train" in file_path_lower:
                text_parts.append("training script")
                text_parts.append("training code")
        
        # Full name (includes namespace/class context)
        full_name = method.get("fullName", "")
        if full_name and full_name != method_name:
            text_parts.append(f"Full name: {full_name}")
        
        # Signature (includes parameter names - helps with semantic search)
        if method.get("signature"):
            text_parts.append(f"Signature: {method['signature']}")
        
        # Parameter names separately (for better semantic matching)
        if method.get("paramNames"):
            params = method["paramNames"]
            if params and len(params) > 0:
                text_parts.append(f"Parameters: {', '.join(params)}")
        
        # Code (main semantic content - keep substantial amount)
        if method.get("code"):
            code = method["code"]
            # Keep more code for better semantic understanding
            # Prioritize first part of code (usually most important)
            if len(code) > 2000:
                # Take first 1500 chars (most important) + last 500 (context)
                code = code[:1500] + "\n...\n" + code[-500:]
            text_parts.append(f"Code:\n{code}")
        
        # Callees (what this method calls - helps with "who calls X" queries)
        # Also helps understand what the method does
        if method.get("callees"):
            callees = method["callees"]
            if callees:
                # Filter out operator calls for cleaner representation
                meaningful_callees = [c for c in callees[:20] if not c.startswith("<operator")]
                if meaningful_callees:
                    text_parts.append(f"Calls methods: {', '.join(meaningful_callees)}")
        
        # File path (if not already added at the beginning)
        if file_path and not has_important_keyword:
            # Extract meaningful parts of path (directory names can be semantic)
            path_parts = file_path.replace("\\", "/").split("/")
            if len(path_parts) > 1:
                # Include directory context
                text_parts.append(f"In: {'/'.join(path_parts[-2:])}")
            else:
                text_parts.append(f"File: {file_path}")
        
        method_text = "\n".join(text_parts)
        method_texts.append(method_text)
        
        # Build metadata
        metadata = {
            "project_name": project_name,
            "method_name": method.get("methodName", ""),
            "full_name": method.get("fullName", ""),
            "file_path": method.get("filePath", ""),
            "line_number": str(method.get("lineNumber", 0)),
            "signature": method.get("signature", "")
        }
        method_metadata.append(metadata)
    
    print(f"✓ Built {len(method_texts)} method representations")
    
    # Generate embeddings
    print("Generating embeddings...")
    try:
        embeddings = model.encode(
            method_texts,
            show_progress_bar=True,
            batch_size=32,
            convert_to_numpy=True
        )
        print(f"✓ Generated {len(embeddings)} embeddings")
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return False
    
    # Initialize ChromaDB
    print(f"Initializing ChromaDB at '{chromadb_dir}'...")
    chromadb_path = Path(chromadb_dir)
    chromadb_path.mkdir(parents=True, exist_ok=True)
    
    client = chromadb.PersistentClient(
        path=str(chromadb_path),
        settings=Settings(anonymized_telemetry=False)
    )
    
    collection_name = f"methods_{project_name}"
    
    # Get or create collection
    try:
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"description": f"Method embeddings for {project_name}"}
        )
        print(f"✓ Collection '{collection_name}' ready")
    except Exception as e:
        print(f"Error creating collection: {e}")
        return False
    
    # Add to ChromaDB in batches (ChromaDB has a max batch size limit)
    print("Indexing methods in ChromaDB...")
    try:
        # ChromaDB has a maximum batch size, so we need to split into smaller batches
        max_batch_size = 5000  # Safe batch size (ChromaDB limit is around 5461)
        total_methods = len(methods)
        ids = [f"{project_name}_{i}" for i in range(total_methods)]
        
        # Split into batches
        num_batches = (total_methods + max_batch_size - 1) // max_batch_size
        print(f"  Adding {total_methods} methods in {num_batches} batch(es)...")
        
        for batch_idx in range(num_batches):
            start_idx = batch_idx * max_batch_size
            end_idx = min(start_idx + max_batch_size, total_methods)
            
            batch_ids = ids[start_idx:end_idx]
            batch_embeddings = embeddings[start_idx:end_idx].tolist()
            batch_documents = method_texts[start_idx:end_idx]
            batch_metadatas = method_metadata[start_idx:end_idx]
            
            collection.add(
                ids=batch_ids,
                embeddings=batch_embeddings,
                documents=batch_documents,
                metadatas=batch_metadatas
            )
            
            print(f"  Batch {batch_idx + 1}/{num_batches}: Added {end_idx - start_idx} methods ({end_idx}/{total_methods} total)")
        
        print(f"✓ Indexed {len(methods)} methods in ChromaDB")
        print(f"  Collection: {collection_name}")
        print(f"  Total items: {collection.count()}")
        
    except Exception as e:
        print(f"Error indexing in ChromaDB: {e}")
        return False
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Embed methods and index in ChromaDB"
    )
    parser.add_argument(
        "methods_json",
        help="Path to JSON file with extracted methods"
    )
    parser.add_argument(
        "--project-name", "-p",
        required=True,
        help="Project name (for collection naming)"
    )
    parser.add_argument(
        "--embedding-model",
        default="microsoft/graphcodebert-base",
        help="Embedding model name (default: microsoft/graphcodebert-base)"
    )
    parser.add_argument(
        "--chromadb-dir",
        default="./data/chromadb",
        help="ChromaDB persistence directory (default: ./data/chromadb)"
    )
    
    args = parser.parse_args()
    
    success = embed_and_index(
        args.methods_json,
        args.project_name,
        args.embedding_model,
        args.chromadb_dir
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
