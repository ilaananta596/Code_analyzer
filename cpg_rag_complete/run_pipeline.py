#!/usr/bin/env python3
"""
CPG RAG Complete Pipeline - Run All Steps

This script runs the complete pipeline from source code to RAG analysis:
1. Generate CPG from source code (joern-parse)
2. Extract JSON with deduplication and accurate line counts
3. Setup RAG system with vector stores
4. Run security analysis queries

Usage:
    python run_pipeline.py /path/to/source/code
    python run_pipeline.py /path/to/source/code --query "Find SQL injection"
    python run_pipeline.py /path/to/source/code --all --export md

Requirements:
    - Joern CLI installed
    - Ollama running with llama3.2 and nomic-embed-text models
"""

import argparse
import sys
import subprocess
from pathlib import Path
import shutil


def check_requirements():
    """Check if required tools are available."""
    print("🔍 Checking requirements...")
    
    issues = []
    
    # Check Joern - look in PATH and current directory
    joern_parse = shutil.which("joern-parse")
    joern_cli_local = Path.cwd() / "joern-cli"
    
    if joern_parse:
        print(f"   ✅ joern-parse: {joern_parse}")
    elif joern_cli_local.exists() and (joern_cli_local / "joern-parse").exists():
        print(f"   ✅ joern-parse: {joern_cli_local / 'joern-parse'} (local)")
    else:
        issues.append("joern-parse not found in PATH or ./joern-cli/")
    
    joern = shutil.which("joern")
    if joern:
        print(f"   ✅ joern: {joern}")
    elif joern_cli_local.exists() and (joern_cli_local / "joern").exists():
        print(f"   ✅ joern: {joern_cli_local / 'joern'} (local)")
    else:
        issues.append("joern not found in PATH or ./joern-cli/")
    
    # Check Ollama
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("   ✅ Ollama is running")
        else:
            issues.append("Ollama not responding (run: ollama serve)")
    except Exception:
        issues.append("Cannot connect to Ollama (run: ollama serve)")
    
    # Check Python packages
    try:
        import langchain_community
        print("   ✅ langchain_community installed")
    except ImportError:
        issues.append("langchain_community not installed (pip install langchain-community)")
    
    try:
        import chromadb
        print("   ✅ chromadb installed")
    except ImportError:
        issues.append("chromadb not installed (pip install chromadb)")
    
    if issues:
        print("\n⚠️  Missing requirements:")
        for issue in issues:
            print(f"   - {issue}")
        return False
    
    print("   ✅ All requirements satisfied!")
    return True


def run_step(step_name: str, command: list, cwd: str = None):
    """Run a pipeline step."""
    print(f"\n{'=' * 60}")
    print(f"🔄 {step_name}")
    print('=' * 60)
    
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            timeout=1800  # 30 minute timeout
        )
        
        if result.returncode != 0:
            print(f"\n❌ {step_name} failed with return code {result.returncode}")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print(f"\n❌ {step_name} timed out")
        return False
    except Exception as e:
        print(f"\n❌ {step_name} error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run complete CPG RAG pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Full pipeline with interactive query mode
    python run_pipeline.py /path/to/your/code --interactive
    
    # Full pipeline with specific query
    python run_pipeline.py /path/to/your/code --query "Find SQL injection"
    
    # Full pipeline with security analysis
    python run_pipeline.py /path/to/your/code --all --export md
    
    # Skip CPG generation (use existing cpg.bin)
    python run_pipeline.py --skip-cpg --cpg data/cpg.bin
    
    # Only run steps 1-2 (generate and extract)
    python run_pipeline.py /path/to/your/code --steps 1,2
        """
    )
    
    parser.add_argument(
        "source_dir",
        nargs='?',
        help="Path to source code directory"
    )
    parser.add_argument(
        "--cpg",
        help="Path to existing CPG file (skip step 1)"
    )
    parser.add_argument(
        "--skip-cpg",
        action="store_true",
        help="Skip CPG generation (use existing)"
    )
    parser.add_argument(
        "--steps",
        help="Steps to run (e.g., '1,2,3' or '2-4')"
    )
    parser.add_argument(
        "--query", "-q",
        help="Query to run after setup"
    )
    parser.add_argument(
        "--all", "-a",
        action="store_true",
        help="Run full security analysis"
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Run interactive query mode"
    )
    parser.add_argument(
        "--export", "-e",
        choices=['json', 'md', 'csv'],
        help="Export format for results"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force recreate all data"
    )
    parser.add_argument(
        "--joern-path",
        help="Path to joern-cli directory"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Only check requirements"
    )
    
    args = parser.parse_args()
    
    # Get script directory
    script_dir = Path(__file__).parent.resolve()
    data_dir = script_dir / "data"
    
    print("=" * 60)
    print("🚀 CPG RAG Complete Pipeline")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        if args.check:
            sys.exit(1)
        print("\n⚠️  Some requirements missing. Continuing anyway...")
    
    if args.check:
        sys.exit(0)
    
    # Determine which steps to run
    steps_to_run = [1, 2, 3, 4]
    
    if args.steps:
        if ',' in args.steps:
            steps_to_run = [int(s) for s in args.steps.split(',')]
        elif '-' in args.steps:
            start, end = args.steps.split('-')
            steps_to_run = list(range(int(start), int(end) + 1))
        else:
            steps_to_run = [int(args.steps)]
    
    if args.skip_cpg:
        steps_to_run = [s for s in steps_to_run if s != 1]
    
    # Validate inputs
    cpg_path = args.cpg or str(data_dir / "cpg.bin")
    
    # Auto-detect joern-cli if not provided
    joern_path = args.joern_path
    if not joern_path:
        local_joern = Path.cwd() / "joern-cli"
        if local_joern.exists():
            joern_path = str(local_joern)
            print(f"   📍 Auto-detected joern-cli: {joern_path}")
    
    if 1 in steps_to_run and not args.source_dir:
        print("❌ Error: Source directory required for step 1")
        print("   Usage: python run_pipeline.py /path/to/source/code")
        sys.exit(1)
    
    # Create data directory
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Step 1: Generate CPG
    if 1 in steps_to_run:
        cmd = [
            sys.executable, str(script_dir / "step1_generate_cpg.py"),
            args.source_dir,
            "--output", cpg_path
        ]
        if joern_path:
            cmd.extend(["--joern-path", joern_path])
        
        if not run_step("Step 1: Generate CPG", cmd, str(script_dir)):
            sys.exit(1)
    
    # Step 2: Extract JSON
    if 2 in steps_to_run:
        cmd = [
            sys.executable, str(script_dir / "step2_extract_json.py"),
            cpg_path,
            "--output", str(data_dir)
        ]
        if args.source_dir:
            cmd.extend(["--source-dir", args.source_dir])
        if joern_path:
            cmd.extend(["--joern-path", joern_path])
        
        if not run_step("Step 2: Extract JSON", cmd, str(script_dir)):
            sys.exit(1)
    
    # Step 3: Setup RAG
    if 3 in steps_to_run:
        cmd = [
            sys.executable, str(script_dir / "step3_setup_rag.py"),
            "--data-dir", str(data_dir)
        ]
        if args.source_dir:
            cmd.extend(["--source-dir", args.source_dir])
        if args.force:
            cmd.append("--force")
        
        if not run_step("Step 3: Setup RAG", cmd, str(script_dir)):
            sys.exit(1)
    
    # Step 4: Query/Analyze
    if 4 in steps_to_run:
        cmd = [sys.executable, str(script_dir / "step4_query_rag.py")]
        
        if args.interactive:
            cmd.append("--interactive")
        elif args.all:
            cmd.append("--all")
            if args.export:
                cmd.extend(["--export", args.export])
        elif args.query:
            cmd.extend(["--query", args.query])
            if args.export:
                cmd.extend(["--export", args.export])
        else:
            # Default: run full analysis
            cmd.append("--all")
            if args.export:
                cmd.extend(["--export", args.export])
        
        if not run_step("Step 4: Query/Analyze", cmd, str(script_dir)):
            sys.exit(1)
    
    print("\n" + "=" * 60)
    print("✅ Pipeline Complete!")
    print("=" * 60)
    
    if 4 not in steps_to_run:
        print("\nTo query the RAG system:")
        print(f"    cd {script_dir}")
        print("    python step4_query_rag.py --interactive")
        print("    python step4_query_rag.py --query 'Your question here'")


if __name__ == "__main__":
    main()
