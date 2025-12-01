#!/usr/bin/env python3
"""
Wrapper script to run fault detection on methods JSON from existing system
"""

import argparse
import json
import sys
from pathlib import Path

# Add cpg_rag_complete to path
sys.path.insert(0, str(Path(__file__).parent.parent / "cpg_rag_complete"))

from config import CONFIG
from analyzers.fault_detector import FaultDetector


def main():
    parser = argparse.ArgumentParser(description='Run fault detection on CPG nodes JSON')
    parser.add_argument(
        '--nodes-json',
        default='cpg_rag_complete/data/cpg_nodes.json',
        help='Path to CPG nodes JSON file (default: cpg_rag_complete/data/cpg_nodes.json)'
    )
    parser.add_argument('--all', action='store_true', help='Analyze all issues')
    parser.add_argument('--security', action='store_true', help='Security issues only')
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
    
    print(f"Loaded {len(nodes)} nodes from {nodes_path}")
    
    # Initialize detector
    detector = FaultDetector(CONFIG)
    findings = []
    
    # Analyze each node (method)
    for node in nodes:
        # CPG nodes have: id, _label, name, signature, fullName, filename, lineNumber, code
        if node.get('_label') != 'METHOD':
            continue
        
        code = node.get('code', '')
        filename = node.get('filename', 'unknown')
        method_name = node.get('name', 'unknown')
        
        # Skip nodes with empty or placeholder code
        if not code or code.strip() in ['', '<empty>']:
            continue
        
        # Skip CPG internal representations (code that starts with <empty> and contains CPG patterns)
        if code.startswith('<empty>') and ('tmp' in code or '__iter__' in code or 'RET' in code):
            continue
        
        # Skip if filename is empty or invalid
        if not filename or filename.strip() == '':
            continue
        
        # Analyze code
        finding = detector.analyze_code(code, filename, node.get('lineNumber', 0))
        
        # Only include if there are issues
        if finding.get('issues'):
            finding['methodName'] = method_name
            findings.append(finding)
    
    # Filter by security if requested
    if args.security:
        findings = [f for f in findings if f.get('security_issues')]
    
    # Generate report
    report = detector.generate_report(findings, format=args.format)
    
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
    total_issues = sum(len(f.get('issues', [])) for f in findings)
    print(f"\n📊 Summary: Found {total_issues} issues across {len(findings)} methods")


if __name__ == '__main__':
    main()

