# CPG RAG Analysis System - Production Package

Complete professional code analysis system using Code Property Graphs, RAG (Retrieval-Augmented Generation), and LLMs.

---

## What You Got

A **production-ready Python package** with separate scripts for each functionality:

### **Core System**
- `setup_environment.py` - Complete environment setup
- `config.py` - Centralized configuration
- `main.py` - Unified command-line interface

### **Analyzers** (`analyzers/`)
- `fault_detector.py` - Find bugs and vulnerabilities
- `sensitive_data_tracker.py` - Track sensitive data flows NEW!
- `code_understander.py` - Generate codebase overviews

### **Tools** (`tools/`)
- `repo_customizer.py` - Interactive customization guide

---

## Quick Start

### **1. Setup Environment**

```bash
cd cpg_rag_system
python setup_environment.py --full
```

This installs:
- Python dependencies
- Ollama + models
- Neo4j Docker container
- Directory structure
- Configuration files

**Time**: ~10 minutes (includes 4GB model download)

---

### **2. Place Your Data**

```bash
# Place CPG files
cp your_cpg_nodes.json data/cpg_nodes.json
cp your_cpg_edges.json data/cpg_edges.json

# Place source code
cp -r YourProject/ data/YourProject/
```

---

### **3. Run Analysis**

```bash
# Unified interface
python main.py

# Or run specific analyzers directly
python analyzers/fault_detector.py --all
python analyzers/sensitive_data_tracker.py --track password
python analyzers/code_understander.py --overview
```

---

## Complete Usage Guide

### **Fault Detection**

Finds security vulnerabilities, bugs, and code quality issues.

**Direct usage:**
```bash
python analyzers/fault_detector.py --all
python analyzers/fault_detector.py --security
python analyzers/fault_detector.py --severity CRITICAL
python analyzers/fault_detector.py --export report.html --format html
```

**Via main.py:**
```bash
python main.py fault-detection --all
python main.py fault-detection --security --export security.html
```

**Detects:**
- SQL injection risks
- XSS vulnerabilities
- eval/exec usage
- Missing error handling
- Resource leaks
- Null pointer risks
- High complexity

**Output:**
```
CRITICAL (3 issues)
----------------------------------------------------------------------

auth.py:45
   • Uses eval() - Remote Code Execution risk
   • Potential SQL injection - string formatting in query

HIGH (5 issues)
----------------------------------------------------------------------

database.py:123
   • No try/except around file I/O
   • Opens resources but no .close() detected
```

---

### **Sensitive Data Tracking**  NEW!

Tracks flow of sensitive data (passwords, API keys, PII) to ensure sanitization.

**Direct usage:**
```bash
python analyzers/sensitive_data_tracker.py --all
python analyzers/sensitive_data_tracker.py --track password
python analyzers/sensitive_data_tracker.py --export data_flow.html
```

**Via main.py:**
```bash
python main.py sensitive-data --track password
python main.py sensitive-data --all --export flow.json
```

**Detects:**
- Sensitive variable declarations
- Data flow through functions
- Unsanitized logging
- Unsanitized external exports
- Missing encryption

**Example Output:**
```
SENSITIVE DATA FLOW ANALYSIS

CRITICAL (2 violations)
----------------------------------------------------------------------

auth.py - authenticate_user() [line 15]
   Sensitive data "password" (password) exported without sanitization
   Code: requests.post("https://api.com", json={"pass": password})

HIGH (1 violation)
----------------------------------------------------------------------

logger.py - log_user_action() [line 45]
   Sensitive data "api_key" (api_key) logged without sanitization
   Code: logger.info(f"API call with key: {api_key}")
```

**Data Flow Visualization:**
```
authenticate_user
├── password (password)
│   ├── Line 10: ASSIGNED_TO:pwd
│   ├── Line 15: LOGGING (UNSANITIZED_LOGGING)
│   ├── Line 20: SANITIZED
│   └── Line 25: EXTERNAL_EXPORT
```

---

### **Code Understanding**

Generates comprehensive codebase overviews.

**Direct usage:**
```bash
python analyzers/code_understander.py --overview
python analyzers/code_understander.py --architecture
python analyzers/code_understander.py --entry-points
python analyzers/code_understander.py --export overview.md
```

**Via main.py:**
```bash
python main.py understand --overview
python main.py understand --architecture --export arch.md
```

**Generates:**
- File organization analysis
- Main modules identification
- Entry point detection
- Design pattern recognition
- Architecture description

**Output:**
```
CODEBASE UNDERSTANDING

Quick Stats:
  Files: 39
  Methods: 1,282
  Entry Points: 5
  Design Patterns: 3

Main Modules:
  1. model.py (245 methods)
  2. transforms.py (123 methods)
  3. utils.py (89 methods)

Entry Points:
  • main (main_function)
  • __init__ (initializer)
  • forward (central_function - 45 callers)
```

---

### **System Customization**

Interactive guide for customizing the system.

**Direct usage:**
```bash
python tools/repo_customizer.py --interactive
python tools/repo_customizer.py --help-config
python tools/repo_customizer.py --explain response_format
python tools/repo_customizer.py --generate-analyzer MyAnalyzer
python tools/repo_customizer.py --examples
```

**Via main.py:**
```bash
python main.py customize --interactive
python main.py customize --examples
```

**Features:**
- Configuration explanation
- Interactive customization wizard
- Custom analyzer template generation
- Code examples

**Example: Generate Custom Analyzer**
```bash
python tools/repo_customizer.py --generate-analyzer PerformanceAnalyzer
```

Creates `analyzers/performance_analyzer.py` with full template.

---

## Configuration

### **Central Config File**: `config.py`

All settings in one place:

```python
from config import CONFIG

# Change response format
CONFIG.default_response_format = ResponseFormat.BRIEF

# Adjust sensitivity
CONFIG.critical_complexity = 10

# Add sensitive data patterns
CONFIG.sensitive_data_patterns.append('private_key')

# Increase analysis depth
CONFIG.top_k_results = 10
CONFIG.graph_context_depth = 3
```

### **Key Settings**:

| Setting | Purpose | Default |
|---------|---------|---------|
| `default_response_format` | Output format (BRIEF, DETAILED, TECHNICAL) | DETAILED |
| `top_k_results` | Number of similar functions | 5 |
| `critical_complexity` | Complexity threshold | 15 |
| `sensitive_data_patterns` | Patterns to detect | ['password', 'api_key', ...] |
| `show_severity_levels` | Show indicators | True |

### **Environment Variables**

Create `.env` file:
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
NEO4J_URI=bolt://localhost:7687
NEO4J_PASSWORD=cpgragagent123
```

---

## Export Formats

All analyzers support multiple export formats:

### **Console** (default)
Rich formatted output with colors and severity indicators.

### **JSON**
```bash
python analyzers/fault_detector.py --all --format json --export report.json
```

Machine-readable, perfect for CI/CD integration.

### **Markdown**
```bash
python analyzers/fault_detector.py --all --format markdown --export report.md
```

Great for documentation, GitHub.

### **HTML**
```bash
python analyzers/fault_detector.py --all --format html --export report.html
```

Styled reports ready to share with stakeholders.

---

## Use Cases

### **1. Security Audit**

```bash
# Find all security issues
python main.py fault-detection --security --export security_audit.html

# Track sensitive data flows
python main.py sensitive-data --all --export data_flows.json
```

### **2. Code Review**

```bash
# Comprehensive fault detection
python main.py fault-detection --all --export code_review.md

# Understand structure
python main.py understand --overview --export overview.md
```

### **3. Onboarding New Developers**

```bash
# Generate codebase overview
python main.py understand --architecture --export architecture.md

# Find entry points
python main.py understand --entry-points
```

### **4. CI/CD Integration**

```bash
# Export JSON for parsing
python analyzers/fault_detector.py --severity CRITICAL --format json --export ci_report.json

# Parse and fail build if critical issues found
python parse_ci_report.py ci_report.json
```

---

## Customization Examples

### **Make Responses Brief**
```python
from config import CONFIG, ResponseFormat

CONFIG.default_response_format = ResponseFormat.BRIEF
CONFIG.max_response_length = 150
CONFIG.include_code_snippets = False
```

### **More Sensitive Fault Detection**
```python
CONFIG.critical_complexity = 10  # Lower threshold
CONFIG.high_coupling_threshold = 5
```

### **Add Custom Sensitive Data Pattern**
```python
CONFIG.sensitive_data_patterns.extend([
    'private_key',
    'certificate',
    'social_security',
    'credit_card'
])
```

### **Customize Sanitization Detection**
```python
CONFIG.sanitization_functions.extend([
    'my_hash_function',
    'custom_encrypt',
    'anonymize'
])
```

---

## Package Structure

```
cpg_rag_system/
├── setup_environment.py       # Complete environment setup
├── config.py                  # Central configuration
├── main.py                    # Unified CLI interface
│
├── analyzers/                 # Analysis tools
│   ├── fault_detector.py         # Bug/vulnerability detection
│   ├── sensitive_data_tracker.py # Data flow tracking
│   └── code_understander.py      # Codebase overview
│
├── tools/                     # Utility tools
│   └── repo_customizer.py        # Customization guide
│
├── data/                      # Your data (create this)
│   ├── cpg_nodes.json            # CPG nodes from Joern
│   ├── cpg_edges.json            # CPG edges from Joern
│   └── YourProject/              # Source code
│
├── reports/                   # Generated reports
├── logs/                      # Application logs
├── chroma_db/                 # Vector stores
│
├── requirements.txt           # Python dependencies
├── .env                       # Configuration
└── README.md                  # This file
```

---

## Advanced Features

### **Batch Analysis**

Analyze multiple aspects in one run:

```python
from analyzers.fault_detector import FaultDetector
from analyzers.sensitive_data_tracker import SensitiveDataTracker

# Run all analyzers
fault_detector = FaultDetector()
data_tracker = SensitiveDataTracker()

# ... your analysis code ...
```

### **Custom Analyzers**

Generate templates and implement custom logic:

```bash
python tools/repo_customizer.py --generate-analyzer PerformanceAnalyzer
```

Edit `analyzers/performance_analyzer.py` and implement your logic.

### **Programmatic Usage**

Use as a library:

```python
from config import CONFIG
from analyzers.fault_detector import FaultDetector

# Configure
CONFIG.critical_complexity = 10

# Analyze
detector = FaultDetector()
findings = detector.analyze_code(code, filename, line_number)
report = detector.generate_report(findings, format='json')
```

---

## Documentation

- **`setup_environment.py`** - Run with `--help` for setup options
- **`config.py`** - See inline comments for all settings
- **Each analyzer** - Run with `--help` for usage
- **`tools/repo_customizer.py`** - Interactive customization guide

---

## Features Summary

### **Analyzers:**
**Fault Detector** - Security, bugs, code quality
**Sensitive Data Tracker** - Privacy, data flow ⭐ NEW!
**Code Understander** - Architecture, overview

### **Capabilities:**
Multi-format export (Console, JSON, MD, HTML)
Severity scoring (CRITICAL, HIGH, MEDIUM, LOW)
Configurable thresholds
Custom analyzer templates
Interactive customization
Unified CLI interface

### **Integration:**
Standalone scripts
Programmatic API
CI/CD ready
Extensible architecture

---

## Requirements

- Python 3.8+
- Ollama (with llama3.2 and nomic-embed-text models)
- Docker (for Neo4j)
- 4-8 GB RAM
- 5-10 GB disk space

---

## Youre Ready!

```bash
# 1. Setup
python setup_environment.py --full

# 2. Add your data
cp cpg_nodes.json data/
cp -r YourProject/ data/

# 3. Run analysis
python main.py fault-detection --all
```

**Happy analyzing!** 
