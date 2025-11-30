#  HOW TO USE - CPG RAG System

**Quick start guide for the complete package**

---

##  What's in This Package

```
cpg_rag_system/
├── setup_environment.py          # Run this FIRST
├── main.py                        # Main interface - run everything from here
├── config.py                      # Configuration (edit this to customize)
├── requirements.txt               # Dependencies
│
├── analyzers/                     # Analysis tools
│   ├── fault_detector.py              # Find bugs & vulnerabilities
│   ├── sensitive_data_tracker.py      # Track sensitive data flow
│   └── code_understander.py           # Understand codebase
│
├── tools/
│   └── repo_customizer.py            # Customization guide
│
└── docs/
    ├── README.md                      # Full documentation
    └── PACKAGE_SUMMARY.md             # Detailed breakdown
```

---

## QUICK START (3 Steps)

### **Step 1: Setup Environment** (First time only - 10 minutes)

```bash
cd cpg_rag_system
python setup_environment.py --full
```

**This installs:**
- Python packages
- Ollama + AI models (4GB download)
- Neo4j database
- Creates folders

**Wait ~10 minutes for downloads to complete.**

---

### **Step 2: Add Your Data**

```bash
# Create data directory if not exists
mkdir -p data

# Copy your CPG files
cp /path/to/cpg_nodes.json data/
cp /path/to/cpg_edges.json data/

# Copy your source code
cp -r /path/to/YourProject data/YourProject/
```

**Required files:**
- `data/cpg_nodes.json` - CPG nodes from Joern
- `data/cpg_edges.json` - CPG edges from Joern
- `data/YourProject/` - Your source code directory

---

### **Step 3: Run Analysis**

```bash
# Find bugs and security issues
python main.py fault-detection --all

# Track sensitive data (passwords, API keys, etc.)
python main.py sensitive-data --all

# Understand codebase structure
python main.py understand --overview
```

**That's it! You're analyzing code!** 

---

##  DETAILED USAGE

### **1. Fault Detection** (Find Bugs)

```bash
# Find all issues
python main.py fault-detection --all

# Security issues only
python main.py fault-detection --security

# Critical issues only
python main.py fault-detection --severity CRITICAL

# Export report
python main.py fault-detection --all --export report.html
```

**Detects:**
- SQL injection
- XSS vulnerabilities
- Missing error handling
- Resource leaks
- Null pointer bugs

---

### **2. Sensitive Data Tracking**  NEW!

```bash
# Track all sensitive data
python main.py sensitive-data --all

# Track specific type
python main.py sensitive-data --track password

# Export report
python main.py sensitive-data --all --export data_flow.html
```

**Tracks:**
- Passwords, API keys, tokens
- Credit cards, SSN, PII
- Data flow through functions
- Unsanitized logging
- Unsanitized exports

---

### **3. Code Understanding**

```bash
# Generate overview
python main.py understand --overview

# Architecture analysis
python main.py understand --architecture

# Find entry points
python main.py understand --entry-points

# Export to file
python main.py understand --overview --export overview.md
```

**Generates:**
- File organization
- Main modules
- Entry points
- Design patterns

---

### **4. Customization**

```bash
# Interactive customization wizard
python main.py customize --interactive

# Show examples
python main.py customize --examples

# Generate custom analyzer
python tools/repo_customizer.py --generate-analyzer MyAnalyzer
```

---

##  CONFIGURATION

Edit `config.py` to customize:

```python
from config import CONFIG, ResponseFormat

# Change response style
CONFIG.default_response_format = ResponseFormat.BRIEF  # or DETAILED

# Adjust sensitivity
CONFIG.critical_complexity = 10  # Lower = more sensitive

# Add your sensitive data patterns
CONFIG.sensitive_data_patterns.append('private_key')
CONFIG.sensitive_data_patterns.append('certificate')

# Increase analysis depth
CONFIG.top_k_results = 10
```

**Main settings:**
- `default_response_format` - BRIEF, DETAILED, or TECHNICAL
- `top_k_results` - How many functions to analyze (default: 5)
- `critical_complexity` - Complexity threshold (default: 15)
- `sensitive_data_patterns` - What to track (passwords, keys, etc.)
- `show_severity_levels` - Show indicators (default: True)

---

## EXPORT FORMATS

All tools support multiple formats:

```bash
# Console (default - colorful output)
python main.py fault-detection --all

# JSON (for automation/CI/CD)
python analyzers/fault_detector.py --all --format json --export report.json

# Markdown (for documentation)
python analyzers/fault_detector.py --all --format markdown --export report.md

# HTML (for sharing)
python analyzers/fault_detector.py --all --format html --export report.html
```

---

## COMMON USE CASES

### **Security Audit**
```bash
python main.py fault-detection --security --export security.html
python main.py sensitive-data --all --export privacy.html
```

### **Code Review**
```bash
python main.py fault-detection --all --export review.md
python main.py understand --overview --export structure.md
```

### **CI/CD Integration**
```bash
# In your CI pipeline:
python main.py fault-detection --severity CRITICAL --format json > ci.json

# Fail build if critical issues found
python -c "import json; exit(1 if json.load(open('ci.json'))['total_issues'] > 0 else 0)"
```

### **Privacy Compliance**
```bash
python main.py sensitive-data --all --export pii_audit.html
```

---

## TROUBLESHOOTING

### **"Command not found: ollama"**
```bash
# Run setup again
python setup_environment.py --ollama
```

### **"Neo4j connection failed"**
```bash
# Check Docker
docker ps

# Restart Neo4j
docker start neo4j

# Or run setup again
python setup_environment.py --neo4j
```

### **"Module not found"**
```bash
# Install dependencies
pip install -r requirements.txt --break-system-packages
```

### **"File not found: cpg_nodes.json"**
```bash
# Make sure files are in data/
ls -la data/
# Should show: cpg_nodes.json, cpg_edges.json
```

---

## DOCUMENTATION

- **README.md** - Complete documentation
- **PACKAGE_SUMMARY.md** - Detailed file breakdown
- **This file (HOW_TO_USE.md)** - Quick reference

For detailed help on any command:
```bash
python main.py --help
python main.py fault-detection --help
python main.py sensitive-data --help
```

---

## EXAMPLES

### **Example 1: First Time Setup**
```bash
# 1. Extract zip
unzip cpg_rag_system.zip
cd cpg_rag_system

# 2. Setup (wait 10 min)
python setup_environment.py --full

# 3. Add data
mkdir -p data
cp ~/MyCPG/cpg_nodes.json data/
cp ~/MyCPG/cpg_edges.json data/
cp -r ~/MyProject data/MyProject

# 4. Run
python main.py fault-detection --all
```

### **Example 2: Daily Usage**
```bash
cd cpg_rag_system

# Quick security check
python main.py fault-detection --security

# Track sensitive data
python main.py sensitive-data --all

# Generate report for team
python main.py fault-detection --all --export daily_report.html
```

### **Example 3: Customize for Your Team**
```bash
# Edit config
nano config.py

# Change these lines:
# CONFIG.default_response_format = ResponseFormat.BRIEF
# CONFIG.sensitive_data_patterns.append('your_custom_pattern')

# Run with your settings
python main.py fault-detection --all
```

---

## COMMAND CHEAT SHEET

```bash
# Setup (first time)
python setup_environment.py --full

# Find bugs
python main.py fault-detection --all

# Track sensitive data
python main.py sensitive-data --all

# Understand code
python main.py understand --overview

# Customize
python main.py customize --interactive

# Export reports
--export report.html
--format json
--format markdown
```

---

## YOUr READY!

**Basic workflow:**
1. Run `setup_environment.py --full` (first time only)
2. Add your data to `data/` folder
3. Run `python main.py [command]`
4. Get insights and reports!

**Need help?** Check:
- `README.md` for full documentation
- `python main.py --help` for command help
- `python main.py customize --examples` for customization examples

---

## SUPPORT

For issues:
1. Check `README.md`
2. Run `python main.py customize --examples`
3. Check logs in `logs/` directory

---

**Happy analyzing!** 
