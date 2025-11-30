#!/usr/bin/env python3
"""
Joern CPG Generator - Create CPG JSON files from source code

This script uses Joern to analyze source code and generate:
- cpg_nodes.json (all nodes in the code property graph)
- cpg_edges.json (all edges/relationships between nodes)

Usage:
    python generate_cpg_json.py --source /path/to/code --output ./data
    python generate_cpg_json.py --source MedSAM --joern-path /opt/joern
"""

import os
import sys
import subprocess
import json
import argparse
from pathlib import Path
from typing import Optional


class JoernCPGGenerator:
    """
    Generate CPG JSON files using Joern.
    
    Requires Joern installation.
    """
    
    def __init__(self, joern_path: Optional[str] = None):
        """
        Initialize generator.
        
        Args:
            joern_path: Path to Joern installation (auto-detected if None)
        """
        self.joern_path = joern_path or self._find_joern()
        self.joern_parse = os.path.join(self.joern_path, 'joern-parse')
        self.joern_export = os.path.join(self.joern_path, 'joern-export')
        
        if not os.path.exists(self.joern_parse):
            raise FileNotFoundError(
                f"Joern not found at {self.joern_path}\n"
                "Install Joern: https://docs.joern.io/installation"
            )
    
    def _find_joern(self) -> str:
        """Auto-detect Joern installation."""
        possible_paths = [
            '/opt/joern',
            '/usr/local/joern',
            os.path.expanduser('~/joern'),
            os.path.expanduser('~/Downloads/joern'),
        ]
        
        for path in possible_paths:
            if os.path.exists(os.path.join(path, 'joern-parse')):
                return path
        
        # Try to find in PATH
        try:
            result = subprocess.run(
                ['which', 'joern-parse'],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                return os.path.dirname(result.stdout.strip())
        except:
            pass
        
        raise FileNotFoundError(
            "Joern not found. Please specify --joern-path or install Joern"
        )
    
    def generate_cpg(self, source_dir: str, output_dir: str = './data') -> dict:
        """
        Generate CPG JSON files from source code.
        
        Args:
            source_dir: Path to source code directory
            output_dir: Where to save JSON files
        
        Returns:
            Dict with paths to generated files
        """
        source_path = Path(source_dir).resolve()
        output_path = Path(output_dir).resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source directory not found: {source_dir}")
        
        print(f"🔍 Analyzing: {source_path}")
        print(f"📁 Output: {output_path}")
        
        # Step 1: Parse code to create CPG
        print("\n📊 Step 1: Parsing code with Joern...")
        cpg_bin = output_path / 'cpg.bin'
        
        parse_cmd = [
            self.joern_parse,
            str(source_path),
            '--output', str(cpg_bin)
        ]
        
        print(f"   Running: {' '.join(parse_cmd)}")
        result = subprocess.run(parse_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Error: {result.stderr}")
            raise RuntimeError("Joern parse failed")
        
        print(f"✅ CPG created: {cpg_bin}")
        
        # Step 2: Export nodes to JSON
        print("\n📤 Step 2: Exporting nodes...")
        nodes_file = output_path / 'cpg_nodes.json'
        
        # Create Joern script to export all nodes
        export_nodes_script = """
// Export all METHOD nodes with their properties
val methods = cpg.method.l
val methodsJson = methods.map { m =>
  Map(
    "id" -> m.id,
    "_label" -> "METHOD",
    "name" -> m.name,
    "signature" -> m.signature,
    "fullName" -> m.fullName,
    "filename" -> m.filename,
    "lineNumber" -> m.lineNumber.getOrElse(0),
    "code" -> m.code,
    "isExternal" -> m.isExternal,
    "order" -> m.order
  )
}

import io.circe.syntax._
import java.nio.file.{Files, Paths}
val json = methodsJson.asJson.spaces2
Files.write(Paths.get("NODES_OUTPUT_PATH"), json.getBytes)
"""
        
        script_file = output_path / 'export_nodes.sc'
        script_content = export_nodes_script.replace('NODES_OUTPUT_PATH', str(nodes_file))
        
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        export_nodes_cmd = [
            os.path.join(self.joern_path, 'joern'),
            '--script', str(script_file),
            '--cpg', str(cpg_bin)
        ]
        
        result = subprocess.run(export_nodes_cmd, capture_output=True, text=True)
        
        if nodes_file.exists():
            print(f"✅ Nodes exported: {nodes_file}")
            with open(nodes_file) as f:
                nodes = json.load(f)
            print(f"   Total nodes: {len(nodes):,}")
        else:
            # Fallback: use joern-export
            print("   Using joern-export as fallback...")
            self._export_with_joern_export(cpg_bin, nodes_file, 'nodes')
        
        # Step 3: Export edges to JSON
        print("\n📤 Step 3: Exporting edges...")
        edges_file = output_path / 'cpg_edges.json'
        
        export_edges_script = """
// Export all CALL edges
val edges = cpg.call.callOut.l
val edgesJson = edges.map { e =>
  Map(
    "src" -> e.inNode.id,
    "dst" -> e.outNode.id,
    "label" -> "CALL"
  )
}

import io.circe.syntax._
import java.nio.file.{Files, Paths}
val json = edgesJson.asJson.spaces2
Files.write(Paths.get("EDGES_OUTPUT_PATH"), json.getBytes)
"""
        
        script_file = output_path / 'export_edges.sc'
        script_content = export_edges_script.replace('EDGES_OUTPUT_PATH', str(edges_file))
        
        with open(script_file, 'w') as f:
            f.write(script_content)
        
        export_edges_cmd = [
            os.path.join(self.joern_path, 'joern'),
            '--script', str(script_file),
            '--cpg', str(cpg_bin)
        ]
        
        result = subprocess.run(export_edges_cmd, capture_output=True, text=True)
        
        if edges_file.exists():
            print(f"✅ Edges exported: {edges_file}")
            with open(edges_file) as f:
                edges = json.load(f)
            print(f"   Total edges: {len(edges):,}")
        else:
            print("   Using joern-export as fallback...")
            self._export_with_joern_export(cpg_bin, edges_file, 'edges')
        
        # Cleanup temporary files
        script_file.unlink(missing_ok=True)
        (output_path / 'export_nodes.sc').unlink(missing_ok=True)
        (output_path / 'export_edges.sc').unlink(missing_ok=True)
        
        print("\n✅ CPG generation complete!")
        return {
            'nodes': str(nodes_file),
            'edges': str(edges_file),
            'cpg_bin': str(cpg_bin)
        }
    
    def _export_with_joern_export(self, cpg_bin: Path, output_file: Path, export_type: str):
        """Fallback export using joern-export."""
        cmd = [
            self.joern_export,
            str(cpg_bin),
            '--repr', 'all',
            '--out', str(output_file)
        ]
        
        subprocess.run(cmd, capture_output=True)
        
        if output_file.exists():
            print(f"✅ {export_type.title()} exported: {output_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate CPG JSON files using Joern',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python generate_cpg_json.py --source MedSAM
  
  # Specify output directory
  python generate_cpg_json.py --source MedSAM --output ./data
  
  # Specify Joern path
  python generate_cpg_json.py --source MedSAM --joern-path /opt/joern
"""
    )
    
    parser.add_argument(
        '--source', '-s',
        required=True,
        help='Source code directory to analyze'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='./data',
        help='Output directory for JSON files (default: ./data)'
    )
    
    parser.add_argument(
        '--joern-path',
        help='Path to Joern installation (auto-detected if not specified)'
    )
    
    args = parser.parse_args()
    
    try:
        generator = JoernCPGGenerator(joern_path=args.joern_path)
        result = generator.generate_cpg(args.source, args.output)
        
        print("\n" + "=" * 70)
        print("📊 GENERATED FILES")
        print("=" * 70)
        print(f"  Nodes: {result['nodes']}")
        print(f"  Edges: {result['edges']}")
        print(f"  CPG Binary: {result['cpg_bin']}")
        print("\n✅ Ready to use with CPG RAG System!")
        print(f"\nNext step:")
        print(f"  python main.py fault-detection --all")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
