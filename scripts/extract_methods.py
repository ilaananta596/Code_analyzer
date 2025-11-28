#!/usr/bin/env python3
"""
Extract method representations from CPG using Joern.
This script queries the CPG to get method information and builds text representations.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# Source code extraction will be imported dynamically when needed


def run_joern_query(cpg_path: str, scala_script: str) -> Dict[str, Any]:
    """
    Run a Joern Scala script and parse JSON output.
    
    Args:
        cpg_path: Path to CPG file
        scala_script: Path to Scala script file
    
    Returns:
        Parsed JSON result or empty dict on error
    """
    try:
        result = subprocess.run(
            [
                "joern",
                "--script", scala_script,
                "--param", f"cpgFile={cpg_path}"
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=300
        )
        
        # Try to extract JSON from output
        output = result.stdout
        # Look for JSON object in output
        start_idx = output.find('{')
        end_idx = output.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = output[start_idx:end_idx]
            return json.loads(json_str)
        else:
            print(f"Warning: No JSON found in Joern output")
            print(f"Output: {output[:500]}")
            return {}
            
    except subprocess.CalledProcessError as e:
        print(f"Error running Joern script:")
        print(f"  Return code: {e.returncode}")
        if e.stderr:
            print(f"  stderr: {e.stderr[:500]}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from Joern output: {e}")
        return {}
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {}


def extract_methods(cpg_path: str, output_json: str, source_dir: Optional[str] = None, enhance_with_source: bool = True) -> bool:
    """
    Extract all methods from CPG and save to JSON.
    
    Args:
        cpg_path: Path to CPG file
        output_json: Path to output JSON file
    
    Returns:
        True if successful
    """
    cpg_file = Path(cpg_path)
    if not cpg_file.exists():
        print(f"Error: CPG file '{cpg_path}' does not exist")
        return False
    
    # Create Scala script for extracting methods
    script_dir = Path(__file__).parent.parent / "joern_scripts"
    script_dir.mkdir(parents=True, exist_ok=True)
    
    extract_script = script_dir / "extract_methods.sc"
    
    # Use the dedicated extract_methods.sc script
    extract_script = script_dir / "extract_methods.sc"
    if not extract_script.exists():
        print(f"Error: Extraction script not found at '{extract_script}'")
        return False
    
    print(f"Extracting methods from CPG '{cpg_path}'...")
    result = run_joern_query(cpg_path, str(extract_script))
    
    if "methods" in result:
        methods = result["methods"]
        print(f"✓ Extracted {len(methods)} methods")
        
        # Save to JSON
        output_path = Path(output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"✓ Saved to '{output_json}'")
        
        # Enhance with source code if source directory is available
        if enhance_with_source and source_dir:
            print(f"\nEnhancing with source code from '{source_dir}'...")
            try:
                # Import from the same directory
                import importlib.util
                extract_source_path = Path(__file__).parent / "extract_source_code.py"
                if extract_source_path.exists():
                    spec = importlib.util.spec_from_file_location("extract_source_code", extract_source_path)
                    extract_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(extract_module)
                    
                    enhanced_output = str(output_path).replace('.json', '_enhanced.json')
                    if extract_module.enhance_methods_with_source_code(str(output_path), enhanced_output, source_dir):
                        print(f"✓ Enhanced methods saved to '{enhanced_output}'")
                        # Replace original with enhanced
                        import shutil
                        shutil.move(enhanced_output, output_path)
                        print(f"✓ Replaced original with enhanced version")
                else:
                    print(f"Warning: extract_source_code.py not found, skipping enhancement")
            except Exception as e:
                print(f"Warning: Could not enhance with source code: {e}")
                print("  Continuing with AST code representation")
        
        return True
    else:
        print("Error: No methods found in Joern output")
        return False


def build_method_text_representation(method: Dict[str, Any]) -> str:
    """
    Build a text representation of a method for embedding.
    
    Format: signature + file path + code + callees
    """
    parts = []
    
    # Signature
    if method.get("signature"):
        parts.append(f"Signature: {method['signature']}")
    
    # File path
    if method.get("filePath"):
        parts.append(f"File: {method['filePath']}")
    
    # Line number
    if method.get("lineNumber"):
        parts.append(f"Line: {method['lineNumber']}")
    
    # Code (truncated if too long)
    if method.get("code"):
        code = method["code"]
        if len(code) > 1000:
            code = code[:1000] + "..."
        parts.append(f"Code:\n{code}")
    
    # Callees
    if method.get("callees"):
        callees = method["callees"]
        if callees:
            parts.append(f"Calls: {', '.join(callees[:10])}")  # Limit to 10 callees
    
    return "\n".join(parts)


def main():
    parser = argparse.ArgumentParser(
        description="Extract method representations from CPG"
    )
    parser.add_argument(
        "cpg_path",
        help="Path to CPG file (.cpg.bin)"
    )
    parser.add_argument(
        "--output", "-o",
        default="methods.json",
        help="Output JSON file path (default: methods.json)"
    )
    parser.add_argument(
        "--source-dir",
        help="Source directory to extract actual code from (auto-detected from .source_info.json if available)"
    )
    parser.add_argument(
        "--no-enhance",
        action="store_true",
        help="Skip enhancing with source code even if source directory is available"
    )
    
    args = parser.parse_args()
    
    # Try to auto-detect source directory from .source_info.json
    source_dir = args.source_dir
    if not source_dir:
        source_info_path = Path(args.cpg_path).with_suffix('.source_info.json')
        if source_info_path.exists():
            try:
                with open(source_info_path, 'r') as f:
                    source_info = json.load(f)
                source_dir = source_info.get("source_dir")
                if source_dir and Path(source_dir).exists():
                    print(f"✓ Auto-detected source directory: {source_dir}")
            except Exception as e:
                print(f"Warning: Could not read source info: {e}")
    
    success = extract_methods(
        args.cpg_path, 
        args.output, 
        source_dir=source_dir,
        enhance_with_source=not args.no_enhance
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

