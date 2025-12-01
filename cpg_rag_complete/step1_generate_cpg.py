#!/usr/bin/env python3
"""
Step 1: Generate CPG from source code using Joern

This script runs joern-parse to create a CPG binary file from your codebase.

Usage:
    python step1_generate_cpg.py /path/to/your/source/code --output cpg.bin

Requirements:
    - Joern CLI installed and in PATH (or set JOERN_CLI_PATH in .env)
"""

import argparse
import subprocess
import sys
from pathlib import Path
import shutil


def find_joern_parse(joern_cli_path: str = None) -> str:
    """Find joern-parse executable."""
    # Check if provided path exists
    if joern_cli_path:
        joern_cli = Path(joern_cli_path)
        # Check if it's a directory containing joern-parse
        if joern_cli.is_dir():
            joern_parse = joern_cli / "joern-parse"
            if joern_parse.exists():
                return str(joern_parse)
        # Check if it's the executable itself
        if joern_cli.name == "joern-parse" and joern_cli.exists():
            return str(joern_cli)
    
    # Check if in PATH
    joern_parse = shutil.which("joern-parse")
    if joern_parse:
        return joern_parse
    
    # Check current directory for joern-cli folder
    cwd = Path.cwd()
    local_paths = [
        cwd / "joern-cli" / "joern-parse",
        cwd / "joern" / "joern-cli" / "joern-parse",
        cwd.parent / "joern-cli" / "joern-parse",
    ]
    
    for path in local_paths:
        if path.exists():
            print(f"   📍 Found joern-parse in local directory: {path}")
            return str(path)
    
    # Common installation paths
    common_paths = [
        Path.home() / "joern" / "joern-cli" / "joern-parse",
        Path.home() / "joern-cli" / "joern-parse",
        Path.home() / "bin" / "joern-parse",
        Path("/opt/joern/joern-cli/joern-parse"),
        Path("/usr/local/bin/joern-parse"),
    ]
    
    for path in common_paths:
        if path.exists():
            return str(path)
    
    return None


def generate_cpg(source_dir: str, output_file: str, joern_cli_path: str = None, 
                 language: str = None) -> bool:
    """
    Generate CPG binary from source code.
    
    Args:
        source_dir: Path to source code directory
        output_file: Output path for cpg.bin
        joern_cli_path: Path to joern-cli directory (optional)
        language: Language hint for Joern (optional, auto-detected)
    
    Returns:
        True if successful, False otherwise
    """
    source_path = Path(source_dir).resolve()
    output_path = Path(output_file).resolve()
    
    if not source_path.exists():
        print(f"❌ Error: Source directory does not exist: {source_path}")
        return False
    
    # Find joern-parse
    joern_parse = find_joern_parse(joern_cli_path)
    if not joern_parse:
        print("❌ Error: joern-parse not found!")
        print("   Please install Joern CLI: https://joern.io/")
        print("   Or set JOERN_CLI_PATH in your .env file")
        return False
    
    print(f"📁 Source directory: {source_path}")
    print(f"📦 Output file: {output_path}")
    print(f"🔧 Using joern-parse: {joern_parse}")
    
    # Build command
    cmd = [joern_parse, str(source_path), "-o", str(output_path)]
    
    if language:
        cmd.extend(["--language", language])
    
    print(f"\n🚀 Running: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        if result.returncode == 0:
            if output_path.exists():
                size_mb = output_path.stat().st_size / (1024 * 1024)
                print(f"✅ CPG generated successfully!")
                print(f"   File: {output_path}")
                print(f"   Size: {size_mb:.2f} MB")
                return True
            else:
                print(f"❌ Command succeeded but output file not found: {output_path}")
                return False
        else:
            print(f"❌ joern-parse failed with return code {result.returncode}")
            if result.stdout:
                print(f"   stdout: {result.stdout}")
            if result.stderr:
                print(f"   stderr: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        print("❌ joern-parse timed out after 10 minutes")
        return False
    except FileNotFoundError:
        print(f"❌ Could not execute joern-parse: {joern_parse}")
        return False
    except Exception as e:
        print(f"❌ Error running joern-parse: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Generate CPG from source code using Joern",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python step1_generate_cpg.py ./my-project
    python step1_generate_cpg.py ./my-project --output data/cpg.bin
    python step1_generate_cpg.py ./my-project --joern-path ~/joern/joern-cli
    python step1_generate_cpg.py ./my-project --language python
        """
    )
    
    parser.add_argument(
        "source_dir",
        help="Path to source code directory"
    )
    parser.add_argument(
        "--output", "-o",
        default="data/cpg.bin",
        help="Output path for CPG binary (default: data/cpg.bin)"
    )
    parser.add_argument(
        "--joern-path",
        help="Path to joern-cli directory"
    )
    parser.add_argument(
        "--language", "-l",
        choices=["python", "java", "javascript", "c", "cpp", "go", "php", "ruby"],
        help="Language hint for Joern (usually auto-detected)"
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("Step 1: Generate CPG from Source Code")
    print("=" * 60)
    
    success = generate_cpg(
        args.source_dir,
        args.output,
        args.joern_path,
        args.language
    )
    
    if success:
        print("\n" + "=" * 60)
        print("✅ Step 1 Complete!")
        print("=" * 60)
        print("\nNext step:")
        print(f"    python step2_extract_json.py {args.output}")
    else:
        print("\n❌ Step 1 Failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
