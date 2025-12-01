#!/usr/bin/env python3
"""
Step 3: Setup RAG System with Vector Stores

This script:
1. Loads the extracted CPG JSON data
2. Enriches methods with graph context and fault features
3. Creates ChromaDB vector stores for semantic search
4. Prepares everything for RAG queries

Usage:
    python step3_setup_rag.py
    python step3_setup_rag.py --data-dir data/ --source-dir ./my-project

Requirements:
    - Ollama running with nomic-embed-text model
    - JSON files from step 2
"""

import argparse
import json
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
from tqdm import tqdm
import shutil

# Suppress all deprecation warnings from langchain BEFORE importing
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*deprecated.*")
warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")

# LangChain imports - use new packages to avoid deprecation warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", message=".*deprecated.*")
    try:
        from langchain_ollama import OllamaEmbeddings
        from langchain_chroma import Chroma
    except ImportError:
        # Fallback to old imports for compatibility
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import OllamaEmbeddings
try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.schema import Document
    except ImportError:
        from langchain.docstore.document import Document

from config import Config


class RAGSetup:
    """Handles RAG system initialization and vector store creation."""
    
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.config.ensure_directories()
        
        self.nodes = []
        self.edges = []
        self.methods = []
        self.source_files = {}
        self.graph_index = {}
        self.enriched_methods = []
        self.embeddings = None
        self.vector_stores = {}
    
    def load_data(self, data_dir: Path = None, source_dir: Path = None):
        """Load CPG data and source files."""
        data_dir = data_dir or self.config.DATA_DIR
        
        print("\n📂 Loading CPG data...")
        
        # Load nodes
        nodes_file = data_dir / "cpg_nodes.json"
        if nodes_file.exists():
            with open(nodes_file) as f:
                self.nodes = json.load(f)
            print(f"   ✅ Loaded {len(self.nodes):,} nodes")
        
        # Load edges
        edges_file = data_dir / "cpg_edges.json"
        if edges_file.exists():
            with open(edges_file) as f:
                self.edges = json.load(f)
            print(f"   ✅ Loaded {len(self.edges):,} edges")
        
        # Load methods (deduplicated)
        methods_file = data_dir / "methods.json"
        if methods_file.exists():
            with open(methods_file) as f:
                self.methods = json.load(f)
            print(f"   ✅ Loaded {len(self.methods):,} methods")
        else:
            # Extract methods from nodes if methods.json doesn't exist
            self.methods = [n for n in self.nodes if n.get('_label') == 'METHOD' 
                          and not n.get('isExternal', False)]
            print(f"   ✅ Extracted {len(self.methods):,} methods from nodes")
        
        # Load source files if directory provided
        if source_dir and Path(source_dir).exists():
            print(f"\n📁 Loading source files from: {source_dir}")
            self._load_source_files(source_dir)
            print(f"   ✅ Loaded {len(self.source_files)} source files")
    
    def _load_source_files(self, source_dir: str):
        """Load source files for code extraction."""
        source_path = Path(source_dir)
        extensions = ['.py', '.java', '.js', '.ts', '.c', '.cpp', '.h', '.go', '.php', '.rb']
        
        for ext in extensions:
            for file_path in source_path.rglob(f'*{ext}'):
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                    rel_path = str(file_path.relative_to(source_path.parent))
                    self.source_files[rel_path] = content
                except Exception:
                    continue
    
    def build_graph_index(self):
        """Build efficient lookup structures for graph traversal."""
        print("\n🏗️ Building graph indexes...")
        
        self.graph_index = {
            'id_to_node': {node['id']: node for node in self.nodes},
            'outgoing': defaultdict(list),
            'incoming': defaultdict(list)
        }
        
        for edge in self.edges:
            src, dst, label = edge.get('src'), edge.get('dst'), edge.get('label', '')
            self.graph_index['outgoing'][src].append((dst, label))
            self.graph_index['incoming'][dst].append((src, label))
        
        print(f"   ✅ Indexed {len(self.nodes):,} nodes and {len(self.edges):,} edges")
    
    def extract_fault_features(self, method: Dict, code: str = None) -> Dict:
        """Extract fault-related features from method code."""
        features = {
            'has_null_checks': False,
            'has_exception_handling': False,
            'opens_resources': False,
            'closes_resources': False,
            'validates_inputs': False,
            'unsafe_operations': [],
            'complexity_score': 0
        }
        
        code = code or method.get('code', '') or ''
        if not code:
            return features
        
        code_lower = code.lower()
        
        # Null/None checks
        features['has_null_checks'] = any(p in code_lower for p in 
            ['is none', '== none', '!= none', 'if not ', 'is not none'])
        
        # Exception handling
        features['has_exception_handling'] = 'try:' in code or 'except' in code or 'finally:' in code
        
        # Resource management
        features['opens_resources'] = any(p in code_lower for p in 
            ['open(', 'connect(', 'socket(', 'cursor(', 'session('])
        features['closes_resources'] = any(p in code_lower for p in 
            ['.close()', 'with ', 'context', '__exit__'])
        
        # Input validation
        features['validates_inputs'] = any(p in code_lower for p in 
            ['assert', 'isinstance(', 'if not ', 'raise valueerror', 'raise typeerror'])
        
        # Unsafe operations
        unsafe = []
        if 'eval(' in code: unsafe.append('eval')
        if 'exec(' in code: unsafe.append('exec')
        if 'pickle.loads' in code: unsafe.append('pickle.loads')
        if 'subprocess.shell=true' in code_lower: unsafe.append('shell=True')
        if 'sql' in code_lower and ('+' in code or 'format' in code or 'f"' in code):
            unsafe.append('potential_sql_injection')
        features['unsafe_operations'] = unsafe
        
        # Complexity (simple heuristic)
        branches = sum(code.count(kw) for kw in ['if ', 'elif ', 'for ', 'while ', 'except'])
        features['complexity_score'] = branches * 2 + len(unsafe) * 10
        
        return features
    
    def get_full_source_code(self, method: Dict) -> str:
        """Get full source code for a method from source files."""
        filename = method.get('filename', '')
        line_number = method.get('lineNumber', 0)
        
        # Find matching file
        file_content = None
        for path, content in self.source_files.items():
            if filename in path:
                file_content = content
                break
        
        if not file_content:
            return method.get('code', '') or ''
        
        # Extract method by indentation
        lines = file_content.split('\n')
        if line_number <= 0 or line_number > len(lines):
            return method.get('code', '') or ''
        
        start = line_number - 1
        if start < len(lines):
            start_indent = len(lines[start]) - len(lines[start].lstrip())
            end = start
            
            for i in range(start + 1, min(len(lines), start + 200)):
                line = lines[i]
                if line.strip():
                    indent = len(line) - len(line.lstrip())
                    if indent <= start_indent and line.strip().startswith(('def ', 'class ', 'async def ')):
                        end = i - 1
                        break
                end = i
            
            return '\n'.join(lines[start:end + 1])
        
        return method.get('code', '') or ''
    
    def get_graph_context(self, node_id: int, depth: int = 1) -> Dict:
        """Get graph context (calls and callers) for a node."""
        context = {'calls': [], 'called_by': []}
        
        # Get outgoing calls
        for dst_id, label in self.graph_index['outgoing'].get(node_id, []):
            if label == 'CALL':
                dst_node = self.graph_index['id_to_node'].get(dst_id)
                if dst_node and dst_node.get('name'):
                    context['calls'].append(dst_node['name'])
        
        # Get incoming calls
        for src_id, label in self.graph_index['incoming'].get(node_id, []):
            if label == 'CALL':
                src_node = self.graph_index['id_to_node'].get(src_id)
                if src_node and src_node.get('_label') == 'METHOD':
                    context['called_by'].append(src_node.get('name', ''))
        
        return context
    
    def enrich_methods(self):
        """Enrich methods with code, graph context, and fault features."""
        print("\n🎯 Enriching methods...")
        
        self.enriched_methods = []
        for method in tqdm(self.methods, desc="Processing"):
            full_code = self.get_full_source_code(method)
            graph_ctx = self.get_graph_context(method.get('id', 0))
            fault_features = self.extract_fault_features(method, full_code)
            
            self.enriched_methods.append({
                'id': method.get('id', 0),
                'name': method.get('name', 'unknown'),
                'fullName': method.get('fullName', ''),
                'filename': method.get('filename', ''),
                'lineNumber': method.get('lineNumber', 0),
                'lineNumberEnd': method.get('lineNumberEnd', 0),
                'line_count': method.get('line_count', 0),
                'full_code': full_code,
                'calls': graph_ctx['calls'],
                'called_by': graph_ctx['called_by'],
                'fault_features': fault_features
            })
        
        print(f"   ✅ Enriched {len(self.enriched_methods):,} methods")
    
    def create_semantic_context(self, method: Dict) -> str:
        """Create context for semantic understanding."""
        parts = [
            f"Function: {method['name']}",
            f"File: {method['filename']}:{method['lineNumber']}"
        ]
        
        code = method.get('full_code', '')
        if code:
            if len(code) > self.config.MAX_CODE_LENGTH:
                code = code[:self.config.MAX_CODE_LENGTH] + "\n# ... (truncated)"
            parts.append(f"\n{code}")
        
        if method.get('calls'):
            parts.append(f"\nCalls: {', '.join(method['calls'][:8])}")
        
        return "\n".join(parts)
    
    def create_fault_context(self, method: Dict) -> str:
        """Create context for fault detection."""
        parts = [
            f"Function: {method['name']}",
            f"File: {method['filename']}:{method['lineNumber']}"
        ]
        
        ff = method.get('fault_features', {})
        
        issues = []
        if not ff.get('has_null_checks'):
            issues.append("No null/None checks detected")
        if not ff.get('has_exception_handling'):
            issues.append("No try/except blocks")
        if ff.get('opens_resources') and not ff.get('closes_resources'):
            issues.append("Opens resources but no .close() detected")
        if ff.get('unsafe_operations'):
            issues.append(f"Uses: {', '.join(ff['unsafe_operations'])}")
        
        if issues:
            parts.append(f"\nObserved patterns: {'; '.join(issues)}")
        
        code = method.get('full_code', '')
        if code:
            if len(code) > 800:
                code = code[:800] + "\n# ..."
            parts.append(f"\n{code}")
        
        return "\n".join(parts)
    
    def create_structural_context(self, method: Dict) -> str:
        """Create context for structural analysis."""
        parts = [
            f"Function: {method['name']}",
            f"File: {method['filename']}"
        ]
        
        if method.get('calls'):
            parts.append(f"Calls ({len(method['calls'])}): {', '.join(method['calls'][:12])}")
        
        if method.get('called_by'):
            parts.append(f"Called by ({len(method['called_by'])}): {', '.join(method['called_by'][:8])}")
        
        return "\n".join(parts)
    
    def init_embeddings(self):
        """Initialize Ollama embeddings."""
        print("\n🚀 Initializing Ollama embeddings...")
        
        # Suppress warnings during instantiation - use action='ignore' for maximum suppression
        with warnings.catch_warnings(record=False):
            warnings.simplefilter("ignore", DeprecationWarning)
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            warnings.filterwarnings("ignore", message=".*deprecated.*")
            warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")
            self.embeddings = OllamaEmbeddings(
                model=self.config.OLLAMA_EMBEDDING_MODEL,
                base_url=self.config.OLLAMA_BASE_URL
            )
        
        # Test embeddings
        try:
            test_embedding = self.embeddings.embed_query("test")
            print(f"   ✅ Embeddings ready (dimension: {len(test_embedding)})")
        except Exception as e:
            print(f"   ❌ Failed to initialize embeddings: {e}")
            print("   Make sure Ollama is running: ollama serve")
            print(f"   And pull the model: ollama pull {self.config.OLLAMA_EMBEDDING_MODEL}")
            raise
    
    def create_vector_stores(self, force_recreate: bool = False):
        """Create ChromaDB vector stores."""
        print("\n💾 Creating vector stores...")
        
        chroma_dir = self.config.CHROMA_DIR
        
        # Remove existing if force recreate
        if force_recreate and chroma_dir.exists():
            print("   🗑️ Removing existing vector stores...")
            shutil.rmtree(chroma_dir)
        
        chroma_dir.mkdir(parents=True, exist_ok=True)
        
        # Create semantic store
        print("   1️⃣ Creating semantic store...")
        semantic_docs = [
            Document(
                page_content=self.create_semantic_context(m),
                metadata={
                    'id': str(m['id']),
                    'name': m['name'],
                    'filename': m['filename'],
                    'line_number': m['lineNumber']
                }
            ) for m in tqdm(self.enriched_methods, desc="Semantic", leave=False)
        ]
        
        self.vector_stores['semantic'] = Chroma.from_documents(
            semantic_docs,
            self.embeddings,
            persist_directory=str(chroma_dir),
            collection_name=self.config.SEMANTIC_COLLECTION
        )
        
        # Create structural store
        print("   2️⃣ Creating structural store...")
        structural_docs = [
            Document(
                page_content=self.create_structural_context(m),
                metadata={
                    'id': str(m['id']),
                    'name': m['name'],
                    'filename': m['filename'],
                    'num_calls': len(m.get('calls', []))
                }
            ) for m in tqdm(self.enriched_methods, desc="Structural", leave=False)
        ]
        
        self.vector_stores['structural'] = Chroma.from_documents(
            structural_docs,
            self.embeddings,
            persist_directory=str(chroma_dir),
            collection_name=self.config.STRUCTURAL_COLLECTION
        )
        
        # Create fault detection store
        print("   3️⃣ Creating fault detection store...")
        fault_docs = [
            Document(
                page_content=self.create_fault_context(m),
                metadata={
                    'id': str(m['id']),
                    'name': m['name'],
                    'filename': m['filename'],
                    'line_number': m['lineNumber'],
                    'has_null_checks': m['fault_features'].get('has_null_checks', False),
                    'has_exception_handling': m['fault_features'].get('has_exception_handling', False)
                }
            ) for m in tqdm(self.enriched_methods, desc="Fault", leave=False)
        ]
        
        self.vector_stores['fault'] = Chroma.from_documents(
            fault_docs,
            self.embeddings,
            persist_directory=str(chroma_dir),
            collection_name=self.config.FAULT_COLLECTION
        )
        
        total_docs = len(semantic_docs) + len(structural_docs) + len(fault_docs)
        print(f"\n   ✅ Created {total_docs} embeddings across 3 stores")
    
    def save_enriched_methods(self, output_path: Path = None):
        """Save enriched methods for later use."""
        output_path = output_path or self.config.DATA_DIR / "enriched_methods.json"
        
        with open(output_path, 'w') as f:
            json.dump(self.enriched_methods, f, indent=2)
        
        print(f"   ✅ Saved enriched methods to {output_path}")
    
    def run(self, data_dir: Path = None, source_dir: Path = None, force_recreate: bool = False):
        """Run the complete RAG setup pipeline."""
        print("=" * 60)
        print("Step 3: Setup RAG System")
        print("=" * 60)
        
        # Load data
        self.load_data(data_dir, source_dir)
        
        if not self.methods:
            print("❌ Error: No methods found! Run step 2 first.")
            return False
        
        # Build graph index
        self.build_graph_index()
        
        # Enrich methods
        self.enrich_methods()
        
        # Initialize embeddings
        self.init_embeddings()
        
        # Create vector stores
        self.create_vector_stores(force_recreate)
        
        # Save enriched methods
        self.save_enriched_methods()
        
        # Print summary
        print("\n" + "=" * 60)
        print("✅ Step 3 Complete!")
        print("=" * 60)
        print(f"\n📊 Summary:")
        print(f"   Methods processed: {len(self.enriched_methods):,}")
        print(f"   Vector stores: 3 (semantic, structural, fault)")
        print(f"   ChromaDB path: {self.config.CHROMA_DIR}")
        print("\nNext step:")
        print("    python step4_query_rag.py --query 'Find SQL injection vulnerabilities'")
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Setup RAG system with vector stores",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--data-dir", "-d",
        default="data/",
        help="Directory containing CPG JSON files (default: data/)"
    )
    parser.add_argument(
        "--source-dir", "-s",
        help="Path to source code directory (for code extraction)"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force recreate vector stores"
    )
    
    args = parser.parse_args()
    
    setup = RAGSetup()
    success = setup.run(
        data_dir=Path(args.data_dir) if args.data_dir else None,
        source_dir=Path(args.source_dir) if args.source_dir else None,
        force_recreate=args.force
    )
    
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
