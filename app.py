#!/usr/bin/env python3
"""
Streamlit frontend for GraphRAG Code Analysis System
"""

import streamlit as st
import subprocess
import os
import sys
from pathlib import Path
import json
import time
import shutil

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent / "scripts"))

# Set page config
st.set_page_config(
    page_title="GraphRAG Code Analyzer",
    page_icon="🔍",
    layout="wide"
)

# Initialize session state
if 'cpg_built' not in st.session_state:
    st.session_state.cpg_built = False
if 'methods_extracted' not in st.session_state:
    st.session_state.methods_extracted = False
if 'methods_indexed' not in st.session_state:
    st.session_state.methods_indexed = False
if 'project_name' not in st.session_state:
    st.session_state.project_name = None
if 'cpg_path' not in st.session_state:
    st.session_state.cpg_path = None
if 'cleanup_done' not in st.session_state:
    st.session_state.cleanup_done = False
if 'cpg_json_extracted' not in st.session_state:
    st.session_state.cpg_json_extracted = False

def cleanup_project_files(project_name=None):
    """Clean up CPG files and cloned repositories"""
    cleaned = []
    
    # Clean up CPG files
    cpg_dir = Path("data/cpg")
    if cpg_dir.exists():
        if project_name:
            # Clean specific project
            cpg_file = cpg_dir / f"{project_name}.cpg.bin"
            source_info_file = cpg_dir / f"{project_name}.source_info.json"
            if cpg_file.exists():
                cpg_file.unlink()
                cleaned.append(f"CPG: {cpg_file}")
            if source_info_file.exists():
                # Read source info to clean up cloned repo
                try:
                    with open(source_info_file, 'r') as f:
                        source_info = json.load(f)
                    clone_dir = source_info.get("source_dir")
                    if clone_dir and Path(clone_dir).exists():
                        # Clean up cloned repo when explicitly resetting
                        # Source code extraction happens immediately after CPG build, so it's safe to clean now
                        shutil.rmtree(clone_dir)
                        cleaned.append(f"Cloned repo: {clone_dir}")
                except Exception as e:
                    pass
                source_info_file.unlink()
                cleaned.append(f"Source info: {source_info_file}")
        else:
            # Clean all CPG files
            for cpg_file in cpg_dir.glob("*.cpg.bin"):
                project = cpg_file.stem
                cpg_file.unlink()
                cleaned.append(f"CPG: {cpg_file}")
                
                # Clean corresponding source_info.json and cloned repo
                source_info_file = cpg_dir / f"{project}.source_info.json"
                if source_info_file.exists():
                    try:
                        with open(source_info_file, 'r') as f:
                            source_info = json.load(f)
                        clone_dir = source_info.get("source_dir")
                        if clone_dir and Path(clone_dir).exists():
                            # Clean up cloned repo when resetting
                            # Source code extraction happens immediately after CPG build, so it's safe to clean now
                            shutil.rmtree(clone_dir)
                            cleaned.append(f"Cloned repo: {clone_dir}")
                    except Exception as e:
                        pass
                    source_info_file.unlink()
                    cleaned.append(f"Source info: {source_info_file}")
    
    # Clean up methods JSON files
    methods_dir = Path("data")
    if methods_dir.exists():
        if project_name:
            methods_file = methods_dir / f"methods_{project_name}.json"
            if methods_file.exists():
                methods_file.unlink()
                cleaned.append(f"Methods JSON: {methods_file}")
        else:
            for methods_file in methods_dir.glob("methods_*.json"):
                methods_file.unlink()
                cleaned.append(f"Methods JSON: {methods_file}")
    
    return cleaned

# Clean up on app refresh/reset (when session state is empty)
if not st.session_state.get('project_name') and not st.session_state.get('cleanup_done'):
    # On first load or after reset, clean up any orphaned temp clone directories
    cpg_dir = Path("data/cpg")
    if cpg_dir.exists():
        for source_info_file in cpg_dir.glob("*.source_info.json"):
            try:
                with open(source_info_file, 'r') as f:
                    source_info = json.load(f)
                clone_dir = source_info.get("source_dir")
                # Clean up orphaned temp directories on app refresh
                # These are from previous sessions where cleanup didn't happen
                if clone_dir and Path(clone_dir).exists() and "graphrag_clone_" in clone_dir:
                    # Clean up orphaned temp directories (from previous sessions)
                    # Active sessions will have their repos cleaned on explicit reset
                    shutil.rmtree(clone_dir)
            except Exception:
                pass
    st.session_state.cleanup_done = True

def get_python_cmd():
    """Get the correct Python command (prefer conda environment)"""
    # Try to find conda environment
    conda_base = os.environ.get('CONDA_PREFIX')
    if conda_base:
        python_cmd = os.path.join(conda_base, 'bin', 'python')
        if os.path.exists(python_cmd):
            return python_cmd
    
    # Try common conda paths
    for base in [os.path.expanduser("~/miniconda3"), os.path.expanduser("~/anaconda3")]:
        python_cmd = os.path.join(base, "envs", "graphrag", "bin", "python")
        if os.path.exists(python_cmd):
            return python_cmd
    
    # Fallback to system python
    return "python"

def run_command(cmd, description):
    """Run a command and show progress"""
    with st.spinner(description):
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes for CPG building
            )
            if result.returncode == 0:
                return True, result.stdout
            else:
                return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Command timed out after 10 minutes"
        except Exception as e:
            return False, str(e)

def normalize_github_url(url):
    """Normalize GitHub URL"""
    url = url.strip()
    if url.startswith('http://') or url.startswith('https://'):
        return url
    elif url.startswith('git@github.com:'):
        return url.replace('git@github.com:', 'https://github.com/').replace('.git', '')
    elif 'github.com' in url:
        if not url.startswith('http'):
            url = 'https://' + url
        return url.replace('.git', '')
    return url

def get_project_name_from_repo(repo):
    """Extract project name from repository URL or path"""
    if repo.startswith('http') or 'github.com' in repo:
        # GitHub URL
        parts = repo.rstrip('/').split('/')
        project_name = parts[-1].replace('.git', '')
    else:
        # Local path
        project_name = Path(repo).name
    return project_name.lower().replace(' ', '_').replace('-', '_')

# Main UI
st.title("🔍 GraphRAG Code Analyzer")
st.markdown("Analyze code repositories using GraphRAG: Semantic retrieval + Graph expansion + LLM reasoning")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    device = st.selectbox(
        "Device",
        ["cuda", "cpu"],
        index=0,
        help="Select GPU (cuda) or CPU for processing"
    )
    
    top_k = st.slider(
        "Top K Methods",
        min_value=3,
        max_value=20,
        value=10,
        help="Number of methods to retrieve for analysis"
    )
    
    llm_model = st.text_input(
        "LLM Model",
        value="Qwen/Qwen2.5-Coder-7B-Instruct",
        help="HuggingFace model name for LLM reasoning"
    )
    
    embedding_model = st.text_input(
        "Embedding Model",
        value="microsoft/graphcodebert-base",
        help="HuggingFace model name for embeddings"
    )

# Main content area
tab1, tab2, tab3 = st.tabs(["📥 Setup", "❓ Query", "🔍 Analysis"])

with tab1:
    st.header("Repository Setup")
    
    repo_input = st.text_input(
        "Repository",
        placeholder="Enter GitHub URL (e.g., https://github.com/user/repo) or local path",
        help="GitHub repository URL or local directory path"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔨 Build CPG", type="primary", use_container_width=True):
            if not repo_input:
                st.error("Please enter a repository URL or path")
            else:
                project_name = get_project_name_from_repo(repo_input)
                st.session_state.project_name = project_name
                
                # Determine if it's a GitHub URL or local path
                normalized_url = normalize_github_url(repo_input)
                is_github = 'github.com' in normalized_url or repo_input.startswith('http')
                
                # Build CPG
                cpg_dir = Path("data/cpg")
                cpg_dir.mkdir(parents=True, exist_ok=True)
                cpg_path = cpg_dir / f"{project_name}.cpg.bin"
                
                python_cmd = get_python_cmd()
                
                if is_github:
                    # Use --keep-clone to preserve source code for extraction
                    cmd = f'{python_cmd} scripts/build_cpg.py "{normalized_url}" --output "{cpg_path}" --keep-clone'
                else:
                    cmd = f'{python_cmd} scripts/build_cpg.py "{repo_input}" --output "{cpg_path}"'
                
                success, output = run_command(cmd, f"Building CPG for {project_name}...")
                
                if success:
                    st.session_state.cpg_built = True
                    st.session_state.cpg_path = str(cpg_path)
                    st.success(f"✓ CPG built successfully: {cpg_path}")
                    st.session_state.methods_extracted = False
                    st.session_state.methods_indexed = False
                    st.session_state.cpg_json_extracted = False
                    
                    # Automatically extract CPG JSON after building CPG
                    with st.spinner("Extracting CPG nodes and edges..."):
                        python_cmd = get_python_cmd()
                        extract_cmd = f'{python_cmd} scripts/extract_cpg_json.py "{cpg_path}" --output cpg_rag_system/data'
                        extract_success, extract_output = run_command(extract_cmd, "Extracting CPG JSON...")
                        if extract_success:
                            st.session_state.cpg_json_extracted = True
                            st.info("✓ CPG nodes and edges extracted to cpg_rag_system/data/")
                        else:
                            st.warning(f"CPG JSON extraction had issues:\n{extract_output}")
                else:
                    st.error(f"Failed to build CPG:\n{output}")
    
    with col2:
        if st.button("📤 Extract Methods", use_container_width=True):
            if not st.session_state.cpg_built or not st.session_state.cpg_path:
                st.error("Please build CPG first")
            else:
                methods_json = Path("data") / f"methods_{st.session_state.project_name}.json"
                
                python_cmd = get_python_cmd()
                cmd = f'{python_cmd} scripts/extract_methods.py "{st.session_state.cpg_path}" --output "{methods_json}"'
                
                success, output = run_command(cmd, "Extracting methods from CPG...")
                
                if success:
                    st.session_state.methods_extracted = True
                    st.success(f"✓ Methods extracted: {methods_json}")
                    st.session_state.methods_indexed = False
                else:
                    st.error(f"Failed to extract methods:\n{output}")
    
    col3, col4 = st.columns(2)
    
    with col3:
        if st.button("🔍 Index Methods", use_container_width=True):
            if not st.session_state.methods_extracted:
                st.error("Please extract methods first")
            else:
                methods_json = Path("data") / f"methods_{st.session_state.project_name}.json"
                
                python_cmd = get_python_cmd()
                cmd = f'{python_cmd} scripts/index_methods.py "{methods_json}" --project-name "{st.session_state.project_name}" --embedding-model "{embedding_model}"'
                
                success, output = run_command(cmd, "Indexing methods in ChromaDB...")
                
                if success:
                    st.session_state.methods_indexed = True
                    st.success(f"✓ Methods indexed in ChromaDB")
                else:
                    st.error(f"Failed to index methods:\n{output}")
    
    with col4:
        if st.button("🔄 Reset", use_container_width=True):
            # Clean up files before resetting
            project_name = st.session_state.project_name
            cleaned = cleanup_project_files(project_name)
            
            # Reset session state
            st.session_state.cpg_built = False
            st.session_state.methods_extracted = False
            st.session_state.methods_indexed = False
            st.session_state.project_name = None
            st.session_state.cpg_path = None
            
            if cleaned:
                st.info(f"✓ Cleaned up {len(cleaned)} files/directories")
            st.rerun()
    
    # Status display
    st.markdown("---")
    st.subheader("📊 Status")
    
    status_cols = st.columns(4)
    with status_cols[0]:
        st.metric("CPG Built", "✓" if st.session_state.cpg_built else "✗")
    with status_cols[1]:
        st.metric("Methods Extracted", "✓" if st.session_state.methods_extracted else "✗")
    with status_cols[2]:
        st.metric("Methods Indexed", "✓" if st.session_state.methods_indexed else "✗")
    with status_cols[3]:
        if st.session_state.project_name:
            st.metric("Project", st.session_state.project_name)
        else:
            st.metric("Project", "None")

with tab2:
    st.header("Query Codebase")
    st.markdown("**Original Query Feature** - Uses methods.json and ChromaDB for semantic search")
    
    if not st.session_state.methods_indexed:
        st.warning("⚠️ Please complete the setup steps first: Build CPG → Extract Methods → Index Methods")
    else:
        query = st.text_area(
            "Enter your question",
            placeholder="e.g., What are the main algorithms used in this code?",
            height=100
        )
        
        if st.button("🚀 Generate Answer", type="primary", use_container_width=True):
            if not query:
                st.error("Please enter a question")
            else:
                python_cmd = get_python_cmd()
                cmd = (
                    f'{python_cmd} scripts/query.py '
                    f'--question "{query}" '
                    f'--project-name "{st.session_state.project_name}" '
                    f'--cpg-path "{st.session_state.cpg_path}" '
                    f'--device {device} '
                    f'--top-k {top_k} '
                    f'--llm-model "{llm_model}" '
                    f'--embedding-model "{embedding_model}"'
                )
                
                # Show spinner while processing (progress goes to terminal)
                with st.spinner("Generating answer... (check your terminal for progress)"):
                    try:
                        # Create a class that writes to both terminal and buffer
                        class TeeOutput:
                            def __init__(self):
                                self.buffer = []
                            
                            def write(self, text):
                                # Write to terminal (stdout)
                                sys.stdout.write(text)
                                sys.stdout.flush()
                                # Also buffer for answer extraction
                                self.buffer.append(text)
                            
                            def flush(self):
                                sys.stdout.flush()
                            
                            def get_output(self):
                                return ''.join(self.buffer)
                        
                        # Save original stdout
                        original_stdout = sys.stdout
                        tee = TeeOutput()
                        
                        # Run command - output goes to terminal AND buffer
                        process = subprocess.Popen(
                            cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        
                        # Stream to terminal and collect for answer extraction
                        output_lines = []
                        for line in process.stdout:
                            # Print to terminal (where Streamlit is running)
                            print(line, end='', file=sys.stdout, flush=True)
                            output_lines.append(line)
                        
                        process.wait()
                        output = "".join(output_lines)
                        
                        if process.returncode == 0:
                            # Extract answer from output
                            if "ANSWER" in output:
                                answer_start = output.find("ANSWER")
                                answer_section = output[answer_start:]
                                # Remove the header
                                lines = answer_section.split('\n')
                                answer_lines = []
                                in_answer = False
                                for line in lines:
                                    if "=" * 80 in line and in_answer:
                                        break
                                    if in_answer and line.strip():
                                        answer_lines.append(line)
                                    if "=" * 80 in line and "ANSWER" in output[output.find("ANSWER"):output.find("ANSWER")+200]:
                                        in_answer = True
                                
                                answer = '\n'.join(answer_lines).strip()
                                if not answer:
                                    answer = output.split("ANSWER")[-1].strip() if "ANSWER" in output else output
                            else:
                                answer = output
                            
                            st.markdown("### Answer")
                            st.markdown(answer)
                            
                            # Show full output in expander (optional)
                            with st.expander("📋 Full Output"):
                                st.text(output)
                        else:
                            st.error(f"Query failed with return code {process.returncode}")
                            st.code(output, language="text")
                    except subprocess.TimeoutExpired:
                        st.error("Query timed out after 10 minutes")
                    except Exception as e:
                        st.error(f"Error running query: {str(e)}")

with tab3:
    st.header("Code Analysis")
    st.markdown("**New Analysis Features** - Uses CPG nodes/edges JSON from `cpg_rag_system/data/`")
    
    # Check if CPG JSON exists
    nodes_json = Path("cpg_rag_system/data/cpg_nodes.json")
    edges_json = Path("cpg_rag_system/data/cpg_edges.json")
    
    if not nodes_json.exists():
        st.warning("⚠️ CPG nodes JSON not found. Please build CPG first (extraction happens automatically) or extract manually:")
        st.code("python scripts/extract_cpg_json.py data/cpg/<project>.cpg.bin")
    else:
        analysis_type = st.radio(
            "Select Analysis Type",
            ["Fault Detection", "Sensitive Data Tracking", "Code Understanding"],
            horizontal=True
        )
        
        if analysis_type == "Fault Detection":
            st.subheader("🔍 Fault Detection")
            st.markdown("Detects security vulnerabilities, missing error handling, resource leaks, and code quality issues.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                security_only = st.checkbox("Security issues only", value=False)
            
            with col2:
                export_format = st.selectbox(
                    "Export Format",
                    ["console", "json", "markdown", "html"],
                    index=0
                )
            
            if st.button("🔍 Run Fault Detection", type="primary", use_container_width=True):
                python_cmd = get_python_cmd()
                
                cmd = f'{python_cmd} scripts/run_fault_detection.py --nodes-json "{nodes_json}" --format {export_format}'
                if security_only:
                    cmd += " --security"
                else:
                    cmd += " --all"
                
                with st.spinner("Running fault detection... (check your terminal for progress)"):
                    try:
                        process = subprocess.Popen(
                            cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        
                        output_lines = []
                        for line in process.stdout:
                            print(line, end='', flush=True)
                            output_lines.append(line)
                        
                        process.wait()
                        output = "".join(output_lines)
                        
                        if process.returncode == 0:
                            # Try to parse JSON output if format is json
                            if export_format == "json":
                                try:
                                    import json
                                    result = json.loads(output)
                                    st.success(f"✅ Found {result.get('total_issues', 0)} issues across {len(result.get('findings', []))} methods")
                                    
                                    # Group by severity
                                    severity_counts = {}
                                    for finding in result.get('findings', []):
                                        severity = finding.get('severity', 'UNKNOWN')
                                        severity_counts[severity] = severity_counts.get(severity, 0) + len(finding.get('issues', []))
                                    
                                    if severity_counts:
                                        st.markdown("### Issues by Severity")
                                        for severity, count in sorted(severity_counts.items(), reverse=True):
                                            st.metric(severity.replace("Severity.", ""), count)
                                    
                                    with st.expander("📋 View Full Report (JSON)"):
                                        st.json(result)
                                except json.JSONDecodeError:
                                    st.text(output)
                            else:
                                st.markdown("### Analysis Results")
                                st.text(output)
                                
                                with st.expander("📋 Full Output"):
                                    st.text(output)
                        else:
                            st.error(f"Fault detection failed with return code {process.returncode}")
                            st.code(output, language="text")
                    except Exception as e:
                        st.error(f"Error running fault detection: {str(e)}")
        
        elif analysis_type == "Sensitive Data Tracking":
            st.subheader("🔐 Sensitive Data Tracking")
            st.markdown("Tracks sensitive data flows (passwords, API keys, tokens, PII) through the codebase.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                track_type = st.text_input(
                    "Track Specific Type (optional)",
                    placeholder="e.g., password, api_key, token",
                    help="Leave empty to track all sensitive data"
                )
            
            with col2:
                export_format = st.selectbox(
                    "Export Format",
                    ["console", "json", "markdown", "html"],
                    index=0
                )
            
            if st.button("🔐 Run Sensitive Data Tracking", type="primary", use_container_width=True):
                python_cmd = get_python_cmd()
                
                cmd = f'{python_cmd} scripts/run_sensitive_data_tracking.py --nodes-json "{nodes_json}" --edges-json "{edges_json}" --format {export_format}'
                if track_type:
                    cmd += f' --track {track_type}'
                else:
                    cmd += " --all"
                
                with st.spinner("Running sensitive data tracking... (check your terminal for progress)"):
                    try:
                        process = subprocess.Popen(
                            cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        
                        output_lines = []
                        for line in process.stdout:
                            print(line, end='', flush=True)
                            output_lines.append(line)
                        
                        process.wait()
                        output = "".join(output_lines)
                        
                        if process.returncode == 0:
                            # Try to parse JSON output if format is json
                            if export_format == "json":
                                try:
                                    import json
                                    result = json.loads(output)
                                    summary = result.get('summary', {})
                                    st.success(
                                        f"✅ Analyzed {summary.get('total_functions', 0)} functions. "
                                        f"Found {summary.get('functions_with_sensitive_data', 0)} with sensitive data. "
                                        f"{summary.get('total_violations', 0)} violations detected."
                                    )
                                    
                                    if summary.get('total_violations', 0) > 0:
                                        st.warning("⚠️ Violations found! Review the report below.")
                                    
                                    with st.expander("📋 View Full Report (JSON)"):
                                        st.json(result)
                                except json.JSONDecodeError:
                                    st.text(output)
                            else:
                                st.markdown("### Analysis Results")
                                st.text(output)
                                
                                with st.expander("📋 Full Output"):
                                    st.text(output)
                        else:
                            st.error(f"Sensitive data tracking failed with return code {process.returncode}")
                            st.code(output, language="text")
                    except Exception as e:
                        st.error(f"Error running sensitive data tracking: {str(e)}")
        
        elif analysis_type == "Code Understanding":
            st.subheader("📚 Code Understanding")
            st.markdown("Generates comprehensive overview of codebase structure, architecture, and entry points.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                understand_mode = st.radio(
                    "Understanding Mode",
                    ["Overview", "Architecture", "Entry Points"],
                    horizontal=False
                )
            
            with col2:
                export_format = st.selectbox(
                    "Export Format",
                    ["console", "markdown"],
                    index=0
                )
            
            if st.button("📚 Generate Understanding", type="primary", use_container_width=True):
                python_cmd = get_python_cmd()
                
                cmd = f'{python_cmd} scripts/run_code_understanding.py --nodes-json "{nodes_json}" --edges-json "{edges_json}" --format {export_format}'
                
                if understand_mode == "Architecture":
                    cmd += " --architecture"
                elif understand_mode == "Entry Points":
                    cmd += " --entry-points"
                else:
                    cmd += " --overview"
                
                with st.spinner("Generating code understanding... (check your terminal for progress)"):
                    try:
                        process = subprocess.Popen(
                            cmd,
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True
                        )
                        
                        output_lines = []
                        for line in process.stdout:
                            print(line, end='', flush=True)
                            output_lines.append(line)
                        
                        process.wait()
                        output = "".join(output_lines)
                        
                        if process.returncode == 0:
                            st.markdown("### Analysis Results")
                            
                            # If markdown format, render as markdown
                            if export_format == "markdown":
                                st.markdown(output)
                            else:
                                # For console output, show as text
                                st.text(output)
                            
                            with st.expander("📋 Full Output"):
                                st.text(output)
                        else:
                            st.error(f"Code understanding failed with return code {process.returncode}")
                            st.code(output, language="text")
                    except Exception as e:
                        st.error(f"Error running code understanding: {str(e)}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: gray;'>
    <p>GraphRAG Code Analyzer | Built with Joern, ChromaDB, and Open-Source LLMs</p>
    </div>
    """,
    unsafe_allow_html=True
)

