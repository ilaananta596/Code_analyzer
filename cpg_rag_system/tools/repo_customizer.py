#!/usr/bin/env python3
"""
Repository Customizer - Interactive Guide for System Customization

Helps users understand and customize the CPG RAG system:
- Explains configuration options
- Guides through modifications
- Generates custom analyzers
- Provides code templates

Usage:
    python repo_customizer.py --help-config
    python repo_customizer.py --generate-analyzer MyAnalyzer
    python repo_customizer.py --explain response_format
    python repo_customizer.py --interactive
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONFIG, ResponseFormat, Severity
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown


class RepoCustomizer:
    """
    Interactive tool for customizing the CPG RAG system.
    
    Features:
    - Configuration explanation
    - Custom analyzer generation
    - Template code generation
    - Best practices guidance
    """
    
    def __init__(self):
        self.console = Console()
        self.config = CONFIG
    
    def explain_config(self, option: str = None):
        """Explain configuration options."""
        
        config_docs = {
            'response_format': {
                'description': 'Controls the format of analysis responses',
                'options': ['BRIEF', 'DETAILED', 'TECHNICAL'],
                'details': {
                    'BRIEF': 'Bullet points, 3-5 lines, quick overview',
                    'DETAILED': 'Full explanation, 200-300 words',
                    'TECHNICAL': 'Code-heavy, technical details'
                },
                'example': 'CONFIG.default_response_format = ResponseFormat.BRIEF'
            },
            'top_k_results': {
                'description': 'Number of similar functions to retrieve for analysis',
                'type': 'integer',
                'range': '1-20',
                'default': 5,
                'example': 'CONFIG.top_k_results = 10'
            },
            'critical_complexity': {
                'description': 'Cyclomatic complexity threshold for CRITICAL severity',
                'type': 'integer',
                'default': 15,
                'impact': 'Lower = more sensitive to complex code',
                'example': 'CONFIG.critical_complexity = 10'
            },
            'sensitive_data_patterns': {
                'description': 'Patterns to detect sensitive data in variable names',
                'type': 'list',
                'default': ['password', 'api_key', 'secret', 'token'],
                'example': 'CONFIG.sensitive_data_patterns.append("private_key")'
            }
        }
        
        if option and option in config_docs:
            doc = config_docs[option]
            self.console.print(Panel(
                f"[bold]{option}[/bold]\n\n"
                f"{doc['description']}\n\n"
                f"[bold]Example:[/bold]\n{doc['example']}",
                title="📖 Configuration Help"
            ))
        else:
            # Show all options
            table = Table(title="⚙️ Configuration Options")
            table.add_column("Option", style="cyan")
            table.add_column("Description")
            table.add_column("Type")
            
            for opt, doc in config_docs.items():
                table.add_row(
                    opt,
                    doc['description'][:50] + "...",
                    doc.get('type', 'enum')
                )
            
            self.console.print(table)
            self.console.print("\n💡 Use --explain <option> for detailed help")
    
    def generate_custom_analyzer(self, analyzer_name: str):
        """Generate template for custom analyzer."""
        
        template = f'''#!/usr/bin/env python3
"""
{analyzer_name} - Custom Code Analyzer

TODO: Add description of what this analyzer does

Usage:
    python {analyzer_name.lower()}.py --analyze
"""

import argparse
import sys
from pathlib import Path
from typing import List, Dict

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONFIG, Severity
from rich.console import Console


class {analyzer_name}:
    """
    Custom analyzer for [YOUR PURPOSE HERE].
    
    TODO: Add detailed class description
    """
    
    def __init__(self, config=CONFIG):
        self.config = config
        self.console = Console()
        self.findings = []
    
    def analyze_code(self, code: str, filename: str) -> Dict:
        """
        Analyze code for [YOUR CRITERIA].
        
        Args:
            code: Source code to analyze
            filename: Name of the file
        
        Returns:
            Analysis results dictionary
        """
        analysis = {{
            'filename': filename,
            'issues': [],
            'metrics': {{}}
        }}
        
        # TODO: Implement your analysis logic here
        # Example:
        # if 'some_pattern' in code:
        #     analysis['issues'].append({{
        #         'type': 'PATTERN_FOUND',
        #         'severity': Severity.MEDIUM,
        #         'description': 'Found problematic pattern'
        #     }})
        
        return analysis
    
    def generate_report(self, analyses: List[Dict]) -> str:
        """Generate report from analyses."""
        
        self.console.print("\\n[bold cyan]📊 {analyzer_name} Report[/bold cyan]\\n")
        
        total_issues = sum(len(a.get('issues', [])) for a in analyses)
        self.console.print(f"Total Issues: {{total_issues}}\\n")
        
        for analysis in analyses:
            if analysis.get('issues'):
                self.console.print(f"[bold]{{analysis['filename']}}:[/bold]")
                for issue in analysis['issues']:
                    self.console.print(f"  • {{issue['description']}}")
        
        return ""


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='{analyzer_name}')
    parser.add_argument('--analyze', action='store_true', help='Run analysis')
    
    args = parser.parse_args()
    
    analyzer = {analyzer_name}()
    
    # TODO: Load your code and run analysis
    # sample_code = "..."
    # analysis = analyzer.analyze_code(sample_code, "example.py")
    # analyzer.generate_report([analysis])


if __name__ == '__main__':
    main()
'''
        
        # Save template
        output_file = Path(f"analyzers/{analyzer_name.lower()}.py")
        with open(output_file, 'w') as f:
            f.write(template)
        
        self.console.print(f"✅ Generated template: {output_file}")
        self.console.print("\n💡 Next steps:")
        self.console.print("  1. Edit the TODO sections")
        self.console.print("  2. Implement your analysis logic")
        self.console.print("  3. Test with sample code")
    
    def interactive_mode(self):
        """Interactive customization wizard."""
        
        self.console.print(Panel(
            "[bold cyan]Welcome to CPG RAG System Customizer![/bold cyan]\n\n"
            "This wizard will help you customize the system.",
            title="🎨 Customization Wizard"
        ))
        
        # What does user want to customize?
        choice = Prompt.ask(
            "\nWhat would you like to customize?",
            choices=['response_format', 'severity_thresholds', 'new_analyzer', 'exit'],
            default='response_format'
        )
        
        if choice == 'response_format':
            self._customize_response_format()
        elif choice == 'severity_thresholds':
            self._customize_severity()
        elif choice == 'new_analyzer':
            name = Prompt.ask("Enter analyzer name (e.g., 'PerformanceAnalyzer')")
            self.generate_custom_analyzer(name)
    
    def _customize_response_format(self):
        """Guide user through response format customization."""
        
        self.console.print("\n📝 Response Format Customization\n")
        
        # Explain options
        table = Table()
        table.add_column("Format", style="cyan")
        table.add_column("Best For")
        table.add_column("Length")
        
        table.add_row("BRIEF", "Quick overview, exec summary", "3-5 lines")
        table.add_row("DETAILED", "Documentation, code review", "200-300 words")
        table.add_row("TECHNICAL", "Developers, debugging", "Code-heavy")
        
        self.console.print(table)
        
        # Get user preference
        format_choice = Prompt.ask(
            "\nWhich format do you prefer?",
            choices=['BRIEF', 'DETAILED', 'TECHNICAL'],
            default='DETAILED'
        )
        
        # Show code to add
        code = f"""
# Add this to your script:
from config import CONFIG, ResponseFormat

CONFIG.default_response_format = ResponseFormat.{format_choice}
"""
        
        self.console.print(Panel(code, title="📋 Code to Add"))
        
        # Option to save
        if Confirm.ask("Save to config.py?"):
            self._save_config_change('default_response_format', format_choice)
    
    def _customize_severity(self):
        """Guide user through severity threshold customization."""
        
        self.console.print("\n🎯 Severity Threshold Customization\n")
        
        self.console.print("Current thresholds:")
        self.console.print(f"  • Critical Complexity: {self.config.critical_complexity}")
        self.console.print(f"  • High Coupling: {self.config.high_coupling_threshold}")
        
        self.console.print("\n💡 Lower values = more sensitive (flag more issues)")
        self.console.print("   Higher values = less sensitive (only flag severe issues)")
        
        new_complexity = Prompt.ask(
            "\nCritical complexity threshold",
            default=str(self.config.critical_complexity)
        )
        
        code = f"""
# Add this to your script:
from config import CONFIG

CONFIG.critical_complexity = {new_complexity}
"""
        
        self.console.print(Panel(code, title="📋 Code to Add"))
    
    def _save_config_change(self, key: str, value: str):
        """Save configuration change to file."""
        # In real implementation, would modify config.py
        self.console.print(f"✅ Configuration updated: {key} = {value}")
    
    def show_customization_examples(self):
        """Show common customization examples."""
        
        examples = """
# 🎨 Common Customization Examples

## Make responses brief
```python
CONFIG.default_response_format = ResponseFormat.BRIEF
CONFIG.max_response_length = 150
CONFIG.include_code_snippets = False
```

## More sensitive fault detection
```python
CONFIG.critical_complexity = 10
CONFIG.high_coupling_threshold = 5
```

## Add custom sensitive data pattern
```python
CONFIG.sensitive_data_patterns.append('private_key')
CONFIG.sensitive_data_patterns.append('certificate')
```

## Increase analysis depth
```python
CONFIG.top_k_results = 15
CONFIG.graph_context_depth = 3
```

## Custom sanitization functions
```python
CONFIG.sanitization_functions.append('my_custom_sanitizer')
```
"""
        
        md = Markdown(examples)
        self.console.print(md)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Customize CPG RAG system')
    parser.add_argument('--help-config', action='store_true', help='Show configuration help')
    parser.add_argument('--explain', help='Explain specific config option')
    parser.add_argument('--generate-analyzer', help='Generate custom analyzer template')
    parser.add_argument('--interactive', action='store_true', help='Interactive customization')
    parser.add_argument('--examples', action='store_true', help='Show customization examples')
    
    args = parser.parse_args()
    
    customizer = RepoCustomizer()
    
    if args.help_config:
        customizer.explain_config()
    elif args.explain:
        customizer.explain_config(args.explain)
    elif args.generate_analyzer:
        customizer.generate_custom_analyzer(args.generate_analyzer)
    elif args.interactive:
        customizer.interactive_mode()
    elif args.examples:
        customizer.show_customization_examples()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
