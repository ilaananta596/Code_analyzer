#!/usr/bin/env python3
"""
Wrapper script to run code understanding on CPG nodes JSON
"""

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict

# Add cpg_rag_complete to path
sys.path.insert(0, str(Path(__file__).parent.parent / "cpg_rag_complete"))

try:
    from config_analyzers import CONFIG
except ImportError:
    from config import CONFIG
from analyzers.code_understander import CodeUnderstander


def main():
    parser = argparse.ArgumentParser(description='Run code understanding on CPG nodes JSON')
    parser.add_argument(
        '--nodes-json',
        default='cpg_rag_complete/data/cpg_nodes.json',
        help='Path to CPG nodes JSON file (default: cpg_rag_complete/data/cpg_nodes.json)'
    )
    parser.add_argument(
        '--edges-json',
        default='cpg_rag_complete/data/cpg_edges.json',
        help='Path to CPG edges JSON file (default: cpg_rag_complete/data/cpg_edges.json)'
    )
    parser.add_argument('--overview', action='store_true', help='Generate overview')
    parser.add_argument('--architecture', action='store_true', help='Architecture description')
    parser.add_argument('--entry-points', action='store_true', help='Find entry points')
    parser.add_argument('--export', help='Export to file')
    parser.add_argument('--format', choices=['console', 'markdown'],
                       default='console', help='Output format')
    
    args = parser.parse_args()
    
    # Load CPG nodes JSON
    nodes_path = Path(args.nodes_json)
    if not nodes_path.exists():
        print(f"Error: CPG nodes JSON file not found: {nodes_path}")
        print(f"Please extract CPG nodes first using: python scripts/extract_cpg_json.py <cpg.bin>")
        sys.exit(1)
    
    with open(nodes_path, 'r') as f:
        nodes = json.load(f)
    
    if not isinstance(nodes, list):
        print(f"Error: Expected list of nodes in {nodes_path}")
        sys.exit(1)
    
    # Load edges for graph context (optional)
    edges = []
    edges_path = Path(args.edges_json)
    if edges_path.exists():
        with open(edges_path, 'r') as f:
            edges = json.load(f)
        print(f"Loaded {len(edges)} edges from {edges_path}")
    
    print(f"Loaded {len(nodes)} nodes from {nodes_path}")
    
    # Initialize understander
    understander = CodeUnderstander(CONFIG)
    
    # Build node ID to node mapping
    node_map = {node.get('id'): node for node in nodes if node.get('_label') == 'METHOD'}
    
    # Build callers map from edges
    callers_map = {}
    for edge in edges:
        if edge.get('label') == 'CALL':
            src = edge.get('src')
            dst = edge.get('dst')
            if src in node_map and dst in node_map:
                if dst not in callers_map:
                    callers_map[dst] = []
                callers_map[dst].append(node_map[src].get('name', ''))
    
    # Build source files dict from nodes (only real files, not empty)
    source_files = {}
    for node in nodes:
        if node.get('_label') == 'METHOD':
            filename = node.get('filename', 'unknown')
            # Skip empty or placeholder filenames
            if filename and filename.strip() not in ['', '<empty>', 'unknown']:
                if filename not in source_files:
                    # Use code as file content (simplified)
                    source_files[filename] = node.get('code', '')
    
    # Convert nodes to format expected by understander
    # The understander expects methods with 'name', 'filename', 'lineNumber', 'called_by'
    # Filter out methods with empty filenames (operator methods, built-ins)
    formatted_methods = []
    for node in nodes:
        if node.get('_label') == 'METHOD':
            filename = node.get('filename', 'unknown')
            # Skip methods with empty filenames for better analysis
            if filename and filename.strip() not in ['', '<empty>', 'unknown']:
                node_id = node.get('id')
                formatted_method = {
                    'name': node.get('name', 'unknown'),
                    'filename': filename,
                    'lineNumber': node.get('lineNumber', 0),
                    'called_by': callers_map.get(node_id, [])
                }
                formatted_methods.append(formatted_method)
    
    # Analyze structure
    structure = understander.analyze_codebase_structure(formatted_methods, source_files)
    entry_points = understander.find_entry_points(formatted_methods)
    patterns = understander.identify_design_patterns(formatted_methods)
    
    # Generate output
    if args.architecture:
        content = understander.generate_architecture_description(structure)
    elif args.entry_points:
        # Generate entry points report
        content = "# 🚀 Entry Points\n\n"
        for ep in entry_points:
            content += f"## {ep['name']} ({ep['type']})\n\n"
            content += f"- **File:** {ep.get('file', 'N/A')}\n"
            if 'line' in ep:
                content += f"- **Line:** {ep['line']}\n"
            if 'callers' in ep:
                content += f"- **Called by:** {ep['callers']} functions\n"
            content += "\n"
    else:
        # Default to overview
        content = understander.generate_overview(structure, entry_points, patterns)
    
    if args.export:
        with open(args.export, 'w') as f:
            f.write(content)
        print(f"\n✅ Report exported to {args.export}")
    elif args.format == 'console':
        # Generate console output
        understander.generate_console_output(structure, entry_points, patterns)
    else:
        print(content)


if __name__ == '__main__':
    main()

