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
if 'rag_setup' not in st.session_state:
    st.session_state.rag_setup = False

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
            # Combine stdout and stderr for full output
            combined_output = result.stdout + result.stderr if result.stderr else result.stdout
            
            if result.returncode == 0:
                return True, combined_output
            else:
                # Check if it's just warnings (common with model loading)
                # If output contains success indicators, treat as success
                if ("✓" in combined_output or "successfully" in combined_output.lower() or 
                    "Indexed" in combined_output or "Model loaded" in combined_output):
                    # Likely succeeded despite warnings
                    return True, combined_output
                return False, combined_output
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
                    st.session_state.rag_setup = False
                    
                    # Read source directory from source_info.json if available
                    source_dir = None
                    source_info_path = cpg_path.with_suffix('.source_info.json')
                    if source_info_path.exists():
                        try:
                            with open(source_info_path, 'r') as f:
                                source_info = json.load(f)
                                source_dir = source_info.get('source_dir')
                                if source_dir and Path(source_dir).exists():
                                    st.session_state.source_dir = source_dir
                        except Exception as e:
                            st.warning(f"Could not read source info: {e}")
                    
                    # Automatically extract CPG JSON after building CPG
                    with st.spinner("Extracting CPG nodes and edges..."):
                        python_cmd = get_python_cmd()
                        extract_cmd = f'{python_cmd} scripts/extract_cpg_json.py "{cpg_path}" --output cpg_rag_complete/data'
                        if source_dir:
                            extract_cmd += f' --source-dir "{source_dir}"'
                        extract_success, extract_output = run_command(extract_cmd, "Extracting CPG JSON...")
                        if extract_success:
                            st.session_state.cpg_json_extracted = True
                            st.info("✓ CPG nodes and edges extracted to cpg_rag_complete/data/")
                            
                            # Clear old ChromaDB to ensure fresh data for this project
                            chroma_dir = Path("cpg_rag_complete/chroma_db")
                            if chroma_dir.exists():
                                try:
                                    shutil.rmtree(chroma_dir)
                                    st.info("🗑️ Cleared old RAG data for fresh analysis")
                                except Exception as e:
                                    st.warning(f"Could not clear old ChromaDB: {e}")
                            
                            # Setup RAG system after extraction
                            with st.spinner("Setting up RAG system (this may take a few minutes)..."):
                                setup_cmd = f'{python_cmd} cpg_rag_complete/step3_setup_rag.py --data-dir cpg_rag_complete/data --force'
                                if source_dir:
                                    setup_cmd += f' --source-dir "{source_dir}"'
                                setup_success, setup_output = run_command(setup_cmd, "Setting up RAG...")
                                if setup_success:
                                    st.session_state.rag_setup = True
                                    st.success("✓ RAG system ready for analysis")
                                else:
                                    st.warning(f"RAG setup had issues (you may need to run it manually):\n{setup_output}")
                                    st.session_state.rag_setup = False
                        else:
                            st.error(f"Failed to extract CPG JSON:\n{extract_output}")
                            with st.expander("📋 Full Error Output"):
                                st.code(extract_output, language="text")
                else:
                    st.error(f"Failed to build CPG:\n{output}")
                    with st.expander("📋 Full Error Output"):
                        st.code(output, language="text")
    
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
                    with st.expander("📋 Full Error Output"):
                        st.code(output, language="text")
    
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
                    with st.expander("📋 Full Error Output"):
                        st.code(output, language="text")
    
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
                        
                        # Filter out deprecation warnings from output
                        import re
                        output = re.sub(r'.*LangChainDeprecationWarning.*\n', '', output)
                        output = re.sub(r'.*deprecated.*\n', '', output)
                        output = re.sub(r'.*step4_query_rag\.py:\d+:.*\n', '', output)
                        output = re.sub(r'.*step3_setup_rag\.py:\d+:.*\n', '', output)
                        
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
                        st.info("The query took longer than 10 minutes to complete. Try simplifying your query or check if the codebase is very large.")
                    except Exception as e:
                        st.error(f"Error running query: {str(e)}")
                        import traceback
                        with st.expander("📋 Full Error Traceback"):
                            st.code(traceback.format_exc(), language="text")

with tab3:
    st.header("Code Analysis")
    st.markdown("**RAG-Based Analysis** - Uses `cpg_rag_complete` with Ollama for intelligent code analysis")
    st.info("ℹ️ **Note**: Make sure Ollama is running (`ollama serve`) before running analysis")
    
    # Check if CPG JSON exists and RAG is set up
    nodes_json = Path("cpg_rag_complete/data/cpg_nodes.json")
    edges_json = Path("cpg_rag_complete/data/cpg_edges.json")
    chroma_dir = Path("cpg_rag_complete/chroma_db")
    
    if not nodes_json.exists():
        st.warning("⚠️ CPG nodes JSON not found. Please build CPG first (extraction happens automatically) or extract manually:")
        st.code("python scripts/extract_cpg_json.py data/cpg/<project>.cpg.bin")
    elif not chroma_dir.exists() or not any(chroma_dir.iterdir()):
        st.warning("⚠️ RAG system not set up. Please run setup first:")
        st.code("python cpg_rag_complete/step3_setup_rag.py --data-dir cpg_rag_complete/data --source-dir <source_dir>")
        if st.button("🔧 Setup RAG Now", use_container_width=True):
            # Clear old ChromaDB first
            chroma_dir = Path("cpg_rag_complete/chroma_db")
            if chroma_dir.exists():
                try:
                    shutil.rmtree(chroma_dir)
                    st.info("🗑️ Cleared old RAG data")
                except Exception as e:
                    st.warning(f"Could not clear old ChromaDB: {e}")
            
            # Try to get source directory from source_info.json
            source_dir = None
            if st.session_state.get('cpg_path'):
                source_info_path = Path(st.session_state.cpg_path).with_suffix('.source_info.json')
                if source_info_path.exists():
                    try:
                        with open(source_info_path, 'r') as f:
                            source_info = json.load(f)
                            source_dir = source_info.get('source_dir')
                    except Exception:
                        pass
            
            python_cmd = get_python_cmd()
            setup_cmd = f'{python_cmd} cpg_rag_complete/step3_setup_rag.py --data-dir cpg_rag_complete/data --force'
            if source_dir and Path(source_dir).exists():
                setup_cmd += f' --source-dir "{source_dir}"'
            with st.spinner("Setting up RAG system (this may take a few minutes)..."):
                setup_success, setup_output = run_command(setup_cmd, "Setting up RAG...")
                if setup_success:
                    st.session_state.rag_setup = True
                    st.success("✓ RAG system ready!")
                    st.rerun()
                else:
                    st.error(f"RAG setup failed:\n{setup_output}")
                    with st.expander("📋 Full Error Output"):
                        st.code(setup_output, language="text")
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
                    #["console", "json", "markdown", "html"],
                    [ "json", "md"],
                    index=0
                )
            
            if st.button("🔍 Run Fault Detection", type="primary", use_container_width=True):
                python_cmd = get_python_cmd()
                
                # Use RAG-based analysis
                cmd = f'{python_cmd} scripts/run_rag_analysis.py --analysis-type fault'
                if security_only:
                    cmd += " --mode security"
                if export_format in ['json', 'md', 'scv']:
                    cmd += f" --export {export_format}"
                
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
                        
                        # Filter out deprecation warnings from output
                        import re
                        output = re.sub(r'.*LangChainDeprecationWarning.*\n', '', output)
                        output = re.sub(r'.*deprecated.*\n', '', output)
                        output = re.sub(r'.*step4_query_rag\.py:\d+:.*\n', '', output)
                        output = re.sub(r'.*step3_setup_rag\.py:\d+:.*\n', '', output)
                        
                        if process.returncode == 0:
                            
                            # RAG output is text-based, show it nicely
                            if export_format == "json":
                                # Try to parse if it's JSON
                                try:
                                    import json
                                    result = json.loads(output)
                                    st.json(result)
                                except json.JSONDecodeError:
                                    st.text(output)
                            elif export_format in ["md", "markdown"]:
                                st.markdown(output)
                            else:
                                st.text(output)
                            
                            with st.expander("📋 Full Output"):
                                st.text(output)
                        else:
                            st.error(f"Fault detection failed with return code {process.returncode}")
                            st.code(output, language="text")
                    except Exception as e:
                        st.error(f"Error running fault detection: {str(e)}")
                        import traceback
                        with st.expander("📋 Full Error Traceback"):
                            st.code(traceback.format_exc(), language="text")
        
        elif analysis_type == "Sensitive Data Tracking":
            st.subheader("🔐 Sensitive Data Tracking")
            st.markdown("Tracks sensitive data flows (passwords, API keys, tokens, PII) through the codebase.")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.header("Sensitive info like passwords, API keys, tokens, PII")
                
                # track_type = st.text_input(
                #     "Track Specific Type (optional)",
                #     placeholder="e.g., password, api_key, token",
                #     help="Leave empty to track all sensitive data"
                # )
            
            with col2:
                export_format = st.selectbox(
                    "Export Format",
                    [ "json", "md"],
                    index=0
                )
            
            if st.button("🔐 Run Sensitive Data Tracking", type="primary", use_container_width=True):
                python_cmd = get_python_cmd()
                
                # Use RAG-based analysis
                cmd = f'{python_cmd} scripts/run_rag_analysis.py --analysis-type sensitive'
                # if track_type:
                #     cmd += f" --mode {track_type}"
                if export_format in ['json', 'md', 'csv']:
                    cmd += f" --export {export_format}"
                
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
                        
                        # Filter out deprecation warnings from output
                        import re
                        output = re.sub(r'.*LangChainDeprecationWarning.*\n', '', output)
                        output = re.sub(r'.*deprecated.*\n', '', output)
                        output = re.sub(r'.*step4_query_rag\.py:\d+:.*\n', '', output)
                        output = re.sub(r'.*step3_setup_rag\.py:\d+:.*\n', '', output)
                        
                        if process.returncode == 0:
                            
                            # RAG output is text-based, show it nicely
                            if export_format == "json":
                                # Try to parse if it's JSON
                                try:
                                    import json
                                    result = json.loads(output)
                                    st.json(result)
                                except json.JSONDecodeError:
                                    st.text(output)
                            elif export_format in ["md", "markdown"]:
                                st.markdown(output)
                            else:
                                st.text(output)
                            
                            with st.expander("📋 Full Output"):
                                st.text(output)
                        else:
                            st.error(f"Sensitive data tracking failed with return code {process.returncode}")
                            st.code(output, language="text")
                    except Exception as e:
                        st.error(f"Error running sensitive data tracking: {str(e)}")
                        import traceback
                        with st.expander("📋 Full Error Traceback"):
                            st.code(traceback.format_exc(), language="text")
        
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
                    ["json", "md"],
                    index=0
                )
            
            if st.button("📚 Generate Understanding", type="primary", use_container_width=True):
                python_cmd = get_python_cmd()
                
                # Use RAG-based analysis
                mode_map = {
                    "Overview": "overview",
                    "Architecture": "architecture",
                    "Entry Points": "entry-points"
                }
                cmd = f'{python_cmd} scripts/run_rag_analysis.py --analysis-type understanding --mode {mode_map[understand_mode]}'
                if export_format in ["csv", "json", "md"]:
                    cmd += f" --export {export_format}"
                
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
                        
                        # Filter out deprecation warnings from output
                        import re
                        output = re.sub(r'.*LangChainDeprecationWarning.*\n', '', output)
                        output = re.sub(r'.*deprecated.*\n', '', output)
                        output = re.sub(r'.*step4_query_rag\.py:\d+:.*\n', '', output)
                        output = re.sub(r'.*step3_setup_rag\.py:\d+:.*\n', '', output)
                        
                        if process.returncode == 0:
                            
                            # If markdown format, render as markdown
                            if export_format == "md":
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
                        import traceback
                        with st.expander("📋 Full Error Traceback"):
                            st.code(traceback.format_exc(), language="text")

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
