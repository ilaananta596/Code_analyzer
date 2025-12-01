#!/usr/bin/env python3
"""
Step 2: Extract JSON from CPG binary

This script extracts methods, calls, and code structure from a CPG binary file
into JSON format for use with the RAG system.

KEY FEATURES:
- Proper deduplication (no duplicate methods for same line number)
- Accurate line counting (correct total lines, not just 6)
- Clean JSON output ready for RAG indexing

Usage:
    python step2_extract_json.py data/cpg.bin --output data/
    python step2_extract_json.py data/cpg.bin --source-dir /path/to/source

Requirements:
    - Joern CLI installed
    - CPG binary file from step 1
"""

import argparse
import json
import subprocess
import sys
import tempfile
import os
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Any, Tuple, Optional
import shutil
import re


def find_joern(joern_cli_path: str = None) -> str:
    """Find joern executable."""
    if joern_cli_path:
        joern_cli = Path(joern_cli_path)
        # Check if it's a directory containing joern
        if joern_cli.is_dir():
            joern = joern_cli / "joern"
            if joern.exists():
                return str(joern)
        # Check if it's the executable itself
        if joern_cli.name == "joern" and joern_cli.exists():
            return str(joern_cli)
    
    joern = shutil.which("joern")
    if joern:
        return joern
    
    # Check current directory for joern-cli folder
    cwd = Path.cwd()
    local_paths = [
        cwd / "joern-cli" / "joern",
        cwd / "joern" / "joern-cli" / "joern",
        cwd.parent / "joern-cli" / "joern",
    ]
    
    for path in local_paths:
        if path.exists():
            print(f"   📍 Found joern in local directory: {path}")
            return str(path)
    
    common_paths = [
        Path.home() / "joern" / "joern-cli" / "joern",
        Path.home() / "joern-cli" / "joern",
        Path.home() / "bin" / "joern",
        Path("/opt/joern/joern-cli/joern"),
    ]
    
    for path in common_paths:
        if path.exists():
            return str(path)
    
    return None


def extract_using_joern_script(cpg_path: str, output_dir: str, 
                                joern_cli_path: str = None) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract nodes and edges using Joern's built-in JSON export.
    
    This method uses Joern scripting to extract data directly,
    avoiding Scala compilation issues.
    """
    cpg_path = Path(cpg_path).resolve()
    output_dir = Path(output_dir).resolve()
    
    joern = find_joern(joern_cli_path)
    if not joern:
        raise RuntimeError("Joern executable not found!")
    
    print(f"🔧 Using Joern: {joern}")
    print(f"📁 CPG file: {cpg_path}")
    
    # Create temporary script file for Joern
    script_content = '''
import scala.util.{Try, Success, Failure}
import java.io.{File, PrintWriter}

// Import CPG
println("Loading CPG...")
importCpg("%s")

// Get output directory from environment
val outputDir = "%s"

// Extract all nodes with their properties
println("Extracting nodes...")
val nodes = cpg.all.map { node =>
  val props = node.propertyMap.map { case (k, v) => 
    val valueStr = v match {
      case s: String => "\\"" + s.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"").replace("\\n", "\\\\n").replace("\\r", "\\\\r").replace("\\t", "\\\\t") + "\\""
      case n: Number => n.toString
      case b: Boolean => b.toString
      case null => "null"
      case other => "\\"" + other.toString.replace("\\\\", "\\\\\\\\").replace("\\"", "\\\\\\"").replace("\\n", "\\\\n") + "\\""
    }
    "\\"" + k + "\\": " + valueStr
  }.mkString(", ")
  "{" + "\\"id\\": " + node.id + ", \\"_label\\": \\"" + node.label + "\\", " + props + "}"
}.toList

// Write nodes
val nodesFile = new PrintWriter(new File(outputDir + "/cpg_nodes.json"))
nodesFile.write("[\\n" + nodes.mkString(",\\n") + "\\n]")
nodesFile.close()
println(s"Wrote ${nodes.size} nodes")

// Extract edges
println("Extracting edges...")
val edges = cpg.all.flatMap { node =>
  node.outE.map { edge =>
    s"""{"src": ${edge.outNode.id}, "dst": ${edge.inNode.id}, "label": "${edge.label}"}"""
  }
}.toList

// Write edges
val edgesFile = new PrintWriter(new File(outputDir + "/cpg_edges.json"))
edgesFile.write("[\\n" + edges.mkString(",\\n") + "\\n]")
edgesFile.close()
println(s"Wrote ${edges.size} edges")

println("Extraction complete!")
''' % (str(cpg_path).replace("\\", "\\\\"), str(output_dir).replace("\\", "\\\\"))

    # Try using joern-export first (simpler approach)
    print("\n📤 Attempting extraction with joern-export...")
    
    try:
        # First try joern-export which may work for some CPG formats
        joern_export = joern.replace("/joern", "/joern-export")
        if Path(joern_export).exists():
            export_dir = output_dir / "export_temp"
            export_dir.mkdir(exist_ok=True)
            
            result = subprocess.run(
                [joern_export, str(cpg_path), "-o", str(export_dir), "--repr", "all"],
                capture_output=True,
                text=True,
                timeout=300
            )
            
            # Check if export created useful files
            dot_files = list(export_dir.glob("*.dot"))
            if dot_files:
                print(f"   Found {len(dot_files)} .dot files from export")
                # We can parse .dot files if needed
    except Exception as e:
        print(f"   joern-export not available or failed: {e}")
    
    # Use Python-based extraction via Joern console
    print("\n📤 Extracting via Joern console...")
    
    # Write script to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.sc', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    try:
        result = subprocess.run(
            [joern, "--script", script_path],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(output_dir)
        )
        
        if result.returncode == 0:
            nodes_file = output_dir / "cpg_nodes.json"
            edges_file = output_dir / "cpg_edges.json"
            
            if nodes_file.exists() and edges_file.exists():
                with open(nodes_file) as f:
                    nodes = json.load(f)
                with open(edges_file) as f:
                    edges = json.load(f)
                print(f"✅ Extracted {len(nodes)} nodes and {len(edges)} edges")
                return nodes, edges
        
        print(f"⚠️  Joern script output: {result.stdout}")
        if result.stderr:
            print(f"⚠️  Joern script errors: {result.stderr}")
            
    except Exception as e:
        print(f"⚠️  Joern script extraction failed: {e}")
    finally:
        os.unlink(script_path)
    
    # Fallback: Try direct JSON via Joern's toJson
    print("\n📤 Trying alternative extraction method...")
    return extract_using_toJson(cpg_path, output_dir, joern)


def extract_using_toJson(cpg_path: str, output_dir: str, joern: str) -> Tuple[List[Dict], List[Dict]]:
    """
    Fallback extraction using Joern's built-in toJson method.
    This is simpler and less error-prone.
    """
    output_dir = Path(output_dir)
    
    script_content = '''
importCpg("%s")

// Extract methods with toJson (built-in, reliable)
val methodsJson = cpg.method.toJsonPretty
new java.io.PrintWriter("%s/methods_raw.json") { write(methodsJson); close }

// Extract calls
val callsJson = cpg.call.toJsonPretty  
new java.io.PrintWriter("%s/calls_raw.json") { write(callsJson); close }

// Also get all nodes for completeness
val allNodesJson = cpg.all.toJsonPretty
new java.io.PrintWriter("%s/all_nodes.json") { write(allNodesJson); close }
''' % (str(cpg_path), str(output_dir), str(output_dir), str(output_dir))

    with tempfile.NamedTemporaryFile(mode='w', suffix='.sc', delete=False) as f:
        f.write(script_content)
        script_path = f.name
    
    try:
        result = subprocess.run(
            [joern, "--script", script_path],
            capture_output=True,
            text=True,
            timeout=600
        )
        
        methods_file = output_dir / "methods_raw.json"
        if methods_file.exists():
            with open(methods_file) as f:
                methods_data = json.load(f)
            
            # Convert to our format
            nodes = []
            for m in methods_data:
                node = {
                    "id": m.get("id", 0),
                    "_label": "METHOD",
                    "name": m.get("name", ""),
                    "fullName": m.get("fullName", ""),
                    "filename": m.get("filename", ""),
                    "lineNumber": m.get("lineNumber"),
                    "lineNumberEnd": m.get("lineNumberEnd"),
                    "code": m.get("code", ""),
                    "signature": m.get("signature", ""),
                    "isExternal": m.get("isExternal", False)
                }
                nodes.append(node)
            
            # Load calls
            edges = []
            calls_file = output_dir / "calls_raw.json"
            if calls_file.exists():
                with open(calls_file) as f:
                    calls_data = json.load(f)
                for c in calls_data:
                    edges.append({
                        "src": c.get("id", 0),
                        "dst": 0,  # Will be resolved later
                        "label": "CALL"
                    })
            
            return nodes, edges
            
    except Exception as e:
        print(f"⚠️  toJson extraction failed: {e}")
    finally:
        os.unlink(script_path)
    
    raise RuntimeError("All extraction methods failed!")


def deduplicate_methods(methods: List[Dict]) -> List[Dict]:
    """
    Remove duplicate methods based on (filename, lineNumber, name).
    
    This fixes the issue where Joern sometimes returns multiple entries
    for the same method definition.
    
    Args:
        methods: List of method dictionaries
    
    Returns:
        Deduplicated list of methods
    """
    seen = {}  # Key: (filename, lineNumber, name) -> method
    duplicates_removed = 0
    
    for method in methods:
        # Create unique key
        filename = method.get('filename', '')
        line_number = method.get('lineNumber', 0)
        name = method.get('name', '')
        
        # Skip methods without proper identification
        if not filename or not name:
            continue
        
        key = (filename, line_number, name)
        
        if key in seen:
            duplicates_removed += 1
            # Keep the one with more information (longer code, more properties)
            existing = seen[key]
            existing_code_len = len(existing.get('code', '') or '')
            new_code_len = len(method.get('code', '') or '')
            
            if new_code_len > existing_code_len:
                seen[key] = method
        else:
            seen[key] = method
    
    deduplicated = list(seen.values())
    
    if duplicates_removed > 0:
        print(f"   🧹 Removed {duplicates_removed} duplicate methods")
        print(f"   📊 {len(methods)} → {len(deduplicated)} methods")
    
    return deduplicated


def calculate_accurate_line_counts(methods: List[Dict], source_files: Dict[str, str] = None) -> List[Dict]:
    """
    Calculate accurate line counts for each method.
    
    This fixes the issue where lineNumberEnd is missing or incorrect,
    leading to wrong total line counts (e.g., showing 6 lines for 15 modules).
    
    Args:
        methods: List of method dictionaries
        source_files: Optional dict of filename -> content for accurate counting
    
    Returns:
        Methods with corrected lineNumberEnd and line_count fields
    """
    for method in methods:
        line_start = method.get('lineNumber', 0) or 0
        line_end = method.get('lineNumberEnd')
        code = method.get('code', '') or ''
        
        # Method 1: Use lineNumberEnd if present and valid
        if line_end and line_end > line_start:
            method['line_count'] = line_end - line_start + 1
            continue
        
        # Method 2: Calculate from code content
        if code:
            code_lines = len(code.split('\n'))
            method['lineNumberEnd'] = line_start + code_lines - 1
            method['line_count'] = code_lines
            continue
        
        # Method 3: Try to get from source files
        if source_files:
            filename = method.get('filename', '')
            matching_file = None
            for path, content in source_files.items():
                if filename in path or path.endswith(filename):
                    matching_file = content
                    break
            
            if matching_file and line_start > 0:
                lines = matching_file.split('\n')
                if line_start <= len(lines):
                    # Find method end by indentation
                    start_idx = line_start - 1
                    if start_idx < len(lines):
                        start_indent = len(lines[start_idx]) - len(lines[start_idx].lstrip())
                        end_idx = start_idx
                        
                        for i in range(start_idx + 1, min(len(lines), start_idx + 500)):
                            line = lines[i]
                            if line.strip():
                                indent = len(line) - len(line.lstrip())
                                if indent <= start_indent and line.strip().startswith(('def ', 'class ', 'async def ')):
                                    end_idx = i - 1
                                    break
                            end_idx = i
                        
                        method['lineNumberEnd'] = end_idx + 1
                        method['line_count'] = end_idx - start_idx + 1
                        continue
        
        # Fallback: Estimate based on typical function size
        method['line_count'] = 1
        method['lineNumberEnd'] = line_start
    
    return methods


def extract_methods_from_nodes(nodes: List[Dict], edges: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    """
    Extract methods and calls from raw node/edge data.
    
    Args:
        nodes: All CPG nodes
        edges: All CPG edges
    
    Returns:
        Tuple of (methods, calls)
    """
    # Filter for METHOD nodes only (exclude external methods)
    methods = []
    for node in nodes:
        if node.get('_label') == 'METHOD':
            if not node.get('isExternal', False):
                methods.append(node)
    
    print(f"   📊 Found {len(methods)} internal methods (excluding external)")
    
    # Filter for CALL edges
    calls = [e for e in edges if e.get('label') == 'CALL']
    print(f"   📊 Found {len(calls)} call edges")
    
    return methods, calls


def load_source_files(source_dir: str) -> Dict[str, str]:
    """Load source files for accurate line counting."""
    source_files = {}
    
    if not source_dir or not Path(source_dir).exists():
        return source_files
    
    source_path = Path(source_dir)
    extensions = ['.py', '.java', '.js', '.ts', '.c', '.cpp', '.h', '.hpp', '.go', '.php', '.rb']
    
    for ext in extensions:
        for file_path in source_path.rglob(f'*{ext}'):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                rel_path = str(file_path.relative_to(source_path))
                source_files[rel_path] = content
            except Exception:
                continue
    
    return source_files


def calculate_codebase_stats(methods: List[Dict], source_dir: str = None) -> Dict:
    """
    Calculate accurate codebase statistics.
    
    This provides correct statistics that match reality, not the buggy
    counts that showed 6 lines for 15 modules.
    """
    stats = {
        'total_methods': len(methods),
        'total_lines': 0,
        'files': defaultdict(lambda: {'methods': 0, 'lines': 0}),
        'by_language': defaultdict(lambda: {'files': 0, 'methods': 0, 'lines': 0}),
        'complexity': {'high': 0, 'medium': 0, 'low': 0},
        'largest_methods': []
    }
    
    # Calculate totals
    for method in methods:
        line_count = method.get('line_count', 0)
        stats['total_lines'] += line_count
        
        filename = method.get('filename', 'unknown')
        stats['files'][filename]['methods'] += 1
        stats['files'][filename]['lines'] += line_count
    
    # Count unique files
    stats['total_files'] = len(stats['files'])
    
    # Detect language by extension
    for filename in stats['files']:
        ext = Path(filename).suffix.lower()
        lang_map = {
            '.py': 'Python', '.java': 'Java', '.js': 'JavaScript',
            '.ts': 'TypeScript', '.c': 'C', '.cpp': 'C++',
            '.go': 'Go', '.php': 'PHP', '.rb': 'Ruby'
        }
        lang = lang_map.get(ext, 'Other')
        stats['by_language'][lang]['files'] += 1
        stats['by_language'][lang]['methods'] += stats['files'][filename]['methods']
        stats['by_language'][lang]['lines'] += stats['files'][filename]['lines']
    
    # Find largest methods
    sorted_methods = sorted(methods, key=lambda m: m.get('line_count', 0), reverse=True)
    stats['largest_methods'] = [
        {
            'name': m.get('name'),
            'filename': m.get('filename'),
            'lineNumber': m.get('lineNumber'),
            'lineNumberEnd': m.get('lineNumberEnd'),
            'line_count': m.get('line_count')
        }
        for m in sorted_methods[:10]
    ]
    
    # Complexity estimation (based on line count as proxy)
    for method in methods:
        lines = method.get('line_count', 0)
        if lines > 100:
            stats['complexity']['high'] += 1
        elif lines > 30:
            stats['complexity']['medium'] += 1
        else:
            stats['complexity']['low'] += 1
    
    # Convert defaultdicts to regular dicts for JSON serialization
    stats['files'] = dict(stats['files'])
    stats['by_language'] = dict(stats['by_language'])
    
    return stats


def print_stats(stats: Dict):
    """Print nicely formatted statistics."""
    print("\n" + "=" * 60)
    print("📊 CODEBASE STATISTICS (Accurate)")
    print("=" * 60)
    print(f"\n📁 Files: {stats['total_files']}")
    print(f"🔧 Methods: {stats['total_methods']}")
    print(f"📝 Total Lines: {stats['total_lines']:,}")
    
    print("\n📈 By Language:")
    for lang, data in stats['by_language'].items():
        print(f"   {lang}: {data['files']} files, {data['methods']} methods, {data['lines']:,} lines")
    
    print("\n🏆 Largest Methods:")
    for i, m in enumerate(stats['largest_methods'][:5], 1):
        print(f"   {i}. {m['name']} ({m['filename']}:{m['lineNumber']}) - {m['line_count']} lines")
    
    print("\n📊 Complexity Distribution:")
    print(f"   High (>100 lines): {stats['complexity']['high']}")
    print(f"   Medium (30-100 lines): {stats['complexity']['medium']}")
    print(f"   Low (<30 lines): {stats['complexity']['low']}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="Extract JSON from CPG binary with deduplication and accurate line counts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python step2_extract_json.py data/cpg.bin
    python step2_extract_json.py data/cpg.bin --output data/
    python step2_extract_json.py data/cpg.bin --source-dir ./my-project
        """
    )
    
    parser.add_argument(
        "cpg_file",
        help="Path to CPG binary file"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/",
        help="Output directory for JSON files (default: data/)"
    )
    parser.add_argument(
        "--source-dir", "-s",
        help="Path to source code directory (for accurate line counting)"
    )
    parser.add_argument(
        "--joern-path",
        help="Path to joern-cli directory"
    )
    
    args = parser.parse_args()
    
    cpg_path = Path(args.cpg_file)
    output_dir = Path(args.output)
    
    if not cpg_path.exists():
        print(f"❌ Error: CPG file not found: {cpg_path}")
        sys.exit(1)
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Step 2: Extract JSON from CPG")
    print("=" * 60)
    print(f"📁 Input: {cpg_path}")
    print(f"📂 Output: {output_dir}")
    
    # Load source files if provided
    source_files = {}
    if args.source_dir:
        print(f"\n📖 Loading source files from: {args.source_dir}")
        source_files = load_source_files(args.source_dir)
        print(f"   Loaded {len(source_files)} source files")
    
    # Extract from CPG
    print("\n🔄 Extracting from CPG...")
    try:
        nodes, edges = extract_using_joern_script(
            str(cpg_path), 
            str(output_dir),
            args.joern_path
        )
    except Exception as e:
        print(f"❌ Extraction failed: {e}")
        sys.exit(1)
    
    # Extract methods and calls
    print("\n🔍 Processing extracted data...")
    methods, calls = extract_methods_from_nodes(nodes, edges)
    
    # Deduplicate methods
    print("\n🧹 Deduplicating methods...")
    methods = deduplicate_methods(methods)
    
    # Calculate accurate line counts
    print("\n📏 Calculating accurate line counts...")
    methods = calculate_accurate_line_counts(methods, source_files)
    
    # Calculate statistics
    stats = calculate_codebase_stats(methods, args.source_dir)
    
    # Save outputs
    print("\n💾 Saving output files...")
    
    # Save all nodes and edges (for graph building)
    nodes_file = output_dir / "cpg_nodes.json"
    edges_file = output_dir / "cpg_edges.json"
    
    with open(nodes_file, 'w') as f:
        json.dump(nodes, f, indent=2)
    print(f"   ✅ Saved {len(nodes)} nodes to {nodes_file}")
    
    with open(edges_file, 'w') as f:
        json.dump(edges, f, indent=2)
    print(f"   ✅ Saved {len(edges)} edges to {edges_file}")
    
    # Save deduplicated methods (for RAG)
    methods_file = output_dir / "methods.json"
    with open(methods_file, 'w') as f:
        json.dump(methods, f, indent=2)
    print(f"   ✅ Saved {len(methods)} methods to {methods_file}")
    
    # Save calls
    calls_file = output_dir / "calls.json"
    with open(calls_file, 'w') as f:
        json.dump(calls, f, indent=2)
    print(f"   ✅ Saved {len(calls)} calls to {calls_file}")
    
    # Save statistics
    stats_file = output_dir / "codebase_stats.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    print(f"   ✅ Saved statistics to {stats_file}")
    
    # Print statistics
    print_stats(stats)
    
    print("\n" + "=" * 60)
    print("✅ Step 2 Complete!")
    print("=" * 60)
    print("\nGenerated files:")
    print(f"   - {nodes_file} ({len(nodes)} nodes)")
    print(f"   - {edges_file} ({len(edges)} edges)")
    print(f"   - {methods_file} ({len(methods)} deduplicated methods)")
    print(f"   - {calls_file} ({len(calls)} calls)")
    print(f"   - {stats_file} (codebase statistics)")
    print("\nNext step:")
    print(f"    python step3_setup_rag.py")


if __name__ == "__main__":
    main()
