# 📘 Manual Joern Commands Reference

For users who prefer direct Joern commands over Python scripts.

---

## 🎯 Complete Manual Workflow

### **Step 1: Generate CPG Binary**

```bash
# Basic command
joern-parse /path/to/your/code

# With custom output
joern-parse /path/to/your/code --output my_cpg.bin

# Example:
joern-parse MedSAM --output data/cpg.bin
```

---

### **Step 2: Extract Nodes to JSON**

Create file `extract_nodes.sc`:

```scala
// Load CPG
importCpg("data/cpg.bin")

// Extract all METHOD nodes
val methods = cpg.method.l

// Convert to JSON format
val methodsJson = methods.map { m =>
  s"""{
    "id": ${m.id},
    "_label": "METHOD",
    "name": "${m.name.replace("\"", "\\\"")}",
    "signature": "${m.signature.replace("\"", "\\\"")}",
    "fullName": "${m.fullName.replace("\"", "\\\"")}",
    "filename": "${m.filename.replace("\"", "\\\"")}",
    "lineNumber": ${m.lineNumber.getOrElse(0)},
    "code": "${m.code.replace("\"", "\\\"").replace("\n", "\\n").take(1000)}",
    "isExternal": ${m.isExternal}
  }"""
}.mkString("[\n", ",\n", "\n]")

// Write to file
import java.nio.file.{Files, Paths}
Files.write(Paths.get("data/cpg_nodes.json"), methodsJson.getBytes("UTF-8"))

println(s"✅ Exported ${methods.size} nodes to data/cpg_nodes.json")
```

**Run it:**
```bash
joern --script extract_nodes.sc
```

---

### **Step 3: Extract Edges to JSON**

Create file `extract_edges.sc`:

```scala
// Load CPG
importCpg("data/cpg.bin")

// Extract CALL edges
val calls = cpg.call.l
val edges = calls.flatMap { call =>
  call.callee(NoResolve).l.map { callee =>
    s"""{"src": ${call.id}, "dst": ${callee.id}, "label": "CALL"}"""
  }
}

val edgesJson = edges.mkString("[\n", ",\n", "\n]")

// Write to file
import java.nio.file.{Files, Paths}
Files.write(Paths.get("data/cpg_edges.json"), edgesJson.getBytes("UTF-8"))

println(s"✅ Exported ${edges.size} edges to data/cpg_edges.json")
```

**Run it:**
```bash
joern --script extract_edges.sc
```

---

## 🔧 Alternative Methods

### **Method 1: Interactive Joern Shell**

```bash
# Start Joern
joern

# In the shell:
importCpg("data/cpg.bin")

// Explore nodes
cpg.method.name.l  // List all method names
cpg.method.size    // Count methods

// Export specific nodes
val methods = cpg.method.l
val json = methods.toJson
save(json, "data/methods.json")

// Export edges
val edges = cpg.call.l
val edgesJson = edges.toJson
save(edgesJson, "data/edges.json")
```

---

### **Method 2: One-Liner Shell Commands**

**Extract nodes:**
```bash
echo 'importCpg("data/cpg.bin"); val m = cpg.method.toJson; save(m, "nodes.json")' | joern
```

**Extract edges:**
```bash
echo 'importCpg("data/cpg.bin"); val e = cpg.call.toJson; save(e, "edges.json")' | joern
```

---

### **Method 3: Using joern-export**

```bash
# Export to JSON
joern-export data/cpg.bin --repr all --out data/export.json

# Then process the export
python -c "
import json
with open('data/export.json') as f:
    data = json.load(f)
    
# Filter nodes and edges
nodes = [n for n in data if n.get('_label') == 'METHOD']
edges = [e for e in data if 'src' in e and 'dst' in e]

with open('data/cpg_nodes.json', 'w') as f:
    json.dump(nodes, f, indent=2)
    
with open('data/cpg_edges.json', 'w') as f:
    json.dump(edges, f, indent=2)
"
```

---

## 📝 Custom Extraction Queries

### **Extract Only External Methods**

```scala
importCpg("data/cpg.bin")

val externalMethods = cpg.method.isExternal(true).l
val json = externalMethods.toJson
save(json, "external_methods.json")
```

### **Extract Methods by File**

```scala
importCpg("data/cpg.bin")

val modelMethods = cpg.method.filename(".*model\\.py").l
val json = modelMethods.toJson
save(json, "model_methods.json")
```

### **Extract Call Chains**

```scala
importCpg("data/cpg.bin")

// Find all calls from main
val mainCalls = cpg.method.name("main").caller.l
val json = mainCalls.toJson
save(json, "main_calls.json")
```

### **Extract High-Complexity Methods**

```scala
importCpg("data/cpg.bin")

// Methods with many parameters
val complex = cpg.method.filter(_.parameter.size > 5).l
val json = complex.toJson
save(json, "complex_methods.json")
```

---

## 🎨 Advanced Extraction

### **Custom Node Format**

```scala
importCpg("data/cpg.bin")

val customFormat = cpg.method.map { m =>
  Map(
    "id" -> m.id,
    "name" -> m.name,
    "file" -> m.filename,
    "line" -> m.lineNumber.getOrElse(0),
    "signature" -> m.signature,
    "loc" -> m.code.split("\n").length,  // Lines of code
    "callCount" -> m.callee.size          // Number of calls
  )
}

val json = customFormat.map { m =>
  s"""{"id":${m("id")},"name":"${m("name")}","file":"${m("file")}","line":${m("line")},"loc":${m("loc")},"callCount":${m("callCount")}}"""
}.mkString("[\n", ",\n", "\n]")

import java.nio.file.{Files, Paths}
Files.write(Paths.get("custom_nodes.json"), json.getBytes("UTF-8"))
```

### **Extract with Metadata**

```scala
importCpg("data/cpg.bin")

val withMetadata = cpg.method.map { m =>
  Map(
    "method" -> m.name,
    "file" -> m.filename,
    "line" -> m.lineNumber.getOrElse(0),
    "calls" -> m.callee.name.l,              // What it calls
    "calledBy" -> m.caller.name.l,           // Who calls it
    "parameters" -> m.parameter.name.l,      // Parameters
    "locals" -> m.local.name.l               // Local variables
  )
}

// Export as JSON
val json = withMetadata.map(_.toString).mkString("[\n", ",\n", "\n]")
import java.nio.file.{Files, Paths}
Files.write(Paths.get("metadata.json"), json.getBytes("UTF-8"))
```

---

## 🔍 Verification Commands

### **Check CPG Contents**

```bash
# Start Joern
joern

# In shell:
importCpg("data/cpg.bin")

// Count different node types
cpg.method.size       // Methods
cpg.call.size         // Calls
cpg.identifier.size   // Identifiers
cpg.literal.size      // Literals

// List filenames
cpg.file.name.l

// Sample methods
cpg.method.name.l.take(10)
```

### **Validate JSON Files**

```bash
# Check if valid JSON
python -m json.tool data/cpg_nodes.json > /dev/null && echo "✅ Valid JSON"

# Count entries
python -c "import json; print(len(json.load(open('data/cpg_nodes.json'))))" 

# Show first entry
python -c "import json; import pprint; pprint.pprint(json.load(open('data/cpg_nodes.json'))[0])"
```

---

## 📊 Batch Processing

### **Process Multiple Projects**

```bash
#!/bin/bash

for project in Project1 Project2 Project3; do
  echo "Processing $project..."
  
  # Generate CPG
  joern-parse $project --output ${project}_cpg.bin
  
  # Extract nodes
  echo "importCpg('${project}_cpg.bin'); val m = cpg.method.toJson; save(m, '${project}_nodes.json')" | joern
  
  # Extract edges
  echo "importCpg('${project}_cpg.bin'); val e = cpg.call.toJson; save(e, '${project}_edges.json')" | joern
  
  echo "✅ $project complete"
done
```

---

## 💡 Tips & Tricks

### **Increase Memory for Large Projects**

```bash
# Set JVM options
export JAVA_OPTS="-Xmx8G -Xms4G"

# Then run Joern
joern-parse LargeProject
```

### **Faster Parsing**

```bash
# Parse only specific file types
joern-parse MyProject --language python

# Skip test files
joern-parse MyProject --exclude-regex ".*test.*"
```

### **Pretty Print JSON**

```bash
# Format JSON nicely
python -m json.tool data/cpg_nodes.json > data/cpg_nodes_pretty.json
```

---

## 🆘 Troubleshooting

### **"Out of memory"**

```bash
export JAVA_OPTS="-Xmx16G"
joern-parse MyProject
```

### **"Cannot import CPG"**

```bash
# Check file exists
ls -lh data/cpg.bin

# Try absolute path
importCpg("/full/path/to/cpg.bin")
```

### **"JSON encoding error"**

**Use safer escaping:**
```scala
def safeString(s: String): String = {
  s.replace("\\", "\\\\")
   .replace("\"", "\\\"")
   .replace("\n", "\\n")
   .replace("\r", "\\r")
   .replace("\t", "\\t")
}

val safe = cpg.method.map { m =>
  s"""{"name":"${safeString(m.name)}","code":"${safeString(m.code)}"}"""
}
```

---

## 🔗 Resources

- **Joern Queries:** https://queries.joern.io/
- **CPG Schema:** https://cpg.joern.io/
- **Joern Docs:** https://docs.joern.io/

---

**Prefer automation?** Use the Python scripts instead:
```bash
python cpg_workflow.py --source MyProject
```
