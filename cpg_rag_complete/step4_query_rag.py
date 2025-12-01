#!/usr/bin/env python3
"""
Step 4: RAG Query Engine — Focused, Code-Grounded Answers

Improvements:
- Better deduplication (removes <metaClassAdapter> duplicates)
- More focused prompts (less verbose, more specific)
- Project-aware context
- Concise output format
"""

import argparse
import json
import re
import sys
import warnings
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

# Suppress all deprecation warnings from langchain BEFORE importing
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*deprecated.*")
warnings.filterwarnings("ignore", message=".*LangChainDeprecationWarning.*")

# Use new packages to avoid deprecation warnings
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", message=".*deprecated.*")
    try:
        from langchain_ollama import OllamaEmbeddings, ChatOllama
        from langchain_chroma import Chroma
    except ImportError:
        # Fallback to old imports for compatibility
        from langchain_community.vectorstores import Chroma
        from langchain_community.embeddings import OllamaEmbeddings
        from langchain_community.chat_models import ChatOllama

from config import Config


class RAGQueryEngine:
    """RAG Query Engine with focused, code-grounded answers."""

    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.embeddings = None
        self.llm = None
        self.vector_stores = {}
        self._initialized = False
        self.enriched_methods = []
        self.codebase_stats = {}

    def initialize(self):
        if self._initialized:
            return

        print("🚀 Initializing RAG Query Engine...")

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

            self.llm = ChatOllama(
                model=self.config.OLLAMA_MODEL,
                temperature=self.config.OLLAMA_TEMPERATURE,
                base_url=self.config.OLLAMA_BASE_URL
            )

            chroma_dir = str(self.config.CHROMA_DIR)

            self.vector_stores['semantic'] = Chroma(
                persist_directory=chroma_dir,
                embedding_function=self.embeddings,
                collection_name=self.config.SEMANTIC_COLLECTION
            )
            self.vector_stores['structural'] = Chroma(
                persist_directory=chroma_dir,
                embedding_function=self.embeddings,
                collection_name=self.config.STRUCTURAL_COLLECTION
            )
            self.vector_stores['fault'] = Chroma(
                persist_directory=chroma_dir,
                embedding_function=self.embeddings,
                collection_name=self.config.FAULT_COLLECTION
            )

        enriched_path = self.config.DATA_DIR / "enriched_methods.json"
        if enriched_path.exists():
            with open(enriched_path) as f:
                self.enriched_methods = json.load(f)

        stats_path = self.config.DATA_DIR / "codebase_stats.json"
        if stats_path.exists():
            with open(stats_path) as f:
                self.codebase_stats = json.load(f)

        # Test LLM (with better error handling)
        try:
            response = self.llm.invoke("Say 'Ready'")
            print(f"   ✅ LLM ready")
        except Exception as e:
            error_msg = str(e)
            print(f"   ❌ LLM error: {error_msg}")
            # Provide helpful error messages
            if "status code 500" in error_msg or "runner process has terminated" in error_msg:
                print(f"   💡 Tip: Ollama model may have crashed. Try:")
                print(f"      - Restart Ollama: pkill ollama && ollama serve")
                print(f"      - Check model: ollama show llama3.2")
                print(f"      - Re-pull model: ollama pull llama3.2")
            elif "Connection refused" in error_msg or "Failed to connect" in error_msg:
                print(f"   💡 Tip: Ollama is not running. Start it with: ollama serve")
            raise

        self._initialized = True
        print("   ✅ RAG Query Engine ready!")

    def _detect_query_type(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in ['vulnerab', 'injection', 'xss', 'unsafe', 'exploit', 'security', 'bug', 'leak', 'error']):
            return 'fault'
        if any(w in q for w in ['who calls', 'called by', 'call graph', 'dependency', 'depends']):
            return 'structural'
        return 'semantic'

    def _get_project_context(self) -> str:
        """Build project-specific context from stats and methods."""
        if not self.codebase_stats:
            return "Unknown project"
        
        s = self.codebase_stats
        
        # Try to infer project name from largest files
        main_files = []
        if s.get('largest_methods'):
            for m in s['largest_methods'][:3]:
                main_files.append(m.get('filename', ''))
        
        # Detect project type
        project_hints = []
        all_files = list(s.get('files', {}).keys())
        file_str = ' '.join(all_files).lower()
        
        if 'medsam' in file_str or 'segment_anything' in file_str:
            project_hints.append("MedSAM - Medical image segmentation using SAM (Segment Anything Model)")
        if 'train' in file_str:
            project_hints.append("Includes training functionality")
        if 'inference' in file_str:
            project_hints.append("Includes inference/prediction")
        
        ctx = f"""PROJECT: {', '.join(project_hints) if project_hints else 'Python codebase'}
STATS: {s.get('total_files', '?')} files | {s.get('total_methods', '?')} functions | {s.get('total_lines', '?')} lines"""
        
        return ctx

    def _normalize_function_name(self, name: str) -> str:
        """Remove metaClassAdapter and other suffixes for deduplication."""
        name = re.sub(r'<metaClassAdapter>$', '', name)
        name = re.sub(r'<metaClassCallHandler>$', '', name)
        name = re.sub(r'<body>$', '', name)
        return name.strip()

    def _deduplicate_docs(self, docs: List) -> List:
        """Remove duplicate documents, including metaClassAdapter variants."""
        seen = set()
        unique = []
        
        for doc in docs:
            name = doc.metadata.get('name', '')
            filename = doc.metadata.get('filename', '')
            line = doc.metadata.get('line_number', '')
            
            # Normalize the function name
            normalized_name = self._normalize_function_name(name)
            
            # Create key with normalized name
            key = f"{filename}:{line}:{normalized_name}"
            
            if key not in seen:
                seen.add(key)
                doc.metadata['display_name'] = normalized_name if normalized_name else name
                unique.append(doc)
        
        return unique

    def query(self, question: str, query_type: str = 'auto', top_k: int = None) -> Dict:
        """Execute a RAG query with focused, code-grounded answers."""
        self.initialize()

        if query_type == 'auto':
            query_type = self._detect_query_type(question)

        q_lower = question.lower()
        is_overview = any(w in q_lower for w in ['overview', 'what is', 'summary', 'main', 'component', 'architecture', 'about'])
        
        if top_k is None:
            top_k = 20 if is_overview else 10

        docs = self.vector_stores[query_type].similarity_search(question, k=top_k)
        docs = self._deduplicate_docs(docs)

        if not docs:
            return {'answer': "No relevant code found.", 'sources': [], 'query_type': query_type}

        # Build context from deduplicated docs
        context_parts = []
        sources = []
        
        for i, doc in enumerate(docs[:8], 1):
            func = doc.metadata.get('display_name', doc.metadata.get('name', 'unknown'))
            file = doc.metadata.get('filename', 'unknown')
            line = doc.metadata.get('line_number', '?')
            
            sources.append({'function': func, 'file': file, 'line': line})
            context_parts.append(f"[{i}] {func} ({file}:{line})")
            context_parts.append(doc.page_content)
            context_parts.append("")

        context = "\n".join(context_parts)
        sources_str = "\n".join([f"[{i+1}] {s['function']} ({s['file']}:{s['line']})" for i, s in enumerate(sources)])
        project_ctx = self._get_project_context()

        prompt = self._build_prompt(question, query_type, sources_str, context, project_ctx)

        try:
            response = self.llm.invoke(prompt)
            answer = getattr(response, 'content', str(response)).strip()
        except Exception as e:
            answer = f"Error: {e}"

        return {'answer': answer, 'sources': sources, 'query_type': query_type, 'question': question}

    def _build_prompt(self, question: str, query_type: str, sources_str: str, context: str, project_ctx: str) -> str:
        """Build focused prompts based on query type."""
        
        base_rules = """RULES:
- Base ALL claims on the provided code snippets ONLY
- Cite functions as: `function_name` (file.py:line)
- Be concise and specific
- Do NOT invent functions or files"""

        if query_type == 'fault':
            return f"""{project_ctx}

TASK: Find security/quality issues in this code.

{base_rules}

QUESTION: {question}

CODE SNIPPETS:
{sources_str}

{context}

FORMAT:
**Issues Found** (or "No issues found"):
- `function` (file:line): Issue description [Severity: Low/Medium/High]

Keep it brief - just list the actual issues found."""

        elif query_type == 'structural':
            return f"""{project_ctx}

TASK: Describe code structure and relationships.

{base_rules}

QUESTION: {question}

CODE SNIPPETS:
{sources_str}

{context}

List the functions and their relationships visible in the code."""

        else:  # semantic
            return f"""{project_ctx}

TASK: Answer this question about the codebase using ONLY the provided code snippets.

{base_rules}

QUESTION: {question}

CODE SNIPPETS:
{sources_str}

{context}

FORMAT YOUR ANSWER:

**Summary**: 2-3 sentences describing what this code does (based on the snippets)

**Key Functions**:
- `function_name` (file.py:line): Brief description
[List the most relevant functions from snippets]

**How It Works**: 2-3 sentences connecting the pieces

Keep your answer focused and grounded in the actual code shown."""

    def run_full_analysis(self) -> List[Dict]:
        """Run security analysis."""
        self.initialize()
        queries = [
            ("Security Issues", "Find security vulnerabilities or unsafe patterns"),
            ("Resource Management", "Find potential resource leaks"),
            ("Error Handling", "Find missing error handling"),
        ]
        results = []
        print("\n🔍 Running Security Analysis...")
        for title, q in queries:
            print(f"   Checking: {title}...")
            res = self.query(q, query_type='fault')
            res['title'] = title
            results.append(res)
        return results

    def export_results(self, results: List[Dict], format: str = 'json', output_path: Path = None) -> Path:
        """Export results."""
        output_dir = self.config.OUTPUT_DIR
        output_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        if format == 'json':
            output_path = output_path or output_dir / f"analysis_{ts}.json"
            with open(output_path, 'w') as f:
                json.dump(results, f, indent=2)
        elif format in ('md', 'markdown'):
            output_path = output_path or output_dir / f"analysis_{ts}.md"
            with open(output_path, 'w') as f:
                f.write("# Code Analysis Report\n\n")
                for r in results:
                    f.write(f"## {r.get('title', r.get('question',''))}\n\n")
                    f.write(r.get('answer', '') + "\n\n---\n\n")
        elif format == 'csv':
            import csv
            output_path = output_path or output_dir / f"analysis_{ts}.csv"
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Title', 'Type', 'Function', 'File', 'Line'])
                for r in results:
                    for s in r['sources']:
                        writer.writerow([r.get('title',''), r['query_type'], s['function'], s['file'], s['line']])
        
        print(f"   ✅ Saved to {output_path}")
        return output_path


def interactive_mode(engine: RAGQueryEngine):
    """Interactive query mode."""
    print("\n" + "=" * 50)
    print("🔍 CPG RAG Interactive Mode")
    print("=" * 50)
    print("Commands: /quit | /stats | /type <semantic|structural|fault>")
    print("=" * 50 + "\n")
    
    query_type = 'auto'
    
    while True:
        try:
            question = input("❓ ").strip()
            if not question:
                continue
            
            if question.lower() in ('/quit', '/exit', 'quit', 'exit'):
                print("👋 Goodbye!")
                break
            
            if question.startswith('/type'):
                parts = question.split()
                if len(parts) > 1 and parts[1] in ('semantic', 'structural', 'fault', 'auto'):
                    query_type = parts[1]
                    print(f"   Type set to: {query_type}")
                continue
            
            if question == '/stats':
                s = engine.codebase_stats
                if s:
                    print(f"\n📊 {s.get('total_files','?')} files | {s.get('total_methods','?')} functions | {s.get('total_lines','?')} lines\n")
                continue
            
            if question == '/help':
                print("Commands: /quit | /stats | /type <semantic|structural|fault|auto>")
                continue

            print("\n🔄 Searching...\n")
            res = engine.query(question, query_type=query_type)
            
            print(f"📊 Type: {res['query_type']} | Sources: {len(res['sources'])}")
            print("-" * 50)
            print(res['answer'])
            print("-" * 50)
            print("Sources:")
            for s in res['sources'][:5]:
                print(f"  • {s['function']} ({s['file']}:{s['line']})")
            if len(res['sources']) > 5:
                print(f"  ... and {len(res['sources'])-5} more")
            print()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


def main():
    parser = argparse.ArgumentParser(description="Query RAG system")
    parser.add_argument('--query', '-q', help='Query')
    parser.add_argument('--type', '-t', choices=['auto', 'semantic', 'structural', 'fault'], default='auto')
    parser.add_argument('--interactive', '-i', action='store_true')
    parser.add_argument('--all', '-a', action='store_true', help='Run full analysis')
    parser.add_argument('--export', '-e', choices=['json', 'md', 'csv'])
    parser.add_argument('--top-k', '-k', type=int, default=8)
    args = parser.parse_args()

    engine = RAGQueryEngine()

    if args.interactive:
        engine.initialize()
        interactive_mode(engine)
    elif args.all:
        results = engine.run_full_analysis()
        for r in results:
            print(f"\n{'='*50}\n{r.get('title')}\n{'='*50}")
            print(r.get('answer', '')[:1000])
        if args.export:
            engine.export_results(results, format=args.export)
    elif args.query:
        res = engine.query(args.query, query_type=args.type, top_k=args.top_k)
        # Print answer without extra headers
        print(res['answer'])
        if args.export:
            engine.export_results([res], format=args.export)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()