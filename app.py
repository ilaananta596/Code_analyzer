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
tab1, tab2 = st.tabs(["📥 Setup", "❓ Query"])

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
                    cmd = f'{python_cmd} scripts/build_cpg.py "{normalized_url}" --output "{cpg_path}"'
                else:
                    cmd = f'{python_cmd} scripts/build_cpg.py "{repo_input}" --output "{cpg_path}"'
                
                success, output = run_command(cmd, f"Building CPG for {project_name}...")
                
                if success:
                    st.session_state.cpg_built = True
                    st.session_state.cpg_path = str(cpg_path)
                    st.success(f"✓ CPG built successfully: {cpg_path}")
                    st.session_state.methods_extracted = False
                    st.session_state.methods_indexed = False
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
            st.session_state.cpg_built = False
            st.session_state.methods_extracted = False
            st.session_state.methods_indexed = False
            st.session_state.project_name = None
            st.session_state.cpg_path = None
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
                
                # Create a placeholder for progress output
                progress_placeholder = st.empty()
                output_lines = []
                
                # Stream output in real-time
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
                    
                    # Read output line by line
                    for line in process.stdout:
                        output_lines.append(line)
                        # Update progress display
                        progress_text = "".join(output_lines[-20:])  # Show last 20 lines
                        with progress_placeholder.container():
                            st.code(progress_text, language="text")
                    
                    process.wait()
                    output = "".join(output_lines)
                    
                    if process.returncode == 0:
                        # Extract answer from output
                        
                        # Try to find the answer section
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
                        
                        # Show full output in expander
                        with st.expander("📋 Full Output"):
                            st.text(output)
                    else:
                        st.error(f"Query failed with return code {process.returncode}")
                        st.code(output, language="text")
                except subprocess.TimeoutExpired:
                    if 'process' in locals():
                        process.kill()
                    st.error("Query timed out after 10 minutes")
                except Exception as e:
                    st.error(f"Error running query: {str(e)}")

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

