#!/usr/bin/env python3
"""
Simple CPG Extractor - Extract nodes and edges from existing CPG

This script extracts data from an existing Joern CPG binary file.
Use this if you already have a cpg.bin file.

Usage:
    python extract_from_cpg.py --cpg cpg.bin --output ./data
    python extract_from_cpg.py --cpg cpg.bin --nodes-only
"""

import os
import sys
import subprocess
import argparse
import json
from pathlib import Path
from typing import Optional, Dict, Any


class CPGExtractor:
    """Extract JSON from existing CPG binary."""
    
    def __init__(self, joern_path: Optional[str] = None):
        self.joern_path = joern_path or self._find_joern()
        
        # Try to find joern executable
        # First check joern-cli subdirectory
        joern_cli_path = os.path.join(self.joern_path, 'joern-cli', 'joern')
        if os.path.exists(joern_cli_path):
            self.joern_cli = joern_cli_path
        else:
            # Check directly in the path
            self.joern_cli = os.path.join(self.joern_path, 'joern')
            if not os.path.exists(self.joern_cli):
                # Last resort: check if joern is in PATH
                try:
                    result = subprocess.run(
                        ["which", "joern"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        self.joern_cli = result.stdout.strip()
                    else:
                        raise FileNotFoundError(f"Joern CLI not found at {self.joern_path}")
                except Exception:
                    raise FileNotFoundError(f"Joern CLI not found at {self.joern_path}")
    
    def _find_joern(self) -> str:
        """Auto-detect Joern installation."""
        # First, check if joern is in PATH
        try:
            result = subprocess.run(
                ["which", "joern"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                joern_path = result.stdout.strip()
                # Get the directory containing joern
                joern_dir = os.path.dirname(joern_path)
                # Go up to find the installation root (joern-cli or joern)
                if os.path.basename(joern_dir) == 'joern-cli':
                    return os.path.dirname(joern_dir)
                return joern_dir
        except Exception:
            pass
        
        # Check if joern-parse is in PATH and derive path from it
        try:
            result = subprocess.run(
                ["which", "joern-parse"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                joern_parse_path = result.stdout.strip()
                # Get the directory containing joern-parse
                joern_dir = os.path.dirname(joern_parse_path)
                # Go up to find the installation root
                if os.path.basename(joern_dir) == 'joern-cli':
                    return os.path.dirname(joern_dir)
                return joern_dir
        except Exception:
            pass
        
        # Fallback: check standard installation paths
        possible_paths = [
            '/opt/joern',
            '/usr/local/joern',
            os.path.expanduser('~/joern'),
            os.path.expanduser('~/bin/joern-installation'),
        ]
        
        for path in possible_paths:
            # Check for joern-cli subdirectory
            joern_cli_path = os.path.join(path, 'joern-cli', 'joern')
            if os.path.exists(joern_cli_path):
                return path
            # Check for joern directly
            joern_path = os.path.join(path, 'joern')
            if os.path.exists(joern_path):
                return path
        
        raise FileNotFoundError("Joern not found. Use --joern-path")
    
    def extract_nodes(self, cpg_file: str, output_file: str):
        """Extract all METHOD nodes."""
        print("📤 Extracting nodes...")
        
        # Extract nodes - use m.code directly (many will be <empty>, we'll filter in analysis)
        # This is simpler and avoids control character issues
        nodes_script = """
val methods = cpg.method.l

val json = methods.map { m =>
  val name = if (m.name != null) m.name.replace("\\"", "\\\\\\"").replace("\\n", "\\\\n").replace("\\r", "\\\\r") else ""
  val filename = if (m.filename != null) m.filename.replace("\\"", "\\\\\\"").replace("\\n", "\\\\n").replace("\\r", "\\\\r") else ""
  val code = if (m.code != null && m.code != "<empty>") m.code.replace("\\"", "\\\\\\"").replace("\\n", "\\\\n").replace("\\r", "\\\\r").take(2000) else "<empty>"
  
  s\"\"\"{"id":${m.id},"_label":"METHOD","name":"${name}","filename":"${filename}","lineNumber":${m.lineNumber.getOrElse(0)},"code":"${code}"}\"\"\"
}.mkString("[\\n  ", ",\\n  ", "\\n]")

import java.nio.file.{Files, Paths}
Files.write(Paths.get("NODES_FILE"), json.getBytes)
println(s"Exported ${methods.size} nodes")
""".replace('NODES_FILE', output_file)
        
        # Add importCpg at the beginning for CPG binary files
        full_script = f'importCpg("{cpg_file}")\n{nodes_script}'
        
        script_file = Path(output_file).parent / 'extract_nodes.sc'
        with open(script_file, 'w') as f:
            f.write(full_script)
        
        # Run Joern with script (newer versions don't use --cpg)
        cmd = [
            self.joern_cli,
            '--script', str(script_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_file):
            # Verify JSON
            try:
                with open(output_file) as f:
                    data = json.load(f)
                print(f"✅ Exported {len(data):,} nodes")
                script_file.unlink()
                return True
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error: {e}")
                return False
        else:
            print(f"❌ Export failed: {result.stderr}")
            return False
    
    def extract_edges(self, cpg_file: str, output_file: str):
        """Extract all CALL edges."""
        print("\n📤 Extracting edges...")
        
        # Build Scala script using escaped quotes (like cpg_workflow.py does)
        edges_script = """
val calls = cpg.call.l
val edges = calls.flatMap { c =>
  c.callee(NoResolve).l.map { callee =>
    s\"\"\"{"src":${c.id},"dst":${callee.id},"label":"CALL"}\"\"\"
  }
}
val json = edges.mkString("[\\n  ", ",\\n  ", "\\n]")

import java.nio.file.{Files, Paths}
Files.write(Paths.get("EDGES_FILE"), json.getBytes("UTF-8"))
println(s"✅ Exported ${edges.size} edges to EDGES_FILE")
""".replace('EDGES_FILE', output_file)
        
        # Add importCpg at the beginning for CPG binary files
        full_script = f'importCpg("{cpg_file}")\n{edges_script}'
        
        script_file = Path(output_file).parent / 'extract_edges.sc'
        with open(script_file, 'w') as f:
            f.write(full_script)
        
        # Run Joern with script (newer versions don't use --cpg)
        cmd = [
            self.joern_cli,
            '--script', str(script_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and os.path.exists(output_file):
            try:
                with open(output_file) as f:
                    data = json.load(f)
                print(f"✅ Exported {len(data):,} edges")
                script_file.unlink()
                return True
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error: {e}")
                return False
        else:
            print(f"❌ Export failed: {result.stderr}")
            return False
    
    def extract_method_source_code(
        self,
        file_path: str,
        line_number: int,
        method_name: str,
        source_base_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract method source code from file.
        
        Args:
            file_path: Path to source file (may be relative)
            line_number: Line number where method starts
            method_name: Name of the method
            source_base_dir: Base directory for source files (if paths are relative)
        
        Returns:
            Method source code or None if not found
        """
        # Try to find the source file
        source_file = Path(file_path)
        
        # If not absolute and base dir provided, try relative to base
        if not source_file.is_absolute() and source_base_dir:
            source_file = Path(source_base_dir) / source_file
        
        # If still doesn't exist, try just the filename
        if not source_file.exists():
            source_file = Path(source_file.name)
        
        if not source_file.exists():
            return None
        
        try:
            with open(source_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            if line_number < 1 or line_number > len(lines):
                return None
            
            # Start from the method line
            start_idx = line_number - 1
            
            # For Python, find the method definition and extract until next def/class at same or lower indentation
            method_lines = []
            base_indent = None
            
            for i in range(start_idx, len(lines)):
                line = lines[i]
                
                # Skip empty lines at start
                if not method_lines and not line.strip():
                    continue
                
                # Determine base indentation from first non-empty line
                if base_indent is None and line.strip():
                    base_indent = len(line) - len(line.lstrip())
                
                # If we hit a line at same or less indentation that's a def/class (and not our method)
                if base_indent is not None:
                    current_indent = len(line) - len(line.lstrip())
                    stripped = line.strip()
                    
                    # Stop if we hit another def/class at same or less indentation
                    if (stripped.startswith('def ') or stripped.startswith('class ')) and \
                       current_indent <= base_indent and \
                       i > start_idx:
                        break
                
                method_lines.append(line.rstrip())
            
            return '\n'.join(method_lines) if method_lines else None
            
        except Exception as e:
            print(f"Warning: Could not read {source_file}: {e}", file=sys.stderr)
            return None
    
    def enhance_nodes_with_source_code(
        self,
        nodes_file: str,
        source_base_dir: Optional[str] = None
    ) -> int:
        """
        Enhance CPG nodes JSON with actual source code from files.
        
        Args:
            nodes_file: Path to CPG nodes JSON file
            source_base_dir: Base directory for source files
        
        Returns:
            Number of nodes enhanced with source code
        """
        if not source_base_dir or not Path(source_base_dir).exists():
            return 0
        
        print(f"\n📝 Enhancing nodes with source code from '{source_base_dir}'...")
        
        with open(nodes_file, 'r') as f:
            nodes = json.load(f)
        
        enhanced_count = 0
        
        for node in nodes:
            if node.get('_label') != 'METHOD':
                continue
            
            filename = node.get('filename', '')
            line_number = node.get('lineNumber', 0)
            method_name = node.get('name', '')
            
            if filename and line_number > 0:
                source_code = self.extract_method_source_code(
                    filename, line_number, method_name, source_base_dir
                )
                
                if source_code and source_code.strip():
                    # Replace CPG representation with actual source code
                    node['code'] = source_code
                    node['codeSource'] = 'source_file'  # Mark as from source
                    enhanced_count += 1
                else:
                    node['codeSource'] = 'cpg'  # Keep CPG code
        
        # Save enhanced nodes
        with open(nodes_file, 'w') as f:
            json.dump(nodes, f, indent=2)
        
        print(f"✓ Enhanced {enhanced_count}/{len([n for n in nodes if n.get('_label') == 'METHOD'])} methods with source code")
        return enhanced_count


def main():
    parser = argparse.ArgumentParser(
        description='Extract JSON from existing CPG binary'
    )
    
    parser.add_argument(
        '--cpg',
        required=True,
        help='Path to cpg.bin file'
    )
    
    parser.add_argument(
        '--output', '-o',
        default='./data',
        help='Output directory (default: ./data)'
    )
    
    parser.add_argument(
        '--nodes-only',
        action='store_true',
        help='Extract only nodes (skip edges)'
    )
    
    parser.add_argument(
        '--edges-only',
        action='store_true',
        help='Extract only edges (skip nodes)'
    )
    
    parser.add_argument(
        '--joern-path',
        help='Path to Joern installation'
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
    
    if not os.path.exists(args.cpg):
        print(f"❌ CPG file not found: {args.cpg}")
        sys.exit(1)
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        extractor = CPGExtractor(joern_path=args.joern_path)
        
        success = True
        
        if not args.edges_only:
            nodes_file = output_dir / 'cpg_nodes.json'
            success = extractor.extract_nodes(args.cpg, str(nodes_file)) and success
        
        if not args.nodes_only:
            edges_file = output_dir / 'cpg_edges.json'
            success = extractor.extract_edges(args.cpg, str(edges_file)) and success
        
        if success:
            print("\n✅ Extraction complete!")
            print(f"\nOutput directory: {output_dir}")
            
            # Enhance with source code if requested
            if not args.no_enhance:
                source_dir = args.source_dir
                if not source_dir:
                    # Try to auto-detect from .source_info.json
                    cpg_path = Path(args.cpg)
                    source_info_path = cpg_path.with_suffix('.source_info.json')
                    if source_info_path.exists():
                        try:
                            with open(source_info_path, 'r') as f:
                                source_info = json.load(f)
                            source_dir = source_info.get("source_dir")
                            if source_dir and Path(source_dir).exists():
                                print(f"\n✓ Auto-detected source directory: {source_dir}")
                        except Exception as e:
                            print(f"Warning: Could not read source_info.json: {e}")
                
                if source_dir and Path(source_dir).exists():
                    if not args.edges_only:
                        extractor.enhance_nodes_with_source_code(str(nodes_file), source_dir)
                else:
                    print(f"\n⚠️  Source directory not found. Skipping source code enhancement.")
                    print(f"   Use --source-dir to specify source directory, or ensure .source_info.json exists.")
            
            print("\nNext step:")
            print(f"  python main.py fault-detection --all")
        else:
            print("\n⚠️  Some extractions failed. Check output files.")
            sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
