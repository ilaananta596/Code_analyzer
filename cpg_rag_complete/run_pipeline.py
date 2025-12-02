#!/usr/bin/env python3
"""
CPG RAG Complete Pipeline Runner - Enhanced Version
Runs the complete pipeline from source code to interactive RAG queries.
"""

import argparse
import subprocess
import sys
from pathlib import Path

from config import Config
from step4_query_rag import EnhancedRAGQueryEngine


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "="*60)
    print(f" {title}")
    print("="*60)


def check_requirements():
    """Check if required tools and packages are available."""
    print_header("Checking Requirements")
    
    issues = []
    
    # Check Ollama
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print(" Ollama is running")
        else:
            issues.append("Ollama not responding")
    except Exception:
        issues.append("Cannot connect to Ollama")
    
    # Check Python packages
    required_packages = {
        'langchain_community': 'langchain_community',
        'chromadb': 'chromadb',
        'tqdm': 'tqdm'
    }
    
    for package, import_name in required_packages.items():
        try:
            __import__(import_name)
            print(f" {package} installed")
        except ImportError:
            issues.append(f"{package} not installed")
    
    # Check joern (optional)
    joern_parse_found = False
    joern_found = False
    
    # Check in PATH
    result = subprocess.run(["which", "joern-parse"], capture_output=True)
    if result.returncode == 0:
        joern_parse_found = True
    
    result = subprocess.run(["which", "joern"], capture_output=True)
    if result.returncode == 0:
        joern_found = True
    
    # Check in local directory
    if Path("./joern-cli/joern-parse").exists():
        joern_parse_found = True
    if Path("./joern-cli/joern").exists():
        joern_found = True
    
    if not joern_parse_found:
        issues.append("joern-parse not found in PATH or ./joern-cli/")
    if not joern_found:
        issues.append("joern not found in PATH or ./joern-cli/")
    
    if issues:
        print("\n Missing requirements:")
        for issue in issues:
            print(f"   - {issue}")
        print("\n Some requirements missing. Continuing anyway...")
    
    return len(issues) == 0


def run_step(step_num: int, title: str, command: list, optional: bool = False):
    """Run a pipeline step."""
    print_header(f"Step {step_num}: {title}")
    
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=False
        )
        return True
    except subprocess.CalledProcessError as e:
        if optional:
            print(f" Step {step_num} failed (optional): {e}")
            return False
        else:
            print(f" Step {step_num} failed: {e}")
            return False
    except Exception as e:
        print(f" Error in step {step_num}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Run the complete CPG RAG pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "source_dir",
        help="Path to source code directory to analyze"
    )
    
    parser.add_argument(
        "--joern-path",
        default="",
        help="Path to joern-cli directory (if not in PATH)"
    )
    
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="Start interactive query mode after pipeline"
    )
    
    parser.add_argument(
        "--skip-cpg",
        action="store_true",
        help="Skip CPG generation (use existing data)"
    )
    
    parser.add_argument(
        "--skip-rag-setup",
        action="store_true",
        help="Skip RAG setup (use existing vector stores)"
    )
    
    args = parser.parse_args()
    
    # Validate source directory
    source_path = Path(args.source_dir)
    if not source_path.exists():
        print(f" Error: Source directory does not exist: {args.source_dir}")
        sys.exit(1)
    
    print("="*60)
    print(" CPG RAG Complete Pipeline - Enhanced Version")
    print("="*60)
    
    # Check requirements
    all_requirements_met = check_requirements()
    
    # Ensure data directories exist
    Config.ensure_directories()
    
    # Step 1: Generate CPG
    if not args.skip_cpg:
        cmd = ["python", "step1_generate_cpg.py", str(source_path)]
        if args.joern_path:
            cmd.extend(["--joern-path", args.joern_path])
        
        success = run_step(1, "Generate CPG", cmd)
        if not success:
            print("\n CPG generation failed. Continuing with AST-only extraction...")
    
    # Step 2: Extract JSON
    if not args.skip_cpg:
        cpg_file = Config.DATA_DIR / "cpg.bin"
        cmd = [
            "python", "step2_extract_json.py",
            str(cpg_file),
            "--source-dir", str(source_path)
        ]
        
        success = run_step(2, "Extract JSON", cmd)
        if not success:
            print("\n JSON extraction failed. Cannot continue.")
            sys.exit(1)
    
    # Step 3: Setup RAG
    if not args.skip_rag_setup:
        cmd = [
            "python", "step3_setup_rag.py",
            "--source-dir", str(source_path)
        ]
        
        success = run_step(3, "Setup RAG", cmd)
        if not success:
            print("\n RAG setup failed. Cannot continue.")
            sys.exit(1)
    
    # Step 4: Interactive Query
    if args.interactive:
        print_header("Step 4: Interactive Query Mode")
        print("Initializing enhanced query engine...\n")
        
        engine = EnhancedRAGQueryEngine()
        engine.initialize()
        
        from step4_query_rag import interactive_mode
        interactive_mode(engine)
    else:
        print_header("Pipeline Complete!")
        print("\nNext steps:")
        print("  1. Run queries: python step4_query_rag.py --query 'your question'")
        print("  2. Interactive mode: python step4_query_rag.py --interactive")
        print("  3. Re-run with updates: python run_pipeline.py <source_dir> --skip-cpg --skip-rag-setup --interactive")


if __name__ == "__main__":
    main()