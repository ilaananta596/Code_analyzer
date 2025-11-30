#!/usr/bin/env python3
"""
CPG RAG System - Main Entry Point

Unified command-line interface for all analysis tools.

Usage:
    python main.py fault-detection --all
    python main.py sensitive-data --track password
    python main.py understand --overview
    python main.py customize --interactive
    python main.py analyze "Find security issues"
"""

import argparse
import sys
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from config import CONFIG
from rich.console import Console
from rich.panel import Panel


class CPGRAGSystem:
    """
    Main entry point for CPG RAG analysis system.
    
    Provides unified access to all analyzers and tools.
    """
    
    def __init__(self):
        self.console = Console()
        self.config = CONFIG
    
    def print_welcome(self):
        """Print welcome message."""
        welcome = """
[bold cyan] CPG RAG Analysis System[/bold cyan]

Professional code analysis powered by:
  • Code Property Graphs (CPG)
  • Vector embeddings (Ollama)
  • Graph database (Neo4j)
  • LLM-powered insights

[bold]Available Commands:[/bold]
  • fault-detection    - Find bugs and vulnerabilities
  • sensitive-data     - Track sensitive data flows
  • understand         - Generate codebase overview
  • customize          - Customize system behavior
  • analyze            - Interactive RAG queries
"""
        self.console.print(Panel(welcome, title="Welcome"))
    
    def run_fault_detection(self, args):
        """Run fault detection analysis."""
        from analyzers.fault_detector import FaultDetector
        
        detector = FaultDetector(self.config)
        
        self.console.print("\n Running Fault Detection...\n")
        
        # TODO: Load actual code from CPG
        # For now, show help
        self.console.print("This will analyze your codebase for:")
        self.console.print("  • Security vulnerabilities")
        self.console.print("  • Missing error handling")
        self.console.print("  • Resource leaks")
        self.console.print("  • Code quality issues")
        
        if args.export:
            self.console.print(f"\n Report will be exported to: {args.export}")
    
    def run_sensitive_data_tracking(self, args):
        """Run sensitive data flow tracking."""
        from analyzers.sensitive_data_tracker import SensitiveDataTracker
        
        tracker = SensitiveDataTracker(self.config)
        
        self.console.print("\n Running Sensitive Data Tracking...\n")
        
        if args.track:
            self.console.print(f"Tracking: {args.track}")
        else:
            self.console.print("Tracking all sensitive data patterns:")
            for pattern in self.config.sensitive_data_patterns:
                self.console.print(f"  • {pattern}")
    
    def run_understanding(self, args):
        """Run code understanding analysis."""
        from analyzers.code_understander import CodeUnderstander
        
        understander = CodeUnderstander(self.config)
        
        self.console.print("\n Analyzing Codebase Structure...\n")
        
        if args.overview:
            self.console.print("Generating overview...")
        elif args.architecture:
            self.console.print("Analyzing architecture...")
        elif args.entry_points:
            self.console.print("Finding entry points...")
    
    def run_customization(self, args):
        """Run customization tool."""
        from tools.repo_customizer import RepoCustomizer
        
        customizer = RepoCustomizer()
        
        if args.interactive:
            customizer.interactive_mode()
        elif args.examples:
            customizer.show_customization_examples()
        else:
            customizer.explain_config()
    
    def run_interactive_analysis(self, query: str):
        """Run interactive RAG analysis."""
        self.console.print(f"\n Analyzing: [cyan]{query}[/cyan]\n")
        
        # TODO: Integrate with actual RAG system
        self.console.print("This will use the RAG system to:")
        self.console.print("  1. Search vector stores for relevant code")
        self.console.print("  2. Use graph context for understanding")
        self.console.print("  3. Generate LLM-powered insights")
        
        self.console.print("\n[dim]RAG integration coming soon...[/dim]")


def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description='CPG RAG Analysis System',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Fault Detection
    fault_parser = subparsers.add_parser('fault-detection', help='Detect faults and bugs')
    fault_parser.add_argument('--all', action='store_true', help='Analyze all issues')
    fault_parser.add_argument('--security', action='store_true', help='Security issues only')
    fault_parser.add_argument('--export', help='Export report')
    
    # Sensitive Data
    sensitive_parser = subparsers.add_parser('sensitive-data', help='Track sensitive data')
    sensitive_parser.add_argument('--track', help='Track specific data type')
    sensitive_parser.add_argument('--all', action='store_true', help='Track all')
    sensitive_parser.add_argument('--export', help='Export report')
    
    # Understanding
    understand_parser = subparsers.add_parser('understand', help='Understand codebase')
    understand_parser.add_argument('--overview', action='store_true', help='Generate overview')
    understand_parser.add_argument('--architecture', action='store_true', help='Architecture')
    understand_parser.add_argument('--entry-points', action='store_true', help='Entry points')
    understand_parser.add_argument('--export', help='Export description')
    
    # Customization
    custom_parser = subparsers.add_parser('customize', help='Customize system')
    custom_parser.add_argument('--interactive', action='store_true', help='Interactive mode')
    custom_parser.add_argument('--examples', action='store_true', help='Show examples')
    
    # Interactive Analysis
    analyze_parser = subparsers.add_parser('analyze', help='Interactive RAG queries')
    analyze_parser.add_argument('query', help='Analysis query')
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    system = CPGRAGSystem()
    
    if not args.command:
        system.print_welcome()
        parser.print_help()
        return
    
    # Route to appropriate handler
    if args.command == 'fault-detection':
        system.run_fault_detection(args)
    
    elif args.command == 'sensitive-data':
        system.run_sensitive_data_tracking(args)
    
    elif args.command == 'understand':
        system.run_understanding(args)
    
    elif args.command == 'customize':
        system.run_customization(args)
    
    elif args.command == 'analyze':
        system.run_interactive_analysis(args.query)


if __name__ == '__main__':
    main()
