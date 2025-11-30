#!/usr/bin/env python3
"""
Sensitive Data Tracker - Data Flow Analysis for Privacy & Security

Tracks the flow of sensitive data through the application to ensure:
- Sensitive data is sanitized before logging
- Credentials are not exposed in external exports
- PII is properly handled
- Data flow paths are documented

Usage:
    python sensitive_data_tracker.py --track password
    python sensitive_data_tracker.py --all
    python sensitive_data_tracker.py --export data_flow.html
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Set, Tuple
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONFIG
from rich.console import Console
from rich.tree import Tree
from rich.panel import Panel


class SensitiveDataTracker:
    """
    Tracks flow of sensitive data through application.
    
    Features:
    - Identifies sensitive data types (passwords, API keys, PII)
    - Traces data flow through function calls
    - Detects unsanitized logging
    - Finds external exports of sensitive data
    """
    
    def __init__(self, config=CONFIG):
        self.config = config
        self.console = Console()
        
        # Sensitive data patterns
        self.sensitive_patterns = config.sensitive_data_patterns
        
        # Sanitization functions
        self.sanitization_functions = config.sanitization_functions
        
        # Track findings
        self.data_flows = []
        self.violations = []
    
    def identify_sensitive_variables(self, code: str) -> List[Dict]:
        """
        Identify variables that may contain sensitive data.
        
        Returns:
            List of sensitive variables with their types
        """
        sensitive_vars = []
        
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            # Look for variable assignments
            if '=' in line and not line.strip().startswith('#'):
                parts = line.split('=')
                if len(parts) >= 2:
                    var_name = parts[0].strip()
                    
                    # Check if variable name suggests sensitive data
                    for pattern in self.sensitive_patterns:
                        if pattern in var_name.lower():
                            sensitive_vars.append({
                                'variable': var_name,
                                'type': pattern,
                                'line': i,
                                'context': line.strip()
                            })
        
        return sensitive_vars
    
    def trace_data_flow(
        self, 
        variable: str, 
        function_code: str,
        graph_context: Dict
    ) -> List[Dict]:
        """
        Trace how a sensitive variable flows through code.
        
        Args:
            variable: Variable to track
            function_code: Code of the function
            graph_context: Graph context with calls/callers
        
        Returns:
            List of data flow steps
        """
        flow_steps = []
        
        lines = function_code.split('\n')
        
        for i, line in enumerate(lines, 1):
            line_stripped = line.strip()
            
            # Skip comments and empty lines
            if line_stripped.startswith('#') or not line_stripped:
                continue
            
            # Check if variable is used
            if variable in line:
                flow_step = {
                    'line': i,
                    'code': line_stripped,
                    'operations': []
                }
                
                # Check for logging
                if any(log in line_stripped for log in ['log.', 'logger.', 'print(']):
                    flow_step['operations'].append('LOGGING')
                    
                    # Check if sanitized
                    if not any(san in line_stripped for san in self.sanitization_functions):
                        flow_step['risk'] = 'UNSANITIZED_LOGGING'
                
                # Check for external export
                if any(exp in line_stripped for exp in ['write', 'dump', 'export', 'send', 'post']):
                    flow_step['operations'].append('EXTERNAL_EXPORT')
                    
                    if not any(san in line_stripped for san in self.sanitization_functions):
                        flow_step['risk'] = 'UNSANITIZED_EXPORT'
                
                # Check for assignment to another variable
                if '=' in line and variable in line.split('=')[1]:
                    new_var = line.split('=')[0].strip()
                    flow_step['operations'].append(f'ASSIGNED_TO:{new_var}')
                
                # Check for function calls
                if '(' in line and variable in line:
                    flow_step['operations'].append('FUNCTION_CALL')
                
                # Check for sanitization
                if any(san in line_stripped for san in self.sanitization_functions):
                    flow_step['operations'].append('SANITIZED')
                
                flow_steps.append(flow_step)
        
        return flow_steps
    
    def detect_violations(self, data_flows: List[Dict]) -> List[Dict]:
        """
        Detect security/privacy violations in data flows.
        
        Returns:
            List of violations with severity
        """
        violations = []
        
        for flow in data_flows:
            variable = flow['variable']
            var_type = flow['type']
            
            for step in flow.get('flow_steps', []):
                risk = step.get('risk')
                
                if risk == 'UNSANITIZED_LOGGING':
                    violations.append({
                        'type': 'UNSANITIZED_LOGGING',
                        'severity': 'HIGH',
                        'variable': variable,
                        'data_type': var_type,
                        'line': step['line'],
                        'code': step['code'],
                        'description': f'Sensitive data "{variable}" ({var_type}) logged without sanitization'
                    })
                
                elif risk == 'UNSANITIZED_EXPORT':
                    violations.append({
                        'type': 'UNSANITIZED_EXPORT',
                        'severity': 'CRITICAL',
                        'variable': variable,
                        'data_type': var_type,
                        'line': step['line'],
                        'code': step['code'],
                        'description': f'Sensitive data "{variable}" ({var_type}) exported without sanitization'
                    })
        
        return violations
    
    def analyze_function(
        self, 
        function_name: str,
        function_code: str,
        filename: str,
        graph_context: Dict = None
    ) -> Dict:
        """
        Analyze a function for sensitive data flows.
        
        Returns:
            Analysis results with flows and violations
        """
        # Identify sensitive variables
        sensitive_vars = self.identify_sensitive_variables(function_code)
        
        if not sensitive_vars:
            return {
                'function': function_name,
                'filename': filename,
                'has_sensitive_data': False
            }
        
        # Trace each sensitive variable
        flows = []
        for var_info in sensitive_vars:
            flow_steps = self.trace_data_flow(
                var_info['variable'],
                function_code,
                graph_context or {}
            )
            
            flows.append({
                'variable': var_info['variable'],
                'type': var_info['type'],
                'declared_line': var_info['line'],
                'flow_steps': flow_steps
            })
        
        # Detect violations
        violations = self.detect_violations(flows)
        
        return {
            'function': function_name,
            'filename': filename,
            'has_sensitive_data': True,
            'sensitive_variables': len(sensitive_vars),
            'data_flows': flows,
            'violations': violations,
            'risk_level': self._calculate_risk_level(violations)
        }
    
    def _calculate_risk_level(self, violations: List[Dict]) -> str:
        """Calculate overall risk level."""
        if not violations:
            return 'SAFE'
        
        severities = [v['severity'] for v in violations]
        
        if 'CRITICAL' in severities:
            return 'CRITICAL'
        elif 'HIGH' in severities:
            return 'HIGH'
        else:
            return 'MEDIUM'
    
    def generate_data_flow_graph(self, analysis: Dict) -> str:
        """Generate visual data flow graph."""
        tree = Tree(f"[bold cyan]📊 {analysis['function']}")
        
        if not analysis.get('has_sensitive_data'):
            tree.add("[green]✅ No sensitive data detected")
            return tree
        
        for flow in analysis.get('data_flows', []):
            var_branch = tree.add(
                f"[yellow]🔐 {flow['variable']} ({flow['type']})"
            )
            
            for step in flow['flow_steps']:
                operations = ', '.join(step['operations'])
                risk = step.get('risk', '')
                
                if risk:
                    icon = "🔴"
                    color = "red"
                else:
                    icon = "✅"
                    color = "green"
                
                var_branch.add(
                    f"[{color}]{icon} Line {step['line']}: {operations}"
                )
        
        self.console.print(tree)
        return ""
    
    def generate_report(
        self, 
        analyses: List[Dict], 
        format: str = 'console'
    ) -> str:
        """Generate comprehensive report."""
        
        if format == 'console':
            return self._generate_console_report(analyses)
        elif format == 'json':
            return self._generate_json_report(analyses)
        elif format == 'html':
            return self._generate_html_report(analyses)
        else:
            return self._generate_markdown_report(analyses)
    
    def _generate_console_report(self, analyses: List[Dict]) -> str:
        """Generate rich console report."""
        self.console.print("\n[bold cyan]" + "=" * 70)
        self.console.print("[bold cyan]🔐 SENSITIVE DATA FLOW ANALYSIS")
        self.console.print("[bold cyan]" + "=" * 70 + "\n")
        
        # Summary
        total_functions = len(analyses)
        functions_with_sensitive = sum(1 for a in analyses if a.get('has_sensitive_data'))
        total_violations = sum(len(a.get('violations', [])) for a in analyses)
        
        self.console.print(Panel(
            f"[bold]Functions Analyzed:[/bold] {total_functions}\n"
            f"[bold]With Sensitive Data:[/bold] {functions_with_sensitive}\n"
            f"[bold]Violations Found:[/bold] {total_violations}",
            title="📊 Summary"
        ))
        
        # Violations by severity
        violations_by_severity = defaultdict(list)
        for analysis in analyses:
            for violation in analysis.get('violations', []):
                violations_by_severity[violation['severity']].append({
                    'function': analysis['function'],
                    'filename': analysis['filename'],
                    **violation
                })
        
        for severity in ['CRITICAL', 'HIGH', 'MEDIUM']:
            violations = violations_by_severity.get(severity, [])
            if not violations:
                continue
            
            self.console.print(f"\n[bold]{'🔴' if severity == 'CRITICAL' else '🟠'} {severity}[/bold] ({len(violations)} violations)")
            self.console.print("-" * 70)
            
            for v in violations:
                self.console.print(f"\n📍 {v['filename']} - {v['function']}() [line {v['line']}]")
                self.console.print(f"   {v['description']}")
                self.console.print(f"   Code: [dim]{v['code']}[/dim]")
        
        return ""
    
    def _generate_json_report(self, analyses: List[Dict]) -> str:
        """Generate JSON report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_functions': len(analyses),
                'functions_with_sensitive_data': sum(1 for a in analyses if a.get('has_sensitive_data')),
                'total_violations': sum(len(a.get('violations', [])) for a in analyses)
            },
            'analyses': analyses
        }
        return json.dumps(report, indent=2, default=str)
    
    def _generate_markdown_report(self, analyses: List[Dict]) -> str:
        """Generate Markdown report."""
        md = "# 🔐 Sensitive Data Flow Analysis\n\n"
        md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Summary
        total = len(analyses)
        with_sensitive = sum(1 for a in analyses if a.get('has_sensitive_data'))
        violations = sum(len(a.get('violations', [])) for a in analyses)
        
        md += "## Summary\n\n"
        md += f"- **Functions Analyzed:** {total}\n"
        md += f"- **With Sensitive Data:** {with_sensitive}\n"
        md += f"- **Violations Found:** {violations}\n\n"
        
        # Violations
        md += "## Violations\n\n"
        for analysis in analyses:
            if analysis.get('violations'):
                md += f"### {analysis['function']} ({analysis['filename']})\n\n"
                for v in analysis['violations']:
                    md += f"- **{v['severity']}** (Line {v['line']})\n"
                    md += f"  - {v['description']}\n"
                    md += f"  - Code: `{v['code']}`\n\n"
        
        return md
    
    def _generate_html_report(self, analyses: List[Dict]) -> str:
        """Generate HTML report."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Sensitive Data Flow Analysis</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .critical {{ color: #d32f2f; font-weight: bold; }}
        .high {{ color: #f57c00; font-weight: bold; }}
        .violation {{ margin: 20px 0; padding: 15px; border-left: 4px solid #ccc; background: #f5f5f5; }}
        code {{ background: #e0e0e0; padding: 2px 4px; }}
    </style>
</head>
<body>
    <h1>🔐 Sensitive Data Flow Analysis</h1>
    <p><em>Generated: {timestamp}</em></p>
"""
        
        for analysis in analyses:
            if analysis.get('violations'):
                html += f"<h2>{analysis['function']} ({analysis['filename']})</h2>"
                for v in analysis['violations']:
                    severity_class = v['severity'].lower()
                    html += f"""
    <div class="violation">
        <div class="{severity_class}">{v['severity']} - Line {v['line']}</div>
        <p>{v['description']}</p>
        <code>{v['code']}</code>
    </div>
"""
        
        html += "</body></html>"
        return html


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Track sensitive data flows')
    parser.add_argument('--track', help='Track specific data type (e.g., password)')
    parser.add_argument('--all', action='store_true', help='Track all sensitive data')
    parser.add_argument('--export', help='Export report to file')
    parser.add_argument('--format', choices=['console', 'json', 'markdown', 'html'],
                       default='console', help='Output format')
    
    args = parser.parse_args()
    
    tracker = SensitiveDataTracker()
    
    # Example analysis
    sample_code = """
def authenticate_user(username, password):
    # Sensitive: password variable
    api_key = get_api_key()
    
    # VIOLATION: Logging password without sanitization
    logger.info(f"Login attempt: {username}, {password}")
    
    # VIOLATION: Exporting api_key without sanitization
    data = {"user": username, "key": api_key}
    requests.post("https://analytics.example.com", json=data)
    
    # SAFE: Password hashed before storage
    hashed_password = hash(password)
    db.save(username, hashed_password)
    
    return True
"""
    
    analysis = tracker.analyze_function(
        'authenticate_user',
        sample_code,
        'auth.py'
    )
    
    analyses = [analysis]
    
    # Generate report
    report = tracker.generate_report(analyses, format=args.format)
    
    if args.export:
        with open(args.export, 'w') as f:
            f.write(report)
        print(f"✅ Report exported to {args.export}")
    elif args.format == 'console':
        # Already printed
        pass
    else:
        print(report)


if __name__ == '__main__':
    main()
