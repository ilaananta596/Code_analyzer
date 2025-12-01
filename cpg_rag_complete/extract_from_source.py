#!/usr/bin/env python3
"""
Alternative CPG Extraction - Python Source Parser

This is a fallback extraction method when Joern extraction fails.
It parses Python source files directly using Python's AST module.

This handles:
- Proper deduplication
- Accurate line counting
- Call relationship extraction

Usage:
    python extract_from_source.py /path/to/source/code --output data/

Note: This works for Python code. For other languages, use step2_extract_json.py
"""

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, asdict
from tqdm import tqdm


@dataclass
class MethodInfo:
    """Information about a method/function."""
    id: int
    name: str
    fullName: str
    filename: str
    lineNumber: int
    lineNumberEnd: int
    line_count: int
    code: str
    signature: str
    is_async: bool
    decorators: List[str]
    docstring: str


@dataclass
class CallInfo:
    """Information about a function call."""
    caller_id: int
    callee_name: str
    line_number: int


class PythonSourceParser:
    """Parse Python source files to extract methods and calls."""
    
    def __init__(self):
        self.methods: List[MethodInfo] = []
        self.calls: List[CallInfo] = []
        self.method_id_counter = 0
        self.method_name_to_id: Dict[str, int] = {}
    
    def _get_next_id(self) -> int:
        self.method_id_counter += 1
        return self.method_id_counter
    
    def _get_source_segment(self, source_lines: List[str], node: ast.AST) -> str:
        """Get source code for an AST node."""
        start_line = node.lineno - 1
        end_line = node.end_lineno
        
        if start_line < 0 or end_line > len(source_lines):
            return ""
        
        return "\n".join(source_lines[start_line:end_line])
    
    def _get_signature(self, node: ast.FunctionDef) -> str:
        """Get function signature."""
        args = []
        
        for arg in node.args.args:
            arg_str = arg.arg
            if arg.annotation:
                try:
                    arg_str += f": {ast.unparse(arg.annotation)}"
                except:
                    pass
            args.append(arg_str)
        
        return_annotation = ""
        if node.returns:
            try:
                return_annotation = f" -> {ast.unparse(node.returns)}"
            except:
                pass
        
        return f"{node.name}({', '.join(args)}){return_annotation}"
    
    def _extract_calls(self, node: ast.AST, caller_id: int):
        """Extract function calls from an AST node."""
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    self.calls.append(CallInfo(
                        caller_id=caller_id,
                        callee_name=child.func.id,
                        line_number=child.lineno
                    ))
                elif isinstance(child.func, ast.Attribute):
                    self.calls.append(CallInfo(
                        caller_id=caller_id,
                        callee_name=child.func.attr,
                        line_number=child.lineno
                    ))
    
    def parse_file(self, file_path: Path, base_path: Path):
        """Parse a single Python file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            
            source_lines = source.split('\n')
            tree = ast.parse(source)
            
            rel_path = str(file_path.relative_to(base_path))
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    method_id = self._get_next_id()
                    
                    # Get decorators
                    decorators = []
                    for decorator in node.decorator_list:
                        try:
                            decorators.append(ast.unparse(decorator))
                        except:
                            pass
                    
                    # Get docstring
                    docstring = ast.get_docstring(node) or ""
                    
                    # Get code
                    code = self._get_source_segment(source_lines, node)
                    
                    # Create method info
                    method = MethodInfo(
                        id=method_id,
                        name=node.name,
                        fullName=f"{rel_path}::{node.name}",
                        filename=rel_path,
                        lineNumber=node.lineno,
                        lineNumberEnd=node.end_lineno or node.lineno,
                        line_count=(node.end_lineno or node.lineno) - node.lineno + 1,
                        code=code,
                        signature=self._get_signature(node),
                        is_async=isinstance(node, ast.AsyncFunctionDef),
                        decorators=decorators,
                        docstring=docstring[:500] if docstring else ""
                    )
                    
                    self.methods.append(method)
                    self.method_name_to_id[node.name] = method_id
                    
                    # Extract calls within this method
                    self._extract_calls(node, method_id)
                    
        except SyntaxError as e:
            print(f"   ⚠️  Syntax error in {file_path}: {e}")
        except Exception as e:
            print(f"   ⚠️  Error parsing {file_path}: {e}")
    
    def parse_directory(self, source_dir: Path):
        """Parse all Python files in a directory."""
        source_path = source_dir.resolve()
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_path}")
        
        py_files = list(source_path.rglob("*.py"))
        
        # Filter out common non-source directories
        exclude_dirs = {'venv', 'env', '.venv', 'node_modules', '__pycache__', 
                       '.git', 'build', 'dist', '.eggs', '*.egg-info'}
        
        py_files = [f for f in py_files 
                   if not any(excluded in f.parts for excluded in exclude_dirs)]
        
        print(f"📁 Found {len(py_files)} Python files to parse")
        
        for file_path in tqdm(py_files, desc="Parsing files"):
            self.parse_file(file_path, source_path)
        
        print(f"   ✅ Extracted {len(self.methods)} methods")
        print(f"   ✅ Extracted {len(self.calls)} calls")
    
    def deduplicate(self):
        """Remove duplicate methods."""
        seen: Dict[Tuple[str, int, str], MethodInfo] = {}
        duplicates = 0
        
        for method in self.methods:
            key = (method.filename, method.lineNumber, method.name)
            
            if key in seen:
                duplicates += 1
                # Keep the one with more code
                if len(method.code) > len(seen[key].code):
                    seen[key] = method
            else:
                seen[key] = method
        
        self.methods = list(seen.values())
        
        if duplicates > 0:
            print(f"   🧹 Removed {duplicates} duplicate methods")
    
    def calculate_statistics(self) -> Dict:
        """Calculate codebase statistics."""
        stats = {
            'total_methods': len(self.methods),
            'total_lines': sum(m.line_count for m in self.methods),
            'total_calls': len(self.calls),
            'files': defaultdict(lambda: {'methods': 0, 'lines': 0}),
            'async_methods': sum(1 for m in self.methods if m.is_async),
            'largest_methods': [],
            'complexity': {'high': 0, 'medium': 0, 'low': 0}
        }
        
        for method in self.methods:
            stats['files'][method.filename]['methods'] += 1
            stats['files'][method.filename]['lines'] += method.line_count
            
            if method.line_count > 100:
                stats['complexity']['high'] += 1
            elif method.line_count > 30:
                stats['complexity']['medium'] += 1
            else:
                stats['complexity']['low'] += 1
        
        stats['total_files'] = len(stats['files'])
        stats['files'] = dict(stats['files'])
        
        # Top 10 largest methods
        sorted_methods = sorted(self.methods, key=lambda m: m.line_count, reverse=True)
        stats['largest_methods'] = [
            {'name': m.name, 'filename': m.filename, 'line_count': m.line_count}
            for m in sorted_methods[:10]
        ]
        
        return stats
    
    def to_json(self) -> Tuple[List[Dict], List[Dict]]:
        """Convert to JSON-serializable format."""
        methods_json = []
        for m in self.methods:
            method_dict = asdict(m)
            # Remove non-essential fields for lighter output
            methods_json.append(method_dict)
        
        calls_json = [asdict(c) for c in self.calls]
        
        return methods_json, calls_json


def print_stats(stats: Dict):
    """Print formatted statistics."""
    print("\n" + "=" * 60)
    print("📊 CODEBASE STATISTICS")
    print("=" * 60)
    print(f"\n📁 Files: {stats['total_files']}")
    print(f"🔧 Methods: {stats['total_methods']}")
    print(f"📝 Total Lines: {stats['total_lines']:,}")
    print(f"🔗 Function Calls: {stats['total_calls']:,}")
    print(f"⚡ Async Methods: {stats['async_methods']}")
    
    print("\n🏆 Largest Methods:")
    for i, m in enumerate(stats['largest_methods'][:5], 1):
        print(f"   {i}. {m['name']} ({m['filename']}) - {m['line_count']} lines")
    
    print("\n📊 Complexity Distribution:")
    print(f"   High (>100 lines): {stats['complexity']['high']}")
    print(f"   Medium (30-100 lines): {stats['complexity']['medium']}")
    print(f"   Low (<30 lines): {stats['complexity']['low']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Extract code structure from Python source files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python extract_from_source.py /path/to/my/project
    python extract_from_source.py /path/to/my/project --output data/
        """
    )
    
    parser.add_argument(
        "source_dir",
        help="Path to source code directory"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/",
        help="Output directory for JSON files (default: data/)"
    )
    
    args = parser.parse_args()
    
    source_path = Path(args.source_dir).resolve()
    output_path = Path(args.output).resolve()
    
    if not source_path.exists():
        print(f"❌ Error: Source directory not found: {source_path}")
        sys.exit(1)
    
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Python Source Parser (Fallback Extraction)")
    print("=" * 60)
    print(f"📁 Source: {source_path}")
    print(f"📂 Output: {output_path}")
    
    # Parse source files
    parser_obj = PythonSourceParser()
    parser_obj.parse_directory(source_path)
    
    # Deduplicate
    print("\n🧹 Deduplicating...")
    parser_obj.deduplicate()
    
    # Calculate statistics
    stats = parser_obj.calculate_statistics()
    
    # Convert to JSON
    methods_json, calls_json = parser_obj.to_json()
    
    # Create nodes/edges format for compatibility with step3
    nodes = []
    for m in methods_json:
        nodes.append({
            'id': m['id'],
            '_label': 'METHOD',
            'name': m['name'],
            'fullName': m['fullName'],
            'filename': m['filename'],
            'lineNumber': m['lineNumber'],
            'lineNumberEnd': m['lineNumberEnd'],
            'line_count': m['line_count'],
            'code': m['code'],
            'signature': m['signature'],
            'isExternal': False
        })
    
    edges = []
    for c in calls_json:
        edges.append({
            'src': c['caller_id'],
            'dst': 0,  # Would need method lookup
            'label': 'CALL',
            'callee_name': c['callee_name']
        })
    
    # Save outputs
    print("\n💾 Saving output files...")
    
    # Save nodes
    with open(output_path / "cpg_nodes.json", 'w') as f:
        json.dump(nodes, f, indent=2)
    print(f"   ✅ Saved {len(nodes)} nodes")
    
    # Save edges
    with open(output_path / "cpg_edges.json", 'w') as f:
        json.dump(edges, f, indent=2)
    print(f"   ✅ Saved {len(edges)} edges")
    
    # Save methods (deduplicated)
    with open(output_path / "methods.json", 'w') as f:
        json.dump(nodes, f, indent=2)
    print(f"   ✅ Saved {len(nodes)} methods")
    
    # Save calls
    with open(output_path / "calls.json", 'w') as f:
        json.dump(calls_json, f, indent=2)
    print(f"   ✅ Saved {len(calls_json)} calls")
    
    # Save statistics
    with open(output_path / "codebase_stats.json", 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"   ✅ Saved statistics")
    
    # Print statistics
    print_stats(stats)
    
    print("\n" + "=" * 60)
    print("✅ Extraction Complete!")
    print("=" * 60)
    print("\nNext step:")
    print("    python step3_setup_rag.py --data-dir data/")


if __name__ == "__main__":
    main()
