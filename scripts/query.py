#!/usr/bin/env python3
"""
Main query orchestrator for GraphRAG code analysis.
Performs semantic retrieval, graph expansion, and LLM reasoning.
"""

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import yaml


def load_config() -> Dict[str, Any]:
    """Load configuration from config.yaml"""
    config_path = Path(__file__).parent.parent / "models" / "config.yaml"
    if config_path.exists():
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def retrieve_methods(
    question: str,
    project_name: str,
    embedding_model: SentenceTransformer,
    chromadb_dir: str,
    top_k: int = 5,
    filter_modules: bool = True
) -> List[Dict[str, Any]]:
    """
    Retrieve top-K methods from ChromaDB based on semantic similarity.
    
    Args:
        question: User's question
        project_name: Project name for ChromaDB collection
        embedding_model: Embedding model for encoding
        chromadb_dir: ChromaDB directory
        top_k: Number of methods to retrieve
        filter_modules: If True, filter out <module> entries and retrieve more to compensate
    
    Returns:
        List of method dictionaries with metadata
    """
    # Initialize ChromaDB client
    client = chromadb.PersistentClient(
        path=chromadb_dir,
        settings=Settings(anonymized_telemetry=False)
    )
    
    collection_name = f"methods_{project_name}"
    
    try:
        collection = client.get_collection(name=collection_name)
    except Exception as e:
        print(f"Error: Collection '{collection_name}' not found: {e}")
        print(f"Please run index_methods.py first to create the index")
        return []
    
    # Embed the question directly - rely on semantic similarity
    # The improved text representations in the index should handle good retrieval
    question_embedding = embedding_model.encode(question, convert_to_numpy=True)
    
    # Query more results if filtering modules to ensure we get enough non-module methods
    # Use a larger multiplier to ensure we get enough results after filtering
    query_k = top_k * 20 if filter_modules else top_k
    
    # Query ChromaDB with semantic similarity
    results = collection.query(
        query_embeddings=[question_embedding.tolist()],
        n_results=query_k,
        include=["documents", "metadatas", "distances"]
    )
    
    methods = []
    if results["ids"] and len(results["ids"][0]) > 0:
        # First pass: collect non-module methods
        for i in range(len(results["ids"][0])):
            metadata = results["metadatas"][0][i]
            method_name = metadata.get("method_name", "")
            
            # Filter out <module> and operator entries if requested
            if filter_modules:
                # Filter out low-level operators and meta methods
                if (method_name == "<module>" or 
                    method_name.startswith("<operator") or 
                    method_name.startswith("<init") or
                    method_name.startswith("<meta") or
                    method_name == "item" or
                    method_name == "keys" or
                    method_name == "t" or
                    method_name == "__iter__" or
                    method_name == "__next__" or
                    len(method_name) <= 2):  # Single letter methods are usually operators
                    continue
                
                # Filter out methods with empty or very short code (relaxed threshold)
                document = results["documents"][0][i]
                if not document or len(document.strip()) < 30:
                    continue
                
                # Filter out methods from unknown files (usually internal/operator methods)
                file_path = metadata.get("file_path", "")
                if file_path == "unknown" or not file_path:
                    continue
            
            method = {
                "id": results["ids"][0][i],
                "document": results["documents"][0][i],
                "metadata": metadata,
                "distance": results["distances"][0][i] if results["distances"] else None
            }
            methods.append(method)
            
            # Stop when we have enough non-module methods
            if len(methods) >= top_k:
                break
        
        # Second pass: if we don't have enough, include modules as fallback
        # but only if they're semantically relevant (not too far in distance)
        if len(methods) < top_k and filter_modules:
            max_distance = None
            if methods:
                # Use the worst distance from collected methods as threshold
                max_distance = max(m.get("distance", 1.0) for m in methods if m.get("distance") is not None)
                if max_distance:
                    # Be more lenient: allow 2.5x worse distance, but cap at 0.9 (more permissive)
                    max_distance = min(max_distance * 2.5, 0.9)
            else:
                # If no methods found yet, be very permissive (allow up to 0.9 distance)
                max_distance = 0.9
            
            for i in range(len(results["ids"][0])):
                if len(methods) >= top_k:
                    break
                
                metadata = results["metadatas"][0][i]
                method_name = metadata.get("method_name", "")
                distance = results["distances"][0][i] if results["distances"] else None
                
                # Apply same filtering as first pass
                if filter_modules:
                    if method_name == "<module>" or method_name.startswith("<operator") or method_name.startswith("<init"):
                        continue
                
                # Skip if already added
                if any(m["metadata"].get("method_name") == method_name for m in methods):
                    continue
                
                # Only include if distance is reasonable
                if max_distance and distance and distance > max_distance:
                    continue
                
                method = {
                    "id": results["ids"][0][i],
                    "document": results["documents"][0][i],
                    "metadata": metadata,
                    "distance": distance
                }
                methods.append(method)
    
    return methods[:top_k]


def get_graph_neighborhood(
    cpg_path: str,
    method_name: str,
    file_path: str = ""
) -> Dict[str, Any]:
    """
    Query Joern to get graph neighborhood (callers, callees, types) for a method.
    
    Returns:
        Dictionary with callers, callees, types, or empty dict on error
    """
    script_path = Path(__file__).parent.parent / "joern_scripts" / "get_graph_neighborhood.sc"
    
    if not script_path.exists():
        print(f"Error: Joern script not found at '{script_path}'")
        return {}
    
    try:
        cmd = [
            "joern",
            "--script", str(script_path),
            "--param", f"cpgFile={cpg_path}",
            "--param", f"methodName={method_name}"
        ]
        
        if file_path:
            cmd.extend(["--param", f"filePath={file_path}"])
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=60
        )
        
        # Extract JSON from output
        output = result.stdout
        start_idx = output.find('{')
        end_idx = output.rfind('}') + 1
        
        if start_idx >= 0 and end_idx > start_idx:
            json_str = output[start_idx:end_idx]
            return json.loads(json_str)
        else:
            print(f"Warning: No JSON found in Joern output")
            return {}
            
    except subprocess.CalledProcessError as e:
        print(f"Error running Joern query:")
        if e.stderr:
            print(f"  {e.stderr[:500]}")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from Joern: {e}")
        return {}
    except Exception as e:
        print(f"Unexpected error querying graph: {e}")
        return {}


def build_prompt(
    question: str,
    methods: List[Dict[str, Any]],
    graph_data: List[Dict[str, Any]],
    project_name: Optional[str] = None
) -> str:
    """
    Build a prompt for the LLM with question, code, and graph context.
    Uses a clear, instruction-following format with question-specific guidance.
    """
    prompt_parts = []
    
    # No need to detect question type - use generic prompt for all questions
    
    prompt_parts.append("You are a code analysis assistant. Answer the question directly and clearly using the provided code and relationship information.")
    prompt_parts.append("\n" + "=" * 80)
    prompt_parts.append("QUESTION")
    prompt_parts.append("=" * 80)
    prompt_parts.append(f"\n{question}\n")
    
    # Load methods JSON to get actual source code (not CPG representations)
    methods_json_data = {}
    if project_name:
        methods_json_path = Path("data") / f"methods_{project_name}.json"
        if methods_json_path.exists():
            try:
                with open(methods_json_path, 'r') as f:
                    methods_json_data = json.load(f)
            except Exception as e:
                print(f"Warning: Could not load methods JSON: {e}")
    
    # Helper to get actual source code from methods JSON
    def get_actual_source_code(metadata: Dict[str, Any], document: str) -> str:
        """Get actual source code from methods JSON if available, otherwise use document"""
        if not methods_json_data or "methods" not in methods_json_data:
            return document
        
        method_name = metadata.get('method_name', '')
        file_path = metadata.get('file_path', '')
        
        # Find matching method in JSON
        for method in methods_json_data["methods"]:
            if (method.get("methodName") == method_name and 
                method.get("filePath") == file_path):
                # Use actual source code if available
                code = method.get("code", "")
                if code and code != "<empty>" and len(code.strip()) > 30:
                    # Check if it's actual source code (not CPG representation)
                    # CPG representations often have patterns like tmp\d+, __iter__, etc.
                    if not re.search(r'tmp\d+|__iter__|__next__|manager_tmp', code):
                        return code
                break
        
        # Fallback to document, but try to extract code from it
        # The document might have "Code:\n..." format
        if "Code:\n" in document:
            code_section = document.split("Code:\n", 1)[1]
            # Take first part before next section
            if "\nCalls:" in code_section:
                code_section = code_section.split("\nCalls:")[0]
            if "\nIn:" in code_section:
                code_section = code_section.split("\nIn:")[0]
            return code_section.strip()
        
        return document
    
    # Filter methods: only include those with code and valid file path
    # Generic filtering that works for any repository
    valid_methods = []
    for method in methods:
        metadata = method.get("metadata", {})
        file_path = metadata.get('file_path', '')
        document = method.get('document', '')
        method_name = metadata.get('method_name', '')
        
        # Skip methods without file path
        if not file_path or file_path == "unknown":
            continue
        
        # Skip methods without code (or code is too short/empty)
        if not document or len(document.strip()) < 30:
            continue
        
        # Check if the code is actually meaningful (not just empty markers)
        # Look for actual code patterns like 'def ', 'class ', 'return ', etc.
        code_lower = document.lower()
        has_actual_code = (
            "def " in code_lower or 
            "class " in code_lower or 
            "return " in code_lower or
            "if " in code_lower or
            "for " in code_lower or
            "while " in code_lower or
            "=" in code_lower and "def" not in code_lower  # Assignment statements
        )
        
        # If document has multiple <empty> markers and no actual code, skip it
        if code_lower.count("<empty>") >= 2 and not has_actual_code:
            continue
        
        # Skip methods that are just internal representations (have code but not meaningful)
        # This is generic - works for any repo that uses Joern
        # Filter out meta/fake methods that are internal Joern representations
        if ("metaClassAdapter" in method_name or 
            "metaClassCallHandler" in method_name or
            method_name.startswith("<fake")):
            continue
        
        valid_methods.append(method)
    
    # If no valid methods, use all methods (fallback)
    if not valid_methods:
        valid_methods = methods
    
    # Add code sections - methods are already sorted by semantic relevance from ChromaDB
    prompt_parts.append("=" * 80)
    prompt_parts.append("RELEVANT CODE METHODS")
    prompt_parts.append("=" * 80)
    prompt_parts.append("(Methods are ordered by semantic relevance to your question)")
    prompt_parts.append("IMPORTANT: Review ALL methods below - even if a method appears later in the list, it may still be highly relevant to your question.")
    
    for i, method in enumerate(valid_methods, 1):
        metadata = method.get("metadata", {})
        file_path = metadata.get('file_path', 'unknown')
        method_name = metadata.get('method_name', 'unknown')
        
        prompt_parts.append(f"\n--- Method {i}: {method_name} ---")
        prompt_parts.append(f"File: {file_path}")
        prompt_parts.append(f"Line: {metadata.get('line_number', 'unknown')}")
        
        # Use actual source code from methods JSON instead of CPG document
        actual_code = get_actual_source_code(metadata, method.get('document', ''))
        prompt_parts.append(f"\nCode:\n{actual_code}")
    
    # Add graph neighborhood with emphasis on callers for "who calls" questions
    prompt_parts.append("\n" + "=" * 80)
    prompt_parts.append("CODE RELATIONSHIPS")
    prompt_parts.append("=" * 80)
    prompt_parts.append("IMPORTANT: The relationships below show which methods call the methods above.")
    prompt_parts.append("Pay special attention to class names and file paths in the 'Called by' section -")
    prompt_parts.append("they often reveal the main components and algorithms in the codebase.")
    #prompt_parts.append("For example, if you see 'A2C_ACKTR.update' or 'PPO.update' in the 'Called by' list,")
   # prompt_parts.append("that means A2C_ACKTR and PPO are algorithms/classes in the codebase.")
    
    # Collect all callers for summary - only for valid methods
    all_callers = []
    for i, (method, graph) in enumerate(zip(valid_methods, graph_data[:len(valid_methods)]), 1):
        if not graph.get("found", False):
            continue
        
        method_name = graph.get('methodName', 'unknown')
        metadata = method.get("metadata", {})
        file_path = metadata.get('file_path', '')
        
        # Only show graph data for methods with valid file paths
        if not file_path or file_path == "unknown":
            continue
        
        prompt_parts.append(f"\n--- Method {i}: {method_name} ---")
        
        callers = graph.get("callers", [])
        if callers:
            prompt_parts.append(f"\n✓ CALLED BY ({len(callers)}):")
            for caller in callers[:15]:  # Show more callers
                prompt_parts.append(f"  • {caller}")
                all_callers.append((method_name, caller))
        else:
            prompt_parts.append("\nCalled by: None found")
        
        callees = graph.get("callees", [])
        if callees:
            filtered_callees = [c for c in callees if not c.startswith("<operator")]
            if filtered_callees:
                prompt_parts.append(f"\nCalls ({len(filtered_callees)}):")
                for callee in filtered_callees[:10]:
                    prompt_parts.append(f"  • {callee}")
    
    # Simple, clear instructions
    prompt_parts.append("\n" + "=" * 80)
    prompt_parts.append("TASK")
    prompt_parts.append("=" * 80)
    prompt_parts.append("""
Answer the question above using the code methods and relationships provided.

Rules:
- Only use information from the methods and relationships shown above
- Extract class names, algorithm names, and file paths from the "Called by" lists in the CODE RELATIONSHIPS section
- Only mention files that appear in the "File:" lines above
- Write a direct answer without phrases like "the provided code shows" or "based on the code above"
- If information is missing, say so clearly
- The user does NOT see the code snippets or context - they only see your answer

Answer:
""")
    
    return "\n".join(prompt_parts)


def generate_answer(
    prompt: str,
    model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct",
    device: str = "cpu",
    max_length: int = 1024,
    temperature: float = 0.3
) -> str:
    """
    Generate answer using an open-source LLM.
    Uses instruction-tuned models with proper chat templates.
    """
    print(f"Loading LLM '{model_name}'...")
    
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        
        # Set pad token if not set
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token
        
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            trust_remote_code=True,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            device_map="auto" if device == "cuda" else None,
            low_cpu_mem_usage=True
        )
        
        if device == "cpu":
            model = model.to(device)
        
        print("✓ Model loaded")
        
        # Use chat template if available (for instruction models)
        if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
            messages = [{"role": "user", "content": prompt}]
            formatted_prompt = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        else:
            formatted_prompt = prompt
        
        # Tokenize with larger context window
        inputs = tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=4096  # Increased from 1024
        )
        
        if device == "cuda":
            inputs = {k: v.to(device) for k, v in inputs.items()}
        
        # Generate
        print("Generating answer...")
        sys.stdout.flush()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_length,
                temperature=temperature,
                do_sample=temperature > 0,
                top_p=0.95,
                repetition_penalty=1.1,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        # Decode - only decode the newly generated tokens (not the input)
        input_length = inputs['input_ids'].shape[1]
        generated_tokens = outputs[0][input_length:]
        answer = tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        # Clean up common artifacts and formatting
        answer = answer.replace("<|endoftext|>", "").replace("</s>", "").strip()
        answer = answer.replace("[/INST]", "").replace("<|assistant|>", "").strip()
        
        # Remove any remaining prompt artifacts
        if "YOUR ANSWER" in answer:
            answer = answer.split("YOUR ANSWER")[-1].strip()
        if "Your answer:" in answer:
            answer = answer.split("Your answer:")[-1].strip()
        
        # Remove prompt instruction fragments that might leak into the answer
        instruction_phrases = [
            "for example:",
            "avoid speculation",
            "only provide information",
            "based on the data given",
            "do not make assumptions",
            "question:",
            "to answer this question",
            "i need to identify",
            "given the current information",
            "i cannot definitively",
            "therefore, my answer is:",
            "to identify the specific",
            "calls sections",
            "avoid assumptions",
            "only include information",
            "don't guess or assume"
        ]
        # Remove lines that start with instruction phrases
        lines = answer.split('\n')
        filtered_lines = []
        for line in lines:
            line_lower = line.lower().strip()
            # Skip lines that are clearly instruction fragments
            if any(line_lower.startswith(phrase) or phrase in line_lower[:50] for phrase in instruction_phrases):
                continue
            # Skip lines that are just numbers or formatting
            if line_lower.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.', '**')):
                # Check if it's an instruction (has words like "avoid", "only", "don't")
                if any(word in line_lower for word in ['avoid', 'only', "don't", 'do not', 'include', 'provide']):
                    continue
            filtered_lines.append(line)
        answer = '\n'.join(filtered_lines).strip()
        
        # Remove instruction phrases from the beginning of the answer
        for phrase in instruction_phrases:
            if answer.lower().startswith(phrase.lower()):
                answer = answer[len(phrase):].strip()
                # Remove leading punctuation
                answer = answer.lstrip('.,:;')
                break
        
        # Filter out meta-commentary and hallucinations
        meta_phrases = [
            "Please provide the most appropriate answer",
            "Based on the given code and relationships",
            "I cannot provide",
            "I don't have enough information",
            "Please provide",
            "I need more information",
            "I would need to see",
            "Without more context",
            "USE THE INFORMATION",
            "Your task is clear",
            "Please confirm",
            "before I provide"
        ]
        for phrase in meta_phrases:
            if phrase.lower() in answer.lower():
                # Remove everything from this phrase onwards, but only if it's near the end
                idx = answer.lower().find(phrase.lower())
                # Only remove if it's in the last 30% of the answer (likely trailing meta-commentary)
                if idx > len(answer) * 0.7:
                    answer = answer[:idx].strip()
                # If it's at the start and answer is short, clear it
                elif idx < 50 and len(answer) < 200:
                    answer = ""
                break
        
        # Filter out repetitive characters (like ssssss)
        # Remove sequences of 4+ repeated characters (allow some repetition)
        answer = re.sub(r'(.)\1{3,}', '', answer)
        # Remove sequences of repeated words (but be more lenient)
        words = answer.split()
        filtered_words = []
        prev_word = None
        repeat_count = 0
        for word in words:
            if word == prev_word:
                repeat_count += 1
                if repeat_count < 3:  # Allow at most 3 repetitions
                    filtered_words.append(word)
            else:
                repeat_count = 0
                filtered_words.append(word)
                prev_word = word
        answer = " ".join(filtered_words)
        
        # Remove lines that are just instructions or meta-commentary
        lines = answer.split('\n')
        filtered_lines = []
        for line in lines:
            line_lower = line.lower().strip()
            # Skip lines that are just meta-commentary (but only if line is short)
            if len(line_lower) < 100 and any(phrase in line_lower for phrase in ["please provide the most appropriate", "based on the given code and relationships", "i cannot provide", "i don't have enough"]):
                continue
            # Skip lines that are just repeated characters (4+ same chars)
            if len(line_lower) > 5 and len(set(line_lower.replace(' ', ''))) <= 1:
                continue
            filtered_lines.append(line)
        answer = '\n'.join(filtered_lines).strip()
        
        # If answer is too short, try extracting from full response
        if len(answer) < 50:
            full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            if formatted_prompt in full_response:
                answer = full_response.split(formatted_prompt)[-1].strip()
                answer = answer.replace("<|endoftext|>", "").replace("</s>", "").strip()
        
        # If still no answer or very short, check if model generated anything
        if not answer or len(answer.strip()) < 10:
            # Try to find any generated content after the prompt
            full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            # Look for common answer patterns
            if "Your answer:" in full_response:
                answer = full_response.split("Your answer:")[-1].strip()
            elif "ANSWER" in full_response:
                parts = full_response.split("ANSWER")
                if len(parts) > 1:
                    answer = parts[-1].strip()
            else:
                # Just take everything after the prompt
                if formatted_prompt in full_response:
                    answer = full_response.split(formatted_prompt)[-1].strip()
                else:
                    answer = "Unable to generate answer. The model may need more context or the question may be too complex."
            
            # Apply filtering to extracted answer
            for phrase in meta_phrases:
                if phrase.lower() in answer.lower():
                    idx = answer.lower().find(phrase.lower())
                    if idx > len(answer) * 0.7:
                        answer = answer[:idx].strip()
                    elif idx < 50 and len(answer) < 200:
                        answer = ""
                    break
            answer = re.sub(r'(.)\1{3,}', '', answer)
        
        
        # Final check: if answer is mostly repetitive characters, reject it
        if answer:
            unique_chars = len(set(answer.replace(' ', '').replace('\n', '')))
            if len(answer) > 50 and unique_chars < 5:
                answer = "Unable to generate a clear answer. The model may need more context or the question may be too complex."
        
        # Clean up formatting issues (multiple quoted strings, etc.)
        # Remove excessive quotes and fix formatting
        answer = re.sub(r'"[^"]*"\s*"[^"]*"', lambda m: m.group(0).replace('" "', ' '), answer)  # Join adjacent quoted strings
        answer = answer.replace('" "', ' ').replace('"', '').strip()  # Remove quote artifacts
        
        # Remove incomplete sentences and fragments
        # If answer ends with incomplete phrases, remove them
        incomplete_phrases = [
            "rather than implying",
            "rather than",
            "instead of",
            "as part of",
            "in the context of",
            "which suggests",
            "which indicates"
        ]
        for phrase in incomplete_phrases:
            if answer.lower().endswith(phrase.lower()):
                # Find the last complete sentence
                sentences = answer.split('.')
                if len(sentences) > 1:
                    answer = '. '.join(sentences[:-1]).strip() + '.'
                else:
                    answer = answer[:answer.lower().rfind(phrase.lower())].strip()
                break
        
        # Remove contradictory statements
        if "no specific location was found" in answer.lower() or "no specific" in answer.lower():
            # If answer contains contradiction, try to extract the positive statement
            lines = answer.split('.')
            filtered_lines = []
            for line in lines:
                line_lower = line.lower().strip()
                if (line_lower and 
                    "no specific" not in line_lower and 
                    "not found" not in line_lower and 
                    "therefore" not in line_lower and
                    "no information" not in line_lower):
                    filtered_lines.append(line)
            if filtered_lines:
                answer = '. '.join(filtered_lines).strip()
                if answer and not answer.endswith('.'):
                    answer += '.'
        
        # Final cleanup
        answer = answer.strip()
        if not answer or len(answer) < 20:
            return "Unable to generate a clear answer. Please try rephrasing your question or providing more context."
        
        return answer
        
    except Exception as e:
        import traceback
        error_msg = f"Error generating answer: {e}"
        # If it's a memory error, suggest using CPU or a smaller model
        if "out of memory" in str(e).lower() or "cuda" in str(e).lower():
            error_msg += "\n\nSuggestion: Try using --device cpu or a smaller model like 'microsoft/phi-2'"
        print(f"\n⚠️ {error_msg}")
        if "verbose" in str(e).lower() or "debug" in str(e).lower():
            print(traceback.format_exc())
        return error_msg


def main():
    parser = argparse.ArgumentParser(
        description="Query codebase using GraphRAG (semantic retrieval + graph expansion + LLM)"
    )
    parser.add_argument(
        "--question", "-q",
        required=True,
        help="Question to answer about the codebase"
    )
    parser.add_argument(
        "--project-name", "-p",
        required=True,
        help="Project name (for ChromaDB collection)"
    )
    parser.add_argument(
        "--cpg-path",
        help="Path to CPG file (required for graph expansion)"
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of methods to retrieve (default: 5)"
    )
    parser.add_argument(
        "--embedding-model",
        default="microsoft/graphcodebert-base",
        help="Embedding model name"
    )
    parser.add_argument(
        "--llm-model",
        default="Qwen/Qwen2.5-Coder-7B-Instruct",
        help="LLM model name for reasoning (default: Qwen/Qwen2.5-Coder-7B-Instruct)"
    )
    parser.add_argument(
        "--chromadb-dir",
        default="./data/chromadb",
        help="ChromaDB directory"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM reasoning, only show retrieved code and graph data"
    )
    parser.add_argument(
        "--device",
        choices=["cpu", "cuda"],
        help="Device to use for models (overrides config.yaml)"
    )
    parser.add_argument(
        "--dump-prompt",
        help="Save the final prompt to a text file"
    )
    
    args = parser.parse_args()
    
    # Load config
    config = load_config()
    embedding_config = config.get("embedding", {})
    llm_config = config.get("llm", {})
    
    # Override with command-line args if provided
    embedding_model_name = args.embedding_model or embedding_config.get("model_name", "microsoft/graphcodebert-base")
    llm_model_name = args.llm_model or llm_config.get("model_name", "Qwen/Qwen2.5-Coder-7B-Instruct")
    device = args.device or llm_config.get("device", "cpu")
    
    # Check if CUDA is available
    if device == "cuda" and not torch.cuda.is_available():
        print("Warning: CUDA requested but not available. Falling back to CPU.")
        device = "cpu"
    
    # Get embedding device (can be overridden by --device flag)
    embedding_device = args.device or embedding_config.get("device", "cpu")
    if embedding_device == "cuda" and not torch.cuda.is_available():
        embedding_device = "cpu"
    
    print("=" * 80)
    print("GraphRAG Code Analysis Query")
    print("=" * 80)
    print(f"Question: {args.question}")
    print(f"Project: {args.project_name}")
    print(f"Device: {device} (LLM), {embedding_device} (Embeddings)")
    if device == "cuda" or embedding_device == "cuda":
        if torch.cuda.is_available():
            print(f"CUDA Device: {torch.cuda.get_device_name(0)}")
        else:
            print("Warning: CUDA not available")
    print()
    
    # Step 1: Semantic retrieval
    print("Step 1: Semantic retrieval from ChromaDB...")
    print(f"  Using device: {embedding_device} for embeddings")
    sys.stdout.flush()
    embedding_model = SentenceTransformer(embedding_model_name, device=embedding_device)
    
    methods = retrieve_methods(
        args.question,
        args.project_name,
        embedding_model,
        args.chromadb_dir,
        args.top_k
    )
    
    if not methods:
        print("Error: No methods retrieved. Please check project name and ensure indexing is complete.")
        sys.stdout.flush()
        sys.exit(1)
    
    print(f"✓ Retrieved {len(methods)} methods")
    sys.stdout.flush()
    for i, method in enumerate(methods, 1):
        metadata = method.get("metadata", {})
        print(f"  {i}. {metadata.get('method_name', 'unknown')} ({metadata.get('file_path', 'unknown')})")
    
    # Step 2: Graph expansion
    graph_data = []
    if args.cpg_path:
        print(f"\nStep 2: Graph expansion via Joern...")
        sys.stdout.flush()
        cpg_path = Path(args.cpg_path)
        if not cpg_path.exists():
            print(f"Warning: CPG file '{args.cpg_path}' not found. Skipping graph expansion.")
            sys.stdout.flush()
        else:
            for method in methods:
                metadata = method.get("metadata", {})
                method_name = metadata.get("method_name", "")
                file_path = metadata.get("file_path", "")
                
                graph = get_graph_neighborhood(str(cpg_path), method_name, file_path)
                graph_data.append(graph)
            
            print(f"✓ Retrieved graph data for {len(graph_data)} methods")
            sys.stdout.flush()
    else:
        print("\nStep 2: Skipped (no CPG path provided)")
        sys.stdout.flush()
        graph_data = [{}] * len(methods)
    
    # Step 3: Build prompt and generate answer
    if not args.no_llm:
        print(f"\nStep 3: Generating answer with LLM '{llm_model_name}'...")
        sys.stdout.flush()
        prompt = build_prompt(args.question, methods, graph_data, args.project_name)
        
        # Dump prompt to file if requested
        if args.dump_prompt:
            prompt_path = Path(args.dump_prompt)
            prompt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(prompt_path, 'w', encoding='utf-8') as f:
                f.write(prompt)
            print(f"✓ Prompt saved to '{prompt_path}'")
            sys.stdout.flush()
        
        answer = generate_answer(
            prompt,
            model_name=llm_model_name,
            device=device,
            max_length=llm_config.get("max_length", 1024),  # Reduced for better quality
            temperature=llm_config.get("temperature", 0.3)  # Lower temperature for more focused answers
        )
        
        print("\n" + "=" * 80)
        print("ANSWER")
        print("=" * 80)
        print(answer)
        sys.stdout.flush()
    else:
        print("\nStep 3: Skipped (--no-llm flag)")
        print("\nRetrieved methods and graph data:")
        for i, (method, graph) in enumerate(zip(methods, graph_data), 1):
            print(f"\n--- Method {i} ---")
            print(f"Document: {method.get('document', '')[:200]}...")
            if graph:
                print(f"Graph: {json.dumps(graph, indent=2)}")


if __name__ == "__main__":
    main()

