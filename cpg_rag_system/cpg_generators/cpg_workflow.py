#!/usr/bin/env python3
"""
Complete CPG Workflow - From Source Code to Analysis

This script handles the complete workflow:
1. Generate CPG from source code (using Joern)
2. Extract nodes and edges to JSON
3. Optionally run analysis

Usage:
    python cpg_workflow.py --source MedSAM
    python cpg_workflow.py --source MedSAM --analyze
    python cpg_workflow.py --source MedSAM --joern /opt/joern --analyze
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
import time


class CPGWorkflow:
    """Complete CPG generation and analysis workflow."""
    
    def __init__(self, joern_path: str = None):
        self.joern_path = joern_path or self._find_joern()
        print(f"🔧 Using Joern: {self.joern_path}")
    
    def _find_joern(self) -> str:
        """Auto-detect Joern."""
        paths = ['/opt/joern', '/usr/local/joern', os.path.expanduser('~/joern')]
        
        for path in paths:
            if os.path.exists(os.path.join(path, 'joern-parse')):
                return path
        
        # Ask user
        print("\n⚠️  Joern not found automatically.")
        print("Please enter Joern installation path (or press Enter to skip):")
        user_path = input("> ").strip()
        
        if user_path and os.path.exists(user_path):
            return user_path
        
        return None
    
    def step1_generate_cpg(self, source_dir: str) -> str:
        """Step 1: Generate CPG binary."""
        print("\n" + "=" * 70)
        print("📊 STEP 1: Generating CPG")
        print("=" * 70)
        
        if not self.joern_path:
            print("❌ Joern not found. Please install Joern first.")
            print("   https://docs.joern.io/installation")
            sys.exit(1)
        
        source_path = Path(source_dir).resolve()
        cpg_file = Path('data/cpg.bin').resolve()
        cpg_file.parent.mkdir(parents=True, exist_ok=True)
        
        joern_parse = os.path.join(self.joern_path, 'joern-parse')
        
        cmd = [joern_parse, str(source_path), '--output', str(cpg_file)]
        
        print(f"🔍 Analyzing: {source_path}")
        print(f"📁 Output: {cpg_file}")
        print(f"⚙️  Command: {' '.join(cmd)}")
        
        start = time.time()
        result = subprocess.run(cmd, capture_output=True, text=True)
        elapsed = time.time() - start
        
        if result.returncode == 0 and cpg_file.exists():
            size_mb = cpg_file.stat().st_size / (1024 * 1024)
            print(f"✅ CPG generated ({size_mb:.1f} MB) in {elapsed:.1f}s")
            return str(cpg_file)
        else:
            print(f"❌ Error: {result.stderr}")
            sys.exit(1)
    
    def step2_extract_json(self, cpg_file: str):
        """Step 2: Extract JSON files."""
        print("\n" + "=" * 70)
        print("📤 STEP 2: Extracting JSON")
        print("=" * 70)
        
        # Use the extract_from_cpg.py script
        extract_script = Path(__file__).parent / 'extract_from_cpg.py'
        
        if extract_script.exists():
            cmd = [
                sys.executable,
                str(extract_script),
                '--cpg', cpg_file,
                '--output', 'data',
                '--joern-path', self.joern_path
            ]
            
            result = subprocess.run(cmd)
            
            if result.returncode == 0:
                return {
                    'nodes': 'data/cpg_nodes.json',
                    'edges': 'data/cpg_edges.json'
                }
        
        # Fallback: manual extraction
        return self._manual_extract(cpg_file)
    
    def _manual_extract(self, cpg_file: str) -> dict:
        """Manual JSON extraction."""
        print("Using manual extraction...")
        
        nodes_file = 'data/cpg_nodes.json'
        edges_file = 'data/cpg_edges.json'
        
        # Nodes extraction script
        nodes_script = """
val methods = cpg.method.l
val json = methods.map { m =>
  s\"\"\"{"id":${m.id},"_label":"METHOD","name":"${m.name.replace("\"", "\\\\\"")}","filename":"${m.filename.replace("\"", "\\\\\"")}","lineNumber":${m.lineNumber.getOrElse(0)},"code":"${m.code.replace("\"", "\\\\\"").replace("\\n", "\\\\n").take(500)}"}\"\"\"
}.mkString("[\\n  ", ",\\n  ", "\\n]")

import java.nio.file.{Files, Paths}
Files.write(Paths.get("NODES_FILE"), json.getBytes)
println(s"Exported ${methods.size} nodes")
""".replace('NODES_FILE', nodes_file)
        
        script_file = Path('data/extract_nodes.sc')
        script_file.write_text(nodes_script)
        
        joern = os.path.join(self.joern_path, 'joern')
        cmd = [joern, '--script', str(script_file), '--cpg', cpg_file]
        
        subprocess.run(cmd, capture_output=True)
        script_file.unlink()
        
        # Edges extraction
        edges_script = """
val calls = cpg.call.l
val edges = calls.flatMap { c =>
  c.callee(NoResolve).l.map { callee =>
    s\"\"\"{"src":${c.id},"dst":${callee.id},"label":"CALL"}\"\"\"
  }
}
val json = edges.mkString("[\\n  ", ",\\n  ", "\\n]")

import java.nio.file.{Files, Paths}
Files.write(Paths.get("EDGES_FILE"), json.getBytes)
println(s"Exported ${edges.size} edges")
""".replace('EDGES_FILE', edges_file)
        
        script_file = Path('data/extract_edges.sc')
        script_file.write_text(edges_script)
        
        cmd = [joern, '--script', str(script_file), '--cpg', cpg_file]
        subprocess.run(cmd, capture_output=True)
        script_file.unlink()
        
        return {'nodes': nodes_file, 'edges': edges_file}
    
    def step3_verify(self, files: dict):
        """Step 3: Verify generated files."""
        print("\n" + "=" * 70)
        print("✅ STEP 3: Verification")
        print("=" * 70)
        
        import json
        
        for name, filepath in files.items():
            if os.path.exists(filepath):
                size_mb = os.path.getsize(filepath) / (1024 * 1024)
                
                try:
                    with open(filepath) as f:
                        data = json.load(f)
                    
                    print(f"✅ {name}: {len(data):,} items ({size_mb:.1f} MB)")
                except:
                    print(f"⚠️  {name}: {size_mb:.1f} MB (JSON validation failed)")
            else:
                print(f"❌ {name}: File not found")
    
    def step4_analyze(self):
        """Step 4: Run analysis."""
        print("\n" + "=" * 70)
        print("🔍 STEP 4: Running Analysis")
        print("=" * 70)
        
        main_script = Path(__file__).parent.parent / 'main.py'
        
        if main_script.exists():
            print("\nRunning fault detection...")
            cmd = [sys.executable, str(main_script), 'fault-detection', '--all']
            subprocess.run(cmd)
        else:
            print("⚠️  main.py not found. Skipping analysis.")
            print("Run manually: python main.py fault-detection --all")


def main():
    parser = argparse.ArgumentParser(
        description='Complete CPG workflow: Generate → Extract → Analyze',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic workflow
  python cpg_workflow.py --source MedSAM

  # With analysis
  python cpg_workflow.py --source MedSAM --analyze

  # Specify Joern path
  python cpg_workflow.py --source MedSAM --joern /opt/joern --analyze
"""
    )
    
    parser.add_argument(
        '--source', '-s',
        required=True,
        help='Source code directory to analyze'
    )
    
    parser.add_argument(
        '--joern',
        help='Path to Joern installation (auto-detected if not specified)'
    )
    
    parser.add_argument(
        '--analyze', '-a',
        action='store_true',
        help='Run analysis after generating CPG'
    )
    
    parser.add_argument(
        '--skip-generation',
        action='store_true',
        help='Skip CPG generation (use existing cpg.bin)'
    )
    
    args = parser.parse_args()
    
    workflow = CPGWorkflow(joern_path=args.joern)
    
    print("\n🚀 CPG WORKFLOW")
    print("=" * 70)
    
    # Step 1: Generate CPG
    if not args.skip_generation:
        cpg_file = workflow.step1_generate_cpg(args.source)
    else:
        cpg_file = 'data/cpg.bin'
        if not os.path.exists(cpg_file):
            print(f"❌ CPG file not found: {cpg_file}")
            sys.exit(1)
    
    # Step 2: Extract JSON
    files = workflow.step2_extract_json(cpg_file)
    
    # Step 3: Verify
    workflow.step3_verify(files)
    
    # Step 4: Analyze (optional)
    if args.analyze:
        workflow.step4_analyze()
    
    print("\n" + "=" * 70)
    print("✅ WORKFLOW COMPLETE!")
    print("=" * 70)
    print(f"\nGenerated files:")
    print(f"  - data/cpg_nodes.json")
    print(f"  - data/cpg_edges.json")
    print(f"  - data/cpg.bin")
    print(f"\nNext steps:")
    if not args.analyze:
        print(f"  python main.py fault-detection --all")
        print(f"  python main.py sensitive-data --all")
        print(f"  python main.py understand --overview")


if __name__ == '__main__':
    main()
