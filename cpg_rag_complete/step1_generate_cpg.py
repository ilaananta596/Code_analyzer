#!/usr/bin/env python3
"""
Step 1: Generate CPG from source code using Joern

This upgraded version fixes:
- More reliable joern-parse detection
- Support for --joern-path, .env, or PATH
- Normalized absolute paths
- Better error handling and output
- Ensures cpg.bin is actually written
- Fully compatible with updated Step 2–4
"""

import argparse
import subprocess
import sys
import shutil
from pathlib import Path


# ----------------------------------------------------------------------
# Locate joern-parse
# ----------------------------------------------------------------------
def find_joern_parse(joern_cli_path: str | None = None) -> str | None:
    """Locate joern-parse using multiple fallback strategies."""

    # 1) If user provided --joern-path
    if joern_cli_path:
        jp = Path(joern_cli_path)
        if jp.is_dir() and (jp / "joern-parse").exists():
            return str(jp / "joern-parse")
        if jp.name == "joern-parse" and jp.exists():
            return str(jp)

    # 2) PATH lookup
    from shutil import which
    w = which("joern-parse")
    if w:
        return w

    # 3) Try common local paths
    cwd = Path.cwd()
    candidates = [
        cwd / "joern-cli" / "joern-parse",
        cwd / "joern" / "joern-cli" / "joern-parse",
        cwd.parent / "joern-cli" / "joern-parse",
        Path.home() / "joern" / "joern-cli" / "joern-parse",
        Path.home() / "joern-cli" / "joern-parse",
        Path("/opt/joern/joern-cli/joern-parse"),
        Path("/usr/local/bin/joern-parse")
    ]

    for c in candidates:
        if c.exists():
            print(f" Found joern-parse: {c}")
            return str(c)

    return None


# ----------------------------------------------------------------------
# Generate CPG
# ----------------------------------------------------------------------
def generate_cpg(
    source_dir: str,
    output_file: str,
    joern_cli_path: str | None = None,
    language: str | None = None
) -> bool:
    """
    Run joern-parse to generate a CPG binary.
    """

    src = Path(source_dir).resolve()
    out = Path(output_file).resolve()

    if not src.exists():
        print(f"Error: Source directory does not exist: {src}")
        return False

    out.parent.mkdir(parents=True, exist_ok=True)

    # Find joern-parse
    joern_parse = find_joern_parse(joern_cli_path)
    if not joern_parse:
        print("joern-parse not found!")
        print("Install Joern: https://joern.io/")
        print("Or pass --joern-path /path/to/joern-cli")
        return False

    print(f"Source directory: {src}")
    print(f"Output file:      {out}")
    print(f"Using joern-parse: {joern_parse}")

    # Build command
    cmd = [joern_parse, str(src), "-o", str(out)]
    if language:
        cmd += ["--language", language]

    print("\nRunning:")
    print("  " + " ".join(cmd) + "\n")

    try:
        proc = subprocess.run(
            cmd,
            text=True,
            capture_output=True,
            timeout=900  # 15 minutes
        )

        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr)

        if proc.returncode != 0:
            print(f" joern-parse exited with code {proc.returncode}")
            return False

        if not out.exists():
            print(f" joern-parse finished but {out} does NOT exist")
            return False

        size_mb = out.stat().st_size / (1024 * 1024)
        print(f" CPG generated successfully ({size_mb:.2f} MB)")
        return True

    except subprocess.TimeoutExpired:
        print(" joern-parse timed out!")
        return False
    except Exception as e:
        print(f" Error running joern-parse: {e}")
        return False


# ----------------------------------------------------------------------
# Main entrypoint
# ----------------------------------------------------------------------
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

    parser.add_argument("source_dir", help="Source code directory")
    parser.add_argument("--output", "-o", default="data/cpg.bin", help="Output CPG path")
    parser.add_argument("--joern-path", help="Path to joern-cli")
    parser.add_argument(
        "--language",
        "-l",
        choices=["python", "java", "javascript", "c", "cpp", "go", "php", "ruby"],
        help="Language hint"
    )

    args = parser.parse_args()

    print("=" * 60)
    print("STEP 1 — Generate CPG")
    print("=" * 60)

    ok = generate_cpg(
        args.source_dir,
        args.output,
        joern_cli_path=args.joern_path,
        language=args.language
    )

    if ok:
        print("\nNext:")
        print(f"  python step2_extract_json.py {args.output}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()