"""
Central Configuration for CPG RAG System

This module provides centralized configuration management for all components.
Modify settings here to customize system behavior.
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class ResponseFormat(Enum):
    """Response formatting options."""
    BRIEF = "brief"
    DETAILED = "detailed"
    TECHNICAL = "technical"


class Severity(Enum):
    """Issue severity levels."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class SystemConfig:
    """
    Central configuration for the entire CPG RAG system.
    
    Modify these values to customize system behavior without changing code.
    All settings can also be overridden via environment variables.
    """
    
    # =====================================================================
    # DATA SOURCES
    # =====================================================================
    cpg_nodes_file: str = field(default='data/cpg_nodes.json')
    cpg_edges_file: str = field(default='data/cpg_edges.json')
    source_dir: str = field(default='data/MedSAM')
    
    # =====================================================================
    # OLLAMA SETTINGS
    # =====================================================================
    ollama_base_url: str = field(default='http://localhost:11434')
    ollama_model: str = field(default='llama3.2')
    ollama_embedding_model: str = field(default='nomic-embed-text')
    ollama_temperature: float = field(default=0.0)  # 0=deterministic, 1=creative
    
    # =====================================================================
    # NEO4J SETTINGS
    # =====================================================================
    neo4j_uri: str = field(default='bolt://localhost:7687')
    neo4j_user: str = field(default='neo4j')
    neo4j_password: str = field(default='cpgragagent123')
    
    # =====================================================================
    # VECTOR STORE SETTINGS
    # =====================================================================
    chroma_persist_dir: str = field(default='./chroma_db')
    semantic_collection: str = field(default='prod_semantic')
    structural_collection: str = field(default='prod_structural')
    fault_collection: str = field(default='prod_fault')
    sensitive_data_collection: str = field(default='prod_sensitive_data')
    
    # =====================================================================
    # ANALYSIS SETTINGS
    # =====================================================================
    top_k_results: int = field(default=5)
    graph_context_depth: int = field(default=2)
    max_context_nodes: int = field(default=10)
    
    # =====================================================================
    # RESPONSE SETTINGS
    # =====================================================================
    default_response_format: ResponseFormat = field(default=ResponseFormat.DETAILED)
    max_response_length: int = field(default=500)  # words
    include_code_snippets: bool = field(default=True)
    max_code_snippet_lines: int = field(default=20)
    show_severity_levels: bool = field(default=True)
    
    # =====================================================================
    # FAULT DETECTION THRESHOLDS
    # =====================================================================
    critical_complexity: int = field(default=15)
    high_coupling_threshold: int = field(default=10)
    max_function_length: int = field(default=100)
    
    # =====================================================================
    # SENSITIVE DATA TRACKING
    # =====================================================================
    sensitive_data_patterns: list = field(default_factory=lambda: [
        'password', 'api_key', 'secret', 'token', 'credential',
        'ssn', 'credit_card', 'email', 'phone', 'address'
    ])
    sanitization_functions: list = field(default_factory=lambda: [
        'hash', 'encrypt', 'sanitize', 'mask', 'redact'
    ])
    
    # =====================================================================
    # OUTPUT SETTINGS
    # =====================================================================
    export_format: str = field(default='markdown')
    export_directory: str = field(default='./reports')
    include_timestamp: bool = field(default=True)
    log_directory: str = field(default='./logs')
    
    # =====================================================================
    # PERFORMANCE SETTINGS
    # =====================================================================
    batch_size: int = field(default=1000)
    enable_caching: bool = field(default=True)
    cache_ttl: int = field(default=3600)  # seconds
    
    def __post_init__(self):
        """Load from environment variables if available."""
        load_dotenv()
        
        # Override with environment variables
        env_mappings = {
            'OLLAMA_BASE_URL': 'ollama_base_url',
            'OLLAMA_MODEL': 'ollama_model',
            'OLLAMA_EMBEDDING_MODEL': 'ollama_embedding_model',
            'NEO4J_URI': 'neo4j_uri',
            'NEO4J_USER': 'neo4j_user',
            'NEO4J_PASSWORD': 'neo4j_password',
            'CHROMA_PERSIST_DIR': 'chroma_persist_dir',
            'DEFAULT_TOP_K': ('top_k_results', int),
            'GRAPH_CONTEXT_DEPTH': ('graph_context_depth', int),
            'CRITICAL_COMPLEXITY_THRESHOLD': ('critical_complexity', int),
            'EXPORT_DIRECTORY': 'export_directory',
        }
        
        for env_var, attr in env_mappings.items():
            value = os.getenv(env_var)
            if value:
                if isinstance(attr, tuple):
                    attr_name, converter = attr
                    setattr(self, attr_name, converter(value))
                else:
                    setattr(self, attr, value)
    
    def validate(self) -> bool:
        """Validate configuration."""
        errors = []
        
        # Check file paths
        if not Path(self.cpg_nodes_file).exists():
            errors.append(f"CPG nodes file not found: {self.cpg_nodes_file}")
        
        if not Path(self.cpg_edges_file).exists():
            errors.append(f"CPG edges file not found: {self.cpg_edges_file}")
        
        if not Path(self.source_dir).exists():
            errors.append(f"Source directory not found: {self.source_dir}")
        
        # Check numeric ranges
        if self.top_k_results < 1:
            errors.append("top_k_results must be >= 1")
        
        if self.graph_context_depth < 1:
            errors.append("graph_context_depth must be >= 1")
        
        if errors:
            for error in errors:
                print(f"{error}")
            return False
        
        return True
    
    def to_dict(self) -> dict:
        """Convert config to dictionary."""
        return {
            k: v.value if isinstance(v, Enum) else v
            for k, v in self.__dict__.items()
        }
    
    def save(self, filepath: str = '.env'):
        """Save configuration to .env file."""
        with open(filepath, 'w') as f:
            f.write("# CPG RAG System Configuration\n\n")
            
            sections = {
                'Ollama Settings': ['ollama_base_url', 'ollama_model', 'ollama_embedding_model'],
                'Neo4j Settings': ['neo4j_uri', 'neo4j_user', 'neo4j_password'],
                'Analysis Settings': ['top_k_results', 'graph_context_depth', 'critical_complexity'],
                'Export Settings': ['export_directory', 'include_timestamp']
            }
            
            for section, keys in sections.items():
                f.write(f"\n# {section}\n")
                for key in keys:
                    value = getattr(self, key)
                    env_key = key.upper()
                    f.write(f"{env_key}={value}\n")


# Global configuration instance
CONFIG = SystemConfig()


def get_config() -> SystemConfig:
    """Get global configuration instance."""
    return CONFIG


def reload_config():
    """Reload configuration from environment."""
    global CONFIG
    CONFIG = SystemConfig()
    return CONFIG


if __name__ == '__main__':
    # Test configuration
    config = SystemConfig()
    print("Configuration loaded successfully!")
    print(f"  CPG nodes: {config.cpg_nodes_file}")
    print(f"  Source dir: {config.source_dir}")
    print(f"  Top-K: {config.top_k_results}")
    print(f"  Format: {config.default_response_format.value}")
