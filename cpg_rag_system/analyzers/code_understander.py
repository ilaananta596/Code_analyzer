#!/usr/bin/env python3
"""
Code Understander - Generate Comprehensive Codebase Descriptions

Provides high-level understanding of codebases through:
- Overall architecture description
- Main components and modules
- Entry points and execution flow
- Key design patterns
- Technology stack identification

Usage:
    python code_understander.py --overview
    python code_understander.py --architecture
    python code_understander.py --entry-points
    python code_understander.py --export description.md
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONFIG
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel


class CodeUnderstander:
    """
    Generates comprehensive understanding of codebase.
    
    Features:
    - Architecture overview
    - Component identification
    - Entry point detection
    - Pattern recognition
    """
    
    def __init__(self, config=CONFIG):
        self.config = config
        self.console = Console()
    
    def analyze_codebase_structure(self, methods: List[Dict], source_files: Dict) -> Dict:
        """
        Analyze overall codebase structure.
        
        Returns:
            Dictionary with structure analysis
        """
        analysis = {
            'total_files': len(source_files),
            'total_methods': len(methods),
            'files_by_type': self._categorize_files(source_files),
            'methods_by_file': self._group_methods_by_file(methods),
            'main_modules': self._identify_main_modules(methods, source_files)
        }
        
        return analysis
    
    def _categorize_files(self, source_files: Dict) -> Dict:
        """Categorize files by type/purpose."""
        categories = {
            'models': [],
            'utils': [],
            'tests': [],
            'config': [],
            'main': [],
            'other': []
        }
        
        for filepath in source_files.keys():
            filename = filepath.lower()
            
            if 'model' in filename or 'network' in filename:
                categories['models'].append(filepath)
            elif 'util' in filename or 'helper' in filename:
                categories['utils'].append(filepath)
            elif 'test' in filename:
                categories['tests'].append(filepath)
            elif 'config' in filename or 'setting' in filename:
                categories['config'].append(filepath)
            elif 'main' in filename or '__init__' in filename:
                categories['main'].append(filepath)
            else:
                categories['other'].append(filepath)
        
        return {k: v for k, v in categories.items() if v}
    
    def _group_methods_by_file(self, methods: List[Dict]) -> Dict:
        """Group methods by their source file."""
        by_file = {}
        for method in methods:
            filename = method.get('filename', 'unknown')
            # Skip empty or placeholder filenames
            if not filename or filename.strip() in ['', '<empty>', 'unknown']:
                continue
            if filename not in by_file:
                by_file[filename] = []
            by_file[filename].append(method['name'])
        
        return by_file
    
    def _identify_main_modules(self, methods: List[Dict], source_files: Dict) -> List[Dict]:
        """Identify main modules/components."""
        # Count methods per file, filtering out empty filenames
        methods_per_file = Counter(
            m.get('filename', '') for m in methods 
            if m.get('filename') and m.get('filename', '').strip() not in ['', '<empty>', 'unknown']
        )
        
        # Get top files by method count (increase to show more files)
        main_modules = []
        for filename, count in methods_per_file.most_common(20):
            if filename and filename.strip() not in ['', '<empty>', 'unknown']:
                main_modules.append({
                    'file': filename,
                    'method_count': count,
                    'lines': len(source_files.get(filename, '').split('\n'))
                })
        
        return main_modules
    
    def find_entry_points(self, methods: List[Dict]) -> List[Dict]:
        """Find likely entry points (main functions, __init__, etc.)."""
        entry_points = []
        
        for method in methods:
            name = method.get('name', '')
            filename = method.get('filename', '')
            
            # Skip methods with empty filenames (operator methods, built-ins)
            if not filename or filename.strip() in ['', '<empty>', 'unknown']:
                continue
            
            # Check for main function
            if name in ['main', '__main__', 'run', 'execute', 'start']:
                entry_points.append({
                    'type': 'main_function',
                    'name': name,
                    'file': filename,
                    'line': method.get('lineNumber')
                })
            
            # Check for __init__ (but only if it's a real file, not operator)
            elif name == '__init__' and filename and filename.strip() not in ['', '<empty>']:
                entry_points.append({
                    'type': 'initializer',
                    'name': name,
                    'file': filename,
                    'line': method.get('lineNumber')
                })
            
            # Check if it's called by many others (central function)
            elif len(method.get('called_by', [])) > 10:
                entry_points.append({
                    'type': 'central_function',
                    'name': name,
                    'file': method.get('filename'),
                    'callers': len(method.get('called_by', []))
                })
        
        return entry_points
    
    def identify_design_patterns(self, methods: List[Dict]) -> List[str]:
        """Identify common design patterns used."""
        patterns = set()
        
        method_names = [m.get('name', '') for m in methods]
        
        # Check for factory pattern
        if any('factory' in name.lower() or 'create' in name.lower() for name in method_names):
            patterns.add('Factory Pattern')
        
        # Check for singleton
        if any('instance' in name.lower() or 'singleton' in name.lower() for name in method_names):
            patterns.add('Singleton Pattern')
        
        # Check for builder
        if any('builder' in name.lower() or 'build' in name.lower() for name in method_names):
            patterns.add('Builder Pattern')
        
        # Check for observer
        if any('notify' in name.lower() or 'observe' in name.lower() for name in method_names):
            patterns.add('Observer Pattern')
        
        # Check for strategy
        if any('strategy' in name.lower() for name in method_names):
            patterns.add('Strategy Pattern')
        
        return list(patterns)
    
    def generate_overview(self, structure: Dict, entry_points: List[Dict], patterns: List[str]) -> str:
        """Generate comprehensive overview."""
        md = "# 📚 Codebase Overview\n\n"
        
        # Statistics
        md += "## 📊 Statistics\n\n"
        md += f"- **Total Files:** {structure['total_files']}\n"
        md += f"- **Total Methods:** {structure['total_methods']}\n"
        md += f"- **Entry Points:** {len(entry_points)}\n\n"
        
        # File Categories
        md += "## 📁 File Organization\n\n"
        for category, files in structure['files_by_type'].items():
            md += f"### {category.title()}\n"
            for f in files[:5]:  # Top 5
                md += f"- {f}\n"
            if len(files) > 5:
                md += f"- ... and {len(files) - 5} more\n"
            md += "\n"
        
        # Main Modules - show top 15 to include training files
        md += "## 🎯 Main Modules\n\n"
        for module in structure['main_modules'][:15]:
            file_name = module['file']
            # Highlight training files
            if 'train' in file_name.lower():
                md += f"### 🚂 {file_name} (Training File)\n"
            else:
                md += f"### {file_name}\n"
            md += f"- **Methods:** {module['method_count']}\n"
            md += f"- **Lines:** {module['lines']}\n\n"
        
        # Entry Points - show all entry points
        md += "## 🚀 Entry Points\n\n"
        for ep in entry_points:
            md += f"- **{ep['name']}** ({ep['type']})\n"
            md += f"  - File: {ep.get('file', 'N/A')}\n"
            if ep.get('line'):
                md += f"  - Line: {ep['line']}\n"
            if 'callers' in ep:
                md += f"  - Called by: {ep['callers']} functions\n"
            md += "\n"
        
        # Design Patterns
        if patterns:
            md += "## 🎨 Design Patterns\n\n"
            for pattern in patterns:
                md += f"- {pattern}\n"
            md += "\n"
        
        return md
    
    def generate_architecture_description(self, structure: Dict) -> str:
        """Generate detailed architecture description."""
        md = "# 🏗️ Architecture Description\n\n"
        
        # Overview
        md += "## Overview\n\n"
        md += f"The codebase consists of {structure['total_files']} files with {structure['total_methods']} methods.\n\n"
        
        # Layer analysis
        md += "## Architectural Layers\n\n"
        
        if 'models' in structure['files_by_type']:
            md += "### Model Layer\n"
            md += f"Contains {len(structure['files_by_type']['models'])} files implementing core models and data structures.\n\n"
        
        if 'utils' in structure['files_by_type']:
            md += "### Utility Layer\n"
            md += f"Contains {len(structure['files_by_type']['utils'])} helper/utility files.\n\n"
        
        if 'tests' in structure['files_by_type']:
            md += "### Testing Layer\n"
            md += f"Contains {len(structure['files_by_type']['tests'])} test files.\n\n"
        
        return md
    
    def generate_console_output(self, structure: Dict, entry_points: List[Dict], patterns: List[str]):
        """Generate rich console output."""
        self.console.print("\n[bold cyan]" + "=" * 70)
        self.console.print("[bold cyan]📚 CODEBASE UNDERSTANDING")
        self.console.print("[bold cyan]" + "=" * 70 + "\n")
        
        # Statistics
        stats = f"""[bold]Files:[/bold] {structure['total_files']}
[bold]Methods:[/bold] {structure['total_methods']}
[bold]Entry Points:[/bold] {len(entry_points)}
[bold]Design Patterns:[/bold] {len(patterns)}"""
        
        self.console.print(Panel(stats, title="📊 Quick Stats"))
        
        # Main modules - show top 15 to include training files
        self.console.print("\n[bold]🎯 Main Modules:[/bold]")
        for i, module in enumerate(structure['main_modules'][:15], 1):
            file_name = module['file']
            # Highlight training files
            if 'train' in file_name.lower():
                self.console.print(f"  {i}. [bold yellow]{file_name}[/bold yellow] ({module['method_count']} methods)")
            else:
                self.console.print(f"  {i}. {file_name} ({module['method_count']} methods)")
        
        # Entry points - show all entry points
        self.console.print("\n[bold]🚀 Entry Points:[/bold]")
        for ep in entry_points:
            file_info = ep.get('file', 'N/A')
            line_info = f":{ep.get('line', '?')}" if ep.get('line') else ""
            callers_info = f" (called by {ep.get('callers', 0)} functions)" if ep.get('callers') else ""
            self.console.print(f"  • {ep['name']} ({ep['type']}) - {file_info}{line_info}{callers_info}")
        
        # Patterns
        if patterns:
            self.console.print("\n[bold]🎨 Design Patterns:[/bold]")
            for pattern in patterns:
                self.console.print(f"  • {pattern}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Understand codebase structure')
    parser.add_argument('--overview', action='store_true', help='Generate overview')
    parser.add_argument('--architecture', action='store_true', help='Architecture description')
    parser.add_argument('--entry-points', action='store_true', help='Find entry points')
    parser.add_argument('--export', help='Export to file')
    
    args = parser.parse_args()
    
    understander = CodeUnderstander()
    
    # Example: analyze sample data
    sample_methods = [
        {'name': 'main', 'filename': 'main.py', 'lineNumber': 10, 'called_by': []},
        {'name': '__init__', 'filename': 'model.py', 'lineNumber': 15, 'called_by': ['main']},
        {'name': 'forward', 'filename': 'model.py', 'lineNumber': 30, 'called_by': ['train', 'inference', 'test']},
    ]
    
    sample_files = {
        'main.py': '# Main entry point\n',
        'model.py': '# Model definition\n',
        'utils.py': '# Utilities\n'
    }
    
    structure = understander.analyze_codebase_structure(sample_methods, sample_files)
    entry_points = understander.find_entry_points(sample_methods)
    patterns = understander.identify_design_patterns(sample_methods)
    
    if args.export:
        if args.architecture:
            content = understander.generate_architecture_description(structure)
        else:
            content = understander.generate_overview(structure, entry_points, patterns)
        
        with open(args.export, 'w') as f:
            f.write(content)
        print(f"✅ Exported to {args.export}")
    else:
        understander.generate_console_output(structure, entry_points, patterns)


if __name__ == '__main__':
    main()
