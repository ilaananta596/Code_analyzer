#!/usr/bin/env python3
"""
CPG RAG System - Environment Setup Script

This script sets up the complete environment for the CPG RAG system including:
- Python dependencies
- Ollama installation and model downloads
- Neo4j Docker container
- Directory structure
- Configuration files

Usage:
    python setup_environment.py --full       # Complete setup
    python setup_environment.py --python     # Only Python dependencies
    python setup_environment.py --ollama     # Only Ollama setup
    python setup_environment.py --neo4j      # Only Neo4j setup
"""

import os
import sys
import subprocess
import platform
import argparse
from pathlib import Path
from typing import List, Tuple


class EnvironmentSetup:
    """Handles complete environment setup for CPG RAG system."""
    
    def __init__(self):
        self.system = platform.system()
        self.python_version = sys.version_info
        self.setup_dir = Path.cwd()
        
    def print_header(self, message: str):
        """Print formatted header."""
        print("\n" + "=" * 70)
        print(f"🚀 {message}")
        print("=" * 70 + "\n")
    
    def print_step(self, step: int, message: str):
        """Print formatted step."""
        print(f"\n📌 Step {step}: {message}")
        print("-" * 70)
    
    def run_command(self, command: List[str], check: bool = True) -> Tuple[bool, str]:
        """Run shell command and return success status."""
        try:
            result = subprocess.run(
                command,
                check=check,
                capture_output=True,
                text=True
            )
            return True, result.stdout
        except subprocess.CalledProcessError as e:
            return False, e.stderr
    
    def check_python_version(self) -> bool:
        """Check if Python version is compatible."""
        self.print_step(1, "Checking Python version")
        
        if self.python_version < (3, 8):
            print("❌ Python 3.8+ required")
            print(f"   Current version: {sys.version}")
            return False
        
        print(f"✅ Python {self.python_version.major}.{self.python_version.minor}.{self.python_version.micro}")
        return True
    
    def create_directory_structure(self):
        """Create necessary directories."""
        self.print_step(2, "Creating directory structure")
        
        directories = [
            'data',           # For CPG files
            'reports',        # For exported reports
            'logs',           # For application logs
            'chroma_db',      # For vector stores
            'models',         # For downloaded models
        ]
        
        for dir_name in directories:
            dir_path = self.setup_dir / dir_name
            dir_path.mkdir(exist_ok=True)
            print(f"✅ Created: {dir_path}")
    
    def install_python_dependencies(self):
        """Install Python dependencies."""
        self.print_step(3, "Installing Python dependencies")
        
        # Create requirements.txt
        requirements = """
# Core dependencies
langchain==0.1.0
langchain-community==0.0.13
chromadb==0.4.22
neo4j==5.14.0
python-dotenv==1.0.0

# Ollama
ollama==0.1.6

# Data processing
numpy==1.24.3
pandas==2.1.0
tqdm==4.66.1

# File handling
openpyxl==3.1.2
python-docx==1.1.0
pypdf2==3.0.1

# Web and API
requests==2.31.0
fastapi==0.104.1
uvicorn==0.24.0

# Utilities
pyyaml==6.0.1
click==8.1.7
rich==13.7.0
""".strip()
        
        requirements_file = self.setup_dir / 'requirements.txt'
        with open(requirements_file, 'w') as f:
            f.write(requirements)
        
        print(f"✅ Created requirements.txt")
        
        # Install
        print("\n📦 Installing packages...")
        success, output = self.run_command([
            sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt',
            '--break-system-packages'
        ])
        
        if success:
            print("✅ Python dependencies installed")
        else:
            print(f"⚠️  Some packages may have failed: {output}")
    
    def install_ollama(self):
        """Install Ollama."""
        self.print_step(4, "Installing Ollama")
        
        if self.system == "Linux":
            print("🐧 Installing Ollama for Linux...")
            success, _ = self.run_command([
                'curl', '-fsSL', 'https://ollama.com/install.sh'
            ], check=False)
            
            if success:
                self.run_command(['sh', '-'])
        
        elif self.system == "Darwin":  # macOS
            print("🍎 Installing Ollama for macOS...")
            print("Please download from: https://ollama.com/download/mac")
            print("Or use: brew install ollama")
        
        elif self.system == "Windows":
            print("🪟 Installing Ollama for Windows...")
            print("Please download from: https://ollama.com/download/windows")
        
        print("\n✅ Ollama installation initiated")
    
    def download_ollama_models(self):
        """Download required Ollama models."""
        self.print_step(5, "Downloading Ollama models")
        
        models = [
            ('llama3.2', '~3.7 GB'),
            ('nomic-embed-text', '~274 MB')
        ]
        
        # Start Ollama service
        print("🚀 Starting Ollama service...")
        subprocess.Popen(['ollama', 'serve'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        import time
        time.sleep(3)  # Wait for service to start
        
        for model, size in models:
            print(f"\n📥 Downloading {model} ({size})...")
            success, _ = self.run_command(['ollama', 'pull', model])
            
            if success:
                print(f"✅ {model} downloaded")
            else:
                print(f"⚠️  Failed to download {model}")
    
    def setup_neo4j(self):
        """Set up Neo4j Docker container."""
        self.print_step(6, "Setting up Neo4j")
        
        # Check if Docker is installed
        success, _ = self.run_command(['docker', '--version'], check=False)
        if not success:
            print("❌ Docker not found. Please install Docker first.")
            print("   Download from: https://www.docker.com/get-started")
            return
        
        # Check if container already exists
        success, output = self.run_command(
            ['docker', 'ps', '-a', '--filter', 'name=neo4j', '--format', '{{.Names}}'],
            check=False
        )
        
        if 'neo4j' in output:
            print("📦 Neo4j container already exists. Starting...")
            self.run_command(['docker', 'start', 'neo4j'])
        else:
            print("📦 Creating Neo4j container...")
            self.run_command([
                'docker', 'run', '-d',
                '--name', 'neo4j',
                '-p', '7474:7474',
                '-p', '7687:7687',
                '-e', 'NEO4J_AUTH=neo4j/cpgragagent123',
                'neo4j:latest'
            ])
        
        print("✅ Neo4j running at http://localhost:7474")
        print("   Username: neo4j")
        print("   Password: cpgragagent123")
    
    def create_env_file(self):
        """Create .env configuration file."""
        self.print_step(7, "Creating configuration file")
        
        env_content = """# CPG RAG System Configuration

# Ollama Settings
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Neo4j Settings
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=cpgragagent123

# Vector Store Settings
CHROMA_PERSIST_DIR=./chroma_db
SEMANTIC_COLLECTION=production_semantic
STRUCTURAL_COLLECTION=production_structural
FAULT_COLLECTION=production_fault

# Analysis Settings
DEFAULT_TOP_K=5
GRAPH_CONTEXT_DEPTH=2
CRITICAL_COMPLEXITY_THRESHOLD=15

# Export Settings
EXPORT_DIRECTORY=./reports
INCLUDE_TIMESTAMP=true
""".strip()
        
        env_file = self.setup_dir / '.env'
        with open(env_file, 'w') as f:
            f.write(env_content)
        
        print(f"✅ Created .env file")
    
    def verify_setup(self):
        """Verify all components are working."""
        self.print_step(8, "Verifying setup")
        
        checks = []
        
        # Check Python packages
        try:
            import langchain
            import chromadb
            import neo4j
            checks.append(("Python packages", True))
        except ImportError as e:
            checks.append(("Python packages", False))
        
        # Check Ollama
        success, _ = self.run_command(['ollama', 'list'], check=False)
        checks.append(("Ollama", success))
        
        # Check Neo4j
        success, _ = self.run_command(
            ['docker', 'ps', '--filter', 'name=neo4j', '--format', '{{.Status}}'],
            check=False
        )
        checks.append(("Neo4j", 'Up' in str(success)))
        
        # Print results
        print("\n📊 Setup Verification:")
        for component, status in checks:
            icon = "✅" if status else "❌"
            print(f"  {icon} {component}")
    
    def run_full_setup(self):
        """Run complete setup."""
        self.print_header("CPG RAG System - Complete Setup")
        
        if not self.check_python_version():
            return
        
        self.create_directory_structure()
        self.install_python_dependencies()
        self.install_ollama()
        self.download_ollama_models()
        self.setup_neo4j()
        self.create_env_file()
        self.verify_setup()
        
        self.print_header("Setup Complete! 🎉")
        print("""
Next steps:
1. Place your CPG files (cpg_nodes.json, cpg_edges.json) in ./data/
2. Place your source code in ./data/[YourProject]/
3. Run: python main.py --help
        """)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Setup CPG RAG System environment')
    parser.add_argument('--full', action='store_true', help='Complete setup')
    parser.add_argument('--python', action='store_true', help='Python dependencies only')
    parser.add_argument('--ollama', action='store_true', help='Ollama setup only')
    parser.add_argument('--neo4j', action='store_true', help='Neo4j setup only')
    
    args = parser.parse_args()
    
    setup = EnvironmentSetup()
    
    if args.full or not any([args.python, args.ollama, args.neo4j]):
        setup.run_full_setup()
    else:
        if args.python:
            setup.check_python_version()
            setup.create_directory_structure()
            setup.install_python_dependencies()
        
        if args.ollama:
            setup.install_ollama()
            setup.download_ollama_models()
        
        if args.neo4j:
            setup.setup_neo4j()


if __name__ == '__main__':
    main()
