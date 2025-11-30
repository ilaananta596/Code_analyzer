#!/usr/bin/env python3
"""
Wrapper script to run sensitive data tracking on CPG nodes JSON
"""

import argparse
import json
import sys
from pathlib import Path

# Add cpg_rag_system to path
sys.path.insert(0, str(Path(__file__).parent.parent / "cpg_rag_system"))

from config import CONFIG
from analyzers.sensitive_data_tracker import SensitiveDataTracker


def main():
    parser = argparse.ArgumentParser(description='Run sensitive data tracking on CPG nodes JSON')
    parser.add_argument(
        '--nodes-json',
        default='cpg_rag_system/data/cpg_nodes.json',
        help='Path to CPG nodes JSON file (default: cpg_rag_system/data/cpg_nodes.json)'
    )
    parser.add_argument(
        '--edges-json',
        default='cpg_rag_system/data/cpg_edges.json',
        help='Path to CPG edges JSON file (default: cpg_rag_system/data/cpg_edges.json)'
    )
    parser.add_argument('--track', help='Track specific data type (e.g., password)')
    parser.add_argument('--all', action='store_true', help='Track all sensitive data')
    parser.add_argument('--export', help='Export report to file')
    parser.add_argument('--format', choices=['console', 'json', 'markdown', 'html'],
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
    
    # Initialize tracker
    tracker = SensitiveDataTracker(CONFIG)
    analyses = []
    
    # Build node ID to node mapping for graph context
    node_map = {node.get('id'): node for node in nodes if node.get('_label') == 'METHOD'}
    
    # Build call graph from edges
    callers_map = {}
    callees_map = {}
    for edge in edges:
        if edge.get('label') == 'CALL':
            src = edge.get('src')
            dst = edge.get('dst')
            if src in node_map and dst in node_map:
                if dst not in callers_map:
                    callers_map[dst] = []
                callers_map[dst].append(node_map[src].get('name', ''))
                if src not in callees_map:
                    callees_map[src] = []
                callees_map[src].append(node_map[dst].get('name', ''))
    
    # Analyze each node (method)
    for node in nodes:
        # CPG nodes have: id, _label, name, signature, fullName, filename, lineNumber, code
        if node.get('_label') != 'METHOD':
            continue
        
        code = node.get('code', '')
        filename = node.get('filename', 'unknown')
        method_name = node.get('name', 'unknown')
        node_id = node.get('id')
        
        if not code:
            continue
        
        # Get graph context from edges
        graph_context = {}
        if node_id in callers_map:
            graph_context['callers'] = callers_map[node_id]
        if node_id in callees_map:
            graph_context['callees'] = callees_map[node_id]
        
        # Analyze function
        analysis = tracker.analyze_function(
            method_name,
            code,
            filename,
            graph_context
        )
        
        # Filter by track type if specified
        if args.track:
            # Check if this analysis has the requested data type
            has_type = any(
                flow.get('type') == args.track 
                for flow in analysis.get('data_flows', [])
            )
            if not has_type:
                continue
        
        # Only include if there's sensitive data or violations
        if analysis.get('has_sensitive_data') or analysis.get('violations'):
            analyses.append(analysis)
    
    # Generate report
    report = tracker.generate_report(analyses, format=args.format)
    
    if args.export:
        with open(args.export, 'w') as f:
            f.write(report)
        print(f"\n✅ Report exported to {args.export}")
    elif args.format == 'console':
        # Already printed by generate_report
        pass
    else:
        print(report)
    
    # Print summary
    total_violations = sum(len(a.get('violations', [])) for a in analyses)
    functions_with_sensitive = sum(1 for a in analyses if a.get('has_sensitive_data'))
    print(f"\n📊 Summary: Found {total_violations} violations across {functions_with_sensitive} functions with sensitive data")


if __name__ == '__main__':
    main()

