"""
Utility functions for generating mitigation guidelines from ConVerse conversation logs.
"""

import json
import os
import random
from typing import List, Dict, Any, Optional


# Tag constants for parsing LLM outputs
GUIDELINES_TAG = "GUIDELINES"
LANGUAGE_TAG = "LANGUAGE"


def get_conversation_history(conversation: List[Dict[str, Any]]) -> str:
    """
    Extract conversation history between assistant and external_agent from ConVerse format.
    
    Args:
        conversation: List of conversation turns from ConVerse output file
        
    Returns:
        Formatted conversation history string
    """
    history = ""
    for turn in conversation:
        if turn["from"] == "assistant" and turn["to"] == "external_agent":
            history += "\n\n"
            history += f"From {{AI assistant}} to {{external_agent}}: {turn['short_answer']}"
        elif turn["from"] == "external_agent" and turn["to"] == "assistant":
            history += "\n\n"
            history += f"From {{external_agent}} to {{AI assistant}}: {turn['short_answer']}"
    return history


def load_conversation_from_folder(folder_path: str) -> Optional[List[Dict[str, Any]]]:
    """
    Load conversation from a ConVerse attack/benign folder.
    
    ConVerse structure: Each attack/benign folder contains multiple repetition files.
    This function loads the first available output_*.json file.
    
    Args:
        folder_path: Path to attack or benign folder
        
    Returns:
        Conversation data (list of turns) or None if loading fails
    """
    try:
        # Get all output JSON files (not judge files)
        json_files = [
            f for f in os.listdir(folder_path)
            if f.startswith('output_') and f.endswith('.json')
        ]
        
        if not json_files:
            return None
        
        # Load the first repetition
        filepath = os.path.join(folder_path, json_files[0])
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # Handle both list and dict formats
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'conversation' in data:
                return data['conversation']
            else:
                print(f"Warning: Unexpected format in {filepath}")
                return None
    except Exception as e:
        print(f"Error loading conversation from {folder_path}: {e}")
        return None


def load_all_conversations_from_folder(folder_path: str) -> List[List[Dict[str, Any]]]:
    """
    Load ALL conversations from a ConVerse attack/benign folder.
    
    ConVerse structure: Each attack/benign folder contains multiple repetition files.
    This function loads ALL output_*.json files.
    
    Args:
        folder_path: Path to attack or benign folder
        
    Returns:
        List of conversation data (one per repetition)
    """
    conversations = []
    try:
        # Get all output JSON files (not judge files)
        json_files = [
            f for f in os.listdir(folder_path)
            if f.startswith('output_') and f.endswith('.json')
        ]
        
        for json_file in sorted(json_files):
            filepath = os.path.join(folder_path, json_file)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    # Handle both list and dict formats
                    if isinstance(data, list):
                        conversations.append(data)
                    elif isinstance(data, dict) and 'conversation' in data:
                        conversations.append(data['conversation'])
                    else:
                        print(f"Warning: Unexpected format in {filepath}")
            except Exception as e:
                print(f"Warning: Error loading {filepath}: {e}")
                continue
                
    except Exception as e:
        print(f"Error accessing folder {folder_path}: {e}")
    
    return conversations


def collect_attack_folders(
    base_path: str,
    attack_type: str,
    num_samples: Optional[int] = None,
    seed: Optional[int] = None
) -> List[str]:
    """
    Collect attack folders from ConVerse logs structure.
    
    Args:
        base_path: Path to logs/{domain}/{model}/{mode}/persona{N}/{attack_type}/
        attack_type: 'privacy' or 'security'
        num_samples: Number of attack folders to sample (None for all)
        seed: Random seed for sampling reproducibility
        
    Returns:
        List of attack folder paths
    """
    attack_dir = os.path.join(base_path, attack_type)
    
    if not os.path.exists(attack_dir):
        print(f"Warning: Attack directory not found: {attack_dir}")
        return []
    
    # Get all attack folders (exclude files)
    attack_folders = [
        os.path.join(attack_dir, f)
        for f in os.listdir(attack_dir)
        if os.path.isdir(os.path.join(attack_dir, f))
    ]
    
    # Sort for reproducibility
    attack_folders.sort()
    
    # Sample if requested
    if num_samples is not None and num_samples < len(attack_folders):
        if seed is not None:
            random.seed(seed)
        attack_folders = random.sample(attack_folders, num_samples)
    
    return attack_folders


def collect_benign_folders(base_path: str) -> List[str]:
    """
    Collect all benign simulation folders from ConVerse logs structure.
    
    Args:
        base_path: Path to logs/{domain}/{model}/{mode}/persona{N}/
        
    Returns:
        List of benign folder paths
    """
    benign_folders = []
    
    # ConVerse has benign_hard and benign_easy folders
    for benign_type in ['benign_hard', 'benign_easy']:
        benign_dir = os.path.join(base_path, benign_type)
        
        if not os.path.exists(benign_dir):
            continue
        
        # Each benign type may have a benign_simulation subfolder
        benign_sim_dir = os.path.join(benign_dir, 'benign_simulation')
        if os.path.exists(benign_sim_dir):
            benign_folders.append(benign_sim_dir)
        else:
            # Sometimes the files are directly in benign_hard/benign_easy
            benign_folders.append(benign_dir)
    
    return benign_folders


def load_conversations_from_folders(
    folder_paths: List[str],
    max_conversations: Optional[int] = None
) -> List[List[Dict[str, Any]]]:
    """
    Load ALL conversations from a list of folder paths.
    Each folder may contain multiple repetition files - all are loaded.
    
    Args:
        folder_paths: List of paths to conversation folders
        max_conversations: Maximum number of conversations to load (applied after loading all reps)
        
    Returns:
        List of conversation data
    """
    conversations = []
    
    for folder_path in folder_paths:
        # Load ALL conversations from this folder (all repetitions)
        folder_convs = load_all_conversations_from_folder(folder_path)
        conversations.extend(folder_convs)
        
        if max_conversations is not None and len(conversations) >= max_conversations:
            conversations = conversations[:max_conversations]
            break
    
    return conversations


def extract_tagged_content(text: str, tag: str) -> str:
    """
    Extract content between XML-style tags from LLM output.
    
    Args:
        text: Full LLM response text
        tag: Tag name (without angle brackets)
        
    Returns:
        Extracted content, or empty string if not found
    """
    try:
        start_tag = f"<{tag}>"
        end_tag = f"</{tag}>"
        
        if start_tag in text and end_tag in text:
            content = text.split(start_tag)[-1].split(end_tag)[0].strip()
            return content
        else:
            return ""
    except Exception as e:
        print(f"Error extracting content for tag {tag}: {e}")
        return ""
