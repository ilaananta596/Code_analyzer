#!/usr/bin/env python3
"""
Build Code Property Graph (CPG) from source code using Joern.
Supports both local directories and GitHub repositories.
"""

import argparse
import subprocess
import sys
import tempfile
import shutil
import re
import json
from pathlib import Path
from urllib.parse import urlparse


def is_github_url(url: str) -> bool:
    """Check if the input is a GitHub URL."""
    patterns = [
        r'^https?://github\.com/[\w\-\.]+/[\w\-\.]+',
        r'^git@github\.com:[\w\-\.]+/[\w\-\.]+',
        r'^github\.com/[\w\-\.]+/[\w\-\.]+'
    ]
    return any(re.match(pattern, url) for pattern in patterns)


def normalize_github_url(url: str) -> str:
    """Normalize GitHub URL to HTTPS format."""
    # Handle git@github.com:user/repo format
    if url.startswith('git@github.com:'):
        url = url.replace('git@github.com:', 'https://github.com/')
    
    # Handle github.com/user/repo format
    if url.startswith('github.com/'):
        url = 'https://' + url
    
    # Remove .git suffix if present
    if url.endswith('.git'):
        url = url[:-4]
    
    return url


def clone_github_repo(github_url: str, target_dir: str, branch: str = None) -> bool:
    """
    Clone a GitHub repository to a target directory.
    
    Args:
        github_url: GitHub repository URL
        target_dir: Directory to clone into
        branch: Optional branch/tag to checkout
    
    Returns:
        True if successful, False otherwise
    """
    normalized_url = normalize_github_url(github_url)
    
    print(f"Cloning repository from '{normalized_url}'...")
    
    try:
        # Check if git is available
        subprocess.run(
            ["git", "--version"],
            check=True,
            capture_output=True,
            timeout=5
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Error: git not found in PATH")
        print("Please install git to clone GitHub repositories")
        return False
    
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)
    
    try:
        # Clone the repository
        clone_cmd = ["git", "clone", normalized_url, str(target_path)]
        if branch:
            clone_cmd.extend(["--branch", branch, "--single-branch"])
        
        result = subprocess.run(
            clone_cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )
        
        print(f"✓ Repository cloned successfully to '{target_dir}'")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Error cloning repository:")
        print(f"  Return code: {e.returncode}")
        if e.stderr:
            print(f"  stderr: {e.stderr}")
        return False
    except subprocess.TimeoutExpired:
        print("Error: Git clone timed out (repository may be too large)")
        return False
    except Exception as e:
        print(f"Unexpected error during clone: {e}")
        return False


def build_cpg(source_dir: str, output_path: str) -> bool:
    """
    Build CPG from source directory using joern-parse.
    
    Args:
        source_dir: Path to source code directory
        output_path: Path where CPG will be saved (.cpg.bin)
    
    Returns:
        True if successful, False otherwise
    """
    source_path = Path(source_dir)
    if not source_path.exists():
        print(f"Error: Source directory '{source_dir}' does not exist")
        return False
    
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if joern-parse is available
    try:
        result = subprocess.run(
            ["joern-parse", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
    except FileNotFoundError:
        print("Error: joern-parse not found in PATH")
        print("Please ensure Joern is installed and joern-parse is accessible")
        return False
    except subprocess.TimeoutExpired:
        pass
    
    print(f"Building CPG from '{source_dir}'...")
    print(f"Output will be saved to '{output_path}'")
    
    try:
        # Run joern-parse
        result = subprocess.run(
            ["joern-parse", source_dir, "--output", output_path],
            check=True,
            capture_output=True,
            text=True
        )
        
        if output_file.exists():
            print(f"✓ CPG successfully created at '{output_path}'")
            print(f"  Size: {output_file.stat().st_size / (1024*1024):.2f} MB")
            return True
        else:
            print(f"Error: CPG file was not created at '{output_path}'")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"Error running joern-parse:")
        print(f"  Return code: {e.returncode}")
        if e.stdout:
            print(f"  stdout: {e.stdout}")
        if e.stderr:
            print(f"  stderr: {e.stderr}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Build Code Property Graph (CPG) from source code or GitHub repository"
    )
    parser.add_argument(
        "source",
        help="Path to source code directory or GitHub repository URL"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output path for CPG file (e.g., project.cpg.bin)"
    )
    parser.add_argument(
        "--branch", "-b",
        help="Git branch or tag to checkout (for GitHub repos only)"
    )
    parser.add_argument(
        "--keep-clone",
        action="store_true",
        help="Keep cloned repository after building CPG (for GitHub repos)"
    )
    parser.add_argument(
        "--clone-dir",
        help="Directory to clone GitHub repo (default: temporary directory)"
    )
    
    args = parser.parse_args()
    
    # Check if input is a GitHub URL
    if is_github_url(args.source):
        print("=" * 80)
        print("GitHub Repository Detected")
        print("=" * 80)
        
        # Determine clone directory
        if args.clone_dir:
            clone_dir = args.clone_dir
            cleanup_clone = False
        else:
            # Use temporary directory
            clone_dir = tempfile.mkdtemp(prefix="graphrag_clone_")
            cleanup_clone = not args.keep_clone
        
        try:
            # Clone repository
            if not clone_github_repo(args.source, clone_dir, args.branch):
                sys.exit(1)
            
            # Build CPG from cloned directory
            print()
            success = build_cpg(clone_dir, args.output)
            
            # Save source directory info for later use (before cleanup)
            if success:
                source_info_path = Path(args.output).with_suffix('.source_info.json')
                source_info = {
                    "source_dir": clone_dir,
                    "source_type": "github_clone",
                    "cleanup": cleanup_clone
                }
                with open(source_info_path, 'w') as f:
                    json.dump(source_info, f, indent=2)
                print(f"✓ Saved source directory info to '{source_info_path}'")
                
                if cleanup_clone:
                    print(f"\n⚠ Note: Cloned repository will be cleaned up.")
                    print(f"  To extract source code, use --keep-clone or extract methods immediately.")
            
            # Cleanup if requested
            if cleanup_clone and Path(clone_dir).exists():
                print(f"\nCleaning up cloned repository at '{clone_dir}'...")
                shutil.rmtree(clone_dir)
                print("✓ Cleanup complete")
            
            sys.exit(0 if success else 1)
            
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            if cleanup_clone and Path(clone_dir).exists():
                print(f"Cleaning up cloned repository...")
                shutil.rmtree(clone_dir)
            sys.exit(1)
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            if cleanup_clone and Path(clone_dir).exists():
                print(f"Cleaning up cloned repository...")
                shutil.rmtree(clone_dir)
            sys.exit(1)
    else:
        # Local directory
        success = build_cpg(args.source, args.output)
        
        # Save source directory info for later use
        if success:
            source_info_path = Path(args.output).with_suffix('.source_info.json')
            source_info = {
                "source_dir": args.source,
                "source_type": "local_directory"
            }
            with open(source_info_path, 'w') as f:
                json.dump(source_info, f, indent=2)
            print(f"✓ Saved source directory info to '{source_info_path}'")
        
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

