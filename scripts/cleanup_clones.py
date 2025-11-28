#!/usr/bin/env python3
"""
Clean up all cloned repositories from previous CPG builds.
"""

import json
import shutil
from pathlib import Path
import sys

def cleanup_all_clones():
    """Delete all cloned repositories found in source_info.json files"""
    cpg_dir = Path("data/cpg")
    if not cpg_dir.exists():
        print("No CPG directory found. Nothing to clean up.")
        return
    
    cleaned = []
    
    # Find all source_info.json files
    for source_info_file in cpg_dir.glob("*.source_info.json"):
        try:
            with open(source_info_file, 'r') as f:
                source_info = json.load(f)
            
            clone_dir = source_info.get("source_dir")
            if clone_dir and Path(clone_dir).exists():
                print(f"Found cloned repo: {clone_dir}")
                try:
                    shutil.rmtree(clone_dir)
                    cleaned.append(clone_dir)
                    print(f"  ✓ Deleted: {clone_dir}")
                except Exception as e:
                    print(f"  ✗ Error deleting {clone_dir}: {e}")
        except Exception as e:
            print(f"Error reading {source_info_file}: {e}")
    
    # Also find any temp clone directories directly
    import tempfile
    temp_base = Path(tempfile.gettempdir())
    for clone_dir in temp_base.glob("graphrag_clone_*"):
        if clone_dir.is_dir():
            print(f"Found temp clone directory: {clone_dir}")
            try:
                shutil.rmtree(clone_dir)
                cleaned.append(str(clone_dir))
                print(f"  ✓ Deleted: {clone_dir}")
            except Exception as e:
                print(f"  ✗ Error deleting {clone_dir}: {e}")
    
    # Check current directory too
    for clone_dir in Path(".").glob("graphrag_clone_*"):
        if clone_dir.is_dir():
            print(f"Found clone directory in current dir: {clone_dir}")
            try:
                shutil.rmtree(clone_dir)
                cleaned.append(str(clone_dir))
                print(f"  ✓ Deleted: {clone_dir}")
            except Exception as e:
                print(f"  ✗ Error deleting {clone_dir}: {e}")
    
    if cleaned:
        print(f"\n✓ Cleaned up {len(cleaned)} cloned repositories")
    else:
        print("\nNo cloned repositories found to clean up.")

if __name__ == "__main__":
    cleanup_all_clones()

