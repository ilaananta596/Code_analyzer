#!/usr/bin/env python3
"""
Step 4: Enhanced RAG Query Engine with Hybrid Retrieval & Graph Expansion

Features:
- Multi-store retrieval (semantic, structural, fault, hybrid)
- Weighted merging of results with keyword re-ranking
- Graph-based expansion (expand retrieved methods by call graph neighbors)
- Improved prompt engineering with strict grounding rules
- Interactive CLI and single query modes
"""

import argparse
import json
import logging
import os
import re
from collections import defaultdict, Counter, deque
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Disable Chroma/PostHog telemetry for local runs
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "1")

# LangChain community wrappers
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.chat_models import ChatOllama
from langchain.docstore.document import Document

from config import Config

# Logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("step4_query_rag")

# -------------------------
# Utilities
# -------------------------
def simple_keyword_score(text: str, keywords: List[str]) -> int:
    t = (text or "").lower()
    return sum(t.count(k.lower()) for k in keywords)

def normalize_text(s: str) -> str:
    return (s or "").strip()

def extract_quoted(query: str) -> Optional[str]:
    m = re.search(r'["\']([^"\']+)["\']', query)
    return m.group(1) if m else None

# -------------------------
# Enhanced RAG Query Engine
# -------------------------
class EnhancedRAGQueryEngine:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        self.embeddings = None
        self.llm = None
        self.vector_stores: Dict[str, Optional[Chroma]] = {
            "semantic": None,
            "structural": None,
            "fault": None,
            "hybrid": None
        }
        self._initialized = False

        # enriched methods (populated from data_dir)
        self.enriched_methods: List[Dict] = []
        self.method_by_id: Dict[int, Dict] = {}
        self.methods_by_file: Dict[str, List[Dict]] = defaultdict(list)
        self.all_method_names: List[str] = []

    # -------------------------
    # Initialization & loading
    # -------------------------
    def initialize(self):
        if self._initialized:
            return

        logger.info(" Initializing Enhanced RAG Query Engine...")

        # Initialize embeddings & LLM
        try:
            self.embeddings = OllamaEmbeddings(
                model=self.config.OLLAMA_EMBEDDING_MODEL,
                base_url=self.config.OLLAMA_BASE_URL
            )
            self.llm = ChatOllama(
                model=self.config.OLLAMA_MODEL,
                temperature=self.config.OLLAMA_TEMPERATURE,
                base_url=self.config.OLLAMA_BASE_URL
            )
        except Exception as e:
            logger.error("Failed to initialize Ollama embeddings/LLM: %s", e)
            raise

        chroma_dir = str(self.config.CHROMA_DIR)

        def load_store(name: str) -> Optional[Chroma]:
            try:
                # Using Chroma constructor compatible with the rest of pipeline
                return Chroma(
                    persist_directory=chroma_dir,
                    embedding_function=self.embeddings,
                    collection_name=name
                )
            except Exception as e:
                logger.warning("Could not load Chroma collection '%s': %s", name, e)
                return None

        # load all four stores (some may be missing)
        self.vector_stores["semantic"] = load_store(self.config.SEMANTIC_COLLECTION)
        self.vector_stores["structural"] = load_store(self.config.STRUCTURAL_COLLECTION)
        self.vector_stores["fault"] = load_store(self.config.FAULT_COLLECTION)
        # new hybrid collection
        hybrid_name = getattr(self.config, "HYBRID_COLLECTION", "cpg_hybrid")
        self.vector_stores["hybrid"] = load_store(hybrid_name)

        # Load enriched methods & stats
        enriched_path = Path(self.config.DATA_DIR) / "enriched_methods.json"
        if enriched_path.exists():
            try:
                with open(enriched_path, "r", encoding="utf-8") as fh:
                    self.enriched_methods = json.load(fh)
                    for method in self.enriched_methods:
                        mid = int(method.get("id") or 0)
                        self.method_by_id[mid] = method
                        fname = method.get("filename", "")
                        self.methods_by_file[fname].append(method)
                        name = method.get("display_name") or method.get("name", "")
                        if name:
                            self.all_method_names.append(name)
                logger.info(" Loaded %d enriched methods", len(self.enriched_methods))
            except Exception as e:
                logger.warning("Failed to load enriched_methods.json: %s", e)
        else:
            logger.warning("enriched_methods.json not found in %s", self.config.DATA_DIR)

        # Load stats if available
        stats_path = Path(self.config.DATA_DIR) / "codebase_stats.json"
        try:
            if stats_path.exists():
                with open(stats_path, "r", encoding="utf-8") as fh:
                    self.codebase_stats = json.load(fh)
            else:
                self.codebase_stats = {}
        except Exception:
            self.codebase_stats = {}

        # LLM smoke test
        try:
            self.llm.invoke("Ready?")
            logger.info(" LLM ready")
        except Exception as e:
            logger.error("LLM initialization error: %s", e)
            raise

        logger.info(" Enhanced RAG Query Engine ready!")
        self._initialized = True

    # -------------------------
    # Preprocess query
    # -------------------------
    def _preprocess_query(self, query: str) -> Dict:
        q = query.strip()
        m = {
            "original": query,
            "clean": q,
            "is_valid": len(q) >= 3,
            "is_overview": False,
            "is_listing": False,
            "specific_entity": extract_quoted(q)
        }

        # overview detection
        overview_patterns = [
            r'\b(overview|summary|summarize|describe|explain)\b',
            r'\bproject structure\b',
            r'\bmain components\b',
            r'\bkey functions\b'
        ]
        for p in overview_patterns:
            if re.search(p, q.lower()):
                m["is_overview"] = True
                break

        # listing detection
        if re.search(r'\b(list|show|find|which|what)\b', q.lower()):
            m["is_listing"] = True

        return m

    # -------------------------
    # Query type detection
    # -------------------------
    def _detect_query_type(self, query: str, metadata: Dict) -> str:
        if metadata.get("is_overview"):
            return "overview"

        q = query.lower()
        fault_keywords = [
            "vulnerab", "injection", "xss", "csrf", "unsafe", "exploit",
            "bug", "leak", "overflow", "race", "deadlock", "sanitize",
            "validation", "attack", "security", "eval(", "exec(", "pickle", "subprocess"
        ]
        structural_keywords = [
            "call graph", "who calls", "called by", "calls", "caller", "callee",
            "dependency", "depends on", "data flow", "control flow", "pipeline",
            "path", "trace", "used in", "imports"
        ]
        if any(w in q for w in fault_keywords):
            return "fault"
        if any(w in q for w in structural_keywords):
            return "structural"
        return "semantic"

    # -------------------------
    # Literal lookup
    # -------------------------
    def _literal_lookup(self, question: str) -> Optional[Dict]:
        literal = extract_quoted(question)
        if not literal:
            # fallback: if user wrote <name> syntax
            m = re.findall(r'<([^>]+)>', question)
            if m:
                literal = m[0]
        if not literal:
            return None

        needle = literal.strip().lower()
        matches = []
        for m in self.enriched_methods:
            name = (m.get("display_name") or m.get("name") or "").lower()
            if needle in name:
                matches.append(m)

        if not matches:
            return {"query_type": "literal", "answer": f"No method matching '<{needle}>' found in this codebase.", "sources": []}

        parts = [f"Found {len(matches)} function(s) matching '<{needle}>':\n"]
        sources = []
        for i, m in enumerate(matches[:20], 1):
            name = m.get("display_name") or m.get("name", "?")
            fname = m.get("filename", "?")
            line = m.get("lineNumber") or "?"
            parts.append(f"\n{i}. {name} ({fname}:{line})")
            snippet = (m.get("full_code") or "").strip().splitlines()
            if snippet:
                parts.append("\n    " + "\n    ".join(snippet[:6]))
            sources.append({"function": name, "file": fname, "line": line})
        return {"query_type": "literal", "answer": "\n".join(parts), "sources": sources}

    # -------------------------
    # Multi-store retrieval (hybrid merge + weights)
    # -------------------------
    def _retrieve_from_store(self, store: Optional[Chroma], query: str, top_k: int) -> List:
        if not store:
            return []
        try:
            return store.similarity_search(query, k=top_k)
        except Exception as e:
            logger.debug("Store retrieval error: %s", e)
            return []

    def _merge_and_score(self, retrieved: Dict[str, List], query: str, query_type: str, top_k: int) -> List:
        """
        Merge docs from multiple stores and compute a combined score.
        Approach:
          - position-based embedding proxy score (rank -> score)
          - presence in multiple stores increases score
          - keyword scoring adds small boost (especially for fault queries)
          - graph expansion will be applied afterwards
        """
        # weights by store per query_type
        default_weights = {
            "semantic": 0.4,
            "structural": 0.25,
            "fault": 0.1,
            "hybrid": 0.25
        }
        structural_focus = {
            "semantic": 0.2,
            "structural": 0.6,
            "fault": 0.05,
            "hybrid": 0.15
        }
        fault_focus = {
            "semantic": 0.1,
            "structural": 0.1,
            "fault": 0.6,
            "hybrid": 0.2
        }
        if query_type == "structural":
            weights = structural_focus
        elif query_type == "fault":
            weights = fault_focus
        else:
            weights = default_weights

        # collect candidates
        candidate_scores = defaultdict(float)
        candidate_docs = {}

        # position-based base scores
        for store_name, docs in retrieved.items():
            w = weights.get(store_name, 0.0)
            for rank, doc in enumerate(docs):
                # proxy embedding score: higher rank -> higher base
                base_score = max(0.0, 1.0 - (rank / max(1, len(docs))))
                # accumulate scaled by weight
                key_meta = getattr(doc, "metadata", {}) or {}
                key = f"{key_meta.get('filename','?')}:{key_meta.get('line_number','?')}:{key_meta.get('display_name','?')}"
                candidate_scores[key] += base_score * w
                # prefer first seen doc for content
                if key not in candidate_docs:
                    candidate_docs[key] = doc

        # keyword rerank for fault queries
        if query_type == "fault":
            keywords = ['unsafe','security','validate','sanitize','error','exception','try','handle','pickle','eval','exec','subprocess','shell']
        else:
            # include tokens from query that look like identifiers
            tokens = re.findall(r"[A-Za-z_][A-Za-z0-9_]+", query.lower())
            keywords = tokens[-10:] if tokens else []

        # apply keyword boost
        for key, doc in candidate_docs.items():
            content = getattr(doc, "page_content", "") or ""
            kw_score = simple_keyword_score(content, keywords)
            # small normalized boost
            candidate_scores[key] += 0.02 * kw_score

        # create sorted list
        ranked = sorted(candidate_scores.items(), key=lambda x: x[1], reverse=True)

        # convert to list of docs with score
        results = []
        for key, score in ranked[: top_k * 3]:
            doc = candidate_docs.get(key)
            if doc:
                results.append((score, doc))

        return results

    # -------------------------
    # Graph expansion: expand retrieved methods by neighbors up to hops
    # -------------------------
    def _graph_expand(self, scored_docs: List[Tuple[float, Document]], hops: int = 1, max_add: int = 20) -> List[Tuple[float, Document]]:
        """
        Given a list of (score, doc), expand by adding neighbors (calls and called_by)
        using enriched_methods adjacency info.
        """
        added = []
        seen_ids = set()
        # build initial queue from doc metadata method_id if present
        queue = deque()
        for score, doc in scored_docs:
            md = getattr(doc, "metadata", {}) or {}
            mid = int(md.get("method_id") or 0)
            if mid:
                queue.append((mid, score, 0))
                seen_ids.add(mid)

        while queue and len(added) < max_add:
            mid, base_score, depth = queue.popleft()
            if depth >= hops:
                continue
            method = self.method_by_id.get(mid)
            if not method:
                continue
            # neighbors
            neighbors = []
            for c in method.get("calls_full", [])[:50]:
                nid = int(c.get("id") or 0)
                if nid and nid not in seen_ids:
                    neighbors.append(nid)
            for c in method.get("called_by_full", [])[:50]:
                nid = int(c.get("id") or 0)
                if nid and nid not in seen_ids:
                    neighbors.append(nid)
            for nid in neighbors:
                seen_ids.add(nid)
                nmethod = self.method_by_id.get(nid)
                if not nmethod:
                    continue
                meta = {
                    "display_name": nmethod.get("display_name"),
                    "filename": nmethod.get("filename"),
                    "line_number": nmethod.get("lineNumber"),
                    "method_id": nmethod.get("id")
                }
                content = nmethod.get("full_code") or ""
                doc = Document(page_content=content, metadata=meta)
                # neighbor score decays with depth
                added.append((base_score * (0.6 ** (depth + 1)), doc))
                # queue further expansion
                queue.append((nid, base_score * (0.6 ** (depth + 1)), depth + 1))
                if len(added) >= max_add:
                    break

        # merge original scored_docs with added neighbors
        combined = list(scored_docs) + added
        # deduplicate by metadata key
        seen = set()
        out = []
        for score, doc in sorted(combined, key=lambda x: x[0], reverse=True):
            md = getattr(doc, "metadata", {}) or {}
            key = f"{md.get('filename','?')}:{md.get('line_number','?')}:{md.get('display_name','?')}"
            if key not in seen:
                seen.add(key)
                out.append((score, doc))
        return out

    # -------------------------
    # Deduplicate and prepare context blocks
    # -------------------------
    def _prepare_context_blocks(self, scored_docs: List[Tuple[float, Document]], max_blocks: int = 12) -> Tuple[str, List[Dict]]:
        blocks = []
        sources = []
        taken = 0
        for score, doc in scored_docs:
            if taken >= max_blocks:
                break
            md = getattr(doc, "metadata", {}) or {}
            name = md.get("display_name") or md.get("name") or "?"
            fname = md.get("filename") or "?"
            line = md.get("line_number") or md.get("lineNumber") or "?"
            content = getattr(doc, "page_content", "") or ""
            # trim long code
            if len(content) > self.config.MAX_CODE_LENGTH:
                content = content[: self.config.MAX_CODE_LENGTH] + "\n\n... (truncated)"
            block = f"""[{taken+1}] Function: {name}
    Location: {fname}:{line}
    Code:
{content}
"""
            blocks.append(block)
            sources.append({"function": name, "file": fname, "line": line})
            taken += 1
        context = "\n".join(blocks)
        return context, sources

    # -------------------------
    # Prompt builder (strict grounding rules)
    # -------------------------
    def _build_prompt(self, question: str, query_type: str, context: str) -> str:
        project_ctx = self._get_project_overview()
        if query_type == "fault":
            task_instruction = """
TASK: Security & Fault Analysis
Analyze the provided code for:
- Security vulnerabilities (injection, insecure deserialization, shell calls, unsafe eval/exec)
- Missing input validation or sanitization
- Error handling issues (missing try/except, unhandled exceptions)
- Resource leaks or unsafe operations (pickle, subprocess, open without context manager)

Be specific about:
- What the vulnerability or issue is
- Where it occurs (file:line)
- Why it's dangerous
- How to fix it (concrete code-level fixes)
"""
        elif query_type == "structural":
            task_instruction = """
TASK: Structural Analysis
Analyze relationships and dependencies:
- Call graph (who calls what)
- Data flow and key dependencies
- Execution path highlights

Be specific:
- Provide direct call chains if possible (A -> B -> C)
- Cite exact function names and locations
"""
        else:
            task_instruction = """
TASK: Code Behavior Analysis
Explain what the code does and how it works, focusing on:
- Key responsibilities of functions
- Data structures and algorithms used
- Any notable design patterns
"""

        strict_rules = """
CRITICAL RULES:
1. Base your answer ONLY on the provided code snippets in the context block.
2. If information is not present in the provided snippets, explicitly state: "Not found in provided code."
3. DO NOT invent functionality or make assumptions beyond the provided code.
4. Cite specific functions with format: function_name (file.py:line)
5. Keep answers concise and include a short summary, then a detailed bullet list.
"""

        response_format = """
RESPONSE FORMAT:
1) Short direct answer (1-3 sentences)
2) Detailed analysis with bullet points
3) Function citations: name (file:line)
4) If insufficient evidence, state exactly: "Not found in provided code."
"""

        prompt = f"""
PROJECT CONTEXT:
{project_ctx}

{task_instruction}

{strict_rules}

USER QUESTION:
{question}

RETRIEVED CODE CONTEXT:
{context}

{response_format}

Answer:
"""
        return prompt.strip()

    def _get_project_overview(self) -> str:
        s = getattr(self, "codebase_stats", {}) or {}
        ctx = f"Total Files: {s.get('total_files','?')}, Total Methods: {s.get('total_methods','?')}, Total Lines: {s.get('total_lines','?')}"
        return ctx

    # -------------------------
    # Main query method
    # -------------------------
    def query(self, question: str, query_type: str = "auto", top_k: int = 15) -> Dict:
        self.initialize()

        processed = self._preprocess_query(question)
        if not processed["is_valid"]:
            return {"answer": "Query too short or invalid. Please provide a more specific question.", "sources": [], "query_type": "invalid", "question": question}

        # literal lookup
        literal = self._literal_lookup(question)
        if literal:
            return literal

        if query_type == "auto":
            query_type = self._detect_query_type(processed["clean"], processed)

        if query_type == "overview":
            # special overview handler
            return self._handle_overview(question)

        # Retrieve from each available store
        top_k_local = max(top_k, self.config.TOP_K_RESULTS or 5)
        retrieved = {}
        for name in ["semantic", "structural", "fault", "hybrid"]:
            store = self.vector_stores.get(name)
            docs = self._retrieve_from_store(store, question, top_k_local)
            retrieved[name] = docs or []

        # Merge and score
        merged = self._merge_and_score(retrieved, question, query_type, top_k_local)

        # Graph expansion (use config graph depth; default to 1 additional hop)
        graph_hops = getattr(self.config, "GRAPH_DEPTH", 2)
        scored_with_docs = self._graph_expand(merged, hops=max(1, graph_hops - 1), max_add=40)

        # Prepare context blocks
        context, sources = self._prepare_context_blocks(scored_with_docs, max_blocks=12)

        if not context.strip():
            return {"answer": "No relevant code found for your query. Try rephrasing or asking about specific functions/files.", "sources": [], "query_type": query_type, "question": question}

        # Build prompt and call LLM
        prompt = self._build_prompt(question, query_type, context)
        try:
            resp = self.llm.invoke(prompt)
            answer = getattr(resp, "content", None) or str(resp)
        except Exception as e:
            logger.error("LLM invoke error: %s", e)
            answer = f"LLM Error: {e}\n\nContext:\n{context}"

        # Trim answer and return
        return {
            "answer": answer.strip(),
            "sources": sources[:10],
            "query_type": query_type,
            "question": question
        }

    # -------------------------
    # Overview handler
    # -------------------------
    def _handle_overview(self, question: str) -> Dict:
        # build a compact overview from stats and top files
        stats = getattr(self, "codebase_stats", {}) or {}
        top_files = stats.get("top_files_by_loc", [])[:10] if isinstance(stats.get("top_files_by_loc", []), list) else []

        # sample file summaries
        file_summaries = []
        for fname, methods in list(self.methods_by_file.items())[:10]:
            method_names = [m.get('display_name') or m.get('name', '') for m in methods[:5]]
            file_summaries.append({"file": fname, "method_count": len(methods), "sample_methods": method_names})

        overview_context = f"""
STATISTICS:
- Total Files: {stats.get('total_files', 'N/A')}
- Total Functions: {stats.get('total_methods', 'N/A')}
- Total Lines: {stats.get('total_lines', 'N/A')}
"""

        if top_files:
            overview_context += "\nTOP FILES (by LOC):\n"
            for f in top_files:
                overview_context += f"  - {f.get('file','?')}: {f.get('loc','?')} lines ({f.get('methods','?')} functions)\n"

        # Use LLM to produce a nice human-readable overview
        prompt = f"""
You are provided with the following codebase summary information below. Produce a concise, structured overview of the codebase including Purpose, Key Components, Main Modules, and Notable Patterns.

{overview_context}

SAMPLE FILE SUMMARIES:
{json.dumps(file_summaries[:10], indent=2)}

USER REQUEST: {question}

Be concise and concrete. Cite the sample files where appropriate.
"""
        try:
            resp = self.llm.invoke(prompt)
            answer = getattr(resp, "content", None) or str(resp)
        except Exception as e:
            answer = f"LLM Error generating overview: {e}\n\nRaw summary:\n{overview_context}"

        return {"answer": answer, "sources": [{"function": "Project Statistics", "file": "Multiple", "line": "N/A"}], "query_type": "overview", "question": question}

# -------------------------
# Interactive CLI
# -------------------------
def interactive_mode(engine: EnhancedRAGQueryEngine):
    print("\n" + "="*70)
    print(" Enhanced CPG RAG Interactive Mode")
    print("="*70)
    print("Commands:")
    print("  /quit or /exit    - Exit the program")
    print("  /stats            - Show codebase statistics")
    print("  /type <type>      - Set query type (semantic|structural|fault|overview|auto)")
    print("  /help             - Show this help message")
    print("="*70 + "\n")

    query_type = "auto"

    while True:
        try:
            q = input("?").strip()
            if not q:
                continue

            if q.lower() in ("/quit", "/exit"):
                print(" Goodbye!")
                return

            if q.startswith("/help"):
                print("\n" + "="*70)
                print("HELP:")
                print("  Ask natural language questions about the code")
                print("  Examples:")
                print("    - What does the authenticate function do?")
                print("    - Are there any SQL injection vulnerabilities?")
                print("    - Show me the call graph for process_data")
                print("    - Give me an overview of the codebase")
                print("="*70 + "\n")
                continue

            if q.startswith("/stats"):
                s = getattr(engine, "codebase_stats", {}) or {}
                print("\n Codebase Statistics:")
                print(f"  Files: {s.get('total_files', 'N/A')}")
                print(f"  Functions: {s.get('total_methods', 'N/A')}")
                print(f"  Lines of Code: {s.get('total_lines', 'N/A')}")
                print(f"  Avg LOC/File: {s.get('avg_loc_per_file', 'N/A')}\n")
                continue

            if q.startswith("/type"):
                parts = q.split()
                if len(parts) > 1 and parts[1] in ("semantic", "structural", "fault", "auto", "overview"):
                    query_type = parts[1]
                    print(f" Query type set to: {query_type}")
                else:
                    print("   Usage: /type semantic|structural|fault|overview|auto")
                continue

            print("\n Analyzing your query...\n")
            res = engine.query(q, query_type=query_type)

            # Display results
            print("="*70)
            print(f" Query Type: {res.get('query_type')} | Sources: {len(res.get('sources') or [])}")
            print("="*70)
            print(res.get("answer"))
            print("="*70)

            sources = res.get("sources") or []
            if sources:
                print("\n Source Functions:")
                for i, s in enumerate(sources[:8], 1):
                    print(f"  {i}. {s.get('function')} ({s.get('file')}:{s.get('line')})")
            print()

        except KeyboardInterrupt:
            print("\n Goodbye!")
            break
        except Exception as e:
            print(f" Error: {e}\n")

# -------------------------
# CLI Entrypoint
# -------------------------
def main():
    parser = argparse.ArgumentParser(description="Enhanced CPG RAG Query Engine (hybrid + graph)", formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--query", "-q", help="Query to execute")
    parser.add_argument("--type", "-t", default="auto", choices=["auto", "semantic", "structural", "fault", "overview"], help="Query type (default: auto)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Start interactive mode")
    parser.add_argument("--top-k", "-k", type=int, default=15, help="Number of results to consider from each store")
    args = parser.parse_args()

    engine = EnhancedRAGQueryEngine()
    if args.interactive:
        engine.initialize()
        interactive_mode(engine)
        return

    if args.query:
        res = engine.query(args.query, query_type=args.type, top_k=args.top_k)
        print("\n" + "="*70)
        print("ANSWER:")
        print("="*70)
        print(res.get("answer", ""))
        print("="*70)
        sources = res.get("sources") or []
        if sources:
            print("\nSOURCES:")
            for s in sources[:10]:
                print(f" - {s.get('function')} ({s.get('file')}:{s.get('line')})")
        return

    parser.print_help()

if __name__ == "__main__":
    main()
