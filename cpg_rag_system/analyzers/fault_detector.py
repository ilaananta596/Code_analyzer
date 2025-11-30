#!/usr/bin/env python3
"""
Fault Detector - Comprehensive Bug and Vulnerability Detection

This script analyzes code for:
- Security vulnerabilities (SQL injection, XSS, unsafe operations)
- Missing error handling
- Resource leaks
- Null pointer risks
- Code complexity issues

Usage:
    python fault_detector.py --all                    # Analyze all issues
    python fault_detector.py --security               # Security issues only
    python fault_detector.py --severity CRITICAL      # Filter by severity
    python fault_detector.py --export report.html     # Export report
"""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import CONFIG, Severity
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


class FaultDetector:
    """
    Comprehensive fault detection for code analysis.
    
    Detects:
    - Security vulnerabilities
    - Missing error handling
    - Resource leaks
    - Code quality issues
    """
    
    def __init__(self, config=CONFIG):
        self.config = config
        self.console = Console()
        self.findings = []
    
    def analyze_code(self, code: str, filename: str, line_number: int) -> Dict:
        """
        Analyze code for faults.
        
        Returns:
            Dictionary with fault features and severity
        """
        features = {
            'filename': filename,
            'line_number': line_number,
            'has_null_checks': False,
            'has_exception_handling': False,
            'opens_resources': False,
            'closes_resources': False,
            'validates_inputs': False,
            'unsafe_operations': [],
            'security_issues': [],
            'complexity_score': 0,
            'issues': []
        }
        
        if not code:
            return features
        
        code_lower = code.lower()
        
        # NULL CHECKS
        null_patterns = ['is none', '== none', '!= none', 'if not']
        features['has_null_checks'] = any(p in code_lower for p in null_patterns)
        
        if not features['has_null_checks']:
            features['issues'].append({
                'type': 'MISSING_NULL_CHECK',
                'severity': Severity.MEDIUM,
                'description': 'No null/None checks detected'
            })
        
        # EXCEPTION HANDLING
        features['has_exception_handling'] = 'try:' in code or 'except' in code
        
        if not features['has_exception_handling']:
            features['issues'].append({
                'type': 'MISSING_EXCEPTION_HANDLING',
                'severity': Severity.HIGH,
                'description': 'No try/except blocks found'
            })
        
        # RESOURCE LEAKS
        open_patterns = ['open(', 'connect(', 'socket(', 'file(']
        close_patterns = ['.close()', 'with ']
        
        features['opens_resources'] = any(p in code_lower for p in open_patterns)
        features['closes_resources'] = any(p in code_lower for p in close_patterns)
        
        if features['opens_resources'] and not features['closes_resources']:
            features['issues'].append({
                'type': 'RESOURCE_LEAK',
                'severity': Severity.HIGH,
                'description': 'Opens resources but no .close() or context manager detected'
            })
        
        # INPUT VALIDATION
        validation_patterns = ['assert', 'isinstance(', 'raise', 'validate']
        features['validates_inputs'] = any(p in code_lower for p in validation_patterns)
        
        # UNSAFE OPERATIONS
        unsafe_ops = []
        security_issues = []
        
        if 'eval(' in code:
            unsafe_ops.append('eval')
            security_issues.append({
                'type': 'UNSAFE_EVAL',
                'severity': Severity.CRITICAL,
                'description': 'Uses eval() - Remote Code Execution risk'
            })
        
        if 'exec(' in code:
            unsafe_ops.append('exec')
            security_issues.append({
                'type': 'UNSAFE_EXEC',
                'severity': Severity.CRITICAL,
                'description': 'Uses exec() - Remote Code Execution risk'
            })
        
        if 'pickle.loads' in code:
            unsafe_ops.append('pickle')
            security_issues.append({
                'type': 'UNSAFE_PICKLE',
                'severity': Severity.HIGH,
                'description': 'Unsafe pickle deserialization'
            })
        
        if 'os.system' in code:
            unsafe_ops.append('os.system')
            security_issues.append({
                'type': 'COMMAND_INJECTION',
                'severity': Severity.CRITICAL,
                'description': 'Uses os.system() - Command injection risk'
            })
        
        # SQL INJECTION
        sql_patterns = ['execute(f"', 'query(f"', '.raw(', 'cursor.execute("%']
        if any(p in code for p in sql_patterns):
            security_issues.append({
                'type': 'SQL_INJECTION',
                'severity': Severity.CRITICAL,
                'description': 'Potential SQL injection - string formatting in query'
            })
        
        # XSS
        if 'render_template_string' in code or '.format(' in code and 'html' in code_lower:
            security_issues.append({
                'type': 'XSS',
                'severity': Severity.HIGH,
                'description': 'Potential XSS - unsanitized template rendering'
            })
        
        features['unsafe_operations'] = unsafe_ops
        features['security_issues'] = security_issues
        features['issues'].extend(security_issues)
        
        # COMPLEXITY
        branches = sum(code.count(kw) for kw in ['if ', 'elif ', 'for ', 'while ', 'try:', 'except'])
        features['complexity_score'] = branches * 2 + len(unsafe_ops) * 10
        
        if features['complexity_score'] > self.config.critical_complexity:
            features['issues'].append({
                'type': 'HIGH_COMPLEXITY',
                'severity': Severity.MEDIUM,
                'description': f'High cyclomatic complexity ({features["complexity_score"]})'
            })
        
        # CALCULATE OVERALL SEVERITY
        features['severity'] = self._calculate_severity(features)
        
        return features
    
    def _calculate_severity(self, features: Dict) -> Severity:
        """Calculate overall severity based on issues found."""
        score = 0
        
        # Critical issues
        if features['unsafe_operations']:
            score += 10
        
        if features['security_issues']:
            for issue in features['security_issues']:
                if issue['severity'] == Severity.CRITICAL:
                    score += 10
                elif issue['severity'] == Severity.HIGH:
                    score += 5
        
        # High severity
        if not features['has_exception_handling']:
            score += 5
        
        if features['opens_resources'] and not features['closes_resources']:
            score += 5
        
        # Medium severity
        if not features['has_null_checks']:
            score += 3
        
        if features['complexity_score'] > self.config.critical_complexity:
            score += 3
        
        # Determine severity
        if score >= 10:
            return Severity.CRITICAL
        elif score >= 7:
            return Severity.HIGH
        elif score >= 4:
            return Severity.MEDIUM
        elif score > 0:
            return Severity.LOW
        else:
            return Severity.INFO
    
    def generate_report(self, findings: List[Dict], format: str = 'console') -> str:
        """Generate formatted report of findings."""
        
        if format == 'console':
            return self._generate_console_report(findings)
        elif format == 'json':
            return self._generate_json_report(findings)
        elif format == 'html':
            return self._generate_html_report(findings)
        else:
            return self._generate_markdown_report(findings)
    
    def _generate_console_report(self, findings: List[Dict]) -> str:
        """Generate rich console report."""
        
        # Group by severity
        by_severity = {
            Severity.CRITICAL: [],
            Severity.HIGH: [],
            Severity.MEDIUM: [],
            Severity.LOW: []
        }
        
        for finding in findings:
            severity = finding.get('severity', Severity.INFO)
            if severity in by_severity:
                by_severity[severity].append(finding)
        
        # Print header
        self.console.print("\n[bold cyan]" + "=" * 70)
        self.console.print("[bold cyan]🔍 FAULT DETECTION REPORT")
        self.console.print("[bold cyan]" + "=" * 70 + "\n")
        
        total_issues = sum(len(issues) for issues in by_severity.values())
        self.console.print(f"[bold]Total Issues Found: {total_issues}[/bold]\n")
        
        # Print by severity
        for severity, issues in by_severity.items():
            if not issues:
                continue
            
            self.console.print(f"\n[bold]{severity.value}[/bold] ({len(issues)} issues)")
            self.console.print("-" * 70)
            
            for issue in issues:
                filename = issue.get('filename', 'unknown')
                line = issue.get('line_number', '?')
                
                self.console.print(f"\n📍 {filename}:{line}")
                
                for fault in issue.get('issues', []):
                    self.console.print(f"   • {fault['description']}")
        
        return ""
    
    def _generate_json_report(self, findings: List[Dict]) -> str:
        """Generate JSON report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_issues': sum(len(f.get('issues', [])) for f in findings),
            'findings': findings
        }
        return json.dumps(report, indent=2, default=str)
    
    def _generate_markdown_report(self, findings: List[Dict]) -> str:
        """Generate Markdown report."""
        md = "# 🔍 Fault Detection Report\n\n"
        md += f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        # Summary
        total = sum(len(f.get('issues', [])) for f in findings)
        md += f"**Total Issues:** {total}\n\n"
        
        # Group by severity
        by_severity = {}
        for finding in findings:
            for issue in finding.get('issues', []):
                sev = issue['severity'].value
                if sev not in by_severity:
                    by_severity[sev] = []
                by_severity[sev].append({
                    'file': finding.get('filename'),
                    'line': finding.get('line_number'),
                    'issue': issue
                })
        
        # Write sections
        for severity, issues in sorted(by_severity.items(), reverse=True):
            md += f"\n## {severity}\n\n"
            for item in issues:
                md += f"- **{item['file']}:{item['line']}**\n"
                md += f"  - {item['issue']['description']}\n\n"
        
        return md
    
    def _generate_html_report(self, findings: List[Dict]) -> str:
        """Generate HTML report."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Fault Detection Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        .critical {{ color: #d32f2f; }}
        .high {{ color: #f57c00; }}
        .medium {{ color: #fbc02d; }}
        .low {{ color: #388e3c; }}
        .issue {{ margin: 20px 0; padding: 15px; border-left: 4px solid #ccc; background: #f5f5f5; }}
        .file-info {{ font-weight: bold; color: #1976d2; }}
    </style>
</head>
<body>
    <h1>🔍 Fault Detection Report</h1>
    <p><em>Generated: {timestamp}</em></p>
    <p><strong>Total Issues: {sum(len(f.get('issues', [])) for f in findings)}</strong></p>
    <hr>
"""
        
        for finding in findings:
            for issue in finding.get('issues', []):
                # Get severity class - handle both enum and string
                severity = issue.get('severity')
                if hasattr(severity, 'value'):
                    severity_str = severity.value
                else:
                    severity_str = str(severity)
                # Extract severity level (e.g., "CRITICAL" from "Severity.CRITICAL" or just "CRITICAL")
                severity_class = severity_str.split('.')[-1].split()[0].lower() if '.' in severity_str or ' ' in severity_str else severity_str.lower()
                html += f"""
    <div class="issue">
        <div class="file-info">{finding.get('filename')}:{finding.get('line_number')}</div>
        <div class="{severity_class}">{severity_str}</div>
        <p>{issue['description']}</p>
    </div>
"""
        
        html += """
</body>
</html>
"""
        return html


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Detect faults in codebase')
    parser.add_argument('--all', action='store_true', help='Analyze all issues')
    parser.add_argument('--security', action='store_true', help='Security issues only')
    parser.add_argument('--severity', choices=['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'], 
                       help='Filter by severity')
    parser.add_argument('--export', help='Export report to file')
    parser.add_argument('--format', choices=['console', 'json', 'markdown', 'html'],
                       default='console', help='Output format')
    
    args = parser.parse_args()
    
    detector = FaultDetector()
    
    # For demonstration, analyze a sample
    sample_code = """
def process_user_input(user_input):
    # No input validation
    query = f"SELECT * FROM users WHERE name = '{user_input}'"
    cursor.execute(query)  # SQL injection risk
    
    # No exception handling
    file = open('data.txt')
    data = file.read()  # Resource leak - no close()
    
    result = eval(user_input)  # Critical: eval with user input
    return result
"""
    
    finding = detector.analyze_code(sample_code, 'example.py', 10)
    findings = [finding]
    
    # Generate report
    report = detector.generate_report(findings, format=args.format)
    
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
