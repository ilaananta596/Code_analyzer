# 🔧 CPG Generators - Create JSON from Source Code

This folder contains scripts to generate CPG (Code Property Graph) JSON files from your source code using Joern.

---

## 📂 What's Here

```
cpg_generators/
├── README.md                  # This file
├── cpg_workflow.py            # Complete automated workflow ⭐ EASIEST
├── generate_cpg_json.py       # Generate CPG + extract JSON
├── extract_from_cpg.py        # Extract JSON from existing CPG
└── MANUAL_COMMANDS.md         # Manual Joern commands
```

---

## ⚡ Quick Start (Easiest Method)

### **Use the Complete Workflow Script**

```bash
# 1. Go to cpg_generators directory
cd cpg_generators

# 2. Run workflow on your source code
python cpg_workflow.py --source /path/to/your/code

# Or if code is in data/ already
python cpg_workflow.py --source ../data/YourProject
```

**This does everything:**
1. ✅ Generates CPG using Joern
2. ✅ Extracts nodes to `data/cpg_nodes.json`
3. ✅ Extracts edges to `data/cpg_edges.json`
4. ✅ Verifies files

**Time:** ~1-5 minutes depending on codebase size

---

## 📋 All Methods

### **Method 1: Complete Workflow** ⭐ RECOMMENDED

**Best for:** First-time users, complete automation

```bash
# Basic usage
python cpg_workflow.py --source YourProject

# With analysis after generation
python cpg_workflow.py --source YourProject --analyze

# Specify Joern path
python cpg_workflow.py --source YourProject --joern /opt/joern
```

**Output:**
- `data/cpg.bin` - Binary CPG file
- `data/cpg_nodes.json` - All nodes (methods, functions)
- `data/cpg_edges.json` - All edges (calls, relationships)

---

### **Method 2: Step-by-Step**

**Best for:** Understanding the process, debugging

#### **Step 1: Generate CPG**
```bash
python generate_cpg_json.py --source YourProject --output ../data
```

#### **Step 2: (Optional) Extract from existing CPG**
```bash
python extract_from_cpg.py --cpg ../data/cpg.bin --output ../data
```

---

### **Method 3: Manual Joern Commands**

**Best for:** Advanced users, custom extraction

See `MANUAL_COMMANDS.md` for direct Joern commands.

---

## 🎯 Script Details

### **cpg_workflow.py** - Complete Workflow

**What it does:**
- Detects Joern installation
- Generates CPG from source
- Extracts nodes and edges
- Verifies JSON files
- Optionally runs analysis

**Usage:**
```bash
python cpg_workflow.py --source MyCode
python cpg_workflow.py --source MyCode --analyze
python cpg_workflow.py --skip-generation  # Use existing cpg.bin
```

**Arguments:**
- `--source, -s` - Source code directory (required)
- `--joern` - Joern installation path (auto-detected)
- `--analyze, -a` - Run analysis after generation
- `--skip-generation` - Use existing cpg.bin

---

### **generate_cpg_json.py** - Generate from Source

**What it does:**
- Runs joern-parse to create CPG
- Exports nodes and edges to JSON
- All-in-one generation

**Usage:**
```bash
python generate_cpg_json.py --source MedSAM
python generate_cpg_json.py --source MedSAM --output ./data
python generate_cpg_json.py --source MedSAM --joern-path /opt/joern
```

**Arguments:**
- `--source, -s` - Source directory (required)
- `--output, -o` - Output directory (default: ./data)
- `--joern-path` - Joern path (auto-detected)

---

### **extract_from_cpg.py** - Extract from Existing CPG

**What it does:**
- Takes existing cpg.bin file
- Extracts nodes and edges to JSON
- Useful if you already have CPG

**Usage:**
```bash
python extract_from_cpg.py --cpg cpg.bin
python extract_from_cpg.py --cpg cpg.bin --output ./data
python extract_from_cpg.py --cpg cpg.bin --nodes-only
```

**Arguments:**
- `--cpg` - Path to cpg.bin (required)
- `--output, -o` - Output directory (default: ./data)
- `--nodes-only` - Extract only nodes
- `--edges-only` - Extract only edges
- `--joern-path` - Joern path

---

## 📊 Output Files

All scripts generate these files:

### **cpg_nodes.json** (~10-50 MB)
```json
[
  {
    "id": 123456,
    "_label": "METHOD",
    "name": "forward",
    "signature": "def forward(self, x)",
    "filename": "model.py",
    "lineNumber": 45,
    "code": "def forward(self, x):\n    return self.model(x)",
    "isExternal": false
  },
  ...
]
```

### **cpg_edges.json** (~20-100 MB)
```json
[
  {
    "src": 123456,
    "dst": 789012,
    "label": "CALL"
  },
  ...
]
```

---

## 🔧 Requirements

### **Required:**
- Python 3.8+
- Joern installed

### **Install Joern:**

**Linux/Mac:**
```bash
# Download
wget https://github.com/joernio/joern/releases/latest/download/joern-install.sh

# Install
chmod +x joern-install.sh
sudo ./joern-install.sh --interactive

# Verify
joern --version
```

**Or specify path:**
```bash
python cpg_workflow.py --source MyCode --joern /path/to/joern
```

---

## 📝 Examples

### **Example 1: Analyze MedSAM Project**

```bash
cd cpg_generators

# Complete workflow
python cpg_workflow.py --source ../data/MedSAM --analyze

# Output:
#   ✅ data/cpg.bin
#   ✅ data/cpg_nodes.json (18 MB, 1,234 nodes)
#   ✅ data/cpg_edges.json (42 MB, 5,678 edges)
#   🔍 Analysis results...
```

### **Example 2: Just Generate JSON**

```bash
# Generate CPG files without analysis
python cpg_workflow.py --source MyProject

# Files created in ../data/
ls -lh ../data/
# cpg.bin
# cpg_nodes.json
# cpg_edges.json
```

### **Example 3: Extract from Existing CPG**

```bash
# You already have cpg.bin
python extract_from_cpg.py --cpg my_project.bin --output ../data

# Only extract nodes
python extract_from_cpg.py --cpg my_project.bin --nodes-only
```

### **Example 4: Custom Joern Path**

```bash
# Joern installed in custom location
python cpg_workflow.py \
  --source ~/Projects/MyApp \
  --joern ~/tools/joern \
  --analyze
```

---

## 🐛 Troubleshooting

### **"Joern not found"**

**Solution 1:** Specify path
```bash
python cpg_workflow.py --source MyCode --joern /opt/joern
```

**Solution 2:** Install Joern
```bash
# See https://docs.joern.io/installation
wget https://github.com/joernio/joern/releases/latest/download/joern-install.sh
sudo ./joern-install.sh
```

**Solution 3:** Add to PATH
```bash
export PATH=$PATH:/opt/joern
```

---

### **"CPG generation failed"**

**Check:**
1. Source directory exists
2. Source has .py files
3. Sufficient disk space (needs ~500MB temp space)

**Verbose output:**
```bash
# Run joern-parse manually
/opt/joern/joern-parse YourProject --output cpg.bin
```

---

### **"JSON extraction failed"**

**Try manual extraction:**
```bash
# Use Joern directly
cd /opt/joern
./joern

// In Joern shell:
importCpg("cpg.bin")
val methods = cpg.method.toJson
save(methods, "nodes.json")
```

---

### **"Invalid JSON"**

**Fix:**
```bash
# Re-extract with verbose output
python extract_from_cpg.py --cpg cpg.bin --output ../data

# Verify JSON
python -m json.tool ../data/cpg_nodes.json > /dev/null
```

If still fails, the CPG might be corrupted. Regenerate:
```bash
rm cpg.bin
python cpg_workflow.py --source YourProject
```

---

## 🎯 Workflow Comparison

| Method | Ease of Use | Flexibility | Best For |
|--------|-------------|-------------|----------|
| **cpg_workflow.py** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | First-time users, automation |
| **generate_cpg_json.py** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Step-by-step control |
| **extract_from_cpg.py** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Existing CPG, custom extraction |
| **Manual commands** | ⭐⭐ | ⭐⭐⭐⭐⭐ | Advanced users, debugging |

---

## 💡 Tips

### **Large Codebases**

For large projects (>100K lines):
```bash
# Increase JVM memory
export JAVA_OPTS="-Xmx8G"

# Then run
python cpg_workflow.py --source BigProject
```

### **Faster Processing**

```bash
# Skip edges if you only need nodes
python extract_from_cpg.py --cpg cpg.bin --nodes-only

# Or skip nodes if you only need edges
python extract_from_cpg.py --cpg cpg.bin --edges-only
```

### **Multiple Projects**

```bash
# Process multiple projects
for project in Project1 Project2 Project3; do
  python cpg_workflow.py --source $project --output data_$project
done
```

---

## 🔗 Next Steps

After generating JSON files:

```bash
cd ..  # Back to main directory

# Run analysis
python main.py fault-detection --all
python main.py sensitive-data --all
python main.py understand --overview
```

---

## 📚 Additional Resources

- **Joern Documentation:** https://docs.joern.io/
- **CPG Specification:** https://cpg.joern.io/
- **Joern Queries:** https://queries.joern.io/

---

**Questions?** Check main README.md or run with `--help`:
```bash
python cpg_workflow.py --help
```
