# 🚀 START HERE - CPG RAG Analysis System

**Professional code analysis using AI and graph technology**

---

## ⚡ QUICK START (3 Commands)

```bash
# 1. Setup (first time - takes 10 minutes)
cd cpg_rag_system
python setup_environment.py --full

# 2. Add your data
cp your_cpg_nodes.json data/
cp your_cpg_edges.json data/
cp -r YourProject/ data/

# 3. Run analysis
python main.py fault-detection --all
python main.py sensitive-data --all
python main.py understand --overview
```

**Done! You're analyzing code!** 🎉

---

## 📚 Documentation Files (Read These!)

1. **HOW_TO_USE.md** ← Start with this one!
2. **README.md** - Complete documentation
3. **PACKAGE_SUMMARY.md** - Detailed breakdown

---

## 🎯 What This System Does

### **1. Find Bugs** 🔍
```bash
python main.py fault-detection --all
```
Finds: SQL injection, XSS, missing error handling, resource leaks

### **2. Track Sensitive Data** 🔐
```bash
python main.py sensitive-data --all
```
Tracks passwords, API keys, PII through your entire application

### **3. Understand Code** 📚
```bash
python main.py understand --overview
```
Generates architecture overview, entry points, design patterns

---

## 📦 What's Inside

```
cpg_rag_system/
├── setup_environment.py    # Run this FIRST
├── main.py                  # Main interface
├── config.py                # Edit to customize
│
├── analyzers/               # Analysis tools
│   ├── fault_detector.py
│   ├── sensitive_data_tracker.py
│   └── code_understander.py
│
└── docs/                    # Documentation
    ├── HOW_TO_USE.md       ← Read this first!
    └── README.md
```

---

## ⚙️ Requirements

- Python 3.8+
- 8 GB RAM
- 10 GB disk space
- Internet (for setup)

**Setup installs:**
- Ollama + AI models
- Neo4j database
- Python packages

---

## 💡 Common Commands

```bash
# Setup (first time)
python setup_environment.py --full

# Find all bugs
python main.py fault-detection --all

# Track passwords/keys
python main.py sensitive-data --all

# Export report
python main.py fault-detection --all --export report.html

# Customize
python main.py customize --interactive
```

---

## 🆘 Need Help?

1. **Quick guide:** Read `HOW_TO_USE.md`
2. **Full docs:** Read `README.md`
3. **Command help:** `python main.py --help`
4. **Examples:** `python main.py customize --examples`

---

## 🎯 Next Steps

1. ✅ Read `HOW_TO_USE.md`
2. ✅ Run `python setup_environment.py --full`
3. ✅ Add your data to `data/` folder
4. ✅ Run `python main.py fault-detection --all`

---

**Ready to analyze code like a pro!** 🚀

See `HOW_TO_USE.md` for detailed instructions.
