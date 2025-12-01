#!/usr/bin/env python3
"""
Step 3: Setup RAG System (ENHANCED)
- Multi-hop graph context
- Hybrid vectorstore (code + structure + faults)
- AST derived features
- Better semantic documents (calls/called_by)
- Telemetry disabled by default for local/dev
"""

import argparse
import ast
import json
import logging
import os
import re
import shutil
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional

from tqdm import tqdm

# Disable Chroma / PostHog telemetry (additional env var for safety)
os.environ.setdefault("CHROMA_TELEMETRY_DISABLED", "1")
os.environ.setdefault("CHROMA_DISABLE_TELEMETRY", "1")

# LangChain community wrappers used in the original pipeline
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain.docstore.document import Document

# Project config (must exist in repo)
from config import Config

# --------------------------
# Logging
# --------------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("step3_setup_rag")

# --------------------------
# Synthetic name filters
# --------------------------
SYNTHETIC_PATTERNS = [
    re.compile(r'^<.*>$'),              # <init>, <module>, <body>
    re.compile(r'^operator\.'),         # operator.add
    re.compile(r'^fake', re.I),         # fake nodes
    re.compile(r'^[^a-zA-Z0-9_]+$'),    # punctuation only
    re.compile(r'^metaClass', re.I),
]

def is_synthetic(name: Optional[str]) -> bool:
    if not name:
        return True
    s = str(name).strip()
    if not s:
        return True
    for p in SYNTHETIC_PATTERNS:
        if p.match(s):
            return True
    return False

# --------------------------
# Utility: extract a function/class name from code snippet
# --------------------------
def extract_name_from_code(code: str) -> Optional[str]:
    if not code:
        return None
    # Python def/class
    m = re.search(r'^\s*(def|async def|class)\s+([A-Za-z_][A-Za-z0-9_]*)', code, re.MULTILINE)
    if m:
        return m.group(2)
    # JS/TS
    m = re.search(r'function\s+([A-Za-z_][A-Za-z0-9_]*)', code)
    if m:
        return m.group(1)
    # const fn = (...) => {}
    m = re.search(r'const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*\(', code)
    if m:
        return m.group(1)
    # C/Java-like signature
    m = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*\([^)]*\)\s*\{', code)
    if m:
        return m.group(1)
    return None

def make_display_name(raw_name, full_name, code, method_id):
    # Use raw name if not synthetic
    if raw_name and not is_synthetic(raw_name):
        return raw_name.strip()
    # Try trailing token from fullName
    if full_name:
        tokens = re.split(r'[.#/:$<> ]+', full_name)
        for t in reversed(tokens):
            if t and not is_synthetic(t):
                return t
    # Extract from code
    extracted = extract_name_from_code(code)
    if extracted and not is_synthetic(extracted):
        return extracted
    # Fallback
    return f"method_{method_id}"

# --------------------------
# AST-derived lightweight features for enrichment
# --------------------------
def ast_features_from_code(code: str) -> Dict[str, Any]:
    features = {
        "num_calls": 0,
        "num_branches": 0,
        "num_loops": 0,
        "num_returns": 0,
        "num_args": None,
        "uses_recursion": False,
        "num_awaits": 0,
        "uses_io": False,
    }
    if not code:
        return features
    try:
        tree = ast.parse(code)
    except Exception:
        return features

    func_defs = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    features["num_args"] = func_defs[0].args.args.__len__() if func_defs else 0

    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            features["num_calls"] += 1
            # crude I/O detection
            if isinstance(n.func, ast.Name) and n.func.id in {"open", "read", "write", "send", "recv"}:
                features["uses_io"] = True
        elif isinstance(n, ast.If):
            features["num_branches"] += 1
        elif isinstance(n, (ast.For, ast.While)):
            features["num_loops"] += 1
        elif isinstance(n, ast.Return):
            features["num_returns"] += 1
        elif isinstance(n, ast.Await):
            features["num_awaits"] += 1

    # detect recursion: simple check if function name appears in calls (best-effort)
    names = {getattr(n, "name", None) for n in func_defs}
    for fd in func_defs:
        fname = getattr(fd, "name", None)
        if fname:
            for n in ast.walk(fd):
                if isinstance(n, ast.Call):
                    if isinstance(n.func, ast.Name) and n.func.id == fname:
                        features["uses_recursion"] = True
                        break
    return features

# --------------------------
# RAG Setup Engine
# --------------------------
class RAGSetup:
    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()
        # ensure directories exist if method exists on Config
        try:
            self.config.ensure_directories()
        except Exception:
            # fallback: create data dir
            Path(getattr(self.config, "DATA_DIR", "data/")).mkdir(parents=True, exist_ok=True)

        self.nodes: List[Dict] = []
        self.edges: List[Dict] = []
        self.methods: List[Dict] = []
        self.source_files: Dict[str, str] = {}

        self.id_to_node: Dict[int, Dict] = {}
        self.outgoing = defaultdict(list)
        self.incoming = defaultdict(list)

        self.enriched_methods: List[Dict] = []

        self.embeddings = None
        self.vector_stores: Dict[str, Optional[Chroma]] = {"semantic": None, "structural": None, "fault": None, "hybrid": None}

        # configuration values (fallback to defaults if not present in Config)
        self.graph_depth = getattr(self.config, "GRAPH_DEPTH", 3)
        self.hybrid_collection = getattr(self.config, "HYBRID_COLLECTION", "hybrid_cpg")
        self.semantic_collection = getattr(self.config, "SEMANTIC_COLLECTION", "semantic_cpg")
        self.structural_collection = getattr(self.config, "STRUCTURAL_COLLECTION", "structural_cpg")
        self.fault_collection = getattr(self.config, "FAULT_COLLECTION", "fault_cpg")
        self.chroma_dir = getattr(self.config, "CHROMA_DIR", "chroma_db")
        self.data_dir = getattr(self.config, "DATA_DIR", "data/")
        self.ollama_embed_model = getattr(self.config, "OLLAMA_EMBEDDING_MODEL", "text-embedding-3-small")
        self.ollama_base = getattr(self.config, "OLLAMA_BASE_URL", "http://localhost:11434")

    # --------------------------
    def load_cpg(self, data_dir: Path):
        data_dir = Path(data_dir)
        logger.info("Loading CPG JSON...")

        nodes_file = data_dir / "cpg_nodes.json"
        edges_file = data_dir / "cpg_edges.json"
        methods_file = data_dir / "methods.json"

        if nodes_file.exists():
            try:
                with open(nodes_file, "r", encoding="utf-8") as fh:
                    self.nodes = json.load(fh)
            except Exception as e:
                logger.warning("Failed to load cpg_nodes.json: %s", e)
                self.nodes = []

        if edges_file.exists():
            try:
                with open(edges_file, "r", encoding="utf-8") as fh:
                    self.edges = json.load(fh)
            except Exception as e:
                logger.warning("Failed to load cpg_edges.json: %s", e)
                self.edges = []

        if methods_file.exists():
            try:
                with open(methods_file, "r", encoding="utf-8") as fh:
                    self.methods = json.load(fh)
            except Exception as e:
                logger.warning("Failed to load methods.json: %s", e)
                self.methods = [n for n in self.nodes if n.get("_label") == "METHOD"]
        else:
            self.methods = [n for n in self.nodes if n.get("_label") == "METHOD"]

        logger.info(" %d nodes", len(self.nodes))
        logger.info(" %d edges", len(self.edges))
        logger.info(" %d methods", len(self.methods))

    # --------------------------
    def load_sources(self, source_dir: Optional[Path]):
        if not source_dir:
            logger.info("Skipping source loading (no source_dir provided)")
            return
        if not Path(source_dir).exists():
            logger.warning("Source dir not found: %s", source_dir)
            return

        logger.info("Loading source files from: %s", source_dir)
        extensions = {".py", ".js", ".ts", ".c", ".cpp", ".h", ".java"}

        for file in Path(source_dir).rglob("*"):
            if file.suffix.lower() in extensions:
                try:
                    text = file.read_text(encoding="utf-8", errors="ignore")
                    rel = str(file.relative_to(source_dir))
                    # index by relative path and basename for flexible lookups
                    self.source_files[rel] = text
                    self.source_files[file.name] = text
                except Exception:
                    logger.debug("Skipping unreadable source file: %s", file)

        logger.info("Loaded %d source files", len(self.source_files))

    # --------------------------
    def build_graph_index(self):
        logger.info("Building graph index...")
        for n in self.nodes:
            nid = n.get("id")
            if nid is not None:
                self.id_to_node[nid] = n

        for e in self.edges:
            src, dst = e.get("src"), e.get("dst")
            lab = (e.get("label") or "").upper()
            if src is not None and dst is not None:
                self.outgoing[src].append((dst, lab))
                self.incoming[dst].append((src, lab))

        logger.info("Indexed %d nodes", len(self.id_to_node))

    # --------------------------
    def extract_full_code(self, method: Dict) -> str:
        filename = method.get("filename") or method.get("file") or ""
        line = int(method.get("lineNumber") or method.get("line_number") or 0)

        src = None
        if filename in self.source_files:
            src = self.source_files[filename]
        else:
            base = Path(filename).name
            if base in self.source_files:
                src = self.source_files[base]
            else:
                for k, v in self.source_files.items():
                    # try partial match heuristics
                    if filename.endswith(k) or k.endswith(filename):
                        src = v
                        break

        if src is None:
            return method.get("code") or ""

        if line <= 0:
            return src

        lines = src.splitlines()
        idx = max(0, line - 1)
        if idx >= len(lines):
            return method.get("code") or ""

        # Expand block until next def/class at same or lower indent (Python-friendly)
        start = idx
        start_indent = len(lines[start]) - len(lines[start].lstrip())

        end = start
        for i in range(start + 1, min(start + 500, len(lines))):
            ln = lines[i]
            if re.match(r'\s*(def|class)\s+', ln) and (len(ln) - len(ln.lstrip())) <= start_indent:
                break
            end = i

        return "\n".join(lines[start : end + 1]) or method.get("code") or ""

    # --------------------------
    def graph_context(self, method_id: int, depth: int = 1) -> Dict[str, List[Dict]]:
        """
        Return calls and called_by up to `depth` hops.
        """
        C = {"calls": [], "called_by": []}

        # outgoing (calls)
        visited = set()
        q = deque([(method_id, 0)])
        while q:
            nid, lv = q.popleft()
            if lv >= depth:
                continue
            for dst, lab in self.outgoing.get(nid, []):
                if lab == "CALL" and dst not in visited:
                    visited.add(dst)
                    node = self.id_to_node.get(dst)
                    if node:
                        C["calls"].append({
                            "id": dst,
                            "name": node.get("name") or node.get("fullName"),
                            "filename": node.get("filename")
                        })
                    q.append((dst, lv + 1))

        # incoming (called_by)
        visited = set()
        q = deque([(method_id, 0)])
        while q:
            nid, lv = q.popleft()
            if lv >= depth:
                continue
            for src, lab in self.incoming.get(nid, []):
                if lab == "CALL" and src not in visited:
                    visited.add(src)
                    node = self.id_to_node.get(src)
                    if node:
                        C["called_by"].append({
                            "id": src,
                            "name": node.get("name") or node.get("fullName"),
                            "filename": node.get("filename")
                        })
                    q.append((src, lv + 1))

        return C

    # --------------------------
    def fault_features(self, code: str) -> Dict[str, Any]:
        code = (code or "").lower()
        ff = {
            "has_null_checks": bool(re.search(r'\bis\s+none\b|\bnot\b.+none', code)),
            "has_exception_handling": ("try:" in code) or ("except" in code),
            "unsafe_operations": []
        }
        if "eval(" in code:
            ff["unsafe_operations"].append("eval")
        if "exec(" in code:
            ff["unsafe_operations"].append("exec")
        if "pickle.load" in code or "pickle.loads" in code:
            ff["unsafe_operations"].append("pickle")
        if "subprocess" in code or "shell=True" in code:
            ff["unsafe_operations"].append("subprocess/shell")
        return ff

    # --------------------------
    def enrich_methods(self):
        logger.info("Enriching methods...")
        out = []
        for m in tqdm(self.methods):
            mid = int(m.get("id") or 0)
            code = self.extract_full_code(m)
            ctx = self.graph_context(mid, depth=self.graph_depth)
            faults = self.fault_features(code)
            ast_feats = ast_features_from_code(code)

            disp = make_display_name(
                m.get("name"),
                m.get("fullName"),
                code,
                mid
            )

            enriched = {
                "id": mid,
                "display_name": disp,
                "name": disp,
                "filename": m.get("filename"),
                "lineNumber": int(m.get("lineNumber") or 0),
                "full_code": code,
                "calls": [c["name"] for c in ctx["calls"]],
                "called_by": [c["name"] for c in ctx["called_by"]],
                "calls_full": ctx["calls"],
                "called_by_full": ctx["called_by"],
                "fault_features": faults,
                "ast_features": ast_feats,
                # preserve some original metadata
                "orig_fullName": m.get("fullName"),
                "orig_signature": m.get("signature", ""),
            }
            out.append(enriched)

        self.enriched_methods = out
        logger.info("Enriched %d methods", len(out))

    # --------------------------
    def init_embeddings(self):
        logger.info("Initializing embeddings...")
        self.embeddings = OllamaEmbeddings(
            model=self.ollama_embed_model,
            base_url=self.ollama_base
        )
        # quick embed to validate
        try:
            test_vec = self.embeddings.embed_query("hello")
            logger.info("Embedding dim = %d", len(test_vec))
        except Exception as e:
            logger.warning("Embedding initialization failed: %s", e)
            raise

    # --------------------------
    # Document builders for different collections
    # --------------------------
    def build_docs_semantic(self, m: Dict) -> str:
        parts = [
            f"Function: {m['display_name']}",
            f"File: {m['filename']}:{m['lineNumber']}",
            "Calls: " + (", ".join(m.get("calls", [])[:20]) or "None"),
            "Called by: " + (", ".join(m.get("called_by", [])[:20]) or "None"),
            "",
            "AST features: " + json.dumps(m.get("ast_features", {})),
            "",
            "Code:\n" + (m.get("full_code") or "")
        ]
        return "\n\n".join(parts)

    def build_docs_structural(self, m: Dict) -> str:
        parts = [
            f"Function: {m['display_name']}",
            f"File: {m['filename']}:{m['lineNumber']}",
            "Call graph (calls -> called_by):",
            "Calls: " + (", ".join(m.get("calls", [])[:50]) or "None"),
            "Called by: " + (", ".join(m.get("called_by", [])[:50]) or "None"),
            "",
            "Call details: " + json.dumps(m.get("calls_full", [])[:10])
        ]
        return "\n".join(parts)

    def build_docs_fault(self, m: Dict) -> str:
        parts = [
            f"Function: {m['display_name']}",
            f"File: {m['filename']}:{m['lineNumber']}",
        ]
        ff = m.get("fault_features", {})
        if not ff.get("has_exception_handling"):
            parts.append("No exception handling")
        if not ff.get("has_null_checks"):
            parts.append("Missing null/None checks")
        if ff.get("unsafe_operations"):
            parts.append("Unsafe ops: " + ", ".join(ff.get("unsafe_operations")))
        parts.append("")
        parts.append("Code:\n" + (m.get("full_code") or ""))
        return "\n\n".join(parts)

    def build_docs_hybrid(self, m: Dict) -> str:
        parts = [
            f"{m['display_name']} ({m['filename']}:{m['lineNumber']})",
            "=== FAULT SIGNALS ===",
            json.dumps(m.get("fault_features", {})),
            "=== AST FEATURES ===",
            json.dumps(m.get("ast_features", {})),
            "=== CALL GRAPH ===",
            "Calls: " + (", ".join(m.get("calls", [])[:50]) or "None"),
            "Called by: " + (", ".join(m.get("called_by", [])[:50]) or "None"),
            "=== CODE ===",
            m.get("full_code") or ""
        ]
        return "\n\n".join(parts)

    # --------------------------
    def create_vectorstores(self, force: bool = False):
        chroma_dir = Path(self.chroma_dir)
        if force and chroma_dir.exists():
            shutil.rmtree(chroma_dir)
        chroma_dir.mkdir(parents=True, exist_ok=True)

        logger.info("Creating Chroma stores...")

        # Build Documents
        semantic_docs = []
        structural_docs = []
        fault_docs = []
        hybrid_docs = []

        for m in self.enriched_methods:
            meta = {
                "display_name": m["display_name"],
                "filename": m["filename"],
                "line_number": m["lineNumber"],
                "method_id": m["id"]
            }

            semantic_docs.append(Document(page_content=self.build_docs_semantic(m), metadata=meta))
            structural_docs.append(Document(page_content=self.build_docs_structural(m), metadata=meta))
            fault_docs.append(Document(page_content=self.build_docs_fault(m), metadata=meta))
            hybrid_docs.append(Document(page_content=self.build_docs_hybrid(m), metadata=meta))

        # Create collections; use from_documents to persist
        # SEMANTIC
        Chroma.from_documents(
            documents=semantic_docs,
            embedding=self.embeddings,
            persist_directory=str(chroma_dir),
            collection_name=self.semantic_collection
        )

        # STRUCTURAL
        Chroma.from_documents(
            documents=structural_docs,
            embedding=self.embeddings,
            persist_directory=str(chroma_dir),
            collection_name=self.structural_collection
        )

        # FAULT
        Chroma.from_documents(
            documents=fault_docs,
            embedding=self.embeddings,
            persist_directory=str(chroma_dir),
            collection_name=self.fault_collection
        )

        # HYBRID
        Chroma.from_documents(
            documents=hybrid_docs,
            embedding=self.embeddings,
            persist_directory=str(chroma_dir),
            collection_name=self.hybrid_collection
        )

        logger.info("Vector stores created (semantic, structural, fault, hybrid)")

    # --------------------------
    def save_enriched(self):
        out = Path(self.data_dir) / "enriched_methods.json"
        try:
            json.dump(self.enriched_methods, open(out, "w", encoding="utf-8"), indent=2)
            logger.info("Saved %s", out)
        except Exception as e:
            logger.warning("Failed to save enriched methods: %s", e)

    # --------------------------
    def run(self, data_dir, source_dir, force=False):
        logger.info("============================================================")
        logger.info("STEP 3 — Setting up RAG")
        logger.info("============================================================")

        self.load_cpg(data_dir)
        self.load_sources(source_dir)
        self.build_graph_index()
        self.enrich_methods()
        self.init_embeddings()
        self.create_vectorstores(force=force)
        self.save_enriched()

        logger.info("============================================================")
        logger.info("Step 3 complete.")
        logger.info("Next: python step4_query_rag.py --interactive")

# --------------------------
# CLI Entrypoint
# --------------------------
def main():
    parser = argparse.ArgumentParser(description="Step 3: Setup RAG (enhanced)")
    parser.add_argument("--data-dir", default="data/")
    parser.add_argument("--source-dir")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    cfg = None
    try:
        cfg = Config()
    except Exception:
        cfg = None

    setup = RAGSetup(config=cfg)
    setup.run(
        data_dir=Path(args.data_dir),
        source_dir=Path(args.source_dir) if args.source_dir else None,
        force=args.force
    )

if __name__ == "__main__":
    main()
