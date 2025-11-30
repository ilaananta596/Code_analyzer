#!/usr/bin/env python3
"""
Extract CPG nodes and edges JSON from CPG binary file.
Outputs to cpg_rag_system/data/ directory.
"""

import argparse
import sys
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(
        description='Extract CPG nodes and edges JSON from CPG binary'
    )
    parser.add_argument(
        'cpg_path',
        help='Path to CPG binary file (.cpg.bin)'
    )
    parser.add_argument(
        '--output', '-o',
        default='cpg_rag_system/data',
        help='Output directory (default: cpg_rag_system/data)'
    )
    parser.add_argument(
        '--joern-path',
        help='Path to Joern installation (auto-detected if not specified)'
    )
    parser.add_argument(
        '--source-dir',
        help='Source directory to extract actual code from (auto-detected from .source_info.json if available)'
    )
    parser.add_argument(
        '--no-enhance',
        action='store_true',
        help='Skip source code enhancement (use CPG representation only)'
    )
    
    args = parser.parse_args()
    
    cpg_path = Path(args.cpg_path)
    if not cpg_path.exists():
        print(f"❌ CPG file not found: {cpg_path}")
        sys.exit(1)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📤 Extracting CPG JSON from {cpg_path}")
    print(f"📁 Output directory: {output_dir}")
    
    # Use the extract_from_cpg.py script from cpg_rag_system
    extract_script = Path(__file__).parent.parent / "cpg_rag_system" / "cpg_generators" / "extract_from_cpg.py"
    
    if not extract_script.exists():
        print(f"❌ Extract script not found: {extract_script}")
        sys.exit(1)
    
    cmd = [
        sys.executable,
        str(extract_script),
        '--cpg', str(cpg_path),
        '--output', str(output_dir)
    ]
    
    if args.joern_path:
        cmd.extend(['--joern-path', args.joern_path])
    if args.source_dir:
        cmd.extend(['--source-dir', args.source_dir])
    if args.no_enhance:
        cmd.append('--no-enhance')
    
    print(f"\n⚙️  Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        nodes_file = output_dir / 'cpg_nodes.json'
        edges_file = output_dir / 'cpg_edges.json'
        
        print("\n✅ Extraction complete!")
        print(f"   Nodes: {nodes_file}")
        print(f"   Edges: {edges_file}")
        
        # Verify files
        if nodes_file.exists():
            import json
            with open(nodes_file) as f:
                nodes = json.load(f)
            print(f"   Total nodes: {len(nodes):,}")
        
        if edges_file.exists():
            import json
            with open(edges_file) as f:
                edges = json.load(f)
            print(f"   Total edges: {len(edges):,}")
    else:
        print(f"\n❌ Extraction failed")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)


if __name__ == '__main__':
    main()
