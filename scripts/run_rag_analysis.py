#!/usr/bin/env python3
"""
Wrapper script to run RAG-based analysis using cpg_rag_complete/step4_query_rag.py
"""

import argparse
import sys
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='Run RAG-based code analysis')
    parser.add_argument(
        '--analysis-type',
        choices=['fault', 'sensitive', 'understanding'],
        required=True,
        help='Type of analysis to run'
    )
    parser.add_argument(
        '--query',
        help='Custom query (optional, uses default if not provided)'
    )
    parser.add_argument(
        '--mode',
        help='Analysis mode (e.g., security, overview, architecture, entry-points)'
    )
    parser.add_argument(
        '--export',
        choices=['json', 'md', 'markdown'],
        help='Export format'
    )
    parser.add_argument(
        '--data-dir',
        default='cpg_rag_complete/data',
        help='Data directory (default: cpg_rag_complete/data)'
    )
    
    args = parser.parse_args()
    
    # Get the step4_query_rag.py script
    script_path = Path(__file__).parent.parent / "cpg_rag_complete" / "step4_query_rag.py"
    
    if not script_path.exists():
        print(f"Error: step4_query_rag.py not found at {script_path}")
        sys.exit(1)
    
    # Build query based on analysis type
    if args.query:
        query = args.query
    else:
        if args.analysis_type == 'fault':
            if args.mode == 'security':
                query = "Find security vulnerabilities or unsafe patterns"
            else:
                query = "Find security vulnerabilities, resource leaks, missing error handling, and code quality issues"
        elif args.analysis_type == 'sensitive':
            if args.mode:
                query = f"Find functions that handle {args.mode} (passwords, API keys, tokens, PII)"
            else:
                query = "Find hardcoded credentials, API keys, tokens, and sensitive data exposure"
        elif args.analysis_type == 'understanding':
            if args.mode == 'overview':
                query = "What is the overview of this codebase? What are the main components?"
            elif args.mode == 'architecture':
                query = "Describe the architecture of this codebase. How are components organized?"
            elif args.mode == 'entry-points':
                query = "Find entry points and main functions in this codebase"
            else:
                query = "What is the overview of this codebase?"
    
    # Build command - determine query type
    if args.analysis_type == 'fault':
        query_type = 'fault'
    elif args.analysis_type == 'sensitive':
        query_type = 'fault'  # Sensitive data is also a security/fault concern
    else:  # understanding
        query_type = 'auto'  # Let it auto-detect based on query
    
    # Set environment variable to suppress warnings - more aggressive
    import os
    env = os.environ.copy()
    env['PYTHONWARNINGS'] = 'ignore::DeprecationWarning:langchain'
    # Also set for stderr redirection
    import sys
    if hasattr(sys, '_getframe'):
        # Redirect stderr temporarily if needed
        pass
    
    cmd = [
        sys.executable,
        str(script_path),
        '--query', query,
        '--type', query_type
    ]
    
    if args.export:
        cmd.extend(['--export', args.export])
    
    # Run the command with environment variable to suppress warnings
    result = subprocess.run(cmd, capture_output=True, text=True, env=env)
    
    # Print output
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    
    sys.exit(result.returncode)


if __name__ == '__main__':
    main()

