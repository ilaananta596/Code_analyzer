#!/usr/bin/env python3
"""
Helper script to extract actual source code from methods.json
by reading from source files using filePath and lineNumber.
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, Optional


def extract_method_source_code(
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


def enhance_methods_with_source_code(
    methods_json_path: str,
    output_json_path: str,
    source_base_dir: Optional[str] = None
) -> bool:
    """
    Enhance methods.json with actual source code.
    
    Args:
        methods_json_path: Path to input methods.json
        output_json_path: Path to output enhanced methods.json
        source_base_dir: Base directory for source files
    """
    with open(methods_json_path, 'r') as f:
        data = json.load(f)
    
    methods = data.get("methods", [])
    enhanced_count = 0
    
    for method in methods:
        file_path = method.get("filePath", "")
        line_number = method.get("lineNumber", 0)
        method_name = method.get("methodName", "")
        
        if file_path and line_number > 0:
            source_code = extract_method_source_code(
                file_path, line_number, method_name, source_base_dir
            )
            
            if source_code:
                # Replace AST code with actual source code
                method["code"] = source_code
                method["codeSource"] = "source_file"  # Mark as from source
                enhanced_count += 1
            else:
                method["codeSource"] = "ast"  # Keep AST code
    
    # Save enhanced methods
    output_path = Path(output_json_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Enhanced {enhanced_count}/{len(methods)} methods with source code")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Enhance methods.json with actual source code from files"
    )
    parser.add_argument("methods_json", help="Input methods.json file")
    parser.add_argument("--output", "-o", help="Output JSON file (default: overwrite input)")
    parser.add_argument("--source-dir", help="Base directory for source files")
    
    args = parser.parse_args()
    
    output = args.output or args.methods_json
    
    enhance_methods_with_source_code(
        args.methods_json,
        output,
        args.source_dir
    )

